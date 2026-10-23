import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/app_session.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';
import 'package:photo_coach_v2/features/poses/pose.dart';
import 'package:photo_coach_v2/shell/app_shell.dart';

/// App 外壳的接线测试（F3.7：姿势页 → 拍摄页）。
///
/// v2 S4 版本起：三个 tab 全部是真实页面。
/// v0.5.0 三模块：拍摄 tab 恢复叫「拍摄」（取景对位 + 跳系统相机，
/// 不再有调参功能；快门链路在 test/camera_page_test.dart 覆盖）。
/// 断言 = 「三个 tab 都在 + 教练页模型配置卡可见 + 姿势页可用 + 共享状态正确」。
/// 拍摄页自己的行为由 test/camera_page_test.dart 覆盖（用假相机平台）；
/// 教练页自己的行为由 test/coach_page_test.dart 覆盖（显式注入 config）。
///
/// 注意：教练页 initState 会读 SharedPreferences；widget 测试里没有平台
/// 插件，会抛 MissingPluginException —— coach_page 捕获后按「未配置」处理，
/// 所以这里不需要 mock 插件。
void main() {
  Future<AppSession> pumpShell(WidgetTester tester) async {
    tester.view.physicalSize = const Size(390 * 3, 844 * 3);
    tester.view.devicePixelRatio = 3.0;
    addTearDown(tester.view.reset);

    final session = AppSession();
    addTearDown(session.dispose);
    await tester.pumpWidget(MaterialApp(home: AppShell(session: session)));
    await tester.pump();

    // 测试环境里没有摄像头，相机初始化会一直 pending，留下一个 12 秒的
    // 超时定时器 —— 不清理的话 teardown 会报 "A Timer is still pending"。
    // 这里把它推过去，让初始化走完超时分支，界面落到「相机不可用」状态。
    // 顺便这也是一种覆盖：验证「相机挂了 App 也不崩」。
    await tester.pump(const Duration(seconds: 13));
    return session;
  }

  testWidgets('三个 tab 都在（拍摄 / 教练 / 姿势）', (tester) async {
    await pumpShell(tester);
    // v0.5.0 三模块：tab 恢复叫「拍摄」（取景对位，不再调参）。
    expect(find.text('拍摄'), findsOneWidget);
    expect(find.text('教练'), findsOneWidget);
    expect(find.text('姿势'), findsOneWidget);
  });

  testWidgets('教练 tab 是真实教练页（S4 已迁入；模型配置卡可见）', (
          tester,
        ) async {
    await pumpShell(tester);
    await tester.tap(find.text('教练'));
    await tester.pump();
    // S4 迁入后的真实页面：顶部「模型配置」卡（Key 只存本机），不再是占位。
    expect(find.text('模型配置'), findsOneWidget);
    expect(find.textContaining('教练（迁移中）'), findsNothing);
  });

  testWidgets('能切到姿势页并看到参考照卡片', (tester) async {
    await pumpShell(tester);
    await tester.tap(find.text('姿势'));
    // 注意：不能用 pumpAndSettle —— 页面有动画时 settle 可能等不到「静止」。
    // 用固定次数的 pump 就够。
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.byType(GridView), findsOneWidget);
    // v0.4.0：姿势页只剩真实参考照片（火柴人库已删）—— 第一张就是数据里的第一张。
    expect(find.textContaining(photoPoses.first.title), findsWidgets);
  });

  testWidgets('姿势页 →「送到拍摄页」→ 切到拍摄 tab（实机问题回归）', (tester) async {
    final session = await pumpShell(tester);

    await tester.tap(find.text('姿势'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    // 点开一个姿势 → 进入图片模式（F3.8：整页换成 PageView）
    await tester.tap(find.textContaining(photoPoses.first.title).first);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.byType(PageView), findsOneWidget,
        reason: '点卡片应进入图片模式（PageView）');

    // 点「送到拍摄页」（图片模式底部按钮）
    await tester.tap(find.widgetWithText(FilledButton, '送到拍摄页'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    // ① tab 必须已经切到拍摄页
    final nav = tester.widget<NavigationBar>(find.byType(NavigationBar));
    expect(nav.selectedIndex, 0, reason: '应该切到「拍摄」');
    // ② 姿势确实送过去了
    expect(session.activePose, isNotNull);
  });

  testWidgets('共享状态：sendPoseToCamera 写进 activePose 并让 sendSeq +1', (tester) async {
    final session = await pumpShell(tester);
    final pose = photoPoses.first;

    expect(session.hasActivePose, isFalse);
    final before = session.sendSeq;
    session.sendPoseToCamera(pose);
    await tester.pump();

    expect(session.activePose, pose);
    expect(session.hasActivePose, isTrue);
    expect(session.sendSeq, before + 1);
  });

  testWidgets('连续送同一个姿势两次，序号也会 +2（bool 做不到这件事）', (tester) async {
    final session = await pumpShell(tester);
    final pose = photoPoses.first;

    session.sendPoseToCamera(pose);
    await tester.pump();
    session.sendPoseToCamera(pose);
    await tester.pump();

    expect(session.sendSeq, 2);
  });

  testWidgets('clearPose 清掉姿势，且空转不会重复通知', (tester) async {
    final session = await pumpShell(tester);
    var notifications = 0;
    session.addListener(() => notifications++);

    session.sendPoseToCamera(photoPoses.first);
    expect(notifications, 1);
    session.clearPose();
    expect(notifications, 2);
    session.clearPose(); // 已经空了，不该再通知
    expect(notifications, 2);
    expect(session.hasActivePose, isFalse);
  });

  // 从老 app 原样迁入（只改包名）：没送姿势时，拍摄页不显示「照姿势」条。
  // 相机在测试环境里初始化会失败（没有摄像头），这是预期行为，不算崩溃。
  testWidgets('没送姿势时，拍摄页不显示「照姿势」条', (tester) async {
    await pumpShell(tester);
    expect(find.textContaining('照姿势'), findsNothing);
  });

  // v0.5.0 三模块闭环（外壳层）：教练方案写进共享状态 → 切到拍摄 tab，
  // 取景界面上出现方案条。相机在测试环境里是坏的，不影响这条链路。
  testWidgets('教练方案投射：拍摄 tab 出现方案条（不需要姿势）', (tester) async {
    final session = await pumpShell(tester);

    session.setSuggestion(const Suggestion(
      composition: CompositionHint(rule: 'rule_of_thirds'),
      subject: SubjectHint(
        label: '人物',
        targetBox: Rect01(0.2, 0.2, 0.3, 0.6),
      ),
      cameraMove: CameraMoveHint(),
      exposure: ExposureHint(),
      shootingPlan: ShootingPlan(
        position: '到窗边，手机降到胸口高度',
        direction: '从人物左前方 45° 拍',
      ),
    ));

    await tester.tap(find.text('拍摄'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.textContaining('方案：'), findsOneWidget,
        reason: '教练给了方案，拍摄页却没有任何提示 = 闭环断了');
  });
}
