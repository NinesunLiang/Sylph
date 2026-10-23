import '../coach/suggestion.dart' show Rect01;

/// F2.11 —— 实时对位反馈：把「主体现在在哪」和「建议在哪」比一比，
/// 输出一句人话（往左挪 / 靠近点 / 保持不动）。
///
/// 纯函数，可单测。UI 只负责把它画成箭头和文字。
///
/// 为什么不用大模型做这件事：这是在**预览期间反复跑**的（每秒一两次），
/// 网络往返 3–8 秒根本来不及，而且用户挪一下就要重算。所以必须本地。
/// 大模型负责「应该拍成什么样」（一次性），本地负责「你现在差多少」（实时）。
enum AlignAction {
  stable('保持不动，可以按快门了'),
  moveLeft('向左移一点'),
  moveRight('向右移一点'),
  moveUp('相机往上抬一点'),
  moveDown('相机往下压一点'),
  moveCloser('靠近一点'),
  moveBack('往后退一点');

  const AlignAction(this.label);
  final String label;
}

/// 一次对位判定。
class AlignFeedback {
  const AlignFeedback({
    required this.action,
    required this.dx,
    required this.dy,
    required this.sizeRatio,
    required this.aligned,
    required this.message,
    this.degrees,
  });

  final AlignAction action;

  /// 目标中心 - 当前中心（归一化，正数 = 主体要往右/下走）。
  final double dx;
  final double dy;

  /// 当前主体大小 / 目标主体大小。>1 说明太近了。
  final double sizeRatio;

  /// 是否已经对齐（在容差内）。
  final bool aligned;

  /// 给用户看的一句话（带幅度和角度）。
  final String message;

  /// 需要转动多少度（估算，不同镜头 FOV 不同，UI 上标「约」）。
  final double? degrees;

  bool get hasSubject => true;

  Map<String, Object?> toJson() => {
        'action': action.name,
        'dx': dx,
        'dy': dy,
        'size_ratio': sizeRatio,
        'aligned': aligned,
        'message': message,
        if (degrees != null) 'degrees': degrees,
      };
}

class AlignThresholds {
  const AlignThresholds({
    this.posTolerance = 0.07,
    this.sizeTolerance = 0.25,
    this.preferSize = true,
    this.posFloor = 0.12,
    this.severeSizeFactor = 0.5,
  });

  /// 中心点差多少以内算对齐（归一化，0.07 ≈ 画面宽度的 7%）。
  final double posTolerance;

  /// 大小差多少以内算对齐（0.25 = 25%）。
  final double sizeTolerance;

  /// 是否对主体大小也提要求（推荐构图通常对大小有要求）。
  final bool preferSize;

  /// **绝对**位移门槛。
  ///
  /// 为什么需要它：主体「太小」时，它的中心总是偏向画面中心，
  /// 于是「太小」会顺带产生一个小位移。如果只看 [posTolerance]，
  /// 就会对着一个其实在中间的小主体喊「往右挪」，很蠢。
  /// 低于这个绝对量就当没偏，交给大小逻辑处理。
  final double posFloor;

  /// 主体面积小于目标面积的这个比例时，不管位置，先让用户靠近。
  ///
  /// 理由：主体只占画面 1/4 大小时，抠位置没有意义 —— 靠近了位置自然会变。
  final double severeSizeFactor;

  static const standard = AlignThresholds();
}

/// 比较当前主体框与目标框。
///
/// [current] 本地检测到的（[Rect01]），[target] 建议的（来自 F2 建议 JSON）。
/// 任一为空时返回「没数据」（用 [null] 表示，调用方据此显示兜底提示）。
AlignFeedback? compareAlignment(
  Rect01? current,
  Rect01? target, {
  AlignThresholds thresholds = AlignThresholds.standard,
}) {
  if (current == null || target == null) return null;

  final dx = target.centerX - current.centerX;
  final dy = target.centerY - current.centerY;

  final targetArea = target.width * target.height;
  final currentArea = current.width * current.height;
  final sizeRatio =
      targetArea <= 0 ? 1.0 : currentArea / targetArea;

  final t = thresholds;

  // 「偏了」的判定：既要超过相对容差，也要超过绝对量。
  // 只超过容差不算 —— 小主体天生会带一点中心偏移（见 posFloor 注释）。
  final xOff = dx.abs() > t.posTolerance && dx.abs() > t.posFloor;
  final yOff = dy.abs() > t.posTolerance && dy.abs() > t.posFloor;
  final tooSmall = thresholds.preferSize &&
      sizeRatio < t.severeSizeFactor;
  final sizeOff = thresholds.preferSize &&
      (sizeRatio - 1.0).abs() > t.sizeTolerance;

  if (!xOff && !yOff && !sizeOff) {
    return AlignFeedback(
      action: AlignAction.stable,
      dx: dx,
      dy: dy,
      sizeRatio: sizeRatio,
      aligned: true,
      message: AlignAction.stable.label,
    );
  }

  double? degrees;

  // 情况 1：主体严重偏小 → 先让用户靠近（位置等靠近完再算）
  if (tooSmall) {
    return AlignFeedback(
      action: AlignAction.moveCloser,
      dx: dx,
      dy: dy,
      sizeRatio: sizeRatio,
      aligned: false,
      message: '人太小了，走近一点再拍',
    );
  }

  final parts = <String>[];
  AlignAction action = AlignAction.stable;

  if (xOff) {
    // ⚠️ 这里回答的是「**相机**往哪边摇」，不是「主体往哪边走」——
    // 看 label 的口吻就知道（moveUp 是「相机往上抬一点」）。
    // dx > 0：目标在主体右边 → 要让主体在画面里往右走 → 相机必须往**左**摇。
    // （相机往右摇，画面里的东西会往左走。）
    // 之前这里写反了：用户照着做会离目标越来越远，而且图层上那个
    // 「当前框 → 目标框」的箭头方向是对的，文字却和箭头相反。
    action = dx > 0 ? AlignAction.moveLeft : AlignAction.moveRight;
    final deg = panDegreesFor(-dx);
    degrees = deg;
    parts.add('${action.label} ${(dx.abs() * 100).toStringAsFixed(0)}%'
        '（约 ${deg.abs().toStringAsFixed(0)}°）');
  }
  if (yOff) {
    // dy > 0：目标在主体下方 → 要让主体在画面里往下走 → 相机必须往**上**抬。
    final yAction = dy > 0 ? AlignAction.moveUp : AlignAction.moveDown;
    if (action == AlignAction.stable) {
      action = yAction;
      final deg = tiltDegreesFor(-dy);
      degrees = deg;
    }
    // ⚠️ 必须用 `yAction.label`，不能写 `'$yAction'` ——
    // 枚举插值会把内部名字直接给用户看（「AlignAction.moveUp 30%」）。
    parts.add('${yAction.label} ${(dy.abs() * 100).toStringAsFixed(0)}%');
  }
  if (!xOff && !yOff && sizeOff) {
    if (sizeRatio < 1) {
      action = AlignAction.moveCloser;
      // 偏小 → 人话（不用百分比，小白看不懂 70% 意味着什么）
      final deficit = 1 - sizeRatio;
      parts.add(deficit > 0.5
          ? '离太远了，走近一点'
          : '再走近一点，人有点小');
    } else {
      action = AlignAction.moveBack;
      // 偏大 → 人话（435% 这种数字对小白毫无意义）
      final excess = sizeRatio - 1;
      parts.add(excess > 1.5
          ? '离太近了，往后退几步'
          : '再退后一点，人有点大');
    }
  }

  return AlignFeedback(
    action: action,
    dx: dx,
    dy: dy,
    sizeRatio: sizeRatio,
    aligned: false,
    message: parts.isEmpty ? action.label : parts.join('，'),
    degrees: degrees,
  );
}

/// 把当前框画到目标框需要转多少度（粗略，用画面假设 FOV）。
///
/// 用途：告诉用户「相机往左摇约 12°」。这只是估算 ——
/// 不同镜头 FOV 不同，所以 UI 上标「约」。
double panDegreesFor(double dx, {double horizontalFovDeg = 65}) =>
    dx * horizontalFovDeg;

double tiltDegreesFor(double dy, {double verticalFovDeg = 45}) =>
    -dy * verticalFovDeg; // 画面往下 => 相机往上抬
