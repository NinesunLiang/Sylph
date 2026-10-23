import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';
import 'package:photo_coach_v2/features/guidance/alignment.dart';
import 'package:photo_coach_v2/features/guidance/guidance_overlay.dart';

/// 引导图层的渲染测试。
///
/// 为什么值得测：真正的取景框效果只能在真机上看，但「有实时数据时画不画、
/// 数据缺失时会不会崩」这两件事在这里就能锁住 —— 而它们正是最容易出问题的地方。

Suggestion makeSuggestion({Rect01? current, Rect01? target}) => Suggestion(
      composition: const CompositionHint(rule: 'rule_of_thirds', confidence: 0.8),
      subject: SubjectHint(
        label: 'person',
        currentBox: current,
        targetBox: target,
      ),
      cameraMove: const CameraMoveHint(hint: '向左半步'),
      exposure: const ExposureHint(ev: -0.3, reason: '高光过曝'),
      tips: const ['主体放在左三分之一线'],
    );

Future<void> pumpOverlay(
  WidgetTester tester, {
  required Suggestion suggestion,
  Rect01? liveBox,
  AlignFeedback? liveFeedback,
  String liveStatus = '',
}) async {
  // 用接近真机的窄屏尺寸：宽 390。窄屏才容易暴露溢出问题。
  tester.view.physicalSize = const Size(390 * 3, 844 * 3);
  tester.view.devicePixelRatio = 3.0;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: GuidanceOverlay(
          suggestion: suggestion,
          liveBox: liveBox,
          liveFeedback: liveFeedback,
          liveStatus: liveStatus,
        ),
      ),
    ),
  );
  await tester.pump();
}

void main() {
  const target = Rect01(0.333, 0.22, 0.334, 0.56);

  // 框上的文字（「目标」「实时」）是 CustomPainter 画在 canvas 上的，不是 Text widget，
  // find.text 查不到。所以这里断言「有 CustomPaint 且渲染没报错」。
  Finder guidancePaint() =>
      find.byWidgetPredicate((w) => w is CustomPaint && w.painter != null);

  testWidgets('只有静态建议时能正常渲染（画目标框）', (tester) async {
    await pumpOverlay(tester, suggestion: makeSuggestion(target: target));
    expect(tester.takeException(), isNull);
    expect(guidancePaint(), findsWidgets);
    // 兜底提示条是真 widget，能查到；框上的「目标」二字是 canvas 画的，查不到
    expect(find.textContaining('向左半步'), findsOneWidget);
  });

  testWidgets('完全没有坐标时也不崩（只画网格）', (tester) async {
    await pumpOverlay(tester, suggestion: makeSuggestion());
    expect(tester.takeException(), isNull);
    // 没开实时 → 不该出现实时反馈条
    expect(find.textContaining('还没测到主体'), findsNothing);
  });

  testWidgets('主体偏小时，反馈条让人靠近', (tester) async {
    // 主体只占 8%（目标约 19%）→ 应该先提示靠近
    await pumpOverlay(
      tester,
      suggestion: makeSuggestion(target: target),
      liveBox: const Rect01(0.1, 0.3, 0.2, 0.4),
      liveFeedback: compareAlignment(
        const Rect01(0.1, 0.3, 0.2, 0.4),
        target,
      ),
    );
    expect(tester.takeException(), isNull);
    // v0.9.3：文案改人话（「走近一点」替代「靠近（主体只占画面X%）」）
    expect(find.textContaining('走近'), findsOneWidget);
    expect(find.textContaining('主体占画面'), findsOneWidget);
  });

  testWidgets('主体大小合适但偏左 → 反馈条让镜头往左摇', (tester) async {
    const cur = Rect01(0.05, 0.25, 0.30, 0.50);
    await pumpOverlay(
      tester,
      suggestion: makeSuggestion(target: target),
      liveBox: cur,
      liveFeedback: compareAlignment(cur, target),
    );
    expect(tester.takeException(), isNull);
    // 主体偏左、目标在右 → 相机要往左摇（往右摇会把主体推得更左）
    expect(find.textContaining('向左移'), findsOneWidget);
  });

  testWidgets('对齐时显示「保持不动」', (tester) async {
    await pumpOverlay(
      tester,
      suggestion: makeSuggestion(target: target),
      liveBox: target,
      liveFeedback: compareAlignment(target, target),
    );
    expect(find.textContaining('保持不动'), findsOneWidget);
  });

  testWidgets('开了实时但没测到主体 → 显示原因，不显示假框', (tester) async {
    await pumpOverlay(
      tester,
      suggestion: makeSuggestion(target: target),
      liveStatus: '没找到主体：主体和背景颜色接近',
    );
    expect(tester.takeException(), isNull);
    expect(find.textContaining('没找到主体'), findsOneWidget);
  });

  testWidgets('边界坐标（贴边、极小）不崩', (tester) async {
    await pumpOverlay(
      tester,
      suggestion: makeSuggestion(
        current: const Rect01(0, 0, 0.02, 0.02),
        target: const Rect01(0.98, 0.98, 0.02, 0.02),
      ),
      liveBox: const Rect01(0, 0, 1, 1),
      liveFeedback: compareAlignment(const Rect01(0, 0, 1, 1), target),
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('地平线倾斜提示能渲染', (tester) async {
    final s = Suggestion(
      composition: const CompositionHint(
        rule: 'rule_of_thirds',
        horizonTiltDeg: -6,
      ),
      subject: const SubjectHint(targetBox: target),
      cameraMove: const CameraMoveHint(),
      exposure: const ExposureHint(),
    );
    await pumpOverlay(tester, suggestion: s);
    expect(tester.takeException(), isNull);
  });
}
