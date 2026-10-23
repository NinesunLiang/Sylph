import 'dart:async';
import 'dart:ui' show Offset;

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';

import '../guidance/live_guide_controller.dart' show LiveFrameSource;
import 'photo_saver.dart';

/// F1 相机会话：把「官方插件能给的能力」和「给不了的能力」显式分开。
///
/// 已对照 **实际安装的插件源码** 核对（camera 0.12.1 / camera_platform_interface 2.14.0，
/// 路径 `.tooling/pub-cache/hosted/pub.dev/camera-0.12.1/lib/src/camera_controller.dart`）：
///
/// 本会话只管**取景对位**要用的能力：`setExposureMode`（自动曝光）/
/// `setFocusMode` / `setFocusPoint` / `setExposurePoint`。
///
/// **EV / 变焦 / 闪光灯一概不管**（2026-10-11 三模块职责重构删除）：
/// 出片在系统相机里，App 内预览调这些参数对最终照片没有影响；
/// 参数的建议与解释归教练模块。
///
/// 插件**不提供**手动 ISO 和手动快门 —— 这就是 [canManualIso] 恒为 false 的原因。
///
/// 重要：`FocusMode` 只有 `auto` 和 `locked` 两个值（源码
/// `camera_platform_interface-2.14.0/lib/src/types/focus_mode.dart`），
/// 没有 single/continuous，别照抄旧文档。
class CameraSession extends ChangeNotifier implements LiveFrameSource {
  CameraSession({this.saver = const GalleryPhotoSaver()});

  /// 拍完把照片交存到相册。默认走真实插件（gal）；测试里注入假实现。
  final PhotoSaver saver;

  CameraController? _controller;
  List<CameraDescription> _cameras = const [];
  String? _error;

  /// 中性提示（比如「本平台不支持某项参数」）—— 不是错误，UI 用灰色显示。
  String? _note;

  /// 非致命警告（比如「这一次某项参数没设上」）—— 相机还能用，
  /// UI 用琥珀色挂一条，**绝不**替换整页预览。
  ///
  /// 为什么要和 [_error] 分开：真机实测，华为 OCE-AN50 上把对焦模式设为
  /// 「锁定」会抛 `IllegalArgumentException`。旧代码把它记进 `_error`，
  /// 于是整页变成「相机没能用起来」、预览直接消失 —— 其实相机好好的，
  /// 只是那一个参数没设上，用户却被吓得以为相机坏了。
  String? _warning;
  bool _initializing = false;

  /// 正在做的事（「正在找摄像头…」「正在打开…」）。
  /// 为什么要它：卡住时用户只看到一个转圈，不知道卡在哪一步。
  String _progress = '';

  /// 卡住的秒数（超过阈值 UI 会提示「可能不支持」）。
  int _stuckSeconds = 0;
  bool _stuck = false;

  /// 初始化期间的心跳定时器。必须存成字段并在 dispose 时清掉 ——
  /// 否则「widget 树已销毁但定时器还在跑」，测试会报
  /// "A Timer is still pending"，真机上也是资源泄漏。
  Timer? _ticker;

  // 当前参数 —— 只剩对焦（EV/变焦/闪光灯已随参数模块一起删除）。
  FocusMode _focusMode = FocusMode.auto;
  Offset? _focusPoint;

  bool _capabilitiesLoaded = false;

  // 逐项标记「这台设备到底能不能用」。
  // 为什么要逐项：以前是一个大 try，任何一个查失败就**全部**退回默认值，
  // 实测：华为 OCE-AN50 上 setFocusMode 会抛异常，逐项标记后其余能力不受牵连。
  bool _canSetFocus = false;
  bool _canSetExposureMode = false;

  CameraController? get controller => _controller;
  List<CameraDescription> get cameras => _cameras;
  String? get error => _error;
  String? get note => _note;

  /// 非致命警告 —— 相机还能用，只是某项操作没成功。
  String? get warning => _warning;
  bool get initializing => _initializing;
  String get progress => _progress;

  /// 初始化超时了（可能这台设备的浏览器/系统不让用摄像头）。
  bool get stuck => _stuck;
  int get stuckSeconds => _stuckSeconds;
  bool get isReady => _controller?.value.isInitialized ?? false;
  bool get capabilitiesLoaded => _capabilitiesLoaded;

  /// 这台设备的摄像头实际支持哪些能力（UI 据此灰掉不可用的控件）。
  bool get canSetFocus => _canSetFocus;
  bool get canSetExposureMode => _canSetExposureMode;

  /// 有没有任何一项设不上（UI 用来显示一行中性说明）。
  bool get hasLimitedCapabilities =>
      _capabilitiesLoaded &&
      !(_canSetFocus && _canSetExposureMode);

  FocusMode get focusMode => _focusMode;
  Offset? get focusPoint => _focusPoint;

  /// 官方插件无此能力 —— UI 必须显示为「不可用」，不能假装能调。
  bool get canManualIso => false;
  bool get canManualShutter => false;

  /// 单步超时。为什么要它：Web（和某些设备）上相机初始化可能**永远不返回**，
  /// 之前没有超时，界面就永久锁在一个转圈上，用户以为 App 死了。
  static const _stepTimeout = Duration(seconds: 12);

  Future<void> initialize({
    CameraLensDirection preferred = CameraLensDirection.back,
  }) async {
    _initializing = true;
    _error = null;
    _stuck = false;
    _stuckSeconds = 0;
    _progress = '正在查找摄像头…';
    notifyListeners();

    // 重试/切前后台时，上一个控制器可能还在占着摄像头。
    // 不先释放就会卡住 —— 这是「点重试后一直转圈」的直接原因。
    await _releaseController();

    // 每秒更新「卡了多少秒」，让 UI 能提示用户
    _ticker?.cancel();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!_initializing) return;
      _stuckSeconds++;
      if (_stuckSeconds >= 12 && !_stuck) {
        _stuck = true;
      }
      notifyListeners();
    });

    try {
      final cams = await availableCameras().timeout(_stepTimeout);
      _cameras = cams;
      if (_cameras.isEmpty) {
        _error = '没有找到可用摄像头';
        return;
      }
      final desc = _cameras.firstWhere(
        (c) => c.lensDirection == preferred,
        orElse: () => _cameras.first,
      );
      _progress = '正在打开摄像头…';
      notifyListeners();
      await _open(desc).timeout(_stepTimeout);
    } on TimeoutException {
      _error = '相机启动超时（超过 ${_stepTimeout.inSeconds} 秒没反应）。'
          '这台设备/浏览器可能不允许网页使用摄像头。';
    } catch (e) {
      // iOS 模拟器没有摄像头、Web 权限被拒 —— 都会走到这里
      _error = '相机初始化失败：$e';
    } finally {
      _ticker?.cancel();
      _ticker = null;
      _initializing = false;
      _progress = '';
      notifyListeners();
    }
  }

  /// 交出摄像头，但**不销毁自己**（前后台切换用）。
  ///
  /// 为什么要有这个方法：`dispose()` 的语义是「这个对象不要了」，
  /// 而进后台只是「先把摄像头交出去，回前台还要用」—— 这两件事必须分开。
  ///
  /// 之前页面在 `inactive` 时直接 `dispose()` 了会话，回前台又
  /// `initialize()`：对已销毁的 `ChangeNotifier` 调用会断言失败、
  /// 页面再也收不到通知（实测：拉一下通知栏，拍摄页就永久卡死）。
  Future<void> releaseCamera() async {
    await _releaseController();
    _capabilitiesLoaded = false;
    notifyListeners();
  }

  /// 打开某个摄像头。
  ///
  /// ⚠️ 必须**先释放旧的、再建新的**。
  /// 之前是先建新的、后放旧的，在华为等把摄像头当独占资源的设备上，
  /// 两个 CameraController 同时存在会让 `initialize()` 永远不返回
  /// （实测：切前置 / 点重试 之后就无限转圈）。这是真机才暴露的问题。
  Future<void> _open(CameraDescription desc) async {
    await _releaseController();

    final next = CameraController(
      desc,
      // ⚠️ 用户真机反馈（v0.4.0 电话测试）：预览左右留黑边。
      // 根因在插件的 preset 映射（camera_android_camerax）：
      //   high   → 1280×720 + 强制 16:9
      //   medium → 720×480，不锁比例（设备可能回 16:9）
      //   low    → 320×240 + **强制 4:3**（ratio4To3）
      // 之前用 high：流是 16:9，竖屏预览区里 contain 居中 = 中间一条 9:16、
      // 左右黑边。改 low 后 CameraX 被强制回 4:3 的流（设备实际多半给
      // 640×480 档，清晰度够用）→ 预览永远全宽、只剩上下边（正常相机观感），
      // 而且和系统相机的 4:3 画面一致 —— 预览页的核心职责是姿势对位，
      // 取景范围必须和系统相机出片一致，否则用户照 16:9 预览摆姿势、
      // 出片却是 4:3，对位全错。
      // 清晰度权衡：v0.4.0 出片走系统相机，本流只用于取景/姿势叠加/
      // 点按对焦/EV 预览，640×480 足够。
      ResolutionPreset.low,
      enableAudio: false,
    );
    await next.initialize();
    _controller = next;
    _capabilitiesLoaded = false;
    await _loadCapabilities();
    await applyAll();
  }

  /// 释放当前控制器（幂等）。
  Future<void> _releaseController() async {
    final old = _controller;
    _controller = null;
    if (old == null) return;
    try {
      await old.dispose();
    } catch (_) {
      // 释放失败不该阻断后续流程（设备已经没了之类的）
    }
  }

  /// 相机支持的范围是**异步查**出来的，不是 CameraValue 上的同步字段
  @override
  void dispose() {
    _ticker?.cancel();
    _ticker = null;
    _controller?.dispose();
    _controller = null;
    super.dispose();
  }

  /// 逐项探测能力。对焦 / 曝光模式没有「查询范围」的接口，
  /// 先当作可用，真设的时候失败了再翻掉（见 applyAll）。
  Future<void> _loadCapabilities() async {
    final c = _controller;
    if (c == null || !c.value.isInitialized) return;

    _canSetFocus = true;
    _canSetExposureMode = true;

    // 走到这里说明这项探测流程跑完了。
    _capabilitiesLoaded = true;
  }

  /// 把当前参数一次性套到相机上（自动调参也是调这个）。
  ///
  /// ⚠️ **必须串行化 + 合并**。为什么：滑块拖动会连着触发很多次 `applyAll`，
  /// 并发地向 CameraX 提交请求会让它取消前一个请求
  /// （CameraX 的 "a new request was submitted"）；而插件 Dart 层把
  /// 「被取消」翻译成 `setExposureOffsetFailed`（Java 侧本来当成功处理，
  /// 见 `CameraControlProxyApi.java` 里 `OperationCanceledException` 分支），
  /// App 又把这个码归成「这台设备不支持 EV」→ 滑块**永久置灰**。
  /// 真机现象（华为 OCE-AN50）：「拖一下曝光补偿，就再也不能调了」。
  Future<void> applyAll() async {
    if (_applying) {
      _applyQueued = true;
      return;
    }
    _applying = true;
    try {
      do {
        _applyQueued = false;
        await _applyAllOnce();
      } while (_applyQueued);
    } finally {
      _applying = false;
    }
  }

  /// 是否有一次 applyAll 正在执行。
  bool _applying = false;

  /// 执行期间又有人要求 apply —— 合并成「跑完再来一轮」，不并发。
  bool _applyQueued = false;

  /// 每个参数**单独 try**：某个平台不支持其中一项（比如 Web 上没有
  /// setExposureMode），不该让其余参数也一起失效，更不该往界面上抛一个
  /// 「参数应用失败」吓用户。
  Future<void> _applyAllOnce() async {
    final c = _controller;
    if (c == null || !c.value.isInitialized) return;

    final unsupported = <String>[];
    final failed = <String>[];

    /// 尝试设置一项。失败时**翻掉对应能力标记** —— 下次不再试，
    /// 用户也不会每动一下就再看到一次报错。
    Future<void> attempt(
      String name,
      Future<void> Function() call, {
      void Function()? markUnsupported,
    }) async {
      try {
        await call();
      } on UnimplementedError {
        unsupported.add(name);
        markUnsupported?.call();
      } on CameraException catch (e) {
        if (isTransientCameraError(e)) {
          // 临时失败（被后一个请求取消 / 相机刚好关了一下）：
          // **不**翻能力标记、也**不**当故障 —— 下一次操作自然会重试。
          // 翻掉的话控件会被永久置灰，用户以为设备不支持。
          return;
        }
        if (isCameraCapabilityMissingCode(e.code)) {
          unsupported.add(name);
          markUnsupported?.call();
        } else {
          failed.add('$name（${e.code}）');
        }
      } catch (_) {
        failed.add(name);
      }
    }

    if (_canSetExposureMode) {
      await attempt('曝光模式', () => c.setExposureMode(ExposureMode.auto),
          markUnsupported: () => _canSetExposureMode = false);
    }
    if (_canSetFocus) {
      if (_focusPoint != null) {
        await attempt('对焦点', () => c.setFocusPoint(_focusPoint),
            markUnsupported: () => _canSetFocus = false);
        await attempt('测光点', () => c.setExposurePoint(_focusPoint));
      } else {
        await attempt('对焦模式', () => c.setFocusMode(_focusMode),
            markUnsupported: () => _canSetFocus = false);
      }
    }

    _lastUnsupported = unsupported;

    if (failed.isNotEmpty) {
      // 真的出错了：**但只是某些参数没设上，相机还是好的** ——
      // 所以挂一条琥珀色警告，保持预览可用。
      // （旧代码在这里写 `_error`，页面会把整块预览换成错误框：
      //   真机实测「对焦：锁定」抛 IllegalArgumentException 就是这样，
      //   用户看到「相机没能用起来」，其实相机一直在正常工作。）
      _warning = '这些设置没能生效：${failed.join("、")}。'
          '预览仍可用，也可以换个摄像头试试。';
      _note = null;
    } else if (unsupported.isNotEmpty) {
      _warning = null;
      _note = '这台设备的摄像头不支持：${unsupported.join("、")}'
          '（其余参数正常，界面上的对应控件已置灰）';
    } else {
      _warning = null;
      _note = null;
    }
    notifyListeners();
  }

  /// 最近一次被判定为「设备不支持」的参数名。
  List<String> get lastUnsupported => _lastUnsupported;
  List<String> _lastUnsupported = const [];

  // ---------------------------------------------------------------------
  // 设置公开接口（只剩对焦相关；EV/变焦/闪光 setter 已随参数模块删除）
  // ---------------------------------------------------------------------

  Future<void> setFocusMode(FocusMode mode) async {
    _focusMode = mode;
    _focusPoint = null; // 回到自动对焦就清掉手动点
    notifyListeners();
    await applyAll();
  }

  /// 点屏幕对焦 + 测光。[p] 是归一化坐标（0–1）。
  Future<void> tapToFocus(Offset p) async {
    _focusPoint = Offset(p.dx.clamp(0.0, 1.0), p.dy.clamp(0.0, 1.0));
    notifyListeners();
    await applyAll();
  }

  /// 拍一张。相机没准备好 / 正忙时返回 null，不抛异常。
  Future<XFile?> takePicture() async {
    final c = _controller;
    if (c == null || !c.value.isInitialized) return null;
    if (c.value.isTakingPicture) return null;
    try {
      return await c.takePicture();
    } catch (e) {
      // 拍一张失败**不是**「相机坏了」—— 不能把整页预览换成错误框。
      _warning = '这张没拍成：$e';
      notifyListeners();
      return null;
    }
  }

  /// 相机当前是否正忙（正在拍照）。实时引导要避开这个时刻。
  bool get isBusy => _controller?.value.isTakingPicture ?? false;

  /// 拍一张并**存进系统相册** —— 快门按钮走的是这条路径。
  ///
  /// ⚠️ 为什么不把「存相册」直接塞进 [takePicture]：
  /// 实时引导每秒都会调 [grabFrame] → [takePicture] 去取帧分析。
  /// 在那里顺手存相册的话，用户开一分钟引导就会往相册里灌上百张废照片。
  /// 所以「取帧」和「用户按下快门」必须是两条路径，这里用测试锁住。
  Future<XFile?> captureAndSave() async {
    final file = await takePicture();
    if (file == null) return null;
    await _saveToGallery(file);
    return file;
  }

  /// 最近一次拍照有没有成功存进相册（`null` = 还没拍过）。
  bool? get lastShotSaved => _lastShotSaved;
  bool? _lastShotSaved;

  Future<void> _saveToGallery(XFile file) async {
    try {
      await saver.save(file.path);
      _lastShotSaved = true;
      // 上一次的存档警告已经过时，清掉（否则会一直挂在界面上）
      if (_warning?.startsWith('照片没能存进相册') ?? false) _warning = null;
    } on PhotoSaveException catch (e) {
      _lastShotSaved = false;
      _warning = '照片没能存进相册：${e.message}';
    } catch (e) {
      _lastShotSaved = false;
      _warning = '照片没能存进相册：$e';
    }
    notifyListeners();
  }

  // ---- LiveFrameSource 实现（给实时引导用）----

  @override
  bool get ready => isReady;

  @override
  bool get busy => isBusy;

  @override
  Future<Uint8List?> grabFrame() async {
    final file = await takePicture();
    if (file == null) return null;
    return file.readAsBytes();
  }

  Future<void> switchCamera() async {
    if (_cameras.length < 2 || _controller == null) return;
    final current = _controller!.description;
    final next = _cameras.firstWhere(
      (c) => c.lensDirection != current.lensDirection,
      orElse: () => current,
    );

    _initializing = true;
    _error = null;
    _progress = next.lensDirection == CameraLensDirection.front
        ? '正在切换到前置摄像头…'
        : '正在切换到后置摄像头…';
    notifyListeners();

    try {
      await _open(next).timeout(_stepTimeout);
      _note = null;
    } on TimeoutException {
      _error = '切换摄像头超时（${_stepTimeout.inSeconds} 秒没反应）。'
          '这台设备的前置摄像头可能不支持当前的设置。';
    } catch (e) {
      _error = '切换摄像头失败：$e';
    } finally {
      _initializing = false;
      _progress = '';
      notifyListeners();
    }
  }

}


/// 判断一个 CameraException 的错误码是不是「这台设备/平台不支持」。
///
/// 为什么单独抽出来：这是**纯逻辑**，可以单测；
/// 而「切摄像头、改参数」这些必须真机才能试。
/// 实测华为/浏览器会抛这些码：zoomLevelNotSupported、torchModeNotSupported、
/// focusModeNotSupported…，它们都表示「能力缺失」，不是「故障」。
bool isUnsupportedCameraErrorCode(String code) {
  final c = code.toLowerCase();
  return c.contains('notsupported') ||
      c.contains('unsupported') ||
      c.contains('not_supported');
}

/// 判断一个错误码是否表示「这台设备做不到这件事」。
///
/// 为什么不能只判 `NotSupported`：
/// 真机实测华为 OCE-AN50 在设曝光补偿时抛的是 **`setExposureOffsetFailed`** ——
/// 里面没有 `NotSupported` 字样。如果只按字面判断，它会被归成「故障」，
/// 于是整页报红「相机没能用起来」，而实际上只是**这台机器不支持调 EV**。
///
/// 所以：`xxxFailed` / `NotAvailable` / `InvalidArgument` 这类在相机参数设置
/// 场景下，一律按「能力缺失」处理 —— 表现是**控件置灰**，而不是红色报错。
/// 宁可少报一个错，也不要把「设备不支持」渲染成「App 坏了」。
bool isCameraCapabilityMissingCode(String code) {
  if (isUnsupportedCameraErrorCode(code)) return true;
  final c = code.toLowerCase();
  return c.endsWith('failed') ||
      c.contains('failed') ||
      c.contains('notavailable') ||
      c.contains('not_available') ||
      c.contains('notsupported') ||
      c.contains('invalidargument') ||
      c.contains('invalid_argument') ||
      // ⚠️ 真机实测：华为 OCE-AN50 上 `setFocusMode(FocusMode.locked)` 抛的是
      // Java 异常名 **`IllegalArgumentException`**（Pigeon 把 Java 异常的
      // 类名直接当成错误码传回来）。它拼写是 "illegal" 而不是 "invalid"，
      // 所以上面那条 `invalidargument` 匹配不到 → 被误判成「故障」→
      // 整页变错误框。这里补上。
      c.contains('illegalargument') ||
      c.contains('illegal_argument') ||
      c.contains('illegalstate');
}

/// 这次失败是不是「临时的」—— 被后一个请求取消、或相机刚好关了一下？
///
/// 为什么必须区分：插件 Dart 层把 CameraX 的 `OperationCanceledException`
/// 翻译成 `setExposureOffsetFailed`（Java 侧 `CameraControlProxyApi.java`
/// 里那个分支本来是当**成功**处理的：`ResultCompat.success(null, callback)`，
/// 然后是 Dart 侧看到 `newIndex == null` 才抛的错）。
/// 如果我们把它当成「这台设备不支持 EV」，滑块会被**永久置灰** ——
/// 真机现象就是「拖一下曝光补偿，就再也不能调了」。
bool isTransientCameraError(CameraException e) {
  // ⚠️ 字段名是 `description` 不是 `message`
  // （camera_platform_interface-2.14.0/lib/src/types/camera_exception.dart:8）。
  final m = (e.description ?? '').toLowerCase();
  return m.contains('cancel') ||
      m.contains('closed') ||
      m.contains('new request');
}
