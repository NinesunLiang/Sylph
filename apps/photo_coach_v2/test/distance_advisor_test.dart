import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/analysis/distance_advisor.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart';

/// [DistanceAdvisor] 的全部档位：
/// 半身 / 全身 / 七分身 ×（tooFar / 模糊区 / okay / 模糊区 / tooClose）
/// + 没脸没主体的 unknown + 主体兜底三档 + 景别识别。
void main() {
  const advisor = DistanceAdvisor();

  // 方便构造「只关心高度」的脸框。
  Rect01 face(double h) => Rect01(0.4, 0.2, 0.2, h);
  Rect01 body(double h) => Rect01(0.25, 0.1, 0.5, h);

  group('半身（默认档）', () {
    test('faceH 在 [0.28, 0.55] → okay', () {
      for (final h in [0.28, 0.4, 0.55]) {
        final a = advisor.advise(faceFound: true, faceBox: face(h));
        expect(a.level, DistanceLevel.okay, reason: 'faceH=$h');
        expect(a.faceRatio, closeTo(h, 1e-9));
      }
    });

    test('faceH < 0.18 → tooFar「站近一点」', () {
      final a = advisor.advise(faceFound: true, faceBox: face(0.10));
      expect(a.level, DistanceLevel.tooFar);
      expect(a.message, '站近一点，脸在画面里太小');
    });

    test('faceH > 0.75 → tooClose「退远一点」', () {
      final a = advisor.advise(faceFound: true, faceBox: face(0.85));
      expect(a.level, DistanceLevel.tooClose);
      expect(a.message, '退远一点，脸占满了画面');
    });

    test('模糊区按最近档给「差不多，微调」', () {
      // 下模糊区：[0.18, 0.28) → 按 tooFar 档
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.24)).level,
        DistanceLevel.tooFar,
      );
      // 上模糊区：(0.55, 0.75] → 按 tooClose 档
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.65)).level,
        DistanceLevel.tooClose,
      );
      // 边界值本身：0.18 不是 < 0.18，模糊区；0.75 不是 > 0.75，模糊区
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.18)).level,
        DistanceLevel.tooFar,
      );
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.75)).level,
        DistanceLevel.tooClose,
      );
    });
  });

  group('全身（目标脸占比更小）', () {
    test('faceH 在 [0.08, 0.22] → okay', () {
      for (final h in [0.08, 0.15, 0.22]) {
        final a = advisor.advise(
          faceFound: true,
          faceBox: face(h),
          framing: '全身',
        );
        expect(a.level, DistanceLevel.okay, reason: 'faceH=$h');
      }
    });

    test('faceH < 0.05 → tooFar；> 0.34 → tooClose；中间模糊区按最近档', () {
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.02), framing: '全身')
            .level,
        DistanceLevel.tooFar,
      );
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.5), framing: '全身')
            .level,
        DistanceLevel.tooClose,
      );
      // 0.06 在 [0.05, 0.08) → 模糊区按 tooFar；0.28 在 (0.22, 0.34] → tooClose
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.06), framing: '全身')
            .level,
        DistanceLevel.tooFar,
      );
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.28), framing: '全身')
            .level,
        DistanceLevel.tooClose,
      );
    });

    test('全身目标下同样的脸，比半身更「太近」', () {
      // 半身下 0.3 是 okay；全身下 0.3 在模糊区按 tooClose —— 景别差异
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.3)).level,
        DistanceLevel.okay,
      );
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.3), framing: '全身')
            .level,
        DistanceLevel.tooClose,
      );
    });
  });

  group('七分身（介于全身和半身）', () {
    test('faceH 在 [0.14, 0.34] → okay', () {
      for (final h in [0.14, 0.24, 0.34]) {
        final a = advisor.advise(
          faceFound: true,
          faceBox: face(h),
          framing: '七分身',
        );
        expect(a.level, DistanceLevel.okay, reason: 'faceH=$h');
      }
    });

    test('faceH < 0.08 → tooFar；> 0.48 → tooClose；模糊区按最近档', () {
      expect(
        advisor.advise(
            faceFound: true, faceBox: face(0.04), framing: '七分身').level,
        DistanceLevel.tooFar,
      );
      expect(
        advisor.advise(
            faceFound: true, faceBox: face(0.6), framing: '七分身').level,
        DistanceLevel.tooClose,
      );
      expect(
        advisor.advise(
            faceFound: true, faceBox: face(0.10), framing: '七分身').level,
        DistanceLevel.tooFar, // 模糊区 [0.08, 0.14)
      );
      expect(
        advisor.advise(
            faceFound: true, faceBox: face(0.42), framing: '七分身').level,
        DistanceLevel.tooClose, // 模糊区 (0.34, 0.48]
      );
    });

    test('同一张脸：七分身比全身宽松', () {
      // 全身下 0.30 → tooClose（模糊区）；七分身下 0.30 → okay
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.30), framing: '全身')
            .level,
        DistanceLevel.tooClose,
      );
      expect(
        advisor.advise(
            faceFound: true, faceBox: face(0.30), framing: '七分身').level,
        DistanceLevel.okay,
      );
    });
  });

  group('景别识别', () {
    test('framing 传 null / 空串 → 按半身档', () {
      // 0.3：半身=okay，全身=tooClose
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.3), framing: null)
            .level,
        DistanceLevel.okay,
      );
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.3), framing: '')
            .level,
        DistanceLevel.okay,
      );
      // 没见过的景别名（比如「特写」）也落默认档，不崩
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.3), framing: '特写')
            .level,
        DistanceLevel.okay,
      );
    });
  });

  group('没脸时的处理', () {
    test('没脸没主体 → unknown，如实说，绝不编', () {
      final a = advisor.advise(faceFound: false, faceBox: null);
      expect(a.level, DistanceLevel.unknown);
      expect(a.faceRatio, isNull);
      expect(a.message, '没找到人脸，没法判断距离——把脸转正朝向镜头');
    });
  });

  group('主体兜底（脸没找到、人找到了）', () {
    test('主体高度 < 0.3 → tooFar', () {
      final a = advisor.advise(
        faceFound: false,
        faceBox: null,
        subjectBox: body(0.2),
      );
      expect(a.level, DistanceLevel.tooFar);
      expect(a.faceRatio, isNull);
    });

    test('主体高度 > 0.85 → tooClose', () {
      final a = advisor.advise(
        faceFound: false,
        faceBox: null,
        subjectBox: body(0.9),
      );
      expect(a.level, DistanceLevel.tooClose);
    });

    test('主体高度在中间 → okay（按身体占比判断）', () {
      final a = advisor.advise(
        faceFound: false,
        faceBox: null,
        subjectBox: body(0.5),
      );
      expect(a.level, DistanceLevel.okay);
      expect(a.message, '按身体占比看距离合适');
    });

    test('边界值：0.3 不是 < 0.3 → okay；0.85 不是 > 0.85 → okay', () {
      expect(
        advisor.advise(
            faceFound: false, faceBox: null, subjectBox: body(0.3)).level,
        DistanceLevel.okay,
      );
      expect(
        advisor.advise(
            faceFound: false, faceBox: null, subjectBox: body(0.85)).level,
        DistanceLevel.okay,
      );
    });

    test('脸找到了 → 不看主体，按脸来', () {
      // 主体很高（>0.85，按兜底该 tooClose），但脸很小（tooFar）
      // → 脸优先，主体框不生效
      final a = advisor.advise(
        faceFound: true,
        faceBox: face(0.1),
        subjectBox: body(0.9),
      );
      expect(a.level, DistanceLevel.tooFar);
      expect(a.faceRatio, closeTo(0.1, 1e-9));
    });
  });

  group('阈值可注入（可调）', () {
    test('换一套阈值，同一输入得到不同档位', () {
      const wide = DistanceAdvisor(
        thresholds: DistanceAdvisorThresholds(
          halfOkayMin: 0.01,
          halfOkayMax: 0.99, // 一切都 okay
          halfTooFarMax: 0.0,
          halfTooCloseMin: 1.0, // 拉开 tooFar/tooClose，别抢在 okay 前面判
        ),
      );
      // 标准档下 0.85 是 tooClose
      expect(
        advisor.advise(faceFound: true, faceBox: face(0.85)).level,
        DistanceLevel.tooClose,
      );
      // 宽阈值下就是 okay
      expect(
        wide.advise(faceFound: true, faceBox: face(0.85)).level,
        DistanceLevel.okay,
      );
    });
  });
}
