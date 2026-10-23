import 'dart:math' as math;

import '../coach/suggestion.dart' show Rect01;
import 'subject_detector.dart' show RgbGrid;

/// 本地判得出来的「拍照要素」问题（实时取景用）。
///
/// ⚠️ **能力边界（必须诚实）**：这里只用**画面本身能算出来的信息** ——
/// 亮度、边缘密度、主体位置。**判不出"那是什么东西"**（垃圾桶、路人、电线杆
/// 都需要 ML 识别模型）。所以文案只写「背景偏乱」，**绝不写**「右边有个垃圾桶」。
///
/// 好处是：这一层**完全本地、不联网、不花钱**，而且可以离线单测。
enum LiveIssueKind {
  blownHighlight('高光过曝'),
  busyBackground('背景偏乱'),
  subjectClipped('主体贴边');

  const LiveIssueKind(this.label);

  final String label;
}

/// 一条实时要素提示。
class LiveIssue {
  const LiveIssue({
    required this.kind,
    required this.text,
    required this.severity,
    this.rect,
  });

  final LiveIssueKind kind;

  /// 给用户的一句话（已经是能照着做的说法，不含猜测）。
  final String text;

  /// 0–1，越大越该先处理。
  final double severity;

  /// 问题在画面上的位置。**算得出来才给**；算不出就是 null（不瞎画）。
  final Rect01? rect;
}

/// 从一帧里挑出**最该处理**的那一条；没有就返回 null。
///
/// 一次只提示一条 —— 取景画面上刷一堆字没人看得进去（少即是多）。
LiveIssue? probeTopIssue(RgbGrid g, {Rect01? subjectBox}) {
  final issues = <LiveIssue>[];
  final blown = _blownHighlight(g);
  if (blown != null) issues.add(blown);
  final busy = _busyBackground(g, subjectBox);
  if (busy != null) issues.add(busy);
  final clipped = _subjectClipped(subjectBox);
  if (clipped != null) issues.add(clipped);
  if (issues.isEmpty) return null;
  issues.sort((a, b) => b.severity.compareTo(a.severity));
  return issues.first;
}

/// 过曝：三个通道都顶到 1 的像素占比。
///
/// 位置 = 这些像素的**包围盒** —— 这个位置是**真算出来的**（不是猜的）。
LiveIssue? _blownHighlight(RgbGrid g) {
  final total = g.width * g.height;
  if (total == 0) return null;

  var count = 0;
  var minX = g.width, minY = g.height, maxX = -1, maxY = -1;
  for (var y = 0; y < g.height; y++) {
    final row = y * g.width;
    for (var x = 0; x < g.width; x++) {
      final i = row + x;
      // 三个通道都到顶才是真的"白到没细节"；只有一个通道高不一定是过曝
      if (g.r[i] < 0.98 || g.g[i] < 0.98 || g.b[i] < 0.98) continue;
      count++;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }

  final frac = count / total;
  // 2% 以下当没有：小反光点、噪点不值得提示（提示了就是噪声）
  if (frac < 0.02) return null;

  return LiveIssue(
    kind: LiveIssueKind.blownHighlight,
    text: '高光过曝了（约 ${(frac * 100).round()}% 已经白到没细节）→ 减一点曝光',
    severity: (frac / 0.15).clamp(0.0, 1.0),
    rect: maxX < 0
        ? null
        : Rect01(
            minX / g.width,
            minY / g.height,
            (maxX - minX + 1) / g.width,
            (maxY - minY + 1) / g.height,
          ),
  );
}

/// 背景杂乱：主体框**以外**区域的边缘密度。
///
/// 用**相对**判断（最乱的背景块 vs 背景整体均值）而不是一刀切的死阈值：
/// 死阈值在不同手机 / 不同题材下必然误报。
/// ⚠️ 绝对下限（[_minEdge]）仍是拍脑袋定的，**需要在真机上校准**。
LiveIssue? _busyBackground(RgbGrid g, Rect01? subjectBox) {
  const blocks = 3;
  if (g.width < blocks * 3 || g.height < blocks * 3) return null;

  final bw = g.width ~/ blocks;
  final bh = g.height ~/ blocks;

  var best = 0.0;
  var bestX = 0;
  var bestY = 0;
  var sum = 0.0;
  var n = 0;

  for (var by = 0; by < blocks; by++) {
    for (var bx = 0; bx < blocks; bx++) {
      final x0 = bx * bw, y0 = by * bh;
      // 主体所在的块不算背景（那是主体自己的细节）
      if (_blockIsSubject(x0, y0, bw, bh, g, subjectBox)) continue;
      final e = _edgeEnergy(g, x0, y0, bw, bh);
      sum += e;
      n++;
      if (e > best) {
        best = e;
        bestX = bx;
        bestY = by;
      }
    }
  }

  if (n == 0) return null; // 主体占满了画面 —— 没有背景可评
  final mean = sum / n;
  if (best < _minEdge) return null; // 整体都很干净
  if (best < mean * 1.8) return null; // 没有明显更乱的一块

  final where = '${_colName(bestX)}${_rowName(bestY)}';
  return LiveIssue(
    kind: LiveIssueKind.busyBackground,
    text: '背景$where偏乱 → 换个角度，或让人离背景远一点（虚化掉）',
    severity: ((best - mean) / math.max(best, 1e-6)).clamp(0.0, 0.9),
    rect: Rect01(
      bestX * bw / g.width,
      bestY * bh / g.height,
      bw / g.width,
      bh / g.height,
    ),
  );
}

/// 主体贴到画面边缘（常见的"切头/切手"）。
LiveIssue? _subjectClipped(Rect01? b) {
  if (b == null) return null;
  const m = 0.01;
  final sides = <String>[];
  if (b.left <= m) sides.add('左');
  if (b.top <= m) sides.add('上');
  if (b.left + b.width >= 1 - m) sides.add('右');
  if (b.top + b.height >= 1 - m) sides.add('下');
  if (sides.isEmpty) return null;

  // 人话：多于一边就合并成一句（「左和上和右和下」对小白是噪声）。
  // 本质原因几乎都是"人太大/太偏"，统一引导回中间。
  final text = sides.length >= 3
      ? '人太大了，退后一点让四周留点空间'
      : '人贴到画面${sides.join('、')}边了，往中间挪一点';

  return LiveIssue(
    kind: LiveIssueKind.subjectClipped,
    text: text,
    // 贴边不算灾难，优先级排在其他问题之后
    severity: sides.length >= 3 ? 0.5 : 0.35,
    rect: b,
  );
}

/// 平均边缘强度（相邻像素亮度差）。0 = 一片纯色，越大越"花"。
double _edgeEnergy(RgbGrid g, int x0, int y0, int w, int h) {
  var sum = 0.0;
  var n = 0;
  for (var y = y0; y < y0 + h && y < g.height; y++) {
    for (var x = x0; x < x0 + w && x < g.width; x++) {
      final c = g.at(x, y);
      if (x + 1 < g.width) {
        sum += (g.at(x + 1, y) - c).abs();
        n++;
      }
      if (y + 1 < g.height) {
        sum += (g.at(x, y + 1) - c).abs();
        n++;
      }
    }
  }
  return n == 0 ? 0 : sum / n;
}

/// 这一块是不是主体所在（按块中心判断）。
bool _blockIsSubject(
    int x0, int y0, int w, int h, RgbGrid g, Rect01? box) {
  if (box == null) return false;
  final cx = (x0 + w / 2) / g.width;
  final cy = (y0 + h / 2) / g.height;
  return cx >= box.left &&
      cx <= box.left + box.width &&
      cy >= box.top &&
      cy <= box.top + box.height;
}

/// 边缘密度下限：低于它认为"背景本来就干净"。（**待真机校准**）
const double _minEdge = 0.045;

String _colName(int bx) => switch (bx) { 0 => '左侧', 1 => '中间', _ => '右侧' };
String _rowName(int by) => switch (by) { 0 => '上方', 1 => '', _ => '下方' };
