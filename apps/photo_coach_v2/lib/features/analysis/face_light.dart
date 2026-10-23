library;

import 'dart:math' as math;

import '../guidance/subject_detector.dart' show RgbGrid;
import 'face_detector.dart' show FaceDetection;

/// 面部光影判定 —— 纯规则、纯 Dart、零新增依赖、离线可用。
///
/// 量五个量（全部 0-1 亮度，Rec.709）：
/// 脸平均亮度 / 背景亮度 / 左右差 / 上下差 / 明暗对比，
/// 然后按优先级落进五档之一。**量不出就诚实说量不出**，不编。

/// 五档光影。
enum FaceLightVerdict {
  backlight, // 逆光：脸比背景暗
  overexposed, // 过曝：脸太亮
  underexposed, // 欠曝：整张太暗
  sideLight, // 侧光：脸左右亮度差明显
  flatLight, // 平光：均匀适中（好事）
  mixed, // 混合：没有明显单因素问题
}

extension FaceLightVerdictLabel on FaceLightVerdict {
  String get label => switch (this) {
        FaceLightVerdict.backlight => '逆光（脸比背景暗）',
        FaceLightVerdict.overexposed => '过曝（脸太亮）',
        FaceLightVerdict.underexposed => '欠曝（整张偏暗）',
        FaceLightVerdict.sideLight => '侧光（脸左右不均）',
        FaceLightVerdict.flatLight => '平光（均匀适中）',
        FaceLightVerdict.mixed => '混合（无明显单一问题）',
      };

  String get icon => switch (this) {
        FaceLightVerdict.backlight => '🌘',
        FaceLightVerdict.overexposed => '🌞',
        FaceLightVerdict.underexposed => '🌑',
        FaceLightVerdict.sideLight => '◐',
        FaceLightVerdict.flatLight => '😌',
        FaceLightVerdict.mixed => '🎲',
      };
}

/// 测量值（0-1 亮度口径）。
class FaceLightStats {
  const FaceLightStats({
    required this.faceLuma,
    required this.bgLuma,
    required this.faceBgRatio,
    required this.leftLuma,
    required this.rightLuma,
    required this.sideGradient,
    required this.topLuma,
    required this.bottomLuma,
    required this.verticalGradient,
    required this.contrast,
  });

  /// 脸平均亮度。
  final double faceLuma;

  /// 背景平均亮度（画面边缘环）。
  final double bgLuma;

  /// 脸/背景 亮度比。<1 = 脸比背景暗。
  final double faceBgRatio;

  final double leftLuma;
  final double rightLuma;

  /// 左右亮度差 / max(L,R)。>0.22 ≈ 明显侧光。
  final double sideGradient;

  final double topLuma;
  final double bottomLuma;

  final double verticalGradient;

  /// 脸内亮度标准差（明暗对比）。
  final double contrast;

  /// 给视觉模型参考的测量段（本地测得，喂进 prompt 让模型聚焦）。
  String get promptText {
    String pct(double v) => (v * 100).round().toString();
    final l2r = (rightLuma - leftLuma).abs();
    final t2b = (bottomLuma - topLuma).abs();
    return '【本地测量·面部光影】'
        '脸平均亮度 ${pct(faceLuma)}%，背景 ${pct(bgLuma)}%'
        '（脸/背景 = ${(faceBgRatio * 100).round()}%），'
        '左右亮度差 ${pct(l2r)}%，上下差 ${pct(t2b)}%，'
        '脸内明暗对比 ${pct(contrast)}%。'
        '评估时请重点看面部光影：脸是否吃光、阴影一侧是否死黑。';
  }
}

/// 阈值集中管理，方便按真机效果调。
class FaceLightThresholds {
  const FaceLightThresholds({
    this.backlightFaceMax = 0.32,
    this.backlightBgMin = 0.45,
    this.backlightRatioMax = 0.75,
    this.overexposedFaceMin = 0.85,
    this.underexposedFaceMax = 0.22,
    this.underexposedBgMax = 0.50,
    this.sideGradientMin = 0.22,
    this.flatFaceMin = 0.35,
    this.flatFaceMax = 0.68,
    this.flatContrastMax = 0.20,
    this.flatSideMax = 0.15,
    this.shrink = 0.15,
  });

  static const standard = FaceLightThresholds();

  final double backlightFaceMax;
  final double backlightBgMin;
  final double backlightRatioMax;
  final double overexposedFaceMin;
  final double underexposedFaceMax;
  final double underexposedBgMax;
  final double sideGradientMin;
  final double flatFaceMin;
  final double flatFaceMax;
  final double flatContrastMax;
  final double flatSideMax;

  /// 脸框向内缩的比例（避开头发/脖子边缘）。
  final double shrink;
}

/// 一次面部光影分析的结果。
class FaceLightReport {
  const FaceLightReport({
    required this.faceFound,
    required this.verdict,
    required this.summary,
    this.advice = const [],
    this.stats,
    this.detectorSource = '',
    this.detectorNote = '',
  });

  final bool faceFound;
  final FaceLightVerdict verdict;

  /// 一句话判断（给用户看，说人话）。
  final String summary;

  /// 可执行建议（1-3 条，按优先级排好）。
  final List<String> advice;

  /// 量不出（框太小/没脸）时为 null —— 诚实边界。
  final FaceLightStats? stats;

  /// 脸框来自谁（heuristic/yunet/…），UI 标注来源。
  final String detectorSource;

  /// 检测器没找到时的原因。
  final String detectorNote;

  /// 供 prompt 使用的测量段（没量出 = 空）。
  String get promptSection => stats?.promptText ?? '';

  /// 测量值的口语化描述（UI 卡片用）。
  String get measurementLine {
    final s = stats;
    if (s == null) return '（框太小，量不出亮度）';
    String pct(double v) => '${(v * 100).round()}%';
    return '脸亮度 ${pct(s.faceLuma)} · 背景 ${pct(s.bgLuma)} · '
        '左右差 ${pct((s.rightLuma - s.leftLuma).abs())}';
  }
}

/// 面部光影分析器：网格 + 脸框 → 五档判定 + 建议。无 IO，可单测。
class FaceLightAnalyzer {
  const FaceLightAnalyzer({
    this.thresholds = FaceLightThresholds.standard,
  });

  final FaceLightThresholds thresholds;

  FaceLightReport analyze(RgbGrid grid, FaceDetection face) {
    final src = face.source;
    final note = face.reason;

    if (!face.found || face.box == null || grid.width < 4 || grid.height < 4) {
      return FaceLightReport(
        faceFound: false,
        verdict: FaceLightVerdict.mixed,
        summary: '这张照片没找到脸，给不了面部光影判断',
        advice: const [
          '把脸拍进画面、占一点面积，就能量面部亮度了',
          '通用技巧：看屏幕取景，让脸处于「不黑不白」的中间亮度',
        ],
        detectorSource: src,
        detectorNote: note,
      );
    }

    final t = thresholds;
    final w = grid.width;
    final h = grid.height;
    final box = face.box!;

    // 脸框 → 像素（先夹住边界）
    var x0 = (box.left * w).round();
    var y0 = (box.top * h).round();
    var x1 = (box.right * w).round() - 1;
    var y1 = (box.bottom * h).round() - 1;
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 >= w) x1 = w - 1;
    if (y1 >= h) y1 = h - 1;
    if (x1 <= x0 || y1 <= y0) {
      return FaceLightReport(
        faceFound: true,
        verdict: FaceLightVerdict.mixed,
        summary: '找到了脸，但框太小，量不出光影',
        advice: const [
          '离近一点再拍，脸占大一些就能量面部亮度了',
        ],
        detectorSource: src,
        detectorNote: note,
      );
    }

    // 向内缩（避开头发/脖子）
    final bw = x1 - x0 + 1;
    final bh = y1 - y0 + 1;
    final sx = (bw * t.shrink).floor();
    final sy = (bh * t.shrink).floor();
    final ix0 = x0 + sx;
    final iy0 = y0 + sy;
    final ix1 = x1 - sx;
    final iy1 = y1 - sy;

    var sum = 0.0, sumSq = 0.0, count = 0;
    var lSum = 0.0, lN = 0, rSum = 0.0, rN = 0;
    var tSum = 0.0, tN = 0, bSum = 0.0, bN = 0;
    final cx = (ix0 + ix1) / 2;
    final cy = (iy0 + iy1) / 2;

    for (var y = iy0; y <= iy1; y++) {
      for (var x = ix0; x <= ix1; x++) {
        final l = grid.lumaAt(y * w + x);
        sum += l;
        sumSq += l * l;
        count++;
        if (x < cx) {
          lSum += l;
          lN++;
        } else {
          rSum += l;
          rN++;
        }
        if (y < cy) {
          tSum += l;
          tN++;
        } else {
          bSum += l;
          bN++;
        }
      }
    }

    if (count < 4 || lN < 1 || rN < 1) {
      return FaceLightReport(
        faceFound: true,
        verdict: FaceLightVerdict.mixed,
        summary: '脸框太小（缩进后不足 4 格），量不出光影',
        advice: const [
          '离近一点再拍，脸占大一些就能量面部亮度了',
        ],
        detectorSource: src,
        detectorNote: note,
      );
    }

    final faceLuma = sum / count;
    final variance =
        (sumSq / count - faceLuma * faceLuma).clamp(0.0, 1.0);
    final contrast = math.sqrt(variance);
    final leftLuma = lSum / lN;
    final rightLuma = rSum / rN;
    final topLuma = tN > 0 ? tSum / tN : leftLuma;
    final bottomLuma = bN > 0 ? bSum / bN : rightLuma;
    double gradOf(double a, double b) {
      final m = math.max(a, b);
      return m < 0.04 ? 0.0 : (a - b).abs() / m;
    }
    final sideGradient = gradOf(leftLuma, rightLuma);
    final verticalGradient = gradOf(topLuma, bottomLuma);

    // 背景 = 画面边缘环（1 圈）
    var bgSum = 0.0;
    var bgN = 0;
    for (var x = 0; x < w; x++) {
      for (final y in [0, h - 1]) {
        bgSum += grid.lumaAt(y * w + x);
        bgN++;
      }
    }
    for (var y = 1; y < h - 1; y++) {
      for (final x in [0, w - 1]) {
        bgSum += grid.lumaAt(y * w + x);
        bgN++;
      }
    }
    final bgLuma = bgN > 0 ? bgSum / bgN : 0.5;
    final faceBgRatio = faceLuma / math.max(bgLuma, 0.04);

    final stats = FaceLightStats(
      faceLuma: faceLuma,
      bgLuma: bgLuma,
      faceBgRatio: faceBgRatio,
      leftLuma: leftLuma,
      rightLuma: rightLuma,
      sideGradient: sideGradient,
      topLuma: topLuma,
      bottomLuma: bottomLuma,
      verticalGradient: verticalGradient,
      contrast: contrast,
    );

    // ---- 规则优先级：逆光 > 过曝 > 欠曝 > 侧光 > 平光 > 混合 ----
    if (faceLuma < t.backlightFaceMax &&
        bgLuma > t.backlightBgMin &&
        faceBgRatio < t.backlightRatioMax) {
      return FaceLightReport(
        faceFound: true,
        verdict: FaceLightVerdict.backlight,
        summary: '你在逆光里，脸比背景暗，拍出来会偏黑',
        advice: const [
          '让人站回亮处：转向窗户 / 光源方向，别背对强光',
          '要保留亮背景：给脸补光——白墙/白天花板反光，或举一张白纸当补光板',
          '相机里点一下脸对焦，再往上滑曝光补偿，把脸提亮',
        ],
        stats: stats,
        detectorSource: src,
        detectorNote: note,
      );
    }
    if (faceLuma > t.overexposedFaceMin) {
      return FaceLightReport(
        faceFound: true,
        verdict: FaceLightVerdict.overexposed,
        summary: '脸过曝了，皮肤细节拍没了',
        advice: const [
          '相机里点一下脸对焦，往下滑曝光补偿，把脸压暗一点',
          '或让人离强光源（太阳/窗口）退一步',
        ],
        stats: stats,
        detectorSource: src,
        detectorNote: note,
      );
    }
    if (faceLuma < t.underexposedFaceMax && bgLuma < t.underexposedBgMax) {
      return FaceLightReport(
        faceFound: true,
        verdict: FaceLightVerdict.underexposed,
        summary: '整张偏暗，脸也欠曝',
        advice: const [
          '相机里点一下脸对焦，往上滑曝光补偿',
          '或换个亮一点的位置（窗边/灯下）再拍',
        ],
        stats: stats,
        detectorSource: src,
        detectorNote: note,
      );
    }
    if (sideGradient > t.sideGradientMin &&
        faceLuma >= 0.20 &&
        faceLuma <= 0.85) {
      return FaceLightReport(
        faceFound: true,
        verdict: FaceLightVerdict.sideLight,
        summary: '侧光照在脸的一侧，左右亮度差明显',
        advice: const [
          '要均匀：让人脸再转向光源一点，或用反光物给暗侧补一点光',
          '喜欢立体感：脸朝光源 45° 拍也行，但别让暗侧死黑',
        ],
        stats: stats,
        detectorSource: src,
        detectorNote: note,
      );
    }
    if (faceLuma >= t.flatFaceMin &&
        faceLuma <= t.flatFaceMax &&
        contrast <= t.flatContrastMax &&
        sideGradient <= t.flatSideMax) {
      return FaceLightReport(
        faceFound: true,
        verdict: FaceLightVerdict.flatLight,
        summary: '光很均匀，脸亮度合适——这个光就很好',
        advice: const [
          '保持这个光线直接拍，不用调',
        ],
        stats: stats,
        detectorSource: src,
        detectorNote: note,
      );
    }
    return FaceLightReport(
      faceFound: true,
      verdict: FaceLightVerdict.mixed,
      summary: '光影比较混合，没有明显单一问题',
      advice: const [
        '看一眼取景里脸是不是太暗或太白，用曝光补偿微调',
      ],
      stats: stats,
      detectorSource: src,
      detectorNote: note,
    );
  }
}

/// 便捷常量：默认分析器（供教练页直接用）。
const faceLightAnalyzer = FaceLightAnalyzer();

/// 用户**主动声明**的光线方向（v0.9.0 环境指导）。
///
/// 为什么单独一类、不复用 [FaceLightVerdict]：
/// - Verdict 是**系统量出来的结论**（五档，含过曝/欠曝这些"质量"问题）；
/// - Choice 是**用户的意图**（顺光/侧光/逆光，回答"我打算用什么光拍"）。
/// 两者口径不同：选「侧光」是审美选择，不是"出问题了"。混用会互相污染。
///
/// 作用链：拍摄页选择 → AppSession 持有 → 送教练时拼进 prompt 上下文，
/// 让 AI（或本地兜底）能对照「这个姿势要柔光/这个位置是逆光」给建议。
class FaceLightChoice {
  const FaceLightChoice({
    required this.direction,
    required this.confidence,
    required this.estimated,
    required this.timestamp,
  });

  /// 顺光 / 侧光 / 逆光（中文，和 UI 按钮、prompt 同词表）。
  final String direction;

  /// 选择时本地光向探针的置信度（0-1；探针没结论 = null，诚实标注）。
  final double? confidence;

  /// true = 选择基于本地自动探测，false = 用户手点。
  final bool estimated;

  final DateTime timestamp;

  /// 拼进教练 prompt 的一句上下文（没选 = 空串，prompt 不变）。
  String get promptText =>
      '【用户声明·光线方向】$direction'
      '${confidence != null ? '（本地探测置信 ${(confidence! * 100).round()}%）' : '（手动选择）'}。'
      '点评时请结合这个光线方向给建议（比如逆光如何补光、侧光如何转向）。';

  /// 人话摘要（教练页卡片 / 日志用）。
  String get summary => estimated
      ? '光向：$direction（本地探测）'
      : '光向：$direction（手动选择）';
}
