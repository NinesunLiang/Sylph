import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/poses/poses_page.dart';

/// F3.8 图片模式（左右滑切换）的回归测试。
///
/// 锁死的两条硬边界（人类原话）：
/// 1. 姿势进入图片模式后，**左右滑能切换**（下一张 / 上一张）；
/// 2. **退出图片模式后不能再左右切换**（回网格，横向手势无效）。
void main() {
  Future<void> pumpGrid(WidgetTester tester) async {
    tester.view.physicalSize = const Size(390, 900) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(
      theme: ThemeData.dark(),
      home: const PosesPage(),
    ));
    await tester.pump();
  }

  /// 横向滑一笔（[delta] 正 = 向右滑）。
  /// 在图片模式里找 PageView，在网格找 GridView。
  Future<void> dragHorizontal(WidgetTester tester, double delta) async {
    final target = find.byType(PageView).evaluate().isNotEmpty
        ? find.byType(PageView)
        : find.byType(GridView);
    await tester.drag(target, Offset(delta, 0), warnIfMissed: false);
    await tester.pump();
  }

  /// 找参考照卡片（InkWell 嵌在 GridView 里的）。
  Finder cards() => find.descendant(
      of: find.byType(GridView),
      matching: find.byType(InkWell),
    );

  /// 第一张参考照卡片。
  Finder firstCard() => cards().first;

  group('图片模式 · 进入', () {
    testWidgets('点第一张卡片 → 进入图片模式（PageView 出现）', (tester) async {
      await pumpGrid(tester);
      await tester.tap(firstCard().first);
      await tester.pumpAndSettle();

      expect(find.byType(PageView), findsOneWidget,
          reason: '点卡片后应进入图片模式（PageView）');
      expect(find.text('退出图片模式'), findsOneWidget);
      expect(find.text('送到拍摄页'), findsOneWidget);
    });

    testWidgets('AppBar 显示当前序号', (tester) async {
      await pumpGrid(tester);
      await tester.tap(firstCard().first);
      await tester.pumpAndSettle();

      expect(find.textContaining('（1/'), findsOneWidget,
          reason: 'AppBar 应显示当前张数序号');
    });
  });

  group('图片模式 · 左右滑切换（需求①）', () {
    testWidgets('向左滑 → 切到下一张（序号 +1）', (tester) async {
      await pumpGrid(tester);
      await tester.tap(firstCard().first);
      await tester.pumpAndSettle();
      expect(find.textContaining('（1/'), findsOneWidget);

      await dragHorizontal(tester, -200);
      await tester.pumpAndSettle();

      expect(find.textContaining('（2/'), findsOneWidget,
          reason: '向左滑后应切到第 2 张');
    });

    testWidgets('向右滑 → 回到上一张（序号 -1）', (tester) async {
      await pumpGrid(tester);
      await tester.tap(firstCard().first);
      await tester.pumpAndSettle();

      await dragHorizontal(tester, -200);
      await tester.pumpAndSettle();
      expect(find.textContaining('（2/'), findsOneWidget);

      await dragHorizontal(tester, 200);
      await tester.pumpAndSettle();

      expect(find.textContaining('（1/'), findsOneWidget,
          reason: '向右滑应回到第 1 张');
    });

    testWidgets('在边界上滑 → 不越界（还是第 1 张）', (tester) async {
      await pumpGrid(tester);
      await tester.tap(firstCard().first);
      await tester.pumpAndSettle();

      await dragHorizontal(tester, 200);
      await tester.pumpAndSettle();

      expect(find.textContaining('（1/'), findsOneWidget,
          reason: '边界上滑不应越界');
    });

    testWidgets('边界上不显示方向箭头', (tester) async {
      await pumpGrid(tester);
      // 网格只渲染可见的卡片（约 6 张），取中间位置（不在边界）。
      final visibleCount = cards().evaluate().length;
      expect(visibleCount, greaterThan(2),
          reason: '网格至少要有 3 张以上卡片才能测中间位置');
      await tester.tap(cards().at(visibleCount ~/ 2));
      await tester.pumpAndSettle();

      // 中间位置：两个箭头都应该出现。
      expect(find.byKey(const ValueKey('swipe-prev')), findsOneWidget,
          reason: '中间位置应有左箭头');
      expect(find.byKey(const ValueKey('swipe-next')), findsOneWidget,
          reason: '中间位置应有右箭头');

      // 逐笔拖到最后一张（边界）。
      for (var i = 0; i < 300; i++) {
        if (find.byKey(const ValueKey('swipe-next')).evaluate().isEmpty &&
            find.byKey(const ValueKey('swipe-prev')).evaluate().isEmpty) {
          break;
        }
        await dragHorizontal(tester, -200);
        await tester.pumpAndSettle();
      }
      // 边界上两个箭头都不显示（没东西可切）。
      expect(find.byKey(const ValueKey('swipe-next')), findsNothing,
          reason: '最后一张时右箭头不该出现');
      expect(find.byKey(const ValueKey('swipe-prev')), findsNothing,
          reason: '最后一张时左箭头也不该出现（边界）');
    });

    testWidgets('点边缘箭头也能切', (tester) async {
      await pumpGrid(tester);
      // 点中间卡片（不在边界，右箭头才存在）。
      final visibleCount = cards().evaluate().length;
      await tester.tap(cards().at(visibleCount ~/ 2));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const ValueKey('swipe-next')));
      await tester.pumpAndSettle();

      // 序号应该 +1（从中间跳到中间+1）。
      final after = visibleCount ~/ 2 + 1;
      expect(find.textContaining('（${after + 1}/'), findsOneWidget,
          reason: '点右箭头后序号应 +1');
    });
  });

  group('图片模式 · 退出后不切（需求②硬边界）', () {
    testWidgets('退出 → 回网格，横向滑不切换', (tester) async {
      await pumpGrid(tester);
      await tester.tap(firstCard().first);
      await tester.pumpAndSettle();
      expect(find.byType(PageView), findsOneWidget);

      await dragHorizontal(tester, -200);
      await tester.pumpAndSettle();
      expect(find.textContaining('（2/'), findsOneWidget);

      await tester.tap(find.text('退出图片模式'));
      await tester.pumpAndSettle();

      expect(find.byType(PageView), findsNothing,
          reason: '退出后应回网格');
      expect(find.byType(GridView), findsOneWidget);

      await dragHorizontal(tester, -200);
      await tester.pumpAndSettle();
      await dragHorizontal(tester, 200);
      await tester.pumpAndSettle();

      expect(find.textContaining('（2/'), findsNothing,
          reason: '退出图片模式后左右滑不应再切换姿势');
      expect(find.text('退出图片模式'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('退出后再点另一张 → 重新进入图片模式', (tester) async {
      await pumpGrid(tester);
      await tester.tap(firstCard().first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('退出图片模式'));
      await tester.pumpAndSettle();
      expect(find.byType(GridView), findsOneWidget);

      // 网格只显示可见的卡片（~6 张）；最后一张可能在视口外（tap 打不到）。
      // 取第一张（一定可见）+ 非第一张（避免和「进入」那张一样）。
      final count = cards().evaluate().length;
      expect(count, greaterThan(0));
      // 取第二张（index 1），既保证可见，又和之前进入的不同
      await tester.tap(cards().at(1));
      await tester.pumpAndSettle();

      expect(find.byType(PageView), findsOneWidget,
          reason: '退出后再点卡片应能重新进入图片模式');
    });
  });
}
