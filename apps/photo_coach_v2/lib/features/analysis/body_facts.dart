import 'dart:math' as math;

import '../coach/suggestion.dart' show Rect01;

/// 一个关键点 —— **与任何具体姿态引擎解耦的纯数据**，这样这一层能离线单测。
///
/// v2 现状：[NoopBodyScanner] 恒返回 null，本类型暂不被生产代码填充，
/// 保留为「将来接无谷歌依赖姿态引擎」的缝（引擎输出投影成它即可）。
///
/// [type] 沿用人体姿态的通用枚举名（`nose` / `leftShoulder` / `rightAnkle` …），
/// 坐标 x/y 是**归一化 0–1**（与主流姿态引擎的 3D 归一化输出对齐）。
class Landmark {
  const Landmark(this.type, this.x, this.y, {this.likelihood = 1.0});

  final String type;
  final double x;
  final double y;
  final double likelihood;

  @override
  String toString() => '$type(${x.toStringAsFixed(3)},${y.toStringAsFixed(3)})';
}

/// 从人体关键点里**算出来**的客观事实（不是模型的判断）。
///
/// 为什么要有这一层：以前 AI 只能"看图猜"主体在哪、肩是不是歪的。
/// 有了关键点，这些就是**量出来的** —— 界面上必须和"模型判断"分开标注。
class BodyFacts {
  const BodyFacts({
    required this.box,
    required this.visibleCount,
    this.eyeLineY,
    this.shoulderTiltDeg,
    this.lowerShoulder,
    this.headTurnRatio,
    this.headTurnText,
    this.bodySpanRatio,
  });

  /// 可见关键点的包围盒（归一化）。
  final Rect01 box;

  /// 参与计算的关键点个数（置信度达标的）。
  final int visibleCount;

  /// 眼睛所在高度（归一化 y）—— 用来判断"头顶留白够不够"。
  final double? eyeLineY;

  /// 肩线倾斜角（度，已按画面宽高比换算成**真实角度**）。
  final double? shoulderTiltDeg;

  /// 哪边肩膀更低（'左' / '右' / null）。
  final String? lowerShoulder;

  /// 头部左右偏转（-1..1，正 = 头转向画面右侧）。
  final double? headTurnRatio;

  /// 头部转向的文字描述。
  final String? headTurnText;

  /// 可见人体纵向跨度占画面的比例 —— 也就是"人在画面里多大"。
  final double? bodySpanRatio;

  bool get isEmpty => visibleCount == 0;

  /// 给**模型**看的一段话。
  ///
  /// 明确写"这是测量值、直接用、别重新猜"，否则模型还是会按老习惯看图瞎估。
  String toPromptText() {
    final b = <String>[
      '· 可见关键点 $visibleCount 个（置信度 ≥ $_minLikelihood）',
      '· 人体框：左 ${box.left.toStringAsFixed(2)}、上 ${box.top.toStringAsFixed(2)}、'
          '宽 ${box.width.toStringAsFixed(2)}、高 ${box.height.toStringAsFixed(2)}（0–1 归一化）',
      if (bodySpanRatio != null)
        '· 可见人体纵向跨度占画面 ${(bodySpanRatio! * 100).round()}%',
      if (eyeLineY != null)
        '· 眼睛高度在画面 ${(eyeLineY! * 100).round()}% 处'
            '（也就是头顶到画面上边约占 ${(eyeLineY! * 100).round()}%，据此判断头部留白）',
      if (shoulderTiltDeg != null)
        '· 肩线倾斜 ${shoulderTiltDeg!.toStringAsFixed(1)}°'
            '${lowerShoulder == null ? '' : '（${lowerShoulder!}肩低）'}',
      if (headTurnText != null) '· 头部：$headTurnText',
    ];
    return '''
【端上关键点测量值（**请直接采用，不要重新看图猜**）】
${b.join('\n')}
以上是手机端姿态模型**量出来的**，比目测可靠；拍摄方案（站位/机位/方向）请以它为准。
''';
  }

  /// 给**用户**看的事实清单（界面用；必须标注这是"测量值"）。
  List<String> toFactLines() {
    return [
      '人体框 宽 ${(box.width * 100).round()}% · 高 ${(box.height * 100).round()}%',
      if (bodySpanRatio != null)
        '可见人体跨度占画面 ${(bodySpanRatio! * 100).round()}%',
      if (eyeLineY != null) '眼睛在画面 ${(eyeLineY! * 100).round()}% 高度',
      if (shoulderTiltDeg != null)
        '肩线倾斜 ${shoulderTiltDeg!.toStringAsFixed(1)}°'
            '${lowerShoulder == null ? '' : '（${lowerShoulder!}肩低）'}',
      if (headTurnText != null) '头部：$headTurnText',
      '关键点 $visibleCount 个',
    ];
  }
}

/// 置信度门槛：低于它的关键点直接丢掉（宁可少算，也别用不可靠的点）。
const double _minLikelihood = 0.5;

/// 从关键点算客观事实。
///
/// [imageAspectRatio] = 图宽 / 图高。**必须有它**：归一化坐标里 x 和 y 的
/// 单位长度不一样（x 是相对宽度、y 是相对高度），不换算的话"肩线倾斜 6°"
/// 会是个假角度。
///
/// 有任何一点不在 0–1 范围内（说明上游给的不是归一化坐标）→ 返回 null，
/// **绝不用来路不明的坐标算出一个看起来很像的结论**。
BodyFacts? bodyFactsFrom(
  List<Landmark> landmarks, {
  required double imageAspectRatio,
}) {
  if (imageAspectRatio <= 0) return null;

  final usable = [
    for (final l in landmarks)
      if (l.likelihood >= _minLikelihood &&
          l.x >= 0 && l.x <= 1 && l.y >= 0 && l.y <= 1)
        l
  ];
  if (usable.isEmpty) return null;

  final xs = usable.map((l) => l.x);
  final ys = usable.map((l) => l.y);
  final minX = xs.reduce(math.min), maxX = xs.reduce(math.max);
  final minY = ys.reduce(math.min), maxY = ys.reduce(math.max);

  final box = Rect01(minX, minY, maxX - minX, maxY - minY);

  Landmark? find(String t) {
    for (final l in usable) {
      if (l.type == t) return l;
    }
    return null;
  }

  final eyes = [
    find('leftEye'),
    find('rightEye'),
    find('leftEyeInner'),
    find('rightEyeInner'),
    find('leftEyeOuter'),
    find('rightEyeOuter'),
  ].whereType<Landmark>().toList();
  final eyeLineY =
      eyes.isEmpty ? null : eyes.map((e) => e.y).reduce((a, b) => a + b) / eyes.length;

  // 肩线倾斜：换成"真实像素比例"再算角度，否则是个假角度
  double? shoulderTilt;
  String? lowerShoulder;
  final ls = find('leftShoulder');
  final rs = find('rightShoulder');
  if (ls != null && rs != null) {
    final dx = (rs.x - ls.x) * imageAspectRatio; // 横向真实比例
    final dy = rs.y - ls.y; // 纵向本来就是相对高度
    if (dx.abs() > 1e-6) {
      shoulderTilt = math.atan2(dy.abs(), dx.abs()) * 180 / math.pi;
      lowerShoulder = dy > 0 ? '右' : '左'; // y 越大越靠下
    }
  }

  // 头部转向：鼻子相对两耳中点的偏移，用耳距归一化
  double? headTurn;
  String? headTurnText;
  final nose = find('nose');
  final le = find('leftEar');
  final re = find('rightEar');
  if (nose != null && le != null && re != null) {
    final earMid = (le.x + re.x) / 2;
    final earSpan = (re.x - le.x).abs();
    if (earSpan > 1e-6) {
      headTurn = ((nose.x - earMid) / earSpan * 2).clamp(-1.0, 1.0);
      headTurnText = headTurn.abs() < 0.15
          ? '基本正对镜头'
          : (headTurn > 0 ? '头偏向画面右侧' : '头偏向画面左侧');
    }
  }

  return BodyFacts(
    box: box,
    visibleCount: usable.length,
    eyeLineY: eyeLineY,
    shoulderTiltDeg: shoulderTilt,
    lowerShoulder: lowerShoulder,
    headTurnRatio: headTurn,
    headTurnText: headTurnText,
    bodySpanRatio: maxY - minY,
  );
}
