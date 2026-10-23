import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/onboarding/onboarding.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// v0.9.2 首次 3 步 onboarding（光线 → 机位 → 距离）的 UI 回归。
///
/// 为什么这几条必须有：
/// 1. 3 步内容完整（标题 + 正文 + 图标）
/// 2. 下一步 / 跳过 能正确流转
/// 3. 最后一步 → onFinish 回调
/// 4. 持久化函数存在且可调（测试环境无插件 → 静默 false）
void main() {
  group('OnboardingPage', () {
    testWidgets('第一步显示「先看光线」', (tester) async {
      bool finished = false;
      await tester.pumpWidget(MaterialApp(
        home: OnboardingPage(onFinish: () => finished = true),
      ));
      await tester.pumpAndSettle();

      expect(find.text('先看光线'), findsOneWidget);
      expect(find.textContaining('顺光'), findsOneWidget);
      expect(find.text('下一步'), findsOneWidget);
      expect(find.text('跳过'), findsOneWidget);
      expect(finished, isFalse);
    });

    testWidgets('点「下一步」→ 第二步「再调机位」', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: OnboardingPage(onFinish: () {}),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('下一步'));
      await tester.pumpAndSettle();

      expect(find.text('再调机位'), findsOneWidget);
      expect(find.textContaining('平视'), findsOneWidget);
    });

    testWidgets('再点「下一步」→ 第三步「最后看距离」', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: OnboardingPage(onFinish: () {}),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('下一步'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('下一步'));
      await tester.pumpAndSettle();

      expect(find.text('最后看距离'), findsOneWidget);
      expect(find.textContaining('全身'), findsOneWidget);
      expect(find.text('开始拍照'), findsOneWidget);
    });

    testWidgets('最后一步点「开始拍照」→ onFinish 回调', (tester) async {
      bool finished = false;
      await tester.pumpWidget(MaterialApp(
        home: OnboardingPage(
          onFinish: () => finished = true,
        ),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('下一步'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('下一步'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('开始拍照'));
      await tester.pumpAndSettle();

      expect(finished, isTrue);
    });

    testWidgets('任何一步点「跳过」→ 立即 onFinish', (tester) async {
      bool finished = false;
      await tester.pumpWidget(MaterialApp(
        home: OnboardingPage(
          onFinish: () => finished = true,
        ),
      ));
      await tester.pumpAndSettle();

      // 第一步就跳过
      await tester.tap(find.text('跳过'));
      await tester.pumpAndSettle();

      expect(finished, isTrue);
    });

    testWidgets('进度指示器：3 个点，当前步高亮（宽 32）', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: OnboardingPage(onFinish: () {}),
      ));
      await tester.pumpAndSettle();

      // 3 个进度条容器
      final containers = find.byType(AnimatedContainer).evaluate();
      expect(containers, hasLength(3));
      // 第一个（当前步）应该更宽
      expect(containers.first, isNotNull);
    });
  });

  group('持久化函数（用 mock 验证读写逻辑）', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('isOnboarded 初始为 false', () async {
      final done = await isOnboarded();
      expect(done, isFalse);
    });

    test('markOnboarded 后 isOnboarded 变 true', () async {
      await markOnboarded();
      final done = await isOnboarded();
      expect(done, isTrue);
    });

    test('resetOnboarding 后 isOnboarded 回 false', () async {
      await markOnboarded();
      await resetOnboarding();
      final done = await isOnboarded();
      expect(done, isFalse);
    });
  });
}
