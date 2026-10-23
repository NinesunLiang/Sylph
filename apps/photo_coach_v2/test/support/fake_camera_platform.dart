import 'dart:async';
import 'dart:math' show Point, max;

import 'package:camera_platform_interface/camera_platform_interface.dart';
import 'package:flutter/services.dart' show DeviceOrientation;
import 'package:flutter/widgets.dart';
import 'package:plugin_platform_interface/plugin_platform_interface.dart';

/// 假相机平台 —— 让 `CameraSession` 在没有手机的情况下也能被测。
///
/// **为什么必须做这个**：
/// `CameraSession` 里最危险的那段逻辑（切摄像头、能力探测、参数降级）
/// 之前完全测不到 —— 因为 `CameraPlatform.instance` 是真实方法通道，
/// 单测环境里没有平台实现。于是「切前置摄像头死锁」这种 bug
/// 只能靠人在真机上撞出来（第 11 轮就是这么撞到的）。
///
/// 用法：
/// ```dart
/// final fake = FakeCameraPlatform(
///   cameras: [back, front],
///   // 前置摄像头不支持曝光补偿（真机华为就是这样）
///   evSupported: {frontId: false, backId: true},
/// );
/// CameraPlatform.instance = fake;
/// ```
class FakeCameraPlatform extends CameraPlatform with MockPlatformInterfaceMixin {
  FakeCameraPlatform({
    required this.cameras,
    Map<int, bool> evSupported = const {},
    Map<int, bool> zoomSupported = const {},
    Map<int, bool> flashSupported = const {},
    Map<int, bool> focusSupported = const {},
    this.failInitializeFor = const {},
    this.initializeDelay = Duration.zero,
    this.previewSize = const Size(640, 480),
  })  :
        // ⚠️ 必须拷一份成可变的。
        // 直接用 `this.evSupported = const {}` 的话，测试里想中途改
        // （模拟「查范围能成功、设的时候才失败」这个真机时序）会报
        // "Unsupported operation: Cannot modify unmodifiable map"。
        evSupported = Map<int, bool>.of(evSupported),
        zoomSupported = Map<int, bool>.of(zoomSupported),
        flashSupported = Map<int, bool>.of(flashSupported),
        focusSupported = Map<int, bool>.of(focusSupported);

  final List<CameraDescription> cameras;

  /// cameraId → 是否支持设置曝光补偿
  final Map<int, bool> evSupported;
  final Map<int, bool> zoomSupported;
  final Map<int, bool> flashSupported;
  final Map<int, bool> focusSupported;

  /// 这些 cameraId 的 initializeCamera 会抛异常（模拟设备打不开）
  final Set<int> failInitializeFor;

  /// 模拟初始化很慢（用来验证超时兜底）
  final Duration initializeDelay;

  final Size previewSize;

  /// 运行时改某台设备是否支持 EV。
  ///
  /// 为什么要能改：真机上常见的是「**查**范围能成功、**设**的时候才失败」
  /// （华为 OCE-AN50 就是这样，抛 setExposureOffsetFailed）。
  /// 只有支持"先放行、后失败"的时序，才能测出「失败即降级」这条逻辑。
  void setEvSupported(int cameraId, bool supported) =>
      evSupported[cameraId] = supported;

  /// 记录调用，便于断言「有没有按预期释放/切换」
  final List<String> calls = [];
  final Set<int> liveCameraIds = {};
  int _nextId = 1;

  // ---- 给「真机那个坑」用的两个钩子 ----

  /// 按方法名注入**精确的错误**（key 例如 `setFocusMode` / `setExposureOffset`）。
  ///
  /// 为什么需要：真机上报回来的错误码是 Java 异常名
  /// （华为 OCE-AN50 设「对焦锁定」抛的是 `IllegalArgumentException`），
  /// 用 `focusSupported:false` 那种开关造不出这个码，也就测不到分类逻辑。
  final Map<String, CameraException> customFailures = {};

  /// `setExposureOffset` 的模拟耗时 —— 用来**制造并发窗口**，
  /// 验证连续拖滑块时不会并发提交（并发会被 CameraX 取消，
  /// 进而被误判成「设备不支持 EV」）。
  Duration exposureDelay = Duration.zero;

  /// 每个方法的并发峰值：断言「没有被并发调用」时就看它。
  final Map<String, int> maxInFlight = {};
  final Map<String, int> _inFlight = {};

  void _enter(String call) {
    final n = (_inFlight[call] ?? 0) + 1;
    _inFlight[call] = n;
    maxInFlight[call] = max(maxInFlight[call] ?? 0, n);
  }

  void _leave(String call) => _inFlight[call] = (_inFlight[call] ?? 1) - 1;

  /// 注入的错误优先于各 supported 开关。
  void _maybeThrow(String call) {
    final e = customFailures[call];
    if (e != null) throw e;
  }

  // ---- 核心：创建 / 初始化 / 释放 ----

  @override
  Future<List<CameraDescription>> availableCameras() async {
    calls.add('availableCameras');
    return cameras;
  }

  @override
  Future<int> createCameraWithSettings(
    CameraDescription description,
    MediaSettings? mediaSettings,
  ) async {
    final id = _nextId++;
    calls.add('createCamera#${description.name}');
    return id;
  }

  @override
  Future<int> createCamera(
    CameraDescription description,
    ResolutionPreset? resolutionPreset, {
    bool enableAudio = false,
  }) =>
      createCameraWithSettings(description, null);

  @override
  Future<void> initializeCamera(
    int cameraId, {
    ImageFormatGroup imageFormatGroup = ImageFormatGroup.unknown,
  }) async {
    calls.add('initializeCamera#$cameraId');
    if (failInitializeFor.contains(cameraId)) {
      throw CameraException('CameraAccessDenied', '这台设备打不开（测试构造）');
    }
    if (initializeDelay > Duration.zero) {
      await Future<void>.delayed(initializeDelay);
    }
    liveCameraIds.add(cameraId);

    // ⚠️ 必须先 await 一个异步间隔，再推事件。
    //
    // 为什么：真机上事件是**异步**从平台过来的。而 CameraController 的顺序是
    //   unawaited(onCameraInitialized(id).first.then(...))  ← 先订阅
    //   await initializeCamera(id)                           ← 再初始化
    //   await initializeCompleter.future                      ← 等事件
    // 如果在这里**同步** add 事件：
    //   · 订阅可能还没挂上（broadcast 流不缓冲）→ 事件直接丢；
    //   · `_initialized[id]?.add(...)` 里那个 `?.` 把 null 静默吃掉，
    //     于是 `.first` 永远等不到，报 "Bad state: No element"。
    // 我第一版就是这么写的，被测试抓出来了 —— 这就是 mock 的价值。
    //
    // 用 1ms 而不是 Duration.zero：`.first` 在 broadcast 流上注册监听
    // 本身要跨一个事件循环回合（Stream.first 是先监听、收到事件后再
    // 异步 cancel）。Duration.zero 有时抢在监听之前，实测仍会丢事件。
    // 真机上平台回事件本来就有延迟（几毫秒到几十毫秒），1ms 是合理模拟。
    await Future<void>.delayed(const Duration(milliseconds: 1));

    // 平台实现必须主动推这个事件，CameraController 才能完成初始化
    // ⚠️ 参数顺序容易记错（我第一版就写反了 bool 和 FocusMode 的位置）：
    // (cameraId, previewWidth, previewHeight, exposureMode,
    //  exposurePointSupported, focusMode, focusPointSupported)
    _ctl(cameraId).add(CameraInitializedEvent(
      cameraId,
      previewSize.width,
      previewSize.height,
      ExposureMode.auto,
      true,
      FocusMode.auto,
      true,
    ));
  }

  @override
  Future<void> dispose(int cameraId) async {
    calls.add('dispose#$cameraId');
    liveCameraIds.remove(cameraId);
    await _initialized[cameraId]?.close();
    _initialized.remove(cameraId);
  }

  // ---- 事件流 ----

  final Map<int, StreamController<CameraInitializedEvent>> _initialized = {};

  /// 诊断用：这个 cameraId 的事件控制器建出来了吗。
  bool debugHasController(int id) => _initialized.containsKey(id);

  StreamController<CameraInitializedEvent> _ctl(int id) =>
      _initialized.putIfAbsent(
          id, () => StreamController<CameraInitializedEvent>.broadcast());

  @override
  Stream<CameraInitializedEvent> onCameraInitialized(int cameraId) =>
      _ctl(cameraId).stream;

  /// ⚠️ **不能**返回 `Stream.empty()`！
  ///
  /// camera 插件里有这么一段：
  /// ```dart
  /// unawaited(onCameraError(id).first.then((e) {...}));
  /// ```
  /// 对**空流**调用 `.first` 会立刻抛 `Bad state: No element`。
  /// 我第一版就是 `Stream.empty()`，结果每次初始化都炸，
  /// 报错还指向 `initializeCompleter.future`（`camera_controller.dart:359`），
  /// **看起来像是初始化事件没发出来，实际是错误流先炸了** ——
  /// 这个错误信息的方向性误导让我多查了两轮。
  ///
  /// 正确做法：给一个**一直开着、不发任何事件**的流，
  /// 这样 `.first` 会安静地等待（真机上没错误时就是这样）。
  @override
  Stream<CameraErrorEvent> onCameraError(int cameraId) =>
      _errors.putIfAbsent(cameraId,
          () => StreamController<CameraErrorEvent>.broadcast()).stream;

  final Map<int, StreamController<CameraErrorEvent>> _errors = {};

  /// 测试里手动推一个错误事件（模拟设备报错）。
  void emitError(int cameraId, String description) =>
      _errors.putIfAbsent(cameraId,
          () => StreamController<CameraErrorEvent>.broadcast())
        ..add(CameraErrorEvent(cameraId, description));

  /// 关闭事件流：同样不能返回空流（原因见 onCameraError 的注释）。
  @override
  Stream<CameraClosingEvent> onCameraClosing(int cameraId) =>
      _closing.putIfAbsent(cameraId,
          () => StreamController<CameraClosingEvent>.broadcast()).stream;

  final Map<int, StreamController<CameraClosingEvent>> _closing = {};

  @override
  Stream<DeviceOrientationChangedEvent> onDeviceOrientationChanged() =>
      _orientation.stream;

  final StreamController<DeviceOrientationChangedEvent> _orientation =
      StreamController<DeviceOrientationChangedEvent>.broadcast();

  /// 分辨率变化流：同上，不能是空流。
  @override
  Stream<CameraResolutionChangedEvent> onCameraResolutionChanged(int cameraId) =>
      _resolution.putIfAbsent(cameraId,
          () => StreamController<CameraResolutionChangedEvent>.broadcast())
          .stream;

  final Map<int, StreamController<CameraResolutionChangedEvent>> _resolution =
      {};

  // ---- 能力查询（每个 cameraId 可独立配置）----

  @override
  Future<double> getMinExposureOffset(int cameraId) async {
    if (evSupported[cameraId] == false) {
      throw CameraException('setExposureOffsetFailed', '这台不支持测光范围');
    }
    return -2.0;
  }

  @override
  Future<double> getMaxExposureOffset(int cameraId) async {
    if (evSupported[cameraId] == false) {
      throw CameraException('setExposureOffsetFailed', '这台不支持测光范围');
    }
    return 2.0;
  }

  @override
  Future<double> getExposureOffsetStepSize(int cameraId) async => 0.1;

  @override
  Future<double> getMinZoomLevel(int cameraId) async {
    if (zoomSupported[cameraId] == false) {
      throw CameraException('zoomLevelNotSupported', '不支持变焦');
    }
    return 1.0;
  }

  @override
  Future<double> getMaxZoomLevel(int cameraId) async {
    if (zoomSupported[cameraId] == false) {
      throw CameraException('zoomLevelNotSupported', '不支持变焦');
    }
    return 8.0;
  }

  // ---- 参数设置 ----

  @override
  Future<double> setExposureOffset(int cameraId, double offset) async {
    _enter('setExposureOffset');
    try {
      calls.add('setExposureOffset#$cameraId=$offset');
      _maybeThrow('setExposureOffset');
      if (exposureDelay > Duration.zero) {
        await Future<void>.delayed(exposureDelay);
      }
      if (evSupported[cameraId] == false) {
        // 真机华为 OCE-AN50 抛的就是这个码
        throw CameraException('setExposureOffsetFailed', '设不了曝光补偿');
      }
      return offset;
    } finally {
      _leave('setExposureOffset');
    }
  }

  @override
  Future<void> setExposureMode(int cameraId, ExposureMode mode) async {
    calls.add('setExposureMode#$cameraId');
  }

  @override
  Future<void> setExposurePoint(int cameraId, Point<double>? point) async {
    calls.add('setExposurePoint#$cameraId');
  }

  @override
  Future<void> setZoomLevel(int cameraId, double zoom) async {
    calls.add('setZoomLevel#$cameraId=$zoom');
    if (zoomSupported[cameraId] == false) {
      throw CameraException('zoomLevelNotSupported', '设不了变焦');
    }
  }

  @override
  Future<void> setFlashMode(int cameraId, FlashMode mode) async {
    calls.add('setFlashMode#$cameraId');
    if (flashSupported[cameraId] == false) {
      throw CameraException('torchModeNotSupported', '没有闪光灯');
    }
  }

  @override
  Future<void> setFocusMode(int cameraId, FocusMode mode) async {
    _enter('setFocusMode');
    try {
      calls.add('setFocusMode#$cameraId');
      _maybeThrow('setFocusMode');
      if (focusSupported[cameraId] == false) {
        throw CameraException('focusModeNotSupported', '不支持对焦模式');
      }
    } finally {
      _leave('setFocusMode');
    }
  }

  @override
  Future<void> setFocusPoint(int cameraId, Point<double>? point) async {
    calls.add('setFocusPoint#$cameraId');
  }

  @override
  Future<XFile> takePicture(int cameraId) async {
    calls.add('takePicture#$cameraId');
    // 返回一个不存在的路径即可 —— 测试里只会调 readAsBytes 之外的逻辑
    return XFile('/tmp/fake-${DateTime.now().microsecondsSinceEpoch}.jpg');
  }

  @override
  Future<void> lockCaptureOrientation(
          int cameraId, DeviceOrientation orientation) async {}

  @override
  Future<void> unlockCaptureOrientation(int cameraId) async {}

  @override
  Widget buildPreview(int cameraId) => const SizedBox.shrink();
}
