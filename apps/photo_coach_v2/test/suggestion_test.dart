import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';

void main() {
  group('Suggestion.parse —— 契约容错（F2 的核心，必须先红后绿）', () {
    test('完整合法 JSON 能全字段解析', () {
      final (s, warnings) = Suggestion.parse({
        'schema_version': '1.0',
        'composition': {
          'rule': 'rule_of_thirds',
          'confidence': 0.82,
          'horizon_tilt_deg': -3.5,
        },
        'subject': {
          'label': 'person',
          'current_box': [0.42, 0.31, 0.28, 0.55],
          'target_box': [0.33, 0.25, 0.30, 0.60],
        },
        'camera_move': {
          'pan_deg': -8,
          'tilt_deg': 5,
          'dolly_m': -0.4,
          'zoom': 1.0,
          'hint': '向左半步，相机略抬高',
        },
        'exposure': {'ev': -0.3, 'reason': '高光过曝'},
        'tips': ['主体放在左三分之一线', '头顶留出一指宽空白'],
      });

      expect(warnings, isEmpty);
      expect(s.source, SuggestionSource.visionModel);
      expect(s.composition.rule, 'rule_of_thirds');
      expect(s.composition.confidence, closeTo(0.82, 1e-9));
      expect(s.composition.horizonTiltDeg, closeTo(-3.5, 1e-9));
      expect(s.subject.label, 'person');
      expect(s.subject.currentBox!.centerX, closeTo(0.56, 1e-9));
      expect(s.subject.targetBox!.left, closeTo(0.33, 1e-9));
      expect(s.cameraMove.panDeg, closeTo(-8, 1e-9));
      expect(s.cameraMove.tiltDeg, closeTo(5, 1e-9));
      expect(s.cameraMove.dollyM, closeTo(-0.4, 1e-9));
      expect(s.cameraMove.hint, '向左半步，相机略抬高');
      expect(s.exposure.ev, closeTo(-0.3, 1e-9));
      expect(s.tips, hasLength(2));
    });

    test('实时模型只给部分字段 —— 缺的走默认，不抛异常', () {
      final (s, warnings) = Suggestion.parse({
        'composition': {'rule': 'centered'},
      });
      expect(s.composition.rule, 'centered');
      expect(s.subject.currentBox, isNull);
      expect(s.cameraMove.isNoop, isTrue);
      expect(s.exposure.ev, 0);
      expect(s.source, SuggestionSource.visionModel);
      expect(warnings, isNotEmpty); // 必须报告缺字段，不静默
      expect(warnings.any((w) => w.contains('subject')), isTrue);
    });

    test('顶层不是对象 —— 整体降级为规则兜底', () {
      final (s, warnings) = Suggestion.parse('这不是 JSON');
      expect(s.source, SuggestionSource.ruleFallback);
      expect(warnings, hasLength(1));
      expect(s.tips, isNotEmpty);
    });

    test('null 输入也不炸', () {
      final (s, _) = Suggestion.parse(null);
      expect(s.source, SuggestionSource.ruleFallback);
      expect(s.composition.rule, 'rule_of_thirds');
    });

    test('坐标：按契约读 [left, top, width, height]', () {
      final box = Rect01.tryParse([0.2, 0.2, 0.6, 0.8])!;
      expect(box.left, closeTo(0.2, 1e-9));
      expect(box.width, closeTo(0.6, 1e-9));
      expect(box.height, closeTo(0.8, 1e-9));
    });

    test('【真模型实测数据】人物框的高度不能被算成 0.009', () {
      // 这是 deepseek-flash 对一张 800x600 合成照片的**真实输出**
      // （复现：python3 .omc/scripts/probe_vision_llm.py --save；
      //   原始响应存在 .omc/tasks/20260920/photo-coach-framework/state/e2e-vision-llm.json）：
      //   current_box = [0.225, 0.358, 0.113, 0.367]
      // 提示词明确要求 [left, top, width, height] → 宽 0.113、高 0.367。
      // 旧实现在 `0.367 > 0.358` 时把它当成"下边界"，算出高 0.009 ——
      // 主体框会变成一条细线，实时引导的"现在在哪 / 大小比"全是错的。
      final box = Rect01.tryParse([0.225, 0.358, 0.113, 0.367])!;
      expect(box.width, closeTo(0.113, 1e-9));
      expect(box.height, closeTo(0.367, 1e-9));
    });

    test('坐标：真歧义时以契约（width/height）为准', () {
      // [0.1, 0.2, 0.3, 0.4] 两种读法都合法，但提示词要的是 width/height
      final box = Rect01.tryParse([0.1, 0.2, 0.3, 0.4])!;
      expect(box.width, closeTo(0.3, 1e-9));
      expect(box.height, closeTo(0.4, 1e-9));
    });

    test('兼容少数派：width/height 读法会越界时，才回退成右/下边界', () {
      // [0.2, 0.3, 0.9, 0.8]：按 width/height 读 → left+width = 1.1 > 1，不成立；
      // 按 right/bottom 读 → 宽 0.7 / 高 0.5，成立（少数模型会这么给）。
      final box = Rect01.tryParse([0.2, 0.3, 0.9, 0.8])!;
      expect(box.width, closeTo(0.7, 1e-9));
      expect(box.height, closeTo(0.5, 1e-9));
    });

    test('字符串数字能容错（模型偶尔把数字加引号）', () {
      final box = Rect01.tryParse(['0.1', '0.2', '0.5', '0.6'])!;
      expect(box.width, closeTo(0.5, 1e-9));
      expect(box.height, closeTo(0.6, 1e-9));
    });

    test('非法坐标返回 null，不产出越界框', () {
      expect(Rect01.tryParse([0.5]), isNull);
      expect(Rect01.tryParse(['a', 'b', 'c', 'd']), isNull);
      expect(Rect01.tryParse([0.5, 0.5, 0.0, 0.0]), isNull);
      expect(Rect01.tryParse(null), isNull);
    });

    test('tips 不是数组时给警告并忽略', () {
      final (s, warnings) = Suggestion.parse({
        'composition': {'rule': 'centered'},
        'tips': '这不是数组',
      });
      expect(s.tips, isEmpty);
      expect(warnings.any((w) => w.contains('tips')), isTrue);
    });

    test('schema_version 不一致时给警告但仍解析', () {
      final (s, warnings) = Suggestion.parse({
        'schema_version': '2.0',
        'composition': {'rule': 'symmetry'},
      });
      expect(s.composition.rule, 'symmetry');
      expect(warnings.any((w) => w.contains('schema_version')), isTrue);
    });

    test('往返序列化：toJson → parse 保持关键字段', () {
      final original = Suggestion.fallback(reason: '测试');
      final (round, _) = Suggestion.parse(original.toJson());
      expect(round.composition.rule, original.composition.rule);
      expect(round.tips, original.tips);
      expect(round.cameraMove.hint, original.cameraMove.hint);
    });
  });

  group('CameraMoveHint', () {
    test('微小数值视为「不用动」', () {
      expect(const CameraMoveHint().isNoop, isTrue);
      expect(const CameraMoveHint(panDeg: 0.2, tiltDeg: 0.3).isNoop, isTrue);
      expect(const CameraMoveHint(panDeg: 5).isNoop, isFalse);
      expect(const CameraMoveHint(zoom: 1.5).isNoop, isFalse);
    });
  });
}
