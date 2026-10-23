import '../coach/suggestion.dart' show Rect01;

/// 距离建议 —— 「你离镜头太近了 / 退远一点」这种话。
///
/// 为什么是纯 Dart 无 IO：输入只有**归一化框**（0-1），
/// 决策逻辑是几个阈值比较，天生适合单元测试，也不需要再碰像素。
///
/// 数据从哪来（调用方组装）：
/// - face 检测：FaceDetector.detectFromBytes 的结果（脸框 = 占画面多高）；
/// - 目标景别：PoseGuidance.framing（全身 / 七分身 / 半身，中文）；
/// - 主体框兜底：SubjectDetector 的 currentBox（脸没找到但人有时的兜底）。

/// 档位。
enum DistanceLevel {
  /// 距离正合适。
  okay,

  /// 太近了。
  tooClose,

  /// 太远了。
  tooFar,

  /// 判断不了（没脸没主体，或画面量不出来）。
  unknown,
}

/// 阈值集中管理 —— 按真机效果调只改这里，测试直接引用。
///
/// 全部是「脸框高度占画面高度的比例」(faceH，归一化 0-1)：
/// 脸占画面越高 = 人离镜头越近。
class DistanceAdvisorThresholds {
  const DistanceAdvisorThresholds({
    // ── 半身目标 ──
    this.halfOkayMin = 0.28,
    this.halfOkayMax = 0.55,
    this.halfTooFarMax = 0.18, // faceH < 0.18 → 太远了
    this.halfTooCloseMin = 0.75, // faceH > 0.75 → 太近了
    // 模糊区 = [0.18, 0.28) 和 (0.55, 0.75]，按最近档给「差不多，微调」

    // ── 全身目标（目标脸占比更小）──
    this.fullOkayMin = 0.08,
    this.fullOkayMax = 0.22,
    this.fullTooFarMax = 0.05,
    this.fullTooCloseMin = 0.34,

    // ── 七分身目标 ──
    this.threeQuarterOkayMin = 0.14,
    this.threeQuarterOkayMax = 0.34,
    this.threeQuarterTooFarMax = 0.08,
    this.threeQuarterTooCloseMin = 0.48,

    // ── 主体高度占比兜底（脸没找到、人找到了）──
    this.subjectTooFarMax = 0.3, // 主体高度 < 0.3 → 太远了
    this.subjectTooCloseMin = 0.85, // 主体高度 > 0.85 → 太近了
    // 中间一律 okay（按身体占比判断）
  });

  final double halfOkayMin;
  final double halfOkayMax;
  final double halfTooFarMax;
  final double halfTooCloseMin;

  final double fullOkayMin;
  final double fullOkayMax;
  final double fullTooFarMax;
  final double fullTooCloseMin;

  final double threeQuarterOkayMin;
  final double threeQuarterOkayMax;
  final double threeQuarterTooFarMax;
  final double threeQuarterTooCloseMin;

  final double subjectTooFarMax;
  final double subjectTooCloseMin;

  static const standard = DistanceAdvisorThresholds();
}

/// 一次建议。
class DistanceAdvice {
  const DistanceAdvice({
    required this.level,
    required this.message,
    this.faceRatio,
    this.position,
  });

  final DistanceLevel level;

  /// 给 UI 直接显示的一句人话。
  final String message;

  /// 脸框高度占比（没找到脸 = null）。UI 想显示百分比可以用。
  final double? faceRatio;

  /// 0–1 刻度位置：脸占比落在「合适区间」[okayMin, okayMax] 内的位置，
  /// 越靠近 0 越远、越靠近 1 越近。
  ///
  /// 模糊区 clamp 到 0 / 1 端点，太近/太远越界时同样钉在端点外沿
  /// （faceH 超界也 clamp 到 [0,1]，刻度不穿板）。
  /// UI 拿它画「近 ──●── 远」刻度条；unknown = null（画中性 0.5）。
  final double? position;

  /// 不知道怎么说 —— UI 用灰色显示（或干脆隐藏条）。
  static const unknown = DistanceAdvice(
    level: DistanceLevel.unknown,
    message: '没找到人脸，没法判断距离——把脸转正朝向镜头',
  );
}

/// 纯决策类：给框 + 景别 → 建议。无 IO、无 isolate、可任意并发调用。
class DistanceAdvisor {
  const DistanceAdvisor({
    this.thresholds = DistanceAdvisorThresholds.standard,
  });

  final DistanceAdvisorThresholds thresholds;

  /// 给一条建议。
  ///
  /// - [faceFound]/[faceBox]：脸检测的结论。没找到脸时 [faceBox] 应为 null，
  ///   此时按 [subjectBox]（主体框）兜底；主体也没有 → [DistanceAdvice.unknown]。
  /// - [framing]：目标景别中文名（「全身」「七分身」「半身」，来自
  ///   [PoseGuidance.framing]）；null / 不认识 → 按「半身」处理（默认档）。
  DistanceAdvice advise({
    required bool faceFound,
    required Rect01? faceBox,
    Rect01? subjectBox,
    String? framing,
  }) {
    final t = thresholds;

    if (faceFound && faceBox != null) {
      final faceH = faceBox.height;
      return _adviseByFaceH(faceH, framing, t);
    }

    // 脸没找到 → 主体兜底（人比脸大，用**高度**占比）
    if (subjectBox != null) {
      final subjectH = subjectBox.height;
      if (subjectH < t.subjectTooFarMax) {
        return const DistanceAdvice(
          level: DistanceLevel.tooFar,
          message: '按身体占比看有点远，往前走一点',
        );
      }
      if (subjectH > t.subjectTooCloseMin) {
        return const DistanceAdvice(
          level: DistanceLevel.tooClose,
          message: '按身体占比看有点近，往后退一点',
        );
      }
      return const DistanceAdvice(
        level: DistanceLevel.okay,
        message: '按身体占比看距离合适',
      );
    }

    // 脸和主体都没找到 → 如实说不知道，绝不编。
    return DistanceAdvice.unknown;
  }

  /// 按脸高占比分档。规则（全部对着 [DistanceAdvisorThresholds] 的注释读）：
  /// - faceH 在 [okayMin, okayMax] → okay；
  /// - faceH < tooFarMax → tooFar「站近一点，脸在画面里太小」；
  /// - faceH > tooCloseMin → tooClose「退远一点，脸占满了画面」；
  /// - 中间模糊区（tooFarMax ≤ faceH < okayMin 或 okayMax < faceH ≤ tooCloseMin）
  ///   → 按**最近档**给「差不多，微调」，不吓唬人。
  DistanceAdvice _adviseByFaceH(
    double faceH,
    String? framing,
    DistanceAdvisorThresholds t,
  ) {
    // 各档阈值表（半身 / 全身 / 七分身）
    final (okayMin, okayMax, tooFarMax, tooCloseMin) = switch (framing) {
      '全身' => (
          t.fullOkayMin,
          t.fullOkayMax,
          t.fullTooFarMax,
          t.fullTooCloseMin,
        ),
      '七分身' => (
          t.threeQuarterOkayMin,
          t.threeQuarterOkayMax,
          t.threeQuarterTooFarMax,
          t.threeQuarterTooCloseMin,
        ),
      _ => (
          // null 或没写过的景别 → 默认按「半身」档
          t.halfOkayMin,
          t.halfOkayMax,
          t.halfTooFarMax,
          t.halfTooCloseMin,
        ),
    };

    final level = faceH < tooFarMax
        ? DistanceLevel.tooFar
        : faceH > tooCloseMin
            ? DistanceLevel.tooClose
            : (faceH >= okayMin && faceH <= okayMax)
                ? DistanceLevel.okay
                : // 模糊区：按最近档
                    faceH < okayMin
                        ? DistanceLevel.tooFar
                        : DistanceLevel.tooClose;

    const messages = {
      DistanceLevel.okay: '距离合适，就按这个位置拍',
      DistanceLevel.tooFar: '站近一点，脸在画面里太小',
      DistanceLevel.tooClose: '退远一点，脸占满了画面',
      DistanceLevel.unknown: '',
    };
    // 「差不多，微调」用于模糊区（不硬说太远/太近）。
    const fineTune = '差不多，微调一下就对了';

    final message = switch (level) {
      DistanceLevel.okay => messages[DistanceLevel.okay]!,
      DistanceLevel.tooFar => faceH >= tooFarMax
          ? fineTune // 模糊区：不硬说"太小"
          : messages[DistanceLevel.tooFar]!,
      DistanceLevel.tooClose => faceH <= tooCloseMin
          ? fineTune
          : messages[DistanceLevel.tooClose]!,
      _ => messages[level]!,
    };

    return DistanceAdvice(
      level: level,
      message: message,
      faceRatio: faceH,
      position: ((faceH - okayMin) / (okayMax - okayMin)).clamp(0.0, 1.0),
    );
  }
}
