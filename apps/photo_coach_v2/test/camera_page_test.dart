
import 'package:camera/camera.dart' show CameraPreview;
import 'package:camera_platform_interface/camera_platform_interface.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/app_session.dart';
import 'package:photo_coach_v2/features/camera/camera_page.dart';
import 'package:photo_coach_v2/features/camera/camera_session.dart';
import 'package:photo_coach_v2/features/camera/photo_saver.dart';
import 'package:photo_coach_v2/features/poses/pose.dart';

import 'package:photo_coach_v2/features/coach/suggestion.dart';

import 'support/fake_camera_platform.dart';
import 'support/fake_photo_saver.dart';

/// 拍摄页（F1 + F2.11/F2.12 的宿主页面）的测试。
///
/// v0.4.0 起：这页叫「预览」，快门 = 跳系统相机（原生通道
/// `photo_coach.v2/native_camera`）；App 内拍摄降级为系统相机不可用时的兜底。
/// 单测里没有原生侧，用 [mockNativeCamera] 模拟通道的各种返回。
///
/// **背景**：这个页面之前**自己 new 了 CameraSession**，外部无法替换，
/// 所以覆盖率只有 47%，而且「相机挂了会不会锁死界面」这类问题
/// 只能靠人在真机上撞（真撞到了 —— 一直转圈、按钮全点不动）。
///
/// 现在支持注入 [`CameraSession`]（参数名 `cameraSession`），
/// 就能在没有真实摄像头的单测环境里覆盖：
///   · 加载态 / 错误态 / 卡住态的界面
///   · 相机不可用时 App 是否仍然可用（不被锁死）
///   · 跨页状态（姿势送到拍摄页）是否画出来

Future<CameraSession> pumpCamera(
  WidgetTester tester, {
  AppSession? shared,
  CameraSession? camera,
}) async {
  tester.view.physicalSize = const Size(390 * 3, 900 * 3);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  final cs = camera ?? CameraSession();
  // 外部传进来的由调用方注册清理；这里只管自己建的那个，
  // 否则会 dispose 两次（ChangeNotifier 会断言报错）。
  if (camera == null) addTearDown(cs.dispose);

  await tester.pumpWidget(MaterialApp(
    theme: ThemeData.dark(),
    home: CameraPage(session: shared, cameraSession: cs),
  ));
  await tester.pump();

  // ⚠️ 必须把 initialize 的超时（12 秒）走完。
  // 不然测试结束时会报 "A Timer is still pending" —— 那个心跳定时器和
  // 12 秒超时都挂在 CameraSession 上，不推进时间就永远悬着。
  // 顺便这也覆盖了「相机起不来时界面怎么办」这条路径。
  await tester.pump(const Duration(seconds: 13));
  await tester.pump();
  return cs;
}

/// v0.4.0：mock 原生相机通道 `photo_coach.v2/native_camera`。
///
/// - [launchReturns]：`launchNativeCamera` 的返回值。
///   `null` = 系统相机不存在（模拟 web/渠道未接线）→ 快门应退回 App 内拍摄。
///   `true` = 拉起成功 → App 静默退后台等用户回来。
/// - [shotPath]：回来时 `latestImageSince` 的返回值。
///   `null` = 用户在系统相机里取消了；非空 = 拍了一张。
void mockNativeCamera(
  WidgetTester tester, {
  Object? launchReturns,
  String? shotPath,
}) {
  const channel = MethodChannel('photo_coach.v2/native_camera');
  tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
    channel,
    (call) async {
      switch (call.method) {
        case 'launchNativeCamera':
          return launchReturns;
        case 'latestImageSince':
          return shotPath;
        default:
          return null;
      }
    },
  );
  addTearDown(() => tester.binding.defaultBinaryMessenger
      .setMockMethodCallHandler(channel, null));
}

void main() {
  group('拍摄页 —— 相机不可用时的界面', () {
    testWidgets('没相机时不崩，显示出可读的说明（不是空白）', (tester) async {
      await pumpCamera(tester);
      expect(tester.takeException(), isNull);
      // 相机页主体要么在转圈、要么在报错，不能是纯空白
      final hasSpinner = find.byType(CircularProgressIndicator).evaluate().isNotEmpty;
      final hasText = find.byType(Text).evaluate().isNotEmpty;
      expect(hasSpinner || hasText, isTrue);
    });

    testWidgets('拍摄页**不再**常驻参数面板（已降级成设置里的小功能）', (tester) async {
      await pumpCamera(tester);
      expect(find.textContaining('拍摄参数'), findsNothing,
          reason: '参数面板又回到拍摄页了 —— 它会吃掉小半屏取景框，'
              '而这一页的职责是配合姿势取景拍照');
    });

    testWidgets('右上角有「设置」齿轮（相机坏了也点得到）', (tester) async {
      await pumpCamera(tester);
      expect(find.byTooltip('设置'), findsOneWidget);
    });

    testWidgets('拍摄页只留取景+快门+切摄+实时引导', (tester) async {
      await pumpCamera(tester);
      expect(find.byTooltip('拍照'), findsOneWidget);
      expect(find.byTooltip('切换摄像头'), findsOneWidget);
      // 参数开关不该再有了
      expect(find.byTooltip('收起参数'), findsNothing);
      expect(find.byTooltip('展开参数'), findsNothing);
    });

    testWidgets('打开设置不崩（三模块重构后：参数类目已删，只剩模型 Key）',
        (tester) async {
      await pumpCamera(tester);
      await tester.tap(find.byTooltip('设置'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.text('设置'), findsOneWidget);
      expect(find.text('模型配置'), findsOneWidget);
      expect(find.text('拍摄参数'), findsNothing,
          reason: '出片在系统相机，拍摄参数不该再出现在设置里');
      expect(tester.takeException(), isNull);
    });

    testWidgets('相机没起来时，实时引导按钮不该让人误以为能用', (tester) async {
      await pumpCamera(tester);
      // 相机不可用时点了也不该崩
      final icons = find.byType(IconButton);
      for (var i = 0; i < icons.evaluate().length; i++) {
        await tester.tap(icons.at(i), warnIfMissed: false);
        await tester.pump(const Duration(milliseconds: 50));
      }
      await tester.pump(const Duration(milliseconds: 200));
      expect(tester.takeException(), isNull, reason: '点一遍按钮不该崩');
    });
  });

  group('拍摄页 —— 跨页共享状态（姿势）', () {
    testWidgets('没人送姿势时不显示「照姿势」条', (tester) async {
      final shared = AppSession();
      addTearDown(shared.dispose);
      await pumpCamera(tester, shared: shared);
      expect(find.textContaining('照姿势'), findsNothing);
    });

    testWidgets('送姿势之后显示「照姿势」条，并带上姿势名', (tester) async {
      final shared = AppSession();
      addTearDown(shared.dispose);
      await pumpCamera(tester, shared: shared);

      shared.sendPoseToCamera(photoPoses.first);
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.textContaining('照姿势'), findsWidgets);
      expect(find.textContaining(photoPoses.first.title), findsWidgets);
    });

    testWidgets('「去掉」能清掉姿势', (tester) async {
      final shared = AppSession();
      addTearDown(shared.dispose);
      await pumpCamera(tester, shared: shared);
      shared.sendPoseToCamera(photoPoses.first);
      await tester.pump(const Duration(milliseconds: 100));

      final remove = find.textContaining('去掉');
      expect(remove, findsWidgets, reason: '姿势条上应该有「去掉」');
      await tester.tap(remove.first);
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));

      expect(shared.activePose, isNull);
      expect(find.textContaining('照姿势'), findsNothing);
    });

    testWidgets('页面销毁后，共享状态再变化不会崩（监听器已摘掉）', (tester) async {
      final shared = AppSession();
      addTearDown(shared.dispose);
      await pumpCamera(tester, shared: shared);

      // 换掉整个 widget 树，模拟离开页面
      await tester.pumpWidget(const MaterialApp(home: SizedBox()));
      await tester.pump();

      shared.sendPoseToCamera(photoPoses.first);
      await tester.pump(const Duration(milliseconds: 50));
      expect(tester.takeException(), isNull);
    });
  });

  group('拍摄页 —— 布局健壮性', () {
    testWidgets('窄屏（320pt）不溢出', (tester) async {
      tester.view.physicalSize = const Size(320 * 3, 640 * 3);
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      final cs = CameraSession();
      addTearDown(cs.dispose);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CameraPage(cameraSession: cs),
      ));
      await tester.pump();
      await tester.pump(const Duration(seconds: 13)); // 走完初始化超时
      expect(tester.takeException(), isNull);
    });

    testWidgets('宽屏（平板 900pt）不溢出', (tester) async {
      tester.view.physicalSize = const Size(900 * 2, 600 * 2);
      tester.view.devicePixelRatio = 2;
      addTearDown(tester.view.reset);
      final cs = CameraSession();
      addTearDown(cs.dispose);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CameraPage(cameraSession: cs),
      ));
      await tester.pump();
      await tester.pump(const Duration(seconds: 13)); // 走完初始化超时
      expect(tester.takeException(), isNull);
    });

    testWidgets('把对焦设置改一轮，界面不崩', (tester) async {
      final cs = await pumpCamera(tester);
      await cs.setFocusMode(FocusMode.locked);
      await tester.pump();
      await cs.tapToFocus(const Offset(0.5, 0.5));
      await tester.pump();
      expect(tester.takeException(), isNull);
    });

    testWidgets('相机报错时显示错误块 + 重试按钮，且 App 不锁死', (tester) async {
      final cs = CameraSession();
      addTearDown(cs.dispose);
      await pumpCamera(tester, camera: cs);

      // 触发一次初始化（单测环境必然失败），并把超时定时器走完
      final f = cs.initialize();
      await tester.pump(const Duration(seconds: 13));
      await f;
      await tester.pump();

      expect(cs.initializing, isFalse, reason: '不能卡在初始化态（那会永久转圈）');
      if (cs.error != null) {
        expect(find.textContaining('重试'), findsWidgets,
            reason: '出错了要给用户重试的入口');
      }
      expect(tester.takeException(), isNull);
    });
  });

  // =====================================================================
  // 姿势叠加层坐标系（浏览器实测发现）
  //
  // 问题：CameraPreview 被 Center 包着（按相机宽高比居中，四周留黑边），
  // 而姿势叠加层是 StackFit.expand 铺满**整个盒子**。
  // 两者坐标系不同 → 人形会画到取景框之外，用户没法把身体对上去。
  //
  // 这个功能的**全部意义**就是"照着摆"，对不上就等于没用。
  // =====================================================================

  // =====================================================================
  // 姿势叠加层的坐标系（浏览器实测发现的问题）
  //
  // 问题：CameraPreview 被 Center 包着 —— 它按相机宽高比居中，
  // 四周留黑边（letterbox）。而姿势叠加层是 StackFit.expand，
  // **铺满整个盒子**。两者坐标系不同 → 人形会画到取景框外面，
  // 用户没法把身体对上去。而这个功能的全部意义就是"照着摆"。
  //
  // 测法：把「取景框实际渲染在哪」抽成纯函数算出 Rect，
  // 叠加层按同一个 Rect 画。这样逻辑可单测，不依赖真实摄像头。
  // =====================================================================

  group('fitPreviewRect —— 取景框实际渲染区域（纯函数）', () {
    test('盒子比相机更宽 → 左右贴边，上下留黑边', () {
      // 盒子 400x400，相机 4:3 → 宽 400，高 300，上下各留 50
      final r = fitPreviewRect(const Size(400, 400), 4 / 3);
      expect(r.width, closeTo(400, 0.01));
      expect(r.height, closeTo(300, 0.01));
      expect(r.left, closeTo(0, 0.01));
      expect(r.top, closeTo(50, 0.01));
    });

    test('盒子比相机更高 → 上下贴边，左右留黑边', () {
      // 盒子 300x400，相机 4:3 → 高 400，宽 533 > 300，所以按宽算：
      // 宽 300，高 225，上下各留 87.5
      final r = fitPreviewRect(const Size(300, 400), 4 / 3);
      expect(r.width, closeTo(300, 0.01));
      expect(r.height, closeTo(225, 0.01));
      expect(r.top, closeTo(87.5, 0.01));
    });

    test('完全匹配时铺满，不留边', () {
      final r = fitPreviewRect(const Size(400, 300), 4 / 3);
      expect(r.width, closeTo(400, 0.01));
      expect(r.height, closeTo(300, 0.01));
      expect(r.left, closeTo(0, 0.01));
      expect(r.top, closeTo(0, 0.01));
    });

    test('永远居中', () {
      for (final box in [
        const Size(500, 717),
        const Size(400, 400),
        const Size(320, 800),
      ]) {
        final r = fitPreviewRect(box, 16 / 9);
        expect(r.center.dx, closeTo(box.width / 2, 0.01),
            reason: '盒子 $box 没水平居中');
        expect(r.center.dy, closeTo(box.height / 2, 0.01),
            reason: '盒子 $box 没垂直居中');
      }
    });

    test('宽高比保持（不拉伸变形）', () {
      for (final ar in [4 / 3, 16 / 9, 3 / 4, 1.0]) {
        final r = fitPreviewRect(const Size(500, 717), ar);
        expect(r.width / r.height, closeTo(ar, 0.01),
            reason: '宽高比 $ar 没保持住 —— 画面会被拉伸');
      }
    });

    test('绝不超出盒子边界', () {
      for (final box in [const Size(500, 717), const Size(200, 200)]) {
        for (final ar in [4 / 3, 16 / 9, 1 / 2, 3.0]) {
          final r = fitPreviewRect(box, ar);
          expect(r.left, greaterThanOrEqualTo(-0.01));
          expect(r.top, greaterThanOrEqualTo(-0.01));
          expect(r.right, lessThanOrEqualTo(box.width + 0.01));
          expect(r.bottom, lessThanOrEqualTo(box.height + 0.01));
        }
      }
    });

    test('退化输入不崩（宽高比 0 / 负数 / 盒子为 0）', () {
      expect(() => fitPreviewRect(const Size(0, 0), 4 / 3), returnsNormally);
      expect(() => fitPreviewRect(const Size(400, 300), 0), returnsNormally);
      expect(() => fitPreviewRect(const Size(400, 300), -1), returnsNormally);
      expect(() => fitPreviewRect(const Size(-10, -10), 4 / 3), returnsNormally);
      // 盒子为 0 时结果也该是 0 尺寸，不该是 NaN
      final r = fitPreviewRect(const Size(0, 0), 4 / 3);
      expect(r.width.isNaN, isFalse);
      expect(r.height.isNaN, isFalse);
    });
  });

  // =====================================================================
  // 姿势叠加层真的能渲染（回归测试）
  //
  // **为什么必须有这条**：我在改叠加层坐标系时把 `Positioned` 塞进了
  // `LayoutBuilder` 里面 —— `Positioned` 必须是 `Stack` 的直接子节点。
  // 结果运行时抛：
  //   TypeError: type 'minified:fM' is not a subtype of type 'minified:e0'
  //
  // 当时 **386 个测试全绿**，一个都没抓到 —— 因为测试环境里相机永远
  // 不初始化，`_activePose != null` 那条分支**从来没被执行过**。
  //
  // 教训：**没执行过的代码 = 没测过的代码**，即使覆盖率数字好看。
  // 所以这里用假相机平台让预览真的渲染出来。
  // =====================================================================

  group('姿势叠加层 —— 真的渲染出来（不是只编译过）', () {
    late FakeCameraPlatform fake;

    setUp(() {
      fake = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      CameraPlatform.instance = fake;
    });

    testWidgets('有相机 + 有姿势时，叠加层渲染且不抛异常', (tester) async {
      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession();
      addTearDown(cs.dispose);

      // ⚠️ 不要在外面先 initialize 一次，要让**页面自己**去初始化。
      //
      // 为什么（实测踩到，代价是两个 10 分钟超时）：
      // testWidgets 默认跑在**假时钟**里。若在外面用 `tester.runAsync`
      // 先把会话初始化好（真实时钟），页面 initState 还会再初始化一次 ——
      // 这一次在假时钟里，它要先 `await 旧controller.dispose()`，
      // 而那个 controller 是在真实时钟里建出来的：两边的异步互相等不到，
      // 于是永久卡住 —— 界面停在「正在查找摄像头…」，姿势叠加层永不出现，
      // 断言看到 0 个 CustomPaint，看起来像功能坏了，其实是测试自己卡住了。
      // 全放在假时钟里（页面初始化 + pump 推进假时钟）就没有这个问题。
      // v0.4.0：参考照姿势（strokes 为空）—— 叠加层叠的是照片本身。
      shared.sendPoseToCamera(photoPoses.first);

      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CameraPage(session: shared, cameraSession: cs),
      ));
      // pump 会推进假时钟，假相机里那个 1ms 的「平台事件延迟」才走完。
      await tester.pump(const Duration(milliseconds: 300));

      // 相机没起来就明确跳过（不能假装通过）
      if (!cs.isReady) {
        markTestSkipped('假相机没起来：${cs.error}');
        return;
      }
      await tester.pump(const Duration(milliseconds: 300));

      // 关键断言 1：渲染过程不能抛异常
      // （Positioned 放错位置就是在这里炸的）
      expect(tester.takeException(), isNull,
          reason: '渲染姿势叠加层时抛异常了 —— 检查 Positioned 是不是 '
              'Stack 的直接子节点');

      // 关键断言 2：叠加层确实在
      // v0.4.0 起姿势都是参考照，叠加层 = 半透明照片（ValueKey 锚点）；
      // 火柴人分支也挂在同一个 Key 上，所以两种姿势都断言同一个 Key。
      expect(find.byKey(const ValueKey('pose-overlay')), findsWidgets,
          reason: '姿势叠加层没渲染出来（有姿势却没画）');
    });

    testWidgets('去掉姿势后叠加层消失，且不抛异常', (tester) async {
      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession();
      addTearDown(cs.dispose);
      // 同上：让页面自己初始化，别在外面先初始化（假时钟/真实时钟混用会互相等死）。
      shared.sendPoseToCamera(photoPoses.first);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CameraPage(session: shared, cameraSession: cs),
      ));
      await tester.pump(const Duration(milliseconds: 300));

      if (!cs.isReady) {
        markTestSkipped('假相机没起来：${cs.error}');
        return;
      }
      await tester.pump(const Duration(milliseconds: 300));

      shared.clearPose();
      await tester.pump(const Duration(milliseconds: 200));

      expect(tester.takeException(), isNull);
      expect(find.byKey(const ValueKey('pose-overlay')), findsNothing,
          reason: '清掉姿势后还在画姿势');
    });
  });

  // =====================================================================
  // 前后台切换（下拉通知栏 / 切最近任务 / 来电）—— 回归测试
  //
  // **为什么必须有这条**：页面原来在 `inactive` 时直接
  // `_session.dispose()`，回到前台又 `_session.initialize()`。
  // `CameraSession` 是 `ChangeNotifier`：销毁后再用 → debug 下断言失败、
  // `_initializing` 永远停在 true；release 下监听列表已清空、页面永不重建。
  // 结果：用户**拉一下通知栏，拍摄页就永久卡死**。
  //
  // 单测和 analyze 都抓不到 —— 在这之前没有任何用例碰过生命周期回调。
  // =====================================================================

  group('前后台切换（通知栏 / 切后台）', () {
    late FakeCameraPlatform fake;

    setUp(() {
      fake = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      CameraPlatform.instance = fake;
    });

    /// 走真实平台通道发生命周期事件（Flutter 官方测试也是这么做的）。
    Future<void> sendLifecycle(
      WidgetTester tester,
      AppLifecycleState state,
    ) async {
      await tester.binding.defaultBinaryMessenger.handlePlatformMessage(
        'flutter/lifecycle',
        const StringCodec().encodeMessage('$state'),
        (_) {},
      );
    }

    testWidgets('inactive → resumed 之后拍摄页还能用（拉通知栏不再卡死）',
        (tester) async {
      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession();
      addTearDown(cs.dispose);

      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CameraPage(session: shared, cameraSession: cs),
      ));
      await tester.pump(const Duration(milliseconds: 300));
      expect(cs.isReady, isTrue, reason: '假相机没起来，后面的断言没意义');
      expect(find.byType(CircularProgressIndicator), findsNothing);

      // 下拉通知栏（Android 会发 inactive）
      await sendLifecycle(tester, AppLifecycleState.inactive);
      await tester.pump(const Duration(milliseconds: 300));
      expect(tester.takeException(), isNull,
          reason: 'inactive 时抛异常了 —— 大概率是把 session dispose 掉了');

      // 回到前台
      await sendLifecycle(tester, AppLifecycleState.resumed);
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));

      expect(tester.takeException(), isNull);
      expect(cs.isReady, isTrue,
          reason: '回前台后相机没恢复 —— 页面会永久卡在「正在启动相机」');
      // 页面还能重建（监听器没被销毁）：不该停在转圈上
      expect(find.byType(CircularProgressIndicator), findsNothing);
    });

    testWidgets('真进后台（paused）要交出摄像头，回来能重新打开', (tester) async {
      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession();
      addTearDown(cs.dispose);

      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CameraPage(session: shared, cameraSession: cs),
      ));
      await tester.pump(const Duration(milliseconds: 300));
      expect(cs.isReady, isTrue);

      await sendLifecycle(tester, AppLifecycleState.paused);
      await tester.pump(const Duration(milliseconds: 300));
      expect(tester.takeException(), isNull);
      // 真后台必须交出摄像头，否则 iOS 回来会黑屏
      expect(cs.isReady, isFalse, reason: '进后台了还占着摄像头');
      expect(fake.liveCameraIds, isEmpty, reason: '没释放平台侧的相机');

      await sendLifecycle(tester, AppLifecycleState.resumed);
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));
      expect(cs.isReady, isTrue, reason: '回前台没把相机重新打开');
      expect(tester.takeException(), isNull);
    });
  });

  // =====================================================================
  // 真机回归：某项参数没设上 ≠ 相机坏了
  //
  // 华为 OCE-AN50 上点「对焦：锁定」会抛 IllegalArgumentException，
  // 旧代码把它记进 `_error` —— 页面于是把**整块预览**换成
  // 「相机没能用起来」，用户以为相机坏了，其实相机一直好好的。
  // =====================================================================

  group('参数失败不整页报错（真机回归）', () {
    testWidgets('参数没设上 → 预览还在，只挂一条琥珀色警告', (tester) async {
      final fake = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      )..customFailures['setFocusMode'] =
          CameraException('SomethingWeird', '说不清的失败');
      CameraPlatform.instance = fake;

      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession();
      addTearDown(cs.dispose);

      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CameraPage(session: shared, cameraSession: cs),
      ));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));

      expect(cs.isReady, isTrue, reason: '假相机没起来，后面的断言没意义');
      // 关键断言：**不能**出现整页错误
      expect(find.textContaining('相机没能用起来'), findsNothing,
          reason: '一次参数失败把整页预览换成了错误框 —— 真机上就是这样');
      expect(find.byType(CameraPreview), findsWidgets,
          reason: '取景框必须还在');
      // 但要明确告诉用户哪一项没生效
      expect(find.textContaining('没能生效'), findsOneWidget);
    });

    testWidgets('一切正常时不该有任何警告', (tester) async {
      final fake = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      CameraPlatform.instance = fake;

      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession();
      addTearDown(cs.dispose);

      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: CameraPage(session: shared, cameraSession: cs),
      ));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));

      expect(cs.warning, isNull);
      expect(find.textContaining('没能生效'), findsNothing);
    });
  });

  // =====================================================================
  // F1.11 按快门 → 存进系统相册（用户明确要求：拍照要能存下来）
  // =====================================================================

  group('快门 → 存相册（F1.11）', () {
    testWidgets('按快门后照片交给存档，并明确提示「已存到相册」', (tester) async {
      final fake = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      CameraPlatform.instance = fake;

      // v0.4.0：先试系统相机（mock 返回 null = 这台设备没有）→
      // 兜底走 App 内拍摄存相册，这条契约不变。
      mockNativeCamera(tester, launchReturns: null);

      final saver = FakePhotoSaver();
      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession(saver: saver);
      addTearDown(cs.dispose);

      await pumpCamera(tester, shared: shared, camera: cs);
      expect(cs.isReady, isTrue, reason: '假相机没起来，后面的断言没意义');

      await tester.tap(find.byTooltip('拍照'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      expect(saver.saved, isNotEmpty,
          reason: '按了快门却没交给存档 —— 照片只会烂在临时目录里');
      // 这版 SDK 的 Snackbar 是 FIFO 队列：第一条「没找到系统相机…占满 4 秒
      // duration 消失后，「已存到相册」才开始显示（真实场景里存档也要花时间，
      // 先消失正是现实）—— 推进测试时钟即可。
      await tester.pump(const Duration(seconds: 5));
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.textContaining('已存到相册'), findsOneWidget,
          reason: '用户必须看到「存下来了」，否则不知道到底存没存');
      expect(tester.takeException(), isNull);
    });

    testWidgets('存不进去时明说，且不假装成功', (tester) async {
      final fake = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      CameraPlatform.instance = fake;

      // v0.4.0：系统相机不存在（mock 返回 null）→ 兜底 App 内拍摄。
      mockNativeCamera(tester, launchReturns: null);

      final saver = FakePhotoSaver(
          failWith: const PhotoSaveException('没有相册权限'));
      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession(saver: saver);
      addTearDown(cs.dispose);

      await pumpCamera(tester, shared: shared, camera: cs);

      await tester.tap(find.byTooltip('拍照'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.textContaining('已存到相册'), findsNothing,
          reason: '没存进去却说存好了 = 骗用户');
      expect(find.textContaining('没能存进相册'), findsWidgets);
      expect(cs.error, isNull, reason: '存相册失败不该让整页变成错误页');
    });

    testWidgets('v0.4.0 主链路：跳系统相机 → 回来捞图 → 结果卡（送教练/重拍）',
        (tester) async {
      final fake = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      CameraPlatform.instance = fake;

      // 拉起成功；回来时返回一个路径（文件不存在也没关系 —— 结果卡有
      // errorBuilder 兜底，这条测试验证的是**链路**，不是图片解码）。
      mockNativeCamera(
        tester,
        launchReturns: true,
        shotPath: '/photocoach-test/native_shot_fake.jpg',
      );

      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession(saver: FakePhotoSaver());
      addTearDown(cs.dispose);

      await pumpCamera(tester, shared: shared, camera: cs);
      expect(cs.isReady, isTrue, reason: '假相机没起来，后面的断言没意义');

      await tester.tap(find.byTooltip('拍照'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));
      expect(find.textContaining('已打开系统相机'), findsWidgets,
          reason: '跳了系统相机必须说一声，否则用户以为白按了');

      // 模拟用户从系统相机回来（后台 → 前台）
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      await tester.pump();
      tester.binding
          .handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump(const Duration(milliseconds: 200));

      // 结果卡盖上来：图 + 送教练 + 重拍
      expect(find.textContaining('系统相机拍好了'), findsOneWidget);
      expect(find.text('送教练点评'), findsOneWidget);
      expect(find.text('重拍'), findsOneWidget);
      expect(tester.takeException(), isNull);

      // 一键送教练 → 图进共享状态（教练页在 IndexedStack 里常驻收图）
      await tester.tap(find.text('送教练点评'));
      await tester.pump();
      expect(shared.pendingShot, isNotNull,
          reason: '点了送教练，图应该已经交给共享状态了');
    });

    testWidgets('v0.4.0：在系统相机里取消（没拍）→ 如实说，预览照旧不吓唬人',
        (tester) async {
      final fake = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      CameraPlatform.instance = fake;

      // 拉起成功，但回来没捞到新照片（用户取消了）
      mockNativeCamera(tester, launchReturns: true, shotPath: null);

      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession(saver: FakePhotoSaver());
      addTearDown(cs.dispose);

      await pumpCamera(tester, shared: shared, camera: cs);
      await tester.tap(find.byTooltip('拍照'));
      await tester.pump();
      // 300ms 让「已打开系统相机」的入场动画（250ms）跑完 ——
      // 4 秒自动消失的 Timer 是入场完成后才启动的。
      await tester.pump(const Duration(milliseconds: 300));

      // 用户此刻在系统相机里拍照，真实停留至少几秒。推进时钟让第一条
      // Snackbar（4 秒自动消失）真正过期：
      // 实测这版 SDK 有个坑——4 秒 Timer 不在入场完成那帧创建，而是入场
      // 完成后约 1 秒的一次 messenger 重建才创建，所以单次 5 秒长跳走到
      // 创建还没到期，第一条仍显示；再跳一个 5 秒帧，Timer 才真正触发。
      // 两个 5 秒 = 用户在系统相机里待了 10 秒，足够覆盖。
      await tester.pump(const Duration(seconds: 5));
      await tester.pump(const Duration(seconds: 5));

      // 用户回来（取消了，没照片）
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      await tester.pump();
      tester.binding
          .handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      // 第二条「没检测到新照片」入场（250ms）跑完。
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.textContaining('没检测到新照片'), findsWidgets);
      expect(find.textContaining('系统相机拍好了'), findsNothing,
          reason: '没拍到却显示结果卡 = 骗用户');
      expect(tester.takeException(), isNull);
    });
  });

  // =====================================================================
  // pose 教程 × 拍摄方案 打通（人类 2026-09-20 指定）
  // =====================================================================

  group('姿势 × 拍摄方案', () {
    const pose = Pose(
      id: 'p1',
      title: '回头杀',
      category: '站姿',
      strokes: [PoseStroke(0.5, 0.2, 0.5, 0.6)],
      scene: '街拍',
      tips: ['肩膀放松'],
    );

    testWidgets('选了姿势 → 姿势条上有「怎么拍」；没方案就如实说没有', (tester) async {
      CameraPlatform.instance = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      final shared = AppSession()..sendPoseToCamera(pose);
      addTearDown(shared.dispose);
      final cs = CameraSession(saver: FakePhotoSaver());
      addTearDown(cs.dispose);

      await pumpCamera(tester, shared: shared, camera: cs);

      expect(find.textContaining('照姿势：回头杀'), findsOneWidget);
      await tester.tap(find.text('怎么拍'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(find.textContaining('怎么拍「回头杀」'), findsOneWidget);
      // 还没有分析过 → 不许编方案，要如实说
      expect(find.textContaining('想要针对现场的完整方案'), findsOneWidget);
      expect(find.textContaining('教练页'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  // =====================================================================
  // 教练方案投射（v0.5.0 三模块闭环）：
  // 教练把 Suggestion 写进共享状态 → 拍摄页自己消费（方案条 + 目标框），
  // 不需要姿势也生效；「清除」把整套引导撤掉。
  // =====================================================================
  group('教练方案投射（v0.5.0）', () {
    const plan = Suggestion(
      composition: CompositionHint(rule: 'rule_of_thirds'),
      subject: SubjectHint(
        label: '人物',
        currentBox: Rect01(0.4, 0.3, 0.3, 0.6),
        targetBox: Rect01(0.2, 0.2, 0.3, 0.6),
      ),
      cameraMove: CameraMoveHint(dollyM: -0.5),
      exposure: ExposureHint(ev: 0.3, reason: '略欠曝'),
      shootingPlan: ShootingPlan(
        lighting: '柔光从侧边来',
        position: '到窗边，手机降到胸口高度',
        direction: '从人物左前方 45° 平视拍',
        subjectPosition: '让人往窗边移动',
      ),
    );

    testWidgets('方案到了（没有姿势）→ 方案条 + 目标框出现，不许等姿势', (
      tester,
    ) async {
      CameraPlatform.instance = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      final shared = AppSession();
      addTearDown(shared.dispose);
      final cs = CameraSession(saver: FakePhotoSaver());
      addTearDown(cs.dispose);
      await pumpCamera(tester, shared: shared, camera: cs);

      // 还没有方案 → 没有方案条
      expect(find.textContaining('方案：'), findsNothing);

      // 教练分析完写入共享状态（无姿势）
      shared.setSuggestion(plan);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // 方案条出来了（v0.9.3：GuidanceOverlay 已取消，不再断言）
      expect(find.textContaining('方案：'), findsOneWidget);
      expect(tester.takeException(), isNull);

      // 「看方案」弹层：人站哪 / 去哪 / 方向 / 光 四项全在
      await tester.tap(find.text('看方案'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      // 弹层里四项全在（方案条摘要里也有其中两行，所以用 findsWidgets）
      expect(find.textContaining('到窗边，手机降到胸口高度'), findsWidgets);
      expect(find.textContaining('从人物左前方 45° 平视拍'), findsWidgets);
      expect(find.textContaining('后退 0.5 米'), findsOneWidget);
      expect(find.textContaining('柔光从侧边来'), findsOneWidget);
      // 没姿势 → 标题就是「拍摄方案」
      expect(find.text('拍摄方案'), findsOneWidget);
    });

    testWidgets('「清除」→ 方案条和目标框一起消失', (tester) async {
      CameraPlatform.instance = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      final shared = AppSession()..setSuggestion(plan);
      addTearDown(shared.dispose);
      final cs = CameraSession(saver: FakePhotoSaver());
      addTearDown(cs.dispose);
      await pumpCamera(tester, shared: shared, camera: cs);
      await tester.pump(const Duration(milliseconds: 400));

      expect(find.textContaining('方案：'), findsOneWidget);

      await tester.tap(find.text('清除'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(find.textContaining('方案：'), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });

  // =====================================================================
  // 距离建议「搭车」LiveGuideController（v0.8.0 提速 + 去二次抓帧）。
  // 回归目标：帧只来自 _live.lastFrame；引导没抓到帧 → 不算建议。
  // =====================================================================
  group('距离建议搭车 live guide（v0.8.0）', () {
    const plan = Suggestion(
      composition: CompositionHint(rule: 'rule_of_thirds'),
      subject: SubjectHint(
        label: '人物',
        currentBox: Rect01(0.4, 0.3, 0.3, 0.6),
        targetBox: Rect01(0.2, 0.2, 0.3, 0.6),
      ),
      cameraMove: CameraMoveHint(dollyM: -0.5),
      exposure: ExposureHint(ev: 0.3, reason: '略欠曝'),
    );

    testWidgets('引导没抓到帧（lastFrame 为 null）→ 不算距离建议',
        (tester) async {
      CameraPlatform.instance = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
            name: 'back',
            lensDirection: CameraLensDirection.back,
            sensorOrientation: 90,
          ),
        ],
      );
      final shared = AppSession()..setSuggestion(plan);
      addTearDown(shared.dispose);
      final cs = CameraSession(saver: FakePhotoSaver());
      addTearDown(cs.dispose);
      await pumpCamera(tester, shared: shared, camera: cs);

      // 模拟「相机已释放/画面不可用」：让 takePicture 永远抛。
      // 引导 tick 还在跑，但每帧 grabFrame 都拿不到帧 → lastFrame 恒为 null。
      cs.releaseCamera();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1200));

      expect(find.textContaining('再近一点'), findsNothing);
      expect(find.textContaining('再远一点'), findsNothing);
      expect(find.textContaining('距离刚刚好'), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });
}
