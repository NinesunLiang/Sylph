import 'exposure_knowledge.dart';
import 'shot_exif.dart';

/// 一条**本机设不了、要你手动设**的参数（可以带去别的设备照着设）。
class ManualSetting {
  const ManualSetting({required this.name, required this.value, this.note});

  /// ISO / 快门 / …
  final String name;
  final String value;

  /// 为什么是这个值。
  final String? note;
}

/// 一次参数建议的结果。
class ParameterAdvice {
  const ParameterAdvice({
    required this.intent,
    required this.covered,
    this.notCoveredReason,
    this.headline,
    this.recommendations = const [],
    this.basis = const [],
    this.rules = const [],
    this.notes = const [],
  });

  final ShootingIntent intent;

  /// 这个意图有没有可靠依据。false 时 [recommendations] 一定为空。
  final bool covered;

  /// 给不出建议时的一句话说明。
  final String? notCoveredReason;

  /// 需要额外提醒时的一句话（例如"光太亮，必须加 ND"）。
  ///
  /// 平时是 null —— 界面上默认**不显示任何解释**，保持干净；
  /// 只有真的会拍坏照片时必须说这句话。
  final String? headline;

  /// **建议值**（本机设不了的那些）。每一项都能追到 [rules] 里的出处。
  final List<ManualSetting> recommendations;

  /// **计算依据** —— 照片自己实测用的参数，是"事实"不是"建议"，
  /// 界面上必须和 [recommendations] 分开显示，别让用户以为这是推荐值。
  final List<String> basis;

  /// 依据（每条带出处链接）。
  final List<ExposureRule> rules;

  /// 哪些项算不出来、以及为什么。
  final List<String> notes;
}

/// 常见 ISO 档位（1/3 档序列）—— 算出来的 ISO 会**向上**取到最近的档位。
///
/// 这是相机界的通用档位约定（厂商机身上也是这么排的）；向上取整是为了
/// 宁可亮一点也别欠曝。它只是"取整"，不是"经验"。
const List<int> kIsoStops = [
  50, 64, 80, 100, 125, 160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250,
  1600, 2000, 2500, 3200, 4000, 5000, 6400, 8000, 10000, 12800, 25600,
];

/// 把算出来的 ISO 向上取到最近的标准档位。
int roundUpIso(double iso) {
  for (final s in kIsoStops) {
    if (s >= iso) return s;
  }
  return kIsoStops.last;
}

/// 按意图给出参数建议。
///
/// [shot] 是这张照片实测用过的三要素（读不到就传 null）。
/// **读不到时不会瞎猜 ISO** —— 会在 [ParameterAdvice.notes] 里说明算不出来。
ParameterAdvice adviseParameters({
  required ShootingIntent intent,
  ShotExif? shot,
}) {
  final knowledge = kIntentKnowledge[intent]!;

  if (!knowledge.isCovered) {
    return ParameterAdvice(
      intent: intent,
      covered: false,
      notCoveredReason: knowledge.shutterText,
    );
  }

  final recommendations = <ManualSetting>[];
  final basis = <String>[];
  final notes = <String>[];
  String? headline;

  // ---- 快门：只有规则给了确定值才给建议 ----
  final targetShutter = knowledge.shutterSeconds;
  if (targetShutter != null) {
    recommendations.add(ManualSetting(
      name: '快门',
      value: formatShutter(targetShutter),
      note: knowledge.shutterText,
    ));
  } else if (knowledge.shutterText != null) {
    // 规则只给了方法、没给固定值 → 这句话本身就是答案，当主行显示，
    // 不塞进小字注释里（否则卡片上主行是空的，用户会觉得没给东西）。
    headline = knowledge.shutterText;
  }

  // ---- ISO：必须「有确定的快门」+「照片实测的光强度」才算得出来 ----
  if (shot == null) {
    // 读不到实测数据 → 没有基准，算不出 ISO。**不猜一个默认值**。
    headline ??= '读不到这张照片的参数，算不出 ISO';
    notes.add('这张照片的 EXIF 里没有 ISO/快门/光圈，没有实测基准就'
        '算不出该给多少 ISO（不猜）');
  } else {
    basis.add('照片实测：$shot');
    final ev100 = sceneEv100(
      iso: shot.iso,
      shutterSeconds: shot.shutterSeconds,
      aperture: shot.aperture,
    );
    basis.add('推算场景光强度 EV100 ≈ ${ev100.toStringAsFixed(1)}');

    if (targetShutter == null) {
      notes.add('这个意图没有确定的快门值，先定快门才能反算 ISO');
    } else {
      final iso = isoFor(
        ev100: ev100,
        shutterSeconds: targetShutter,
        aperture: shot.aperture,
      );
      if (iso < kIsoStops.first) {
        // 🚨 物理上做不到：光太亮，这么慢的快门需要的 ISO 比任何相机的最低
        // ISO 还低。**绝不能**打印一个"最低 ISO 50"糊过去 —— 那会让用户拍出
        // 一片死白。必须说清真实约束：得靠 ND 减光镜减光。
        // （Canon 官方对流水长曝也正是这么建议的。）
        headline = '光太亮：要用这么慢的快门，必须加 ND 减光镜';
        notes.add('按 ${formatShutter(targetShutter)} 算，需要 ISO ≈ '
            '${iso.toStringAsFixed(2)} —— 比任何相机的最低 ISO 还低。'
            '所以这里**不给 ISO 数字**（给了也是错的），'
            '得靠 ND 减光镜减光（Canon 官方也建议用 ND 换慢快门）');
      } else {
        recommendations.add(ManualSetting(
          name: 'ISO',
          value: '${roundUpIso(iso)}',
          note: '按 f/${shot.aperture.toStringAsFixed(1)} + '
              '${formatShutter(targetShutter)} 反算（计算值 '
              '${iso.toStringAsFixed(0)}，向上取到常见档位）',
        ));
        if (roundUpIso(iso) > 3200) {
          headline ??= '光不够，ISO 会很高（噪点明显）：能补光/上三脚架就别硬提';
        }
      }
    }
  }

  return ParameterAdvice(
    intent: intent,
    covered: true,
    headline: headline,
    recommendations: recommendations,
    basis: basis,
    rules: knowledge.rules,
    notes: notes,
  );
}

/// `1/250s` 这种给人看的写法。
String formatShutter(double seconds) {
  if (seconds >= 1) return '${seconds.toStringAsFixed(seconds == seconds.roundToDouble() ? 0 : 1)}s';
  return '1/${(1 / seconds).round()}s';
}
