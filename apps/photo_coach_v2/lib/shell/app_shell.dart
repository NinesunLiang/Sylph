import 'package:flutter/material.dart';

import '../app_session.dart';
import '../features/camera/camera_page.dart';
import '../features/coach/coach_page.dart';
import '../features/onboarding/onboarding.dart';
import '../features/poses/poses_page.dart';

/// 三个功能的入口。
///
/// v2 渐进迁移（本文件随迁移进度演进）：
/// - S2（v0.1.0）：姿势页已迁移；拍摄/教练 tab 是「迁移中」占位页。
/// - S3（v0.2.0）：拍摄页（CameraPage）+ 实时引导已迁移，替换拍摄占位。
///   相机权限、存相册权限见 android manifest（照抄老 app 的权限结论）。
/// - S4（v0.3.0）：CoachPage 已迁入，替换教练占位（占位页删除）。
///   教练页的模型 Key 在手机里输入（SharedPreferences），不打进 APK。
/// - v0.4.0：tab 一度改名「预览」—— App 内取景只为配合姿势对位，
///   点快门跳系统相机出片；拍完点「送教练」自动切到教练 tab。
/// - v0.5.0（2026-10-11 三模块职责重构）：tab 改回「拍摄」。
///   拍摄 = 对位 + 跳系统相机（无参数控件）；教练 = 镜头语言；姿势 = pose。
class AppShell extends StatefulWidget {
  const AppShell({super.key, this.session});

  /// 允许注入（测试用）。默认自建。
  final AppSession? session;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;
  late final AppSession _session;
  late final bool _ownsSession;

  /// 上一次已经响应过的「送到拍摄页」请求序号。
  int _handledSendSeq = 0;

  /// v0.9.2：首次 onboarding 遮罩（null = 不显示）。
  bool _showOnboarding = true;

  /// 测试注入：跳过 onboarding 检测（直接 false）。
  bool get _forceNoOnboarding => widget.session != null;

  @override
  void initState() {
    super.initState();
    _ownsSession = widget.session == null;

    _session = widget.session ?? AppSession();
    _handledSendSeq = _session.sendSeq;
    _session.addListener(_onSessionChanged);

    // 测试环境注入了 session → 跳过 onboarding（避免每次测试都弹）。
    if (_forceNoOnboarding) {
      _showOnboarding = false;
    } else {
      isOnboarded().then((done) {
        if (mounted && !done) setState(() => _showOnboarding = true);
      });
    }
  }

  @override
  void dispose() {
    _session.removeListener(_onSessionChanged);
    if (_ownsSession) _session.dispose();
    super.dispose();
  }

  /// 姿势页点了「送到拍摄页」→ 自动切到拍摄页。
  ///
  /// 用序号而不是 bool：同一个姿势连续送两次也要能触发（见 AppSession 注释）。
  void _onSessionChanged() {
    if (_session.sendSeq == _handledSendSeq) return;
    _handledSendSeq = _session.sendSeq;
    if (!mounted) return;
    setState(() => _index = 0);
  }

  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[
      // S3 迁入：真实拍摄页（v0.4.0 曾叫「预览」，v0.5.0 改回「拍摄」）。
      // 职责：配合姿势取景对位，快门跳系统相机；**没有参数控件**。
      // AppSession 在 main.dart 根部建好、三 tab 共用，
      // 姿势页「送到拍摄页」的请求就是靠它送达这里的。
      CameraPage(
        session: _session,
        // v0.4.0：系统相机拍完点「送教练」→ 切到教练 tab。
        onNavigateToCoach: () => setState(() => _index = 1),
      ),
      // S4 迁入：真实教练页。模型 Key 在页面内输入、只存本机。
      // v0.5.0：出方案后「发送到拍摄页」→ 切到拍摄 tab（方案已在共享状态，
      // 拍摄页会自动画目标框；这里只负责切页，不重复触发）。
      CoachPage(
        session: _session,
        onNavigateToShoot: () => setState(() => _index = 0),
      ),
      PosesPage(session: _session, onSendToCamera: _session.sendPoseToCamera),
    ];

    return Scaffold(
      body: Stack(
        children: [
          IndexedStack(index: _index, children: pages),
          if (_showOnboarding)
            OnboardingPage(
              onFinish: () => setState(() => _showOnboarding = false),
            ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.camera_alt_outlined),
            selectedIcon: Icon(Icons.camera_alt),
            // v0.5.0 三模块：拍摄 = 取景对位 + 跳系统相机出片。
            label: '拍摄',
          ),
          NavigationDestination(
            icon: Icon(Icons.assistant_outlined),
            selectedIcon: Icon(Icons.assistant),
            label: '教练',
          ),
          NavigationDestination(
            icon: Icon(Icons.collections_outlined),
            selectedIcon: Icon(Icons.collections),
            label: '姿势',
          ),
        ],
      ),
    );
  }
}
