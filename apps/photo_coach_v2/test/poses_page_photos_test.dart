import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/poses/pose.dart';
import 'package:photo_coach_v2/features/poses/poses_page.dart';

/// UI 回归：姿势页（v0.4.0 起 = 参考照库）的 性別/姿态 两级筛选
/// + **点图翻面看指导** + 无照片姿势的详情页防御。
///
/// 为什么这几条必须有：翻面是个纯视觉行为，光靠"我写了 Transform"不算数。
/// 这里断言的是「翻之前看不到指导、翻之后看得到」——翻错了会红。
///
/// v0.4.0：火柴人库删除后，参考照是姿势页**唯一**模式（没有模式切换了），
/// 性別/姿态筛选从打开页面就在。
void main() {
  Future<void> pumpPage(WidgetTester tester, {Size size = const Size(390, 900)}) async {
    tester.view.physicalSize = size * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(
      theme: ThemeData.dark(),
      home: const PosesPage(),
    ));
    await tester.pump();
  }

  /// v0.4.0 前这里要 tap「参考照」chip 切模式；
  /// 火柴人库删除后参考照是唯一模式，筛选行从打开页面就在 —— 只剩一次 pump。
  Future<void> switchToPhotos(WidgetTester tester) async {
    await tester.pump();
  }

  group('姿势页 · 参考照库（唯一模式）', () {
    testWidgets('默认即参考照：性別/姿态两级筛选直接出现，不用切模式', (tester) async {
      await pumpPage(tester);
      // v0.4.0：不再「先火柴人、切参考照才有筛选」—— 打开就是筛选
      expect(find.text('性別'), findsOneWidget);
      expect(find.text('姿态'), findsOneWidget);
      // 一级分类里必须有 女
      expect(find.text('女'), findsWidgets);
      // 搜索框也在
      expect(find.byType(TextField), findsOneWidget);
    });

    testWidgets('点「女」之后出现站/坐/躺三个姿态', (tester) async {
      await pumpPage(tester);
      await switchToPhotos(tester);
      await tester.tap(find.text('女').first);
      await tester.pumpAndSettle();

      for (final p in ['站', '坐', '躺']) {
        expect(find.text(p), findsWidgets, reason: '缺姿态「$p」');
      }
    });

    testWidgets('渲染出多张参考照卡片（不是白屏）', (tester) async {
      await pumpPage(tester);
      await switchToPhotos(tester);
      final n = photoPoses
          .where((p) => find.text(p.title).evaluate().isNotEmpty)
          .length;
      expect(n, greaterThanOrEqualTo(3), reason: '参考照卡片渲染太少');
    });

    testWidgets('点「躺」之后只剩躺姿的图', (tester) async {
      await pumpPage(tester);
      await switchToPhotos(tester);
      await tester.tap(find.text('女').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('躺').first);
      await tester.pumpAndSettle();

      final lying = PoseCatalog.photos(gender: '女', posture: '躺');
      final standing = PoseCatalog.photos(gender: '女', posture: '站');
      expect(lying, isNotEmpty);

      final shown = lying
          .where((p) => find.text(p.title).evaluate().isNotEmpty)
          .length;
      expect(shown, greaterThan(0), reason: '筛「躺」之后一张都没显示');

      final wrong = standing
          .where((p) => find.text(p.title).evaluate().isNotEmpty)
          .length;
      expect(wrong, 0, reason: '筛「躺」时混进了站姿 $wrong 张');
    });

    testWidgets('男图进来之后，「男」能筛出站/坐（不再点了是空的）', (tester) async {
      await pumpPage(tester);
      await switchToPhotos(tester);

      expect(find.text('男'), findsWidgets, reason: '「男」分类没出现');
      await tester.tap(find.text('男').first);
      await tester.pumpAndSettle();

      // 二级只剩 站/坐（男按约定不做躺）
      expect(find.text('站'), findsWidgets);
      expect(find.text('坐'), findsWidgets);
      expect(find.text('躺'), findsNothing, reason: '男不该出现躺姿');

      final men = PoseCatalog.photos(gender: '男');
      expect(men, isNotEmpty, reason: '男分类里一张图都没有');
      final shown =
          men.where((p) => find.text(p.title).evaluate().isNotEmpty).length;
      expect(shown, greaterThan(0), reason: '点「男」之后一张卡片都没渲染');
    });

    testWidgets('窄屏不溢出', (tester) async {
      await pumpPage(tester, size: const Size(320, 800));
      await switchToPhotos(tester);
      expect(tester.takeException(), isNull);
    });
  });

  group('姿势详情页 · 点图翻面', () {
    Future<void> pumpDetail(WidgetTester tester, Pose pose) async {
      tester.view.physicalSize = const Size(390, 900) * 3;
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: PoseDetailPage(pose: pose),
      ));
      await tester.pump();
    }

    testWidgets('翻面之前：看到照片提示，看不到指导正文', (tester) async {
      final pose = photoPoses.first;
      await pumpDetail(tester, pose);
      expect(find.text('点一下翻面看怎么拍'), findsOneWidget);
      // 指导里的动作原文此时不该在屏幕上（背面还没转过来）
      expect(find.text(pose.guidance!.action), findsNothing);
    });

    testWidgets('点一下图 → 翻面，指导出现', (tester) async {
      final pose = photoPoses.first;
      await pumpDetail(tester, pose);

      await tester.tap(find.text('翻面看细节（镜头 / 动作 / 表情）'));
      await tester.pumpAndSettle();

      expect(find.text(pose.guidance!.action), findsOneWidget, reason: '翻面后看不到动作');
      expect(find.text(pose.guidance!.expression), findsOneWidget, reason: '翻面后看不到表情');
      expect(find.text(pose.guidance!.why), findsWidgets, reason: '翻面后看不到为什么好看');
    });

    testWidgets('再点一下 → 翻回照片', (tester) async {
      final pose = photoPoses.first;
      await pumpDetail(tester, pose);

      await tester.tap(find.text('翻面看细节（镜头 / 动作 / 表情）'));
      await tester.pumpAndSettle();
      expect(find.text(pose.guidance!.action), findsOneWidget);

      // 翻回去要用卡片**外面**那个按钮 —— 点图在手势上不通（见 _flipButton 注释）
      await tester.tap(find.text('翻回看照片'));
      await tester.pumpAndSettle();
      expect(find.text(pose.guidance!.action), findsNothing, reason: '没翻回去');
    });

    testWidgets('背面信息齐：镜头 / 动作 / 表情 / 好看 四行都在', (tester) async {
      final pose = photoPoses.first;
      await pumpDetail(tester, pose);
      await tester.tap(find.text('翻面看细节（镜头 / 动作 / 表情）'));
      await tester.pumpAndSettle();

      for (final k in ['镜头', '动作', '表情', '好看']) {
        expect(find.text(k), findsOneWidget, reason: '背面缺「$k」这一行');
      }
    });

    // v0.9.0：指导卡提到「这张为什么好看」之前 → 断言卡片顺序，
    // 锁定「小白先看到怎么拍，再看为什么好看」的阅读顺序。
    // 注意：ListView 只构建视口内的卡片，所以这里只比「都可见」时的 y 序，
    // 而不是比「都存在」（视口外不构建）。
    testWidgets('卡片顺序：这张怎么拍 → 这张为什么好看 → 拍摄要点', (tester) async {
      final pose = photoPoses.first;
      await pumpDetail(tester, pose);
      // 「这张怎么拍」永远在视口内（最上面的卡）
      expect(find.text('这张怎么拍'), findsOneWidget);
      // 「拍摄要点」可能滚出视口 → 只在可见时比位置
      final howFound = find.text('这张怎么拍').evaluate();
      final tipsFound = find.text('拍摄要点').evaluate();
      final whyFound = find.text('这张为什么好看').evaluate();
      if (whyFound.isNotEmpty && tipsFound.isNotEmpty && howFound.isNotEmpty) {
        final pHow = tester.getTopLeft(find.text('这张怎么拍'));
        final pWhy = tester.getTopLeft(find.text('这张为什么好看'));
        final pTips = tester.getTopLeft(find.text('拍摄要点'));
        expect(pWhy.dy, greaterThan(pHow.dy), reason: '「为什么好看」应在「怎么拍」之后');
        expect(pTips.dy, greaterThan(pWhy.dy), reason: '「拍摄要点」应在「为什么好看」之后');
      }
    });

    testWidgets('无照片姿势（脏数据防御）：详情页不崩，退回占位图', (tester) async {
      // v0.4.0 火柴人库已删，这里用合成姿势覆盖「没有照片」这条分支：
      // 详情页正面必须退回占位图，而不是 `imagePath!` 崩掉
      //（v1 就有过「无照片姿势把 App 画崩」的实机崩溃史）。
      const noPhoto = Pose(
        id: 'no_photo_test',
        title: '合成无照片姿势',
        category: '站姿',
        strokes: [
          PoseStroke(0.5, 0.1, 0.5, 0.6),
          PoseStroke(0.5, 0.2, 0.3, 0.5),
          PoseStroke(0.5, 0.2, 0.7, 0.5),
        ],
      );
      await pumpDetail(tester, noPhoto);
      expect(tester.takeException(), isNull,
          reason: '无照片姿势把详情页画崩了 —— v1 崩溃史重演');
      expect(find.text('这张为什么好看'), findsNothing,
          reason: '没有指导数据，不该出现「为什么好看」卡');
    });
  });
}
