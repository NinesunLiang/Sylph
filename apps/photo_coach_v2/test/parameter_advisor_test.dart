import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/params/exposure_knowledge.dart';
import 'package:photo_coach_v2/features/params/parameter_advisor.dart';
import 'package:photo_coach_v2/features/params/shot_exif.dart';

/// 参数建议的测试。
///
/// 这个文件守的是**产品诚实性**，比功能本身更重要：
/// 参数建议错了会毁掉用户一次拍摄。所以核心断言是
/// 「**没有出处就不许出数值**」，而且是对**全部意图**逐个校验的。
void main() {
  group('规矩：没有出处就不许出数值', () {
    test('每个意图：要么给出建议且带出处，要么明确给不出（不能两头不靠）', () {
      for (final intent in ShootingIntent.values) {
        final a = adviseParameters(intent: intent);
        if (a.covered) {
          expect(a.rules, isNotEmpty,
              reason: '${intent.label}：声称"有依据"却没有任何出处 —— 这就是编');
        } else {
          expect(a.recommendations, isEmpty,
              reason: '${intent.label}：没有出处却给了数值 —— 违反「不编造」');
          expect(a.notCoveredReason, isNotNull,
              reason: '${intent.label}：给不出建议时必须说明缺什么');
        }
      }
    });

    test('所有出处都是可核对的链接，且标明了发布者', () {
      for (final k in kIntentKnowledge.values) {
        for (final r in k.rules) {
          expect(r.url, startsWith('http'),
              reason: '${k.intent.label}：出处不是链接，用户没法核对');
          expect(r.publisher.trim(), isNotEmpty,
              reason: '${k.intent.label}：出处没写是谁说的');
          expect(r.statement.trim().length, greaterThan(10),
              reason: '${k.intent.label}：出处只写了个标题，没有可核对的原文要点');
        }
      }
    });

    test('有数值的意图，必须有"确定快门值"或者明确说明没有', () {
      final water = kIntentKnowledge[ShootingIntent.water]!;
      expect(water.isCovered, isTrue);
      expect(water.shutterSeconds, 2.0, reason: 'Canon 官方给的是 2 秒');

      final night = kIntentKnowledge[ShootingIntent.night]!;
      expect(night.isCovered, isTrue, reason: '夜景有官方依据（方法层面）');
      expect(night.shutterSeconds, isNull,
          reason: 'Canon 那一页只讲方法、没给固定快门 —— 不能自己编一个');
    });

    test('明确没依据的意图（人像/风景/运动）不许有数值', () {
      for (final i in [
        ShootingIntent.portrait,
        ShootingIntent.landscape,
        ShootingIntent.motion,
      ]) {
        final k = kIntentKnowledge[i]!;
        expect(k.isCovered, isFalse, reason: '${i.label}：还没找到出处，应标为未覆盖');
        expect(k.shutterSeconds, isNull);
        expect(k.apertureText, isNull);
      }
    });
  });

  group('曝光方程（数学，必须自洽）', () {
    test('阳光16法则能反推出「晴天户外」的光强度', () {
      // f/16 + ISO 100 + 1/100s —— 这正是阳光16法则本身
      final ev = sceneEv100(iso: 100, shutterSeconds: 1 / 100, aperture: 16);
      expect(ev, closeTo(14.64, 0.05));
    });

    test('往返一致：算出 ISO 再反推，能回到同一个光强度', () {
      const ev = 12.0;
      final iso = isoFor(ev100: ev, shutterSeconds: 1 / 250, aperture: 2.8);
      final back = sceneEv100(iso: iso, shutterSeconds: 1 / 250, aperture: 2.8);
      expect(back, closeTo(ev, 1e-9));
    });

    test('光圈开大一档 / 快门慢一档，需要的 ISO 就减半（物理直觉）', () {
      final a = isoFor(ev100: 10, shutterSeconds: 1 / 100, aperture: 4);
      final b = isoFor(ev100: 10, shutterSeconds: 1 / 100, aperture: 2.8);
      // f/2.8 比 f/4 大约多一倍进光量 → ISO 减半
      expect(b / a, closeTo(0.5, 0.06));
    });

    test('非法输入必须抛错，不能悄悄算出个 NaN 让用户去拍', () {
      expect(() => exposureValue(aperture: 0, shutterSeconds: 1 / 100),
          throwsArgumentError);
      expect(() => sceneEv100(iso: 0, shutterSeconds: 1 / 100, aperture: 2.8),
          throwsArgumentError);
    });

    test('ISO 取整是向上取，宁可亮一点不欠曝', () {
      expect(roundUpIso(101), 125);
      expect(roundUpIso(100), 100);
      expect(roundUpIso(99.9), 100);
      expect(roundUpIso(40000), kIsoStops.last);
    });
  });

  group('按意图给建议（带实测基准时）', () {
    // 晴天户外实测：f/1.8、ISO 50、1/2000s（光很足）
    const sunnyShot =
        ShotExif(iso: 50, shutterSeconds: 1 / 2000, aperture: 1.8);

    // 暗光实测：f/1.8、ISO 3200、1/30s（夜景/室内）
    const dimShot = ShotExif(iso: 3200, shutterSeconds: 1 / 30, aperture: 1.8);

    test('流水 + 晴天：只给快门（2s）并指出必须加 ND —— 不给错的 ISO', () {
      final a = adviseParameters(intent: ShootingIntent.water, shot: sunnyShot);

      expect(a.covered, isTrue);
      final shutter = a.recommendations.firstWhere((r) => r.name == '快门');
      expect(shutter.value, '2s');

      // 🚨 关键：晴天 + 2 秒 → 需要 ISO ≈ 0.01，物理上做不到。
      // 这时**不许**打印一个「ISO 50」糊过去（那会让用户拍出一片死白）。
      expect(a.recommendations.map((r) => r.name), isNot(contains('ISO')),
          reason: '光太亮时算出的 ISO 低于任何相机的最低值，给数字就是骗人');
      expect(a.headline, contains('ND'),
          reason: '必须说清真实约束：得加 ND 减光镜');

      expect(a.rules, isNotEmpty);
      expect(a.rules.first.url, contains('canon.com.hk'));
      // 依据里必须说清是拿什么算的，不能只丢一个数字
      expect(a.basis.join(), contains('照片实测'));
    });

    test('流水 + 暗光：能算出合理的 ISO（这时才该给数字）', () {
      final a = adviseParameters(intent: ShootingIntent.water, shot: dimShot);

      expect(a.recommendations.map((r) => r.name), contains('ISO'));
      final iso = a.recommendations.firstWhere((r) => r.name == 'ISO');
      // f/1.8 + 2s、EV100≈1.6 的场景 → 约 ISO 53，向上取到 64
      expect(iso.value, '64');
      expect(iso.note, contains('反算'));
    });

    test('读不到 EXIF 时：只给快门建议，ISO 说明算不出来（不猜）', () {
      final a = adviseParameters(intent: ShootingIntent.water, shot: null);

      expect(a.recommendations.map((r) => r.name), ['快门']);
      expect(a.basis, isEmpty, reason: '没有实测数据时 basis 不该有内容');
      expect(a.notes.join(), isNotEmpty);
    });

    test('夜景：有出处但没确定快门 → 不给数值，只给方法和出处', () {
      final a = adviseParameters(intent: ShootingIntent.night, shot: sunnyShot);

      expect(a.covered, isTrue);
      expect(a.recommendations, isEmpty,
          reason: '官方只给方法没给值，不许自己编一个快门/ISO');
      expect(a.rules, isNotEmpty);
      expect(a.headline, contains('光圈'));
    });
  });

  group('快门写法', () {
    test('整数秒和分数秒都写对', () {
      expect(formatShutter(2.0), '2s');
      expect(formatShutter(1 / 250), '1/250s');
      expect(formatShutter(1 / 1000), '1/1000s');
    });
  });
}
