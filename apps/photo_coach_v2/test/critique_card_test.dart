import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/coach/critique_card.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';

/// 「该站哪/朝哪拍 + 好在哪/差在哪/更优怎么拍」的测试。
///
/// 守两件事：
///  1. 新字段能解析、且**老模型不给这些字段时也不崩**（向后兼容）
///  2. **本地规则兜底时绝不编优缺点** —— 兜底只有几条通用规则，
///     编不出来源不明的"优点/缺点"，那是骗人
void main() {
  Map<String, Object?> fullJson() => {
        'schema_version': '1.0',
        'shooting_plan': {
          'lighting': '光从左窗进来，侧光，右脸偏暗',
          'position': '退后一步，把手机降到胸口高度',
          'direction': '从主体左前方 45°，平视',
          'subject_position': '让人往窗边挪半步，脸朝窗户 45°',
        },
        'pros': ['背景干净，主体够突出'],
        'critiques': [
          {
            'problem': '主体压得太靠下',
            'better': '手机上移一点，让眼睛落在上三分线',
          },
        ],
        'elements': [
          {
            'name': '眼神',
            'verdict': 'problem',
            'advice': '让他看向画面外的远处',
            'anchor': [0.75, 0.15, 0.1, 0.1],
          },
          {'name': '背景杂物', 'verdict': 'good'},
          {'name': '色彩', 'verdict': 'unclear'},
        ],
        'composition': {'rule': 'rule_of_thirds', 'confidence': 0.8},
        'subject': {'label': '人物'},
        'camera_move': {'pan_deg': 0, 'tilt_deg': 5, 'dolly_m': -0.5, 'zoom': 1.0},
        'exposure': {'ev': -0.3, 'reason': '天空偏亮'},
        'tips': ['开网格线'],
      };

  group('契约：新字段解析 + 向后兼容', () {
    test('有 shooting_plan / pros / critiques 时逐项解析出来', () {
      final (s, _) = Suggestion.parse(fullJson());

      expect(s.shootingPlan.lighting, '光从左窗进来，侧光，右脸偏暗');
      expect(s.shootingPlan.position, '退后一步，把手机降到胸口高度');
      expect(s.shootingPlan.direction, '从主体左前方 45°，平视');
      expect(s.shootingPlan.subjectPosition, '让人往窗边挪半步，脸朝窗户 45°');
      expect(s.pros, ['背景干净，主体够突出']);
      expect(s.critiques.single.problem, '主体压得太靠下');
      expect(s.critiques.single.better, '手机上移一点，让眼睛落在上三分线');
      expect(s.source, SuggestionSource.visionModel);
    });

    test('只有人物站位、没有别的 → 也算有方案（不能因为缺项整块丢掉）', () {
      final (s, _) = Suggestion.parse({
        'schema_version': '1.0',
        'shooting_plan': {'subject_position': '让人站到那片光里'},
        'composition': {'rule': 'centered'},
        'subject': {'label': 'x'},
        'camera_move': {'pan_deg': 0, 'tilt_deg': 0, 'dolly_m': 0, 'zoom': 1.0},
        'exposure': {'ev': 0, 'reason': ''},
      });
      expect(s.shootingPlan.isEmpty, isFalse);
      expect(s.shootingPlan.subjectPosition, '让人站到那片光里');
      expect(s.shootingPlan.lighting, isNull);
    });

    test('老模型不给这些字段 → 空着就好，不崩、不编', () {
      final (s, _) = Suggestion.parse({
        'schema_version': '1.0',
        'composition': {'rule': 'centered'},
        'subject': {'label': 'x'},
        'camera_move': {'pan_deg': 0, 'tilt_deg': 0, 'dolly_m': 0, 'zoom': 1.0},
        'exposure': {'ev': 0, 'reason': ''},
        'tips': ['a'],
      });

      expect(s.shootingPlan.isEmpty, isTrue);
      expect(s.pros, isEmpty);
      expect(s.critiques, isEmpty);
    });

    test('shooting_plan 类型不对 → 忽略，不抛异常', () {
      final (s, _) = Suggestion.parse({
        'schema_version': '1.0',
        'shooting_plan': '站左边',
        'composition': {'rule': 'centered'},
        'subject': {'label': 'x'},
        'camera_move': {'pan_deg': 0, 'tilt_deg': 0, 'dolly_m': 0, 'zoom': 1.0},
        'exposure': {'ev': 0, 'reason': ''},
      });
      expect(s.shootingPlan.isEmpty, isTrue);
    });

    test('空壳 critique（problem/better 都是空）要被丢掉', () {
      final (s, _) = Suggestion.parse({
        'schema_version': '1.0',
        'critiques': [
          {'problem': '', 'better': ''},
          {'problem': '有内容', 'better': ''},
        ],
        'composition': {'rule': 'centered'},
        'subject': {'label': 'x'},
        'camera_move': {'pan_deg': 0, 'tilt_deg': 0, 'dolly_m': 0, 'zoom': 1.0},
        'exposure': {'ev': 0, 'reason': ''},
      });
      expect(s.critiques.length, 1);
      expect(s.critiques.single.problem, '有内容');
    });

    test('要素体检：三种 verdict 都要解析对，未知值算 unclear（不硬猜）', () {
      final (s, _) = Suggestion.parse(fullJson());

      expect(s.elements.length, 3);
      expect(s.elements[0].name, '眼神');
      expect(s.elements[0].verdict, ElementVerdict.problem);
      expect(s.elements[0].advice, '让他看向画面外的远处');
      expect(s.elements[1].verdict, ElementVerdict.good);
      expect(s.elements[2].verdict, ElementVerdict.unclear);
    });

    test('要素没名字的空壳要丢掉；完全没给 elements 也不崩', () {
      final (s1, _) = Suggestion.parse({
        'schema_version': '1.0',
        'elements': [
          {'name': '', 'verdict': 'good'},
          {'name': '构图', 'verdict': 'weird_value_xyz'},
        ],
        'composition': {'rule': 'centered'},
        'subject': {'label': 'x'},
        'camera_move': {'pan_deg': 0, 'tilt_deg': 0, 'dolly_m': 0, 'zoom': 1.0},
        'exposure': {'ev': 0, 'reason': ''},
      });
      expect(s1.elements.length, 1, reason: '空名字的丢掉');
      expect(s1.elements.single.name, '构图');
      expect(s1.elements.single.verdict, ElementVerdict.unclear,
          reason: '认不出的 verdict 算"看不出"，不能当成 good');

      final (s2, _) = Suggestion.parse({
        'schema_version': '1.0',
        'composition': {'rule': 'centered'},
        'subject': {'label': 'x'},
        'camera_move': {'pan_deg': 0, 'tilt_deg': 0, 'dolly_m': 0, 'zoom': 1.0},
        'exposure': {'ev': 0, 'reason': ''},
      });
      expect(s2.elements, isEmpty);
    });

    test('要素锚点：给得出就解析成框，给不出就 null（不硬画）', () {
      final (s, _) = Suggestion.parse(fullJson());

      expect(s.elements[0].anchor, isNotNull);
      expect(s.elements[0].anchor!.left, closeTo(0.75, 1e-9));
      expect(s.elements[0].anchor!.width, closeTo(0.1, 1e-9));
      expect(s.elements[1].anchor, isNull, reason: '没给锚点就是 null');

      final marked = anchoredElements(s);
      expect(marked.length, 1);
      expect(marked.single.$1, 1, reason: '编号 = 它在完整清单里的序号');
      expect(marked.single.$2.name, '眼神');
    });

    test('编号和图上的框一一对应（第 2 条带锚点 → 图上就是 2 号框）', () {
      final (s, _) = Suggestion.parse({
        'schema_version': '1.0',
        'elements': [
          {'name': '构图', 'verdict': 'good'},
          {
            'name': '背景杂物',
            'verdict': 'problem',
            'advice': '往左挪半步',
            'anchor': [0.8, 0.4, 0.15, 0.3],
          },
          {
            'name': '眼神',
            'verdict': 'problem',
            'advice': '看向远处',
            'anchor': [0.1, 0.1, 0.1, 0.1],
          },
        ],
        'composition': {'rule': 'centered'},
        'subject': {'label': 'x'},
        'camera_move': {'pan_deg': 0, 'tilt_deg': 0, 'dolly_m': 0, 'zoom': 1.0},
        'exposure': {'ev': 0, 'reason': ''},
      });

      final marked = anchoredElements(s);
      expect(marked.map((m) => m.$1), [2, 3],
          reason: '第 1 条没有锚点，所以图上只有 2 号、3 号框');
      expect(marked.map((m) => m.$2.name), ['背景杂物', '眼神']);
    });

    test('本地规则兜底**不给**优缺点和站位（编不出来就不给）', () {
      final s = Suggestion.fallback(reason: '网络不可用');

      expect(s.source, SuggestionSource.ruleFallback);
      expect(s.shootingPlan.isEmpty, isTrue,
          reason: '本地规则推不出"你该站哪"，不许假装知道');
      expect(s.pros, isEmpty);
      expect(s.critiques, isEmpty);
      expect(s.tips, isNotEmpty, reason: '兜底至少要给通用规则');
    });
  });

  group('卡片显示', () {
    Future<void> pump(WidgetTester tester, Suggestion s) async {
      tester.view.physicalSize = const Size(390 * 3, 900 * 3);
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: Scaffold(body: SingleChildScrollView(child: CritiqueCard(s: s))),
      ));
      await tester.pump();
    }

    testWidgets('光照/人站哪/拍摄点/机位方向 + 好在哪 + 差在哪→更优，都要看得见',
        (tester) async {
      final (s, _) = Suggestion.parse(fullJson());
      await pump(tester, s);

      expect(find.text('拍摄方案'), findsOneWidget);
      expect(find.text('💡 光照'), findsOneWidget);
      expect(find.text('光从左窗进来，侧光，右脸偏暗'), findsOneWidget);
      expect(find.text('🧍 人站哪'), findsOneWidget);
      expect(find.text('让人往窗边挪半步，脸朝窗户 45°'), findsOneWidget);
      expect(find.text('📍 拍摄点'), findsOneWidget);
      expect(find.text('退后一步，把手机降到胸口高度'), findsOneWidget);
      expect(find.text('🧭 机位方向'), findsOneWidget);
      expect(find.text('从主体左前方 45°，平视'), findsOneWidget);
      expect(find.text('✅ 好在哪'), findsOneWidget);
      expect(find.text('⚠️ 差在哪 → 更优怎么拍'), findsOneWidget);
      expect(find.textContaining('→ 手机上移一点'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('光照那一行排在最前面（先讲清光，再讲人站哪）', (tester) async {
      final (s, _) = Suggestion.parse(fullJson());
      await pump(tester, s);

      final lightingY = tester.getTopLeft(find.text('💡 光照')).dy;
      final subjectY = tester.getTopLeft(find.text('🧍 人站哪')).dy;
      final spotY = tester.getTopLeft(find.text('📍 拍摄点')).dy;
      expect(lightingY, lessThan(subjectY));
      expect(subjectY, lessThan(spotY));
    });

    testWidgets('必须标注「这是模型判断」—— 不能让人以为是测量结果', (tester) async {
      final (s, _) = Suggestion.parse(fullJson());
      await pump(tester, s);
      expect(find.textContaining('模型的判断'), findsOneWidget);
    });

    testWidgets('全部要素体检：默认**收起**，展开后有问题的最前', (tester) async {
      final (s, _) = Suggestion.parse(fullJson());
      await pump(tester, s);

      // 收起是可验证的：具体要素名看不到（上面已经有重点了，别再淹人）
      expect(find.textContaining('全部要素体检'), findsOneWidget);
      expect(find.textContaining('眼神'), findsNothing);
      expect(find.textContaining('1 项有问题'), findsOneWidget,
          reason: '收起状态要给出数量概览');
      expect(find.textContaining('1 项看不出'), findsOneWidget);

      await tester.tap(find.textContaining('全部要素体检'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text('⚠️ 1. 眼神'), findsOneWidget,
          reason: '编号要和图上的框号一致');
      expect(find.text('✅ 2. 背景杂物'), findsOneWidget);
      expect(find.text('— 3. 色彩'), findsOneWidget, reason: '看不出也要如实列出');
      expect(find.textContaining('让他看向画面外的远处'), findsOneWidget);

      // 顺序：有问题的排最前
      final yProblem = tester.getTopLeft(find.text('⚠️ 1. 眼神')).dy;
      final yGood = tester.getTopLeft(find.text('✅ 2. 背景杂物')).dy;
      final yUnclear = tester.getTopLeft(find.text('— 3. 色彩')).dy;
      expect(yProblem, lessThan(yGood));
      expect(yGood, lessThan(yUnclear));
      expect(tester.takeException(), isNull);
    });

    testWidgets('有锚点时：清单里要说明"带编号的项已画在画面上"', (tester) async {
      final (s, _) = Suggestion.parse(fullJson());
      await pump(tester, s);

      await tester.tap(find.textContaining('全部要素体检'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.textContaining('已经画在画面上'), findsOneWidget);
      expect(find.text('⚠️ 1. 眼神'), findsOneWidget,
          reason: '清单编号要和图上的框号对得上');
    });

    testWidgets('兜底时整张卡不出现（不给空壳）', (tester) async {
      await pump(tester, Suggestion.fallback(reason: '网络不可用'));

      expect(find.text('该站哪、朝哪拍'), findsNothing);
      expect(find.text('✅ 好在哪'), findsNothing);
      expect(find.textContaining('模型的判断'), findsNothing,
          reason: '本地规则兜底不能冒充模型判断');
      expect(tester.takeException(), isNull);
    });
  });
}
