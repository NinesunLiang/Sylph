import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/analysis/distance_advisor.dart';
import 'package:photo_coach_v2/features/analysis/face_light.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';
import 'package:photo_coach_v2/features/poses/pose.dart';
import 'package:photo_coach_v2/features/poses/pose_guidance_text.dart';
import 'package:photo_coach_v2/features/poses/poses_page.dart';

/// v0.9.0 环境&机位&姿势 指导 —— 回归测试。
///
/// 产品目标：小白选完姿势，不查教程、不配 API Key，也能知道
/// 手机放多高、人朝哪、站多远。本文件锁死这条「离线可懂的指导链」：
///
/// 1. DistanceAdvice.position（距离刻度条的连续量）
/// 2. poseGuidanceLines（术语 → 人话翻译表，250 张参考照全覆盖）
/// 3. 姿势页景别筛选 + 卡片机位副标题
void main() {
  // ────────────────────────────────────────────────────────────
  // 1. DistanceAdvice.position —— 距离刻度的连续量
  // ────────────────────────────────────────────────────────────
  group('DistanceAdvice.position（v0.9.0 距离刻度）', () {
    const advisor = DistanceAdvisor();

    Rect01 box(double h) => Rect01(0.3, 0.1, 0.4, h);

    test('半身：faceH 在 okay 区间内 → position 线性 0..1', () {
      // 半身 okay = [0.28, 0.55]
      final low = advisor.advise(faceFound: true, faceBox: box(0.28));
      final mid = advisor.advise(faceFound: true, faceBox: box(0.415));
      final high = advisor.advise(faceFound: true, faceBox: box(0.55));
      expect(low.position, closeTo(0.0, 1e-9));
      expect(mid.position, closeTo(0.5, 1e-9));
      expect(high.position, closeTo(1.0, 1e-9));
    });

    test('太近/太远/模糊区都 clamp 到 [0,1]，不穿板', () {
      // 半身阈值：tooFarMax=0.18（模糊区起点）、tooCloseMin=0.75（模糊区终点）
      final tooFar = advisor.advise(faceFound: true, faceBox: box(0.05));
      expect(tooFar.level, DistanceLevel.tooFar);
      expect(tooFar.position, closeTo(0.0, 1e-9));

      final tooClose = advisor.advise(faceFound: true, faceBox: box(0.9));
      expect(tooClose.level, DistanceLevel.tooClose);
      expect(tooClose.position, closeTo(1.0, 1e-9));

      final fuzzyFar = advisor.advise(faceFound: true, faceBox: box(0.22));
      expect(fuzzyFar.level, DistanceLevel.tooFar);
      expect(fuzzyFar.position, closeTo(0.0, 1e-9));

      final fuzzyClose = advisor.advise(faceFound: true, faceBox: box(0.65));
      expect(fuzzyClose.level, DistanceLevel.tooClose);
      expect(fuzzyClose.position, closeTo(1.0, 1e-9));
    });

    test('全身景别用全身阈值（0.08..0.22），不是半身阈值', () {
      final a = advisor.advise(
          faceFound: true, faceBox: box(0.08), framing: '全身');
      expect(a.level, DistanceLevel.okay);
      expect(a.position, closeTo(0.0, 1e-9));
    });

    test('unknown（没脸没主体）→ position 为 null（画中性刻度）', () {
      final a = advisor.advise(faceFound: false, faceBox: null);
      expect(a.level, DistanceLevel.unknown);
      expect(a.position, isNull);
    });
  });

  // ────────────────────────────────────────────────────────────
  // 2. poseGuidanceLines —— 术语 → 人话
  // ────────────────────────────────────────────────────────────
  group('poseGuidanceLines（机位术语 → 人话）', () {
    PoseGuidance g(String h, String d, String f) => PoseGuidance(
          cameraHeight: h,
          direction: d,
          framing: f,
          action: 'a',
          expression: 'e',
          why: 'w',
        );

    test('低机位 → 手机放低到腰部以下', () {
      final lines = poseGuidanceLines(g('低机位', '正面', '全身'));
      expect(lines.first.label, '机位');
      expect(lines.first.text, contains('腰部以下'));
    });

    test('平机位 → 胸口到脸之间', () {
      final lines = poseGuidanceLines(g('平机位', '正面', '半身'));
      expect(lines.first.text, contains('胸口到脸'));
    });

    test('高机位 → 头顶上方', () {
      final lines = poseGuidanceLines(g('高机位', '正面', '全身'));
      expect(lines.first.text, contains('头顶上方'));
    });

    test('四分之三侧 → 转 45°（人转/你绕 二选一的表述）', () {
      final lines = poseGuidanceLines(g('平机位', '四分之三侧', '全身'));
      final dir = lines.where((l) => l.label == '站位').first;
      expect(dir.text, contains('45°'));
    });

    test('景别 → 带距离经验值（约）', () {
      final lines = poseGuidanceLines(g('平机位', '正面', '全身'));
      final dist = lines.where((l) => l.label == '距离').first;
      expect(dist.text, contains('约'));
    });

    test('250 张参考照全部有 guidance，且三行翻译都非空', () {
      final photos = PoseCatalog.photos();
      expect(photos, isNotEmpty);
      for (final p in photos) {
        final gg = p.guidance;
        expect(gg, isNotNull, reason: '${p.id} 缺 guidance');
        final lines = poseGuidanceLines(gg!);
        expect(lines.length, 3, reason: '${p.id} 翻译行数 != 3');
        for (final l in lines) {
          expect(l.label, isNotEmpty);
          expect(l.text.trim(), isNotEmpty, reason: '${p.id} ${l.label} 为空');
        }
      }
    });
  });

  // ────────────────────────────────────────────────────────────
  // 3. 姿势页：景别筛选 + 卡片机位副标题
  // ────────────────────────────────────────────────────────────
  group('姿势页（v0.9.0 景别筛选 + 卡片机位副标题）', () {
    testWidgets('筛选行出现 景别，且选项齐全', (tester) async {
      tester.view.physicalSize = const Size(390, 900) * 3;
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: const PosesPage(),
      ));
      await tester.pump();

      expect(find.text('景别'), findsOneWidget);
      expect(find.text('七分身'), findsWidgets);
    });

    testWidgets('点「全身」筛选后只剩全身参考照', (tester) async {
      tester.view.physicalSize = const Size(390, 900) * 3;
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: const PosesPage(),
      ));
      await tester.pump();

      await tester.tap(find.text('全身').first);
      await tester.pump();

      // 网格虚拟化：只能看到视口内的卡片，无法数全量。
      // 所以断言「可见卡片全部是全身」+「数量 > 0」，而不是全量相等。
      final metas = find.textContaining('· 全身').evaluate().length;
      expect(metas, greaterThan(0), reason: '筛选后应有可见的全身卡片');
      expect(
        find.textContaining('· 七分身').evaluate().length +
            find.textContaining('· 半身').evaluate().length,
        0,
        reason: '全身筛选下不应出现非全身卡片的副标题',
      );
    });

    testWidgets('卡片副标题显示机位参数（· 全身 · …），不再是「点开看指导」',
        (tester) async {
      tester.view.physicalSize = const Size(390, 900) * 3;
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: const PosesPage(),
      ));
      await tester.pump();

      // 250 张参考照全有 guidance → 副标题全是机位参数，旧文案消失
      expect(find.textContaining('点开看指导'), findsNothing);
      expect(find.textContaining('· 全身'), findsWidgets);
      expect(find.textContaining('· 四分之三侧'), findsWidgets);
    });
  });

  // ────────────────────────────────────────────────────────────
  // 4. FaceLightChoice —— 光线方向意图（prompt 文本）
  // ────────────────────────────────────────────────────────────
  group('FaceLightChoice（v0.9.0 光线方向意图）', () {
    test('promptText 含方向词，prompt 拼接不串词', () {
      final c = FaceLightChoice(
        direction: '逆光',
        confidence: null,
        estimated: false,
        timestamp: DateTime(2026, 10, 20),
      );
      expect(c.promptText, contains('逆光'));
      expect(c.promptText, contains('手动选择'));
    });
  });
}
