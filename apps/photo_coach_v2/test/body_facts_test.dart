import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/analysis/body_facts.dart';
import 'package:photo_coach_v2/features/coach/prompt.dart';

/// 端上人体关键点 → 客观事实 的测试。
///
/// 这一层**完全离线可验**（纯数学，不需要真机、不需要 ML Kit 插件）。
/// 守两件事：
///  1. 数字要**算对**（角度按真实宽高比换算，别给出假角度）
///  2. 上游坐标不可信时**宁可不算**，也不产出"看起来很像"的结论
void main() {
  Landmark lm(String t, double x, double y, [double p = 0.9]) =>
      Landmark(t, x, y, likelihood: p);

  // 一个标准的半身照：肩膀 0.4/0.6，右肩略低；鼻子正对
  List<Landmark> halfBody() => [
        lm('nose', 0.50, 0.20),
        lm('leftEye', 0.46, 0.18),
        lm('rightEye', 0.54, 0.18),
        lm('leftEar', 0.42, 0.20),
        lm('rightEar', 0.58, 0.20),
        lm('leftShoulder', 0.40, 0.30),
        lm('rightShoulder', 0.60, 0.35),
        lm('leftElbow', 0.38, 0.48),
        lm('rightElbow', 0.62, 0.50),
        lm('leftHip', 0.43, 0.62),
        lm('rightHip', 0.57, 0.63),
      ];

  group('包围盒与可见点', () {
    test('包围盒取所有可用点的范围', () {
      final f = bodyFactsFrom(halfBody(), imageAspectRatio: 3 / 4)!;
      expect(f.visibleCount, 11);
      expect(f.box.left, closeTo(0.38, 1e-9)); // 最左是左肘 0.38
      expect(f.box.left + f.box.width, closeTo(0.62, 1e-9)); // 最右是右肘
      expect(f.box.top, closeTo(0.18, 1e-9));
      expect(f.box.top + f.box.height, closeTo(0.63, 1e-9));
    });

    test('置信度低于 0.5 的点直接丢掉（宁可少算）', () {
      final l = halfBody()
        ..add(lm('leftAnkle', 0.4, 0.98, 0.2)) // 置信度太低
        ..add(lm('rightAnkle', 0.6, 0.99, 0.2));
      final f = bodyFactsFrom(l, imageAspectRatio: 3 / 4)!;
      expect(f.visibleCount, 11, reason: '两个低置信度的点不该算进来');
      expect(f.box.top + f.box.height, lessThan(0.9));
    });

    test('一个可用点都没有 → null（不编）', () {
      expect(bodyFactsFrom(const [], imageAspectRatio: 1), isNull);
      expect(
        bodyFactsFrom([lm('nose', 0.5, 0.5, 0.1)], imageAspectRatio: 1),
        isNull,
      );
    });
  });

  group('肩线倾斜（必须按真实宽高比换算）', () {
    test('角度按图片宽高比换算，不是直接用归一化坐标', () {
      final f = bodyFactsFrom(halfBody(), imageAspectRatio: 0.75)!;
      // 归一化：Δx=0.2, Δy=0.05；真实比例：dx=0.2*0.75=0.15, dy=0.05
      // → atan2(0.05, 0.15) ≈ 18.43°
      expect(f.shoulderTiltDeg, closeTo(18.43, 0.05));
      expect(f.lowerShoulder, '右', reason: 'y 更大 = 更靠下 = 右肩低');
    });

    test('宽高比不同 → 角度必须跟着变（否则就是假角度）', () {
      final narrow = bodyFactsFrom(halfBody(), imageAspectRatio: 0.5)!;
      final wide = bodyFactsFrom(halfBody(), imageAspectRatio: 1.5)!;
      expect(narrow.shoulderTiltDeg, isNot(closeTo(wide.shoulderTiltDeg!, 0.01)));
      expect(narrow.shoulderTiltDeg!, greaterThan(wide.shoulderTiltDeg!));
    });

    test('两肩齐平 → 0°，且不谎报哪边低', () {
      final l = [
        lm('leftShoulder', 0.4, 0.3),
        lm('rightShoulder', 0.6, 0.3),
      ];
      final f = bodyFactsFrom(l, imageAspectRatio: 1)!;
      expect(f.shoulderTiltDeg, closeTo(0, 1e-6));
    });

    test('只有一边肩膀 → 不给角度（不猜）', () {
      final f = bodyFactsFrom([lm('leftShoulder', 0.4, 0.3)],
          imageAspectRatio: 1)!;
      expect(f.shoulderTiltDeg, isNull);
      expect(f.lowerShoulder, isNull);
    });
  });

  group('头部朝向', () {
    test('鼻子在两耳正中 → 基本正对', () {
      final f = bodyFactsFrom(halfBody(), imageAspectRatio: 0.75)!;
      expect(f.headTurnRatio, closeTo(0, 1e-6));
      expect(f.headTurnText, '基本正对镜头');
    });

    test('鼻子偏右 → 头偏向画面右侧', () {
      final l = [
        lm('nose', 0.60, 0.2),
        lm('leftEar', 0.45, 0.2),
        lm('rightEar', 0.65, 0.2),
      ];
      final f = bodyFactsFrom(l, imageAspectRatio: 1)!;
      expect(f.headTurnRatio! > 0.15, isTrue);
      expect(f.headTurnText, '头偏向画面右侧');
    });

    test('缺耳朵 → 不判断头朝向（不猜）', () {
      final f = bodyFactsFrom([lm('nose', 0.5, 0.2)], imageAspectRatio: 1)!;
      expect(f.headTurnText, isNull);
    });
  });

  group('上游坐标不可信时：宁可不算', () {
    test('坐标不在 0–1（说明不是归一化坐标）→ 返回 null', () {
      expect(
        bodyFactsFrom([lm('nose', 320, 240), lm('leftShoulder', 100, 400)],
            imageAspectRatio: 1),
        isNull,
        reason: '来路不明的坐标绝不能算出"看起来很像"的结论',
      );
    });

    test('宽高比非法 → 返回 null', () {
      expect(bodyFactsFrom(halfBody(), imageAspectRatio: 0), isNull);
      expect(bodyFactsFrom(halfBody(), imageAspectRatio: -1), isNull);
    });
  });

  group('给模型的话', () {
    test('必须明确写"这是测量值、直接用、别重新猜"', () {
      final f = bodyFactsFrom(halfBody(), imageAspectRatio: 0.75)!;
      final t = f.toPromptText();
      expect(t, contains('测量值'));
      expect(t, contains('不要重新看图猜'));
      expect(t, contains('肩线倾斜'));
      expect(t, contains('眼睛高度'));
    });

    test('bodyFactsSection：没有测量值就一个字都不加', () {
      expect(CompositionPrompt.bodyFactsSection(null), '');
    });

    test('bodyFactsSection：有测量值就带上', () {
      final f = bodyFactsFrom(halfBody(), imageAspectRatio: 0.75)!;
      final sec = CompositionPrompt.bodyFactsSection(f);
      expect(sec, contains('肩线倾斜'));
      expect(sec, contains('请直接采用'));
    });
  });

  group('给用户看的事实清单', () {
    test('每条都是可读的测量结果', () {
      final f = bodyFactsFrom(halfBody(), imageAspectRatio: 0.75)!;
      final lines = f.toFactLines();
      expect(lines, isNotEmpty);
      expect(lines.join('\n'), contains('肩线倾斜'));
      expect(lines.join('\n'), contains('关键点'));
      expect(lines.join('\n'), contains('人体跨度'));
    });
  });
}
