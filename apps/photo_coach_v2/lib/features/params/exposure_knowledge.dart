/// 曝光知识库 —— 参数建议的「经验」层。
///
/// 🔴 **唯一规矩：这里出现的每一个数值都必须挂在一条有出处的规则上。**
/// 找不到权威出处的场景就明确「给不出建议」，**绝不**填一个看起来合理的数字。
/// 理由：参数建议错了会毁掉用户一次拍摄，比"没有建议"更糟。
/// 这条规矩不是靠自觉 —— `test/parameter_advisor_test.dart` 会机器校验它。
///
/// 人类 2026-09-20 的裁决：「只用有权威出处的规则；覆盖不到的场景宁可写
/// 「给不出建议」，也不编」。
library;

import 'dart:math' as math;

/// 一条有出处的规则。
///
/// [statement] 是**原文要点**（不是我的解读），[url] 必须能打开核对。
class ExposureRule {
  const ExposureRule({
    required this.publisher,
    required this.url,
    required this.statement,
  });

  /// 谁说的（厂商官网优先）。
  final String publisher;

  /// 出处链接。
  final String url;

  /// 原文要点（英文原文或中文官方表述）。
  final String statement;

  @override
  String toString() => '$publisher：$statement（$url）';
}

/// 拍摄意图。
///
/// 为什么必须有它：**没有意图，「最优 ISO/快门」在物理上不存在**。
/// 同一片水流，想冻结水花要 1/1000，想丝滑要 2s —— 照片上看不出你要哪个。
enum ShootingIntent {
  portrait('人像'),
  landscape('风景'),
  motion('运动'),
  night('夜景'),
  water('流水');

  const ShootingIntent(this.label);

  final String label;
}

/// 一个意图已知的东西。
///
/// [rules] 为空 = **这个意图目前给不出建议**（缺可靠出处）。此时所有数值字段
/// 都必须是 null —— 不允许"顺手猜一个"。
class IntentKnowledge {
  const IntentKnowledge({
    required this.intent,
    required this.rules,
    this.shutterSeconds,
    this.shutterText,
    this.apertureText,
  });

  /// 明确「还没有可靠出处」的意图：只说明缺什么，不给任何数值。
  const IntentKnowledge.notCovered(this.intent, this.shutterText)
      : rules = const [],
        shutterSeconds = null,
        apertureText = null;

  final ShootingIntent intent;

  /// 依据。空 = 给不出建议。
  final List<ExposureRule> rules;

  /// 规则给出的**确定**快门值（秒）。null = 官方没给固定值。
  final double? shutterSeconds;

  /// 给用户看的快门说明。
  final String? shutterText;

  /// 给用户看的光圈说明（null = 没有可靠依据）。
  final String? apertureText;

  /// 这个意图有没有可靠依据。
  bool get isCovered => rules.isNotEmpty;
}

/// 晴天户外基准（阳光16法则）。
///
/// 用途有两个：① 教用户；② 作为**曝光计算的锚点** —— 它定义了
/// 「晴天户外」这个场景的 EV100 = log2(16²/(1/100)) ≈ 14.64。
///
/// ⚠️ 出处是 camera-wiki（规则本身是摄影界的通用常识，但这里仍如实标注来源，
/// 不冒充厂商官方）。后续若找到 Canon/Nikon 官方同款表述，应替换为官方出处。
const ExposureRule kSunny16Rule = ExposureRule(
  publisher: 'camera-wiki',
  url: 'https://camera-wiki.org/wiki/Sunny_16',
  statement: 'proper exposure on a sunny day is achieved with aperture set to '
      'f/16, combined with shutter speed set to the reciprocal of your film '
      'speed（ISO 100 → 1/100s）',
);

/// 各意图的知识。
///
/// **加新意图的正确顺序**：先找到权威出处 → 再加规则。
/// 找不到就先登记成 [IntentKnowledge.notCovered] —— 界面上会如实显示
/// 「给不出建议」，而不是给一个编出来的数字。
const Map<ShootingIntent, IntentKnowledge> kIntentKnowledge = {
  ShootingIntent.water: IntentKnowledge(
    intent: ShootingIntent.water,
    shutterSeconds: 2.0,
    shutterText: '2 秒（中等水势）；水流急的话 1 秒就够',
    rules: [
      ExposureRule(
        publisher: 'Canon 官方（Canon HK 摄影俱乐部）',
        url: 'https://www.canon.com.hk/en/club/article/itemDetail.do?itemId=10340',
        statement: 'To make the waterfall look silky and smooth, a shutter '
            'speed of 2s is adequate for a moderate water flow rate. For fast '
            'flowing water, a shutter speed of 1s is enough.',
      ),
      ExposureRule(
        publisher: 'Canon 官方（Canon HK 摄影俱乐部）',
        url: 'https://www.canon.com.hk/en/club/article/itemDetail.do?itemId=10340',
        statement: 'use a ND filter whenever they are taking photos of '
            'waterfall in order to achieve a slower shutter speed；并提醒'
            '快门太慢会让风中的枝叶也糊掉',
      ),
    ],
  ),
  ShootingIntent.night: IntentKnowledge(
    intent: ShootingIntent.night,
    // ⚠️ 官方这一页只给了**方法**，没给固定快门值 —— 所以这里不给数字。
    shutterText: '没有官方固定值 —— 想不糊：开大光圈 或 提高 ISO（有条件上三脚架）',
    rules: [
      ExposureRule(
        publisher: 'Canon 中国 官方（分场景介绍夜景摄影技巧）',
        url: 'https://www.canon.com.cn/special/nightscape/3.html',
        statement: '在夜晚拍摄中要小心快门速度较低引起的手抖动和相机抖动；'
            '若想在保持适当曝光的同时提高快门速度，除了增加主体亮度、'
            '打开镜头光圈之外，还可以提高 ISO 感光度；'
            '在得到适当曝光的同时想提高快门速度，只有「开大光圈」'
            '或「提高 ISO」两种方法',
      ),
    ],
  ),
  // 下面三个**故意留空**：我还没找到可核对的权威出处。
  // 宁可界面上写「给不出建议」，也不编数字（人类 2026-09-20 的裁决）。
  ShootingIntent.portrait: IntentKnowledge.notCovered(
    ShootingIntent.portrait,
    '还没找到可核对的可靠依据 —— 人像的光圈/快门取决于'
        '你要不要虚化、主体动不动',
  ),
  ShootingIntent.landscape: IntentKnowledge.notCovered(
    ShootingIntent.landscape,
    '还没找到可核对的可靠依据',
  ),
  ShootingIntent.motion: IntentKnowledge.notCovered(
    ShootingIntent.motion,
    '还没找到可核对的可靠依据 —— 冻结还是拖影，取决于主体多快',
  ),
};

// ---------------------------------------------------------------------------
// 下面是**数学**，不是经验 —— 曝光方程是物理，可以放心算。
// ---------------------------------------------------------------------------

/// 曝光值：`EV = log2(N² / t)`（N = 光圈值，t = 快门秒数）。
double exposureValue({required double aperture, required double shutterSeconds}) {
  if (aperture <= 0 || shutterSeconds <= 0) {
    throw ArgumentError('光圈和快门必须是正数：f/$aperture, $shutterSeconds s');
  }
  return _log2(aperture * aperture / shutterSeconds);
}

/// 从照片**真实用过**的 ISO/快门/光圈 反推这个场景的光强度（EV100）。
///
/// 这是「通过照片自动算最优值」的关键一步：EXIF 是实测数据，
/// 拿它当基准，再换算成别的快门/光圈需要多少 ISO，全程都是数学。
double sceneEv100({
  required double iso,
  required double shutterSeconds,
  required double aperture,
}) {
  if (iso <= 0) throw ArgumentError('ISO 必须为正数：$iso');
  return exposureValue(aperture: aperture, shutterSeconds: shutterSeconds) -
      _log2(iso / 100);
}

/// 在光强度 [ev100] 的场景里，用 [shutterSeconds] + [aperture] 需要多少 ISO。
///
/// 推导：`EV_setting = log2(N²/t)`，`ISO = 100 · 2^(EV_setting − EV100_scene)`。
double isoFor({
  required double ev100,
  required double shutterSeconds,
  required double aperture,
}) {
  final evSetting =
      exposureValue(aperture: aperture, shutterSeconds: shutterSeconds);
  return 100 * math.pow(2, evSetting - ev100).toDouble();
}

double _log2(double x) => math.log(x) / math.ln2;
