import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../app_session.dart';
import '../analysis/distance_advisor.dart';
import '../analysis/face_detector.dart';

import '../analysis/yunet_backend.dart';
import '../coach/offline_tip_engine.dart';
import '../coach/suggestion.dart';

import '../guidance/live_guide_controller.dart';
import '../poses/pose.dart';
import '../poses/pose_guidance_text.dart';
import '../settings/settings_page.dart';
import 'camera_session.dart';

/// 拍摄页 —— **唯一职责：配合姿势取景对位，好了就跳系统相机拍**。
///
/// 产品流程（人类原话）：预览时用参考照对齐位置/pose，
/// 都调好了 → 点快门 → 拉起**系统相机**（本 App 静默退后台）→
/// 拍完回来，App 自动捞出那张照片展示，一键送教练点评。
///
/// 为什么跳系统相机：系统相机的算法（HDR/对焦/连拍）和取景能力更强，
/// 且照片直接进用户自己的相册；App 内的预览负责"对位"，不负责出片。
///
/// **本页不管拍摄参数**（EV/变焦/闪光灯/ISO/快门）：参数是教练（镜头语言）
/// 的事，而且 App 内预览的参数改不到最终出片（出片在系统相机里），
/// 所以 2026-10-11 起本页**不残留任何参数控件**（三件套已删）。
/// 右上角齿轮 → 设置（模型 API Key）。
///
/// 已完成：实时预览、**实时虚拟引导**（F2.11/F2.12，纯本地）、
///   系统相机桥（v0.4.0，原生侧见 android MainActivity）。
class CameraPage extends StatefulWidget {
  const CameraPage({
    super.key,
    this.session,
    this.cameraSession,
    this.onNavigateToCoach,
  });

  /// 跨页共享状态（可空）：姿势页送来的姿势、教练页送来的建议都从这里读。
  final AppSession? session;

  /// 测试用：注入一个相机会话（真机上留空，自己建）。
  ///
  /// 之前这个页面**自己 new 了 CameraSession**，外部无法替换，
  /// 所以它一直测不了（覆盖率 47%，高于 0 只是因为有间接 UI 覆盖）。
  final CameraSession? cameraSession;

  /// v0.4.0：系统相机拍完、用户点「送教练」时，切到教练 tab 的回调
  /// （由 AppShell 提供；没注入就留图在本页并提示用户手动切 tab）。
  final void Function()? onNavigateToCoach;

  @override
  State<CameraPage> createState() => _CameraPageState();
}

class _CameraPageState extends State<CameraPage> with WidgetsBindingObserver {
  /// 相机会话。外部注入时（测试）由外部负责释放。
  late final CameraSession _session = widget.cameraSession ?? CameraSession();

  /// 自己建的才由自己释放 —— 避免把外部传进来的 session 给 dispose 掉。
  bool get _ownsSession => widget.cameraSession == null;
  late final LiveGuideController _live;

  Suggestion? _overlaySuggestion;
  Pose? _activePose;
  bool _busy = false;

  /// v0.4.0：跳系统相机那一刻的时间戳（毫秒）。
  /// 回来之后用它去 MediaStore 捞「比它新的最新一张」。
  int _shootRequestedAt = 0;

  /// 「已拉起系统相机、还没回来」中 —— 防快门被重复按。
  bool _pickingShot = false;

  /// 系统相机拍完、原生侧拷进 App 缓存的那张照片的本地路径
  /// （非空 = 预览区被「刚拍完」结果卡盖住）。
  String? _nativeShotPath;

  /// 原生相机桥（android MainActivity.kt 里实现；web/桌面测试环境没有）。
  static const _cameraChannel =
      MethodChannel('photo_coach.v2/native_camera');

  /// 脸检测单例（复用 FaceDetector 公共入口；isolate 在它内部处理，
  /// UI 线程只等一个 Future）。
  ///
  /// 原生后端（YuNet）由 [_yunet] 惰性加载：
  /// - 模型加载 / 原生库缺失 → nativeBackend 返回 null → FaceDetector 落启发式。
  /// - 成功 → 返回 YuNet 的 FaceDetection → 距离建议拿到真实人脸框。
  static FaceDetector? _faceDetector;

  /// YuNet 原生后端（opencv_dart）。惰性构建，首次 detect 时加载模型。
  static YunetBackend? _yunet;

  /// 惰性取 FaceDetector（首次访问时构建，含 YuNet 后端）。
  static FaceDetector get _detector {
    return _faceDetector ??= FaceDetector(nativeBackend: (image) async {
      try {
        _yunet ??= YunetBackend(
          modelPath: 'assets/models/face_detection_yunet_2023mar.onnx',
        );
        return _yunet!.detect(image);
      } catch (_) {
        return null; // 降级：FaceDetector 会落启发式
      }
    });
  }

  /// 距离建议决策器（纯 Dart 无 IO，线程随便用）。
  static const DistanceAdvisor _distanceAdvisor = DistanceAdvisor();

  /// 最近一次距离建议。null = 还没算过 / 引导没开。
  DistanceAdvice? _distanceAdvice;

  /// 上一次用哪一帧算的建议 —— 帧字节变了才算，省得重复检测。
  int _lastAdviceFrame = -1;

  /// 打开设置页（右上角齿轮）。
  /// v0.4.0：把共享模型配置实例带过去 —— 设置页保存 Key 后教练页立即生效。
  void _openSettings() {
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => SettingsPage(
        modelConfig: widget.session?.modelConfig,
      ),
    ));
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _live = LiveGuideController(source: _session)..addListener(_onLiveChanged);
    widget.session?.addListener(_onSharedChanged);
    _onSharedChanged();
    _session.initialize();
  }

  /// 共享状态变了：姿势页送了新姿势、或教练页给了新建议。
  void _onSharedChanged() {
    final shared = widget.session;
    if (shared == null || !mounted) return;

    final pose = shared.activePose;
    final suggestion = shared.activeSuggestion;

    setState(() {
      _activePose = pose;
      if (suggestion != null) _overlaySuggestion = suggestion;
    });

    // v0.5.0：只要教练给了建议就自动画目标框 + 开实时引导——
    // 有没有姿势都一样（教练方案本来就含 target_box）。
    // 之前是「有姿势才启动」，没带姿势去分析就看不到任何引导。
    if (_overlaySuggestion != null) {
      _live.setTarget(_overlaySuggestion!.subject.targetBox);
      if (!_live.running) _live.start();
    } else if (pose != null && !_live.running) {
      // v0.5.1：姿势页送了姿势但教练没建议 → 用默认三分法目标开引导，
      // 否则用户到了拍摄页看不到任何距离/构图反馈（F3.8 实测 bug）。
      _overlaySuggestion ??= _defaultThirdsSuggestion();
      _live.setTarget(_overlaySuggestion!.subject.targetBox);
      _live.start();
    }
  }

  @override
  void dispose() {
    if (_ownsSession) _session.dispose(); // 注入进来的由外部负责释放
    _live.removeListener(_onLiveChanged);
    widget.session?.removeListener(_onSharedChanged);
    WidgetsBinding.instance.removeObserver(this);
    _live.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      // 只是「失焦」：下拉通知栏、切最近任务预览、来电横幅。
      // ⚠️ 这里**绝不能** dispose 会话 —— 用户只是拉了一下通知栏，
      // 相机和这个页面都还要继续用。之前就是在这里 dispose() 的，
      // 回到前台再 initialize() 就用到已销毁的 ChangeNotifier：
      // debug 下断言失败、`_initializing` 永远停在 true；
      // release 下监听列表已清空、页面永不重建 → 拍摄页永久卡死。
      case AppLifecycleState.inactive:
        _live.pause();
      // 真进后台：必须把摄像头交出去，否则 iOS 回到前台会黑屏。
      // 注意用 releaseCamera()，不是 dispose()。
      case AppLifecycleState.hidden:
      case AppLifecycleState.paused:
        _live.pause();
        _session.releaseCamera();
      case AppLifecycleState.resumed:
        _live.resume();
        // 只在「没开起来、也没在开」时才重开：否则会和 initState 里那次
        // 初始化撞车，两台相机同时打开过 —— 在把摄像头当独占资源的机型上
        // 会永久卡住（华为上真实踩过）。
        if (!_session.isReady && !_session.initializing) {
          _session.initialize();
        }
        // v0.4.0：从系统相机回来 → 捞出刚拍的照片（没拍就静默忽略）。
        _maybePickNativeShot();
      case AppLifecycleState.detached:
        _live.pause();
    }
  }

  /// 开/关实时引导。
  ///
  /// 第一次开的时候自动给一个「三分法」的默认目标框 ——
  /// 否则用户开了却不知道在引导什么（没有 F2 建议时 target 是空的）。
  void _toggleLive() {
    if (_live.running) {
      _live.stop();
      setState(() {
        _distanceAdvice = null; // 引导关了 → 建议条一起消失
      });
    } else {
      _overlaySuggestion ??= _defaultThirdsSuggestion();
      _live.setTarget(_overlaySuggestion!.subject.targetBox);
      _live.start();
    }
    setState(() {});
  }

  /// 监听实时引导：它每 150ms（v0.8.0，原 900ms）抓一帧跑主体检测，
  /// 这里**复用同一次抓帧**给脸检测 + 距离建议。
  ///
  /// 关键：帧取自 [_live.lastFrame]，**不再自己调 grabFrame** ——
  /// 自己再抓一次会和引导的 takePicture 并发，撞「相机正忙」返回 null。
  void _onLiveChanged() {
    if (!_live.running) return;
    final bytes = _live.lastFrame;
    if (bytes == null) return; // 上一帧还在解析 / 抓失败 → 等下次通知
    _updateDistanceAdvice(bytes);
  }

  /// 异步算一次距离建议（不阻塞 UI）：
  /// 搭车帧 → 脸检测（isolate 在 FaceDetector 内部）→ 按目标景别决策。
  ///
  /// ⚠️ 节奏仍由 [LiveGuideController] 管（v0.8.0 提速到 150ms）；
  /// 这里只是每拍完一次搭车算脸。检测失败/没脸 → 灰条或隐藏，不吓唬人。
  Future<void> _updateDistanceAdvice(List<int> bytes) async {
    if (!_live.running) return;
    if (!mounted) return;
    // 廉价去重：同一帧长度不变就不重复检测（长度撞车最坏是多算一次，无害）。
    final byteKey = Object.hash(bytes.length, bytes[0]);
    if (byteKey == _lastAdviceFrame) return;
    _lastAdviceFrame = byteKey;

    final face = await _detector.detectFromBytes(Uint8List.fromList(bytes));
    if (!mounted) return;
    if (!_live.running) return; // 在途期间被关了 → 丢弃

    final framing = _activePose?.guidance?.framing; // 没选姿势 → null = 默认半身
    final advice = _distanceAdvisor.advise(
      faceFound: face.found,
      faceBox: face.box,
      subjectBox: _live.currentBox, // 脸没找到时按主体兜底
      framing: framing,
    );
    if (advice == _distanceAdvice) return; // 没变化就不重画
    setState(() => _distanceAdvice = advice);
  }

  /// 没接大模型时的默认引导目标：主体放左三分之一线上。
  Suggestion _defaultThirdsSuggestion() {
    final base = const OfflineTipEngine().suggest();
    return Suggestion(
      composition: base.composition,
      subject: const SubjectHint(
        label: '主体',
        targetBox: Rect01(0.333, 0.22, 0.334, 0.56),
      ),
      cameraMove: base.cameraMove,
      exposure: base.exposure,
      tips: base.tips,
      source: SuggestionSource.ruleFallback,
    );
  }

  /// v0.4.0：快门 = **跳系统相机**拍。
  ///
  /// App 内预览只负责"照着参考照片对好位置/光线/姿势"，出片交给系统相机
  ///（算法更强、照片直接进用户相册）。本 App 静默退后台；
  /// 用户拍完回前台时 [didChangeAppLifecycleState] 会调
  /// [_maybePickNativeShot] 把照片捞回来。
  Future<void> _shoot() async {
    setState(() => _busy = true);
    final ok = await _launchNativeCamera();
    if (!mounted) return;
    setState(() => _busy = false);

    if (!ok) {
      // 这台设备上没有可用的系统相机（或渠道未接线，如 web）：
      // 如实说一声，退回 App 内拍摄，别让用户白点一下。
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('没找到系统相机，改在 App 内拍摄并存相册')),
      );
      await _shootInApp();
      return;
    }

    // 记下时间点；回来捞照片时用。
    // 摄像头交回交给后台生命周期处理（paused → releaseCamera），不在这重复。
    _shootRequestedAt = DateTime.now().millisecondsSinceEpoch;
    setState(() => _pickingShot = true);
    _live.pause();
    // 说一声：接下来是系统相机在干活（个别机型 intent 没真正弹出来时，
    // 用户至少知道"刚才那一下"是跳相机了，不是白按）。
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('已打开系统相机，在那儿拍，拍完回来即可')),
    );
  }

  /// App 内直接拍摄（v0.4.0 起是**兜底路径**：系统相机不可用时）。
  Future<void> _shootInApp() async {
    setState(() => _busy = true);
    _live.pause();
    // ⚠️ 用 captureAndSave（拍完存进相册），**不要**用 takePicture ——
    // 后者是实时引导每秒取帧用的路径，在那里存相册会一秒灌一张。
    final file = await _session.captureAndSave();
    if (!mounted) return;
    if (file == null) {
      setState(() => _busy = false);
      _live.resume();
      return;
    }

    // 明确告诉用户「存下来了」。以前拍完一声不吭，而照片其实只躺在
    // 系统临时目录里随时会被清掉 —— 用户以为存好了，其实什么都没留下。
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(_session.lastShotSaved == true
            ? '已存到相册'
            : '已拍下，但没能存进相册（原因见下方提示条）'),
      ),
    );

    setState(() => _busy = false);
    _live.resume();
  }

  /// v0.4.0：请原生侧拉起系统相机。失败/渠道未接线 → false。
  Future<bool> _launchNativeCamera() async {
    try {
      final ok = await _cameraChannel.invokeMethod<bool>('launchNativeCamera');
      return ok == true;
    } catch (_) {
      return false; // web / 测试环境没有原生侧实现
    }
  }

  /// v0.4.0：请原生侧捞「[_shootRequestedAt] 之后拍的最新一张」。
  /// 返回本地文件路径（原生从 MediaStore 拷进 App 缓存）；没有 → null。
  Future<String?> _queryNativeShot() async {
    try {
      return await _cameraChannel
          .invokeMethod<String>('latestImageSince', _shootRequestedAt);
    } catch (_) {
      return null;
    }
  }

  /// 从系统相机回到 App 后：把刚拍的照片捞回来。
  ///
  /// - 捞到 → 盖上「刚拍完」结果卡（图 + 送教练 + 重拍）；
  /// - 没捞到（用户在相机里取消了）→ 只说一声，取景框照旧，别吓唬人。
  Future<void> _maybePickNativeShot() async {
    if (!_pickingShot || _shootRequestedAt <= 0) return;
    final path = await _queryNativeShot();
    if (!mounted) return;
    setState(() {
      _pickingShot = false;
      _shootRequestedAt = 0;
    });
    if (path == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('没检测到新照片 —— 继续预览，调好再按快门')),
      );
      return;
    }
    setState(() => _nativeShotPath = path);
  }

  /// 结果卡：送刚拍这张给教练点评。
  ///
  /// 图放进共享状态（AppSession.pendingShot），教练页（IndexedStack 常驻）
  /// 监听 shotSeq 自己收图并自动开始分析；然后切到教练 tab。
  void _sendNativeShotToCoach() {
    final path = _nativeShotPath;
    final shared = widget.session;
    if (path == null) return;
    if (shared == null) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('未接入共享状态，图没送出去')));
      return;
    }
    shared.sendShotToCoach(File(path));
    final navigate = widget.onNavigateToCoach;
    if (navigate != null) {
      navigate();
    } else {
      // 测试/独立使用场景没接导航：如实告诉用户自己去切 tab。
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('图已备好，请切到「教练」tab')));
    }
  }

  /// 结果卡：再跳一次系统相机重拍（旧的留在结果卡，回来换新的）。
  void _reshoot() {
    setState(() => _nativeShotPath = null);
    _shoot();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: AnimatedBuilder(
        animation: _session,
        builder: (context, _) {
          return SafeArea(
            child: Column(
              children: [
                // 取景框占满，右上角浮一个设置齿轮。
                // 本页**没有参数控件**：参数（曝光/变焦/闪光灯）是教练的活，
                // 而且 App 内预览调了也带不到最终出片（出片在系统相机里）。
                Expanded(
                  child: Stack(
                    children: [
                      Positioned.fill(child: _buildPreview()),
                      Positioned(
                        top: 4,
                        right: 4,
                        child: IconButton(
                          tooltip: '设置',
                          onPressed: _openSettings,
                          icon: const Icon(Icons.settings_outlined,
                              color: Colors.white70),
                        ),
                      ),
                    ],
                  ),
                ),
                // v0.4.0：把快门是干嘛的说清楚 —— 出片跳系统相机。
                const Padding(
                  padding: EdgeInsets.only(bottom: 4),
                  child: Text(
                    '觉得好了按快门 → 跳系统相机拍，回来自动接图',
                    style: TextStyle(fontSize: 11, color: Colors.white54),
                  ),
                ),
                // v0.9.3：实时对位反馈条取消（用户反馈太杂，让姿势图干净显示）。
                // v0.9.3：光 bar 取消（用户反馈「有什么用？」——没有直接行动价值）。
                // 光线方向改由教练页 AI 提示，不在拍摄 tab 占位。
                if (_activePose != null) _buildPoseBar(),
                if (_overlaySuggestion != null &&
                    !_overlaySuggestion!.shootingPlan.isEmpty)
                  _buildPlanBar(),
                // v0.9.3：距离条取消（用户反馈「差不多微调」和「再远一点」矛盾）。
                // 距离信息已融入实时对位反馈（_buildLiveBar）。
                // 中性提示（「本平台不支持某项参数」）或非致命警告
                //（「这一次某项参数没设上」）—— 都**不是**「相机坏了」，
                // 所以只挂一条窄条，绝不替换整页预览。
                if (_session.error == null &&
                    (_session.warning != null || _session.note != null))
                  Container(
                    width: double.infinity,
                    color: Colors.black87,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 6),
                    child: Row(
                      children: [
                        Icon(
                          _session.warning != null
                              ? Icons.warning_amber_outlined
                              : Icons.info_outline,
                          size: 14,
                          color: _session.warning != null
                              ? Colors.amberAccent
                              : Colors.white38,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            _session.warning ?? _session.note!,
                            style: TextStyle(
                              fontSize: 11,
                              color: _session.warning != null
                                  ? Colors.amberAccent
                                  : Colors.white54,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                _buildControls(),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildPreview() {
    if (_session.initializing) {
      // 关键：不能只转圈。要告诉用户卡在哪一步、卡了多久，
      // 否则用户以为 App 死了（实测就是这样）。
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text(
                _session.progress.isEmpty ? '正在启动相机…' : _session.progress,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white70, fontSize: 13),
              ),
              if (_session.stuck) ...[
                const SizedBox(height: 10),
                Text(
                  '已经等了 ${_session.stuckSeconds} 秒还没好…',
                  style: const TextStyle(color: Colors.orangeAccent, fontSize: 12),
                ),
                const SizedBox(height: 6),
                const Text(
                  '这台设备可能不允许用摄像头。\n'
                  '你可以先去「姿势」页看看姿势库 —— 那部分不需要相机。',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white38, fontSize: 11),
                ),
              ],
            ],
          ),
        ),
      );
    }
    if (_session.error != null) {
      // Web 是开发期预览，摄像头能力天然不全 —— 别糊一堆异常出来吓人。
      // 真机上这里显示的是真正的初始化失败原因。
      return _ErrorBox(
        message: _session.error!,
        onRetry: _session.initialize,
        isWebPreview: kIsWeb,
      );
    }
    final controller = _session.controller;
    if (controller == null || !controller.value.isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTapUp: (details) {
            final box = context.findRenderObject() as RenderBox?;
            final size = box?.size;
            if (size == null || size.isEmpty) return;
            // 归一化坐标给相机；注意预览是 cover 裁切的，这里按比例估算
            final p = Offset(
              (details.localPosition.dx / constraints.maxWidth).clamp(0.0, 1.0),
              (details.localPosition.dy / constraints.maxHeight).clamp(0.0, 1.0),
            );
            _session.tapToFocus(p);
          },
          child: Stack(
            fit: StackFit.expand,
            children: [
              Center(child: CameraPreview(controller)),
              // F3.7：姿势页送来的姿势，半透明叠在实时取景框上照着摆。
              //
              // ⚠️ 必须按**取景框实际矩形**作画，不能铺满整个盒子。
              // 取景框有黑边（letterbox），铺满的话人形会画到画外面，
              // 用户没法把身体对上去 —— 而那正是这个功能的全部意义。
              if (_activePose != null)
                // ⚠️ `Positioned` 必须是 `Stack` 的**直接子节点** ——
                // 我第一版把它塞在 LayoutBuilder 里面，运行时直接抛
                // `TypeError: type 'minified:fM' is not a subtype of
                // type 'minified:e0'`（浏览器控制台实测抓到的）。
                // 正确做法：Positioned.fill 放在 Stack 下，
                // 内层再自己用 Padding / Align 落到取景框矩形里。
                Positioned.fill(
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final box =
                          Size(constraints.maxWidth, constraints.maxHeight);
                      final ar = controller.value.aspectRatio;
                      final rect = fitPreviewRect(box, ar > 0 ? ar : (3 / 4));
                      if (rect.isEmpty) return const SizedBox.shrink();
                      return Padding(
                        padding: EdgeInsets.fromLTRB(
                            rect.left, rect.top, 0, 0),
                        child: Align(
                          alignment: Alignment.topLeft,
                          child: SizedBox(
                            width: rect.width,
                            height: rect.height,
                            child: IgnorePointer(
                              child: Opacity(
                                opacity: 0.4,
                                child: _activePose!.hasPhoto
                                    // 参考照姿势没有火柴人线条，只能叠**照片本身**。
                                    // 只画火柴人的话，用户从姿势集选了参考照送过来，
                                    // 预览页会是一片空白；更早的版本甚至因为
                                    // `strokes` 为空抛 `Bad state: No element`
                                    // 直接把 App 画崩（真机："屡次停止运行"）。
                                    ? Image.asset(
                                        _activePose!.imagePath!,
                                        // 测试用稳定锚点（断言叠加层画了/没画）。
                                        key: const ValueKey('pose-overlay'),
                                        fit: BoxFit.contain,
                                        errorBuilder: (_, __, ___) =>
                                            const SizedBox.shrink(),
                                      )
                                    : CustomPaint(
                                        key: const ValueKey('pose-overlay'),
                                        painter: PoseFigurePainter(
                                          pose: _activePose!,
                                          color: Theme.of(context)
                                              .colorScheme
                                              .primary,
                                          strokeWidth: 3,
                                        ),
                                      ),
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              // v0.9.3：GuidanceOverlay 取消（用户反馈目标框/检测框/贴边/网格太杂）。
              // 姿势参考图已在上面单独渲染（opacity 0.4），干净显示即可。
              // 实时检测仍在后台跑（_live），但不画到取景框上。
              if (_overlaySuggestion == null && _activePose == null)
                const IgnorePointer(child: _ThirdsHint()),
              // v0.4.0：从系统相机回来 → 用结果卡盖住取景框
              //（原照片在用户相册里，这里是原生拷进缓存的副本）。
              if (_nativeShotPath != null)
                Positioned.fill(
                  child: _ShotResultCard(
                    path: _nativeShotPath!,
                    onSendToCoach: _sendNativeShotToCoach,
                    onReshoot: _reshoot,
                    onDismiss:
                        () => setState(() => _nativeShotPath = null),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }

  /// 显示「正在照着哪个姿势拍」，并提供一键清除。
  /// 显示这个姿势的拍摄方案（光照/人站哪/拍摄点/机位方向）。
  ///
  /// 方案来自最近一次分析（教练页带姿势分析的结果，存在共享状态里）。
  /// 没有方案就**如实说没有**，不给假东西。
  void _showPosePlan() {
    final plan = _overlaySuggestion?.shootingPlan;
    final pose = _activePose;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 有姿势时说明是「为这个姿势」的方案；没有就是普通拍摄方案。
              Text(
                pose == null ? '拍摄方案' : '怎么拍「${pose.title}」',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              if (plan == null || plan.isEmpty)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // v0.9.0：没有 AI 方案时**不再留白**——姿势自带的基础
                    // 指导（机位高度/站位/距离，离线可用）先顶上，
                    // 小白选完姿势立刻知道手机放哪、人站哪。
                    if (pose?.guidance != null) ...[
                      for (final line in poseGuidanceLines(pose!.guidance!))
                        _planLine('${line.label}（基础）', line.text),
                      const SizedBox(height: 6),
                    ],
                    const Text(
                      '想要针对现场的完整方案：去教练页选一张照片、点分析 —— '
                      '分析时会自动带上你选中的姿势，回来的方案就是'
                      '"为了拍出这个姿势，你该怎么拍"。',
                      style: TextStyle(fontSize: 12, color: Colors.white70),
                    ),
                  ],
                )
              else ...[
                if (plan.lighting != null) _planLine('💡 光照', plan.lighting!),
                if (plan.subjectPosition != null)
                  _planLine('🧍 人站哪', plan.subjectPosition!),
                if (plan.position != null)
                  _planLine('📍 去哪（含高度）', plan.position!),
                if (plan.direction != null)
                  _planLine('🧭 机位方向', plan.direction!),
                // v0.5.0：远近从 camera_move.dolly_m 推。
                // 注意口径：提示词定义「向前移动为正」（suggestion.dart 里
                // 字段注释写的"负=后退"与提示词相反，以提示词为准）。
                if ((_overlaySuggestion?.cameraMove.dollyM ?? 0).abs() >= 0.02)
                  _planLine(
                    '📏 远近',
                    _overlaySuggestion!.cameraMove.dollyM > 0
                        ? '向前 ${_overlaySuggestion!.cameraMove.dollyM.toStringAsFixed(1)} 米'
                        : '后退 ${(-_overlaySuggestion!.cameraMove.dollyM).toStringAsFixed(1)} 米',
                  ),
                const SizedBox(height: 8),
                const Text('以上是模型的判断（主观意见），不是测量结果。',
                    style: TextStyle(fontSize: 10, color: Colors.white38)),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _planLine(String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(k, style: const TextStyle(fontSize: 11, color: Colors.white54)),
            Text(v, style: const TextStyle(fontSize: 13)),
          ],
        ),
      );

  /// 光线方向选择（v0.9.0 环境指导）。
  ///
  /// 为什么放拍摄页：光线是「环境」的第一变量，而用户调环境（搬位置/加反光板）
  /// 就发生在按快门之前。点一下 = 记住方向，送教练点评时自动带上
  /// 「我打算用 X 光」，点评就能对照「这个姿势要柔光」判断对不对。
  /// 再点同一个方向 = 取消选择（回到"没声明"）。
  ///
  /// 诚实的边界：App 内预览的光改不了系统相机的出片，这里**只做意图记录**，
  /// 不提供曝光补偿之类假能改的控件（v0.5.0 已删，不回头）。
  // v0.9.3：_setLightDirection 已删除（光 bar 取消）。
  // 光线方向改由教练页 AI 提示。

  /// 光线方向条：顺光 / 侧光 / 逆光 三个按钮（再点已选 = 取消）。
  ///
  /// 为什么只有按钮、没有"当前光向"实时显示：FaceLightReport 是**照片**级分析
  /// v0.9.3：光 bar 已取消（用户反馈「有什么用？」）。
  /// 光线方向改由教练页 AI 提示，不在拍摄 tab 占位。

  /// v0.5.0 方案条：教练拍摄方案的一行摘要（你站哪+高度）。
  ///
  /// 姿势条（人）之上再挂方案条（环境）—— 站哪/去哪/方向/光 都在「看方案」
  /// 弹层里；「清除」把目标框和引导一起撤掉。
  Widget _buildPlanBar() {
    final plan = _overlaySuggestion!.shootingPlan;
    // 一行放不下四项，只摘「去哪(含高度) + 方向」；全量在「看方案」弹层里。
    final summary = [
      if (plan.position != null && plan.position!.isNotEmpty) '📍 ${plan.position}',
      if (plan.direction != null && plan.direction!.isNotEmpty) '🧭 ${plan.direction}',
    ].join('  ');
    return Container(
      color: Colors.black87,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Row(
        children: [
          const Icon(Icons.lightbulb_outline, size: 16, color: Colors.amberAccent),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '方案：$summary',
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12, color: Colors.white),
            ),
          ),
          TextButton(
            onPressed: _showPosePlan,
            child: const Text('看方案', style: TextStyle(fontSize: 12)),
          ),
          TextButton(
            onPressed: () {
              widget.session?.setSuggestion(null);
              _live.stop();
              setState(() => _overlaySuggestion = null);
            },
            child: const Text('清除', style: TextStyle(fontSize: 12)),
          ),
        ],
      ),
    );
  }

  // v0.9.3：距离条 + 实时对位反馈条均已取消（用户要求让姿势图干净显示）。

  /// 姿势条的机位参数后缀：「 · 全身 · 低拍」之类的简写。
  static String _poseParamsSuffix(Pose pose) {
    final g = pose.guidance;
    if (g == null) return '';
    final height = g.cameraHeight.replaceAll('机位', '');
    return ' · $g.framing · $height拍';
  }


  Widget _buildPoseBar() {
    final pose = _activePose!;
    return Container(
      color: Colors.black87,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Row(
        children: [
          const Icon(Icons.accessibility_new, size: 16, color: Colors.lightBlueAccent),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              // v0.9.0：把机位参数摊在条上（原来藏在「怎么拍」按钮里，
              // 小白不看按钮就不知道手机该放多高、站多远）。
              '照姿势：${pose.title}${_poseParamsSuffix(pose)}',
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12, color: Colors.white),
            ),
          ),
          // pose 教程 × 拍摄方案的打通点②：直接在这儿看"这个姿势该怎么拍"
          TextButton(
            onPressed: _showPosePlan,
            child: const Text('怎么拍', style: TextStyle(fontSize: 12)),
          ),
          TextButton(
            onPressed: () {
              widget.session?.clearPose();
              setState(() => _activePose = null);
            },
            child: const Text('去掉', style: TextStyle(fontSize: 12)),
          ),
        ],
      ),
    );
  }

  Widget _buildControls() {
    return Container(
      color: Colors.black,
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          IconButton(
            tooltip: _live.running ? '关闭实时引导' : '开启实时引导（本地，不联网）',
            onPressed: _session.isReady ? _toggleLive : null,
            icon: Icon(
              _live.running ? Icons.videocam : Icons.videocam_outlined,
              color: _live.running ? Colors.greenAccent : Colors.white,
            ),
          ),
          // 快门：套 Tooltip 一是给无障碍读屏用，二是让测试有个稳定的抓手
          //（原来是个裸 GestureDetector，测不了「按快门会不会存相册」）
          Tooltip(
            message: '拍照',
            child: GestureDetector(
              onTap: _busy || !_session.isReady ? null : _shoot,
              child: Container(
                width: 66,
                height: 66,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 4),
                  color: _busy ? Colors.white24 : Colors.white,
                ),
              ),
            ),
          ),
          IconButton(
            tooltip: '切换摄像头',
            onPressed: _session.isReady ? _session.switchCamera : null,
            icon: const Icon(Icons.cameraswitch, color: Colors.white),
          ),
        ],
      ),
    );
  }
}

/// 没接大模型时，至少给个三分法网格。
class _ThirdsHint extends StatelessWidget {
  const _ThirdsHint();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(painter: _ThirdsPainter());
  }
}

class _ThirdsPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.25)
      ..strokeWidth = 1;
    for (var i = 1; i <= 2; i++) {
      canvas.drawLine(Offset(size.width * i / 3, 0),
          Offset(size.width * i / 3, size.height), paint);
      canvas.drawLine(Offset(0, size.height * i / 3),
          Offset(size.width, size.height * i / 3), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _ErrorBox extends StatelessWidget {
  const _ErrorBox({
    required this.message,
    required this.onRetry,
    this.isWebPreview = false,
  });

  final String message;
  final VoidCallback onRetry;
  final bool isWebPreview;

  /// 让用户不用去设置里翻就能看到系统版本。
  ///
  /// 为什么这么做：判断「这台机器能不能装安卓 APK」需要知道是
  /// HarmonyOS NEXT（不兼容安卓，装不了）还是 HarmonyOS 4.x（能装）。
  /// 让 App 自己报出来，比教用户翻设置快得多。
  static String _osHint() {
    if (kIsWeb) {
      return '当前是浏览器预览（不是安装版 App）';
    }
    try {
      // 只在 Android/iOS 上有效；拿不到就静默跳过
      final d = Platform.operatingSystemVersion;
      return d.length > 120 ? d.substring(0, 120) : d;
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final isSimulator =
        message.contains('模拟器') || message.contains('simulator');
    final headline = isWebPreview
        ? '浏览器预览：摄像头能力有限'
        : (isSimulator ? '模拟器没有摄像头' : '相机没能用起来');
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.no_photography_outlined,
                color: Colors.white54, size: 42),
            const SizedBox(height: 12),
            Text(
              headline,
              textAlign: TextAlign.center,
              style: const TextStyle(
                  color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            if (isWebPreview)
              const Column(
                children: [
                  Text(
                    '浏览器里摄像头只能部分工作，这不代表真机不行。',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white60, fontSize: 13),
                  ),
                  SizedBox(height: 4),
                  Text(
                    '看界面结构够用了；真要拍照请上真机。',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white38, fontSize: 12),
                  ),
                ],
              )
            else if (isSimulator)
              const Text(
                'iOS 模拟器没有摄像头，请用真机运行。',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.orangeAccent, fontSize: 12),
              )
            else
              Text(
                message,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white60, fontSize: 12),
              ),
            if (_osHint().isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                _osHint(),
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white24, fontSize: 10),
              ),
            ],
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onRetry, child: const Text('重试')),
          ],
        ),
      ),
    );
  }
}

/// 取景框在给定盒子里**实际渲染的区域**。
///
/// 为什么需要它：`CameraPreview` 被 `Center` 包着 —— 它按相机宽高比居中，
/// 四周留黑边（letterbox）。而姿势叠加层原来是 `StackFit.expand`，
/// **铺满整个盒子**。两者坐标系不同，结果人形会画到取景框外面，
/// 用户根本没法"照着摆"（这是这个功能的全部意义）。
///
/// 有了这个函数，叠加层就能按**同一个矩形**作画，和画面严格对齐。
///
/// [box] 可用空间，[aspectRatio] 画面宽高比（宽 / 高）。
/// 退化的输入（宽高比为 0/负、盒子为 0）返回空矩形，不抛异常也不产生 NaN。
Rect fitPreviewRect(Size box, double aspectRatio) {
  if (box.width <= 0 || box.height <= 0 || aspectRatio <= 0 ||
      !aspectRatio.isFinite) {
    return Rect.zero;
  }
  // 先按宽度铺满算高度
  var w = box.width;
  var h = w / aspectRatio;
  // 太高了就改成按高度铺满
  if (h > box.height) {
    h = box.height;
    w = h * aspectRatio;
  }
  return Rect.fromLTWH(
    (box.width - w) / 2,
    (box.height - h) / 2,
    w,
    h,
  );
}

/// v0.4.0：从系统相机回来后的「刚拍完」结果卡。
///
/// 照片由系统相机拍摄，原文件在用户自己的相册里（不动它）；
/// 这里显示的是原生侧从 MediaStore 拷进 App 缓存的副本。
class _ShotResultCard extends StatelessWidget {
  const _ShotResultCard({
    required this.path,
    required this.onSendToCoach,
    required this.onReshoot,
    required this.onDismiss,
  });

  final String path;
  final VoidCallback onSendToCoach;
  final VoidCallback onReshoot;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.black,
      child: SafeArea(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              '系统相机拍好了，看看效果',
              style: TextStyle(
                  color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            ConstrainedBox(
              constraints:
                  const BoxConstraints(maxHeight: 400, maxWidth: 340),
              child: Image.file(
                File(path),
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => const SizedBox(
                  height: 200,
                  child: Center(
                    child: Text('照片加载失败',
                        style: TextStyle(color: Colors.white54)),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                FilledButton.icon(
                  onPressed: onSendToCoach,
                  icon: const Icon(Icons.assistant, size: 18),
                  label: const Text('送教练点评'),
                ),
                const SizedBox(width: 12),
                OutlinedButton.icon(
                  onPressed: onReshoot,
                  icon: const Icon(Icons.photo_camera, size: 18),
                  label: const Text('重拍'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: onDismiss,
              child: const Text('关闭（回预览）',
                  style: TextStyle(color: Colors.white54)),
            ),
          ],
        ),
      ),
    );
  }
}

/// 距离刻度条：「近 ──●── 远」+ 站位人话。
///
/// 为什么需要它：文案「脸占满了画面」说了问题，但**没说差多远**——
/// 用户不知道退一步还是一米。刻度条把连续量（faceH → position）画出来，
/// 配合下面一行「平视拍，再远一点」，一眼看懂往哪调、调多少。
///
/// - position 来自 DistanceAdvice（0=最远、1=最近，模糊区 clamp 到端点）；
/// - 绿色高亮带 = 当前景别的「合适区间」，点在带内就对了；
/// - unknown（没测到）= 中性点 + 灰字，不假装知道。
// v0.9.3：_DistanceGauge 已删除（距离条取消）。
