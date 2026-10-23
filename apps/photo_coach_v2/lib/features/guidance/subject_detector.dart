library;

import 'dart:isolate';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:image/image.dart' as img;

import '../coach/suggestion.dart' show Rect01;

/// F2.11/F2.12 —— 本地「主体在哪」检测（不联网、不加原生依赖）。
///
/// ## 为什么不用 ML Kit 姿态检测
/// 用户要的是「往左挪一点」这种**构图级**反馈，不是骨骼关节点。
/// 构图只关心：主体占多大、在图里哪个位置。用「跟背景不一样的区域」
/// 就能算出来，而且：
/// - 不用加原生依赖（ML Kit 要改 Android/iOS 配置，本机还没法验证）
/// - 纯 Dart，**可以单元测试**
/// - 快，能在预览时反复跑
///
/// 真需要骨骼姿势（比如判断手抬高没有）时再上 ML Kit，那时 FEATURES 里会标清楚。
///
/// ## 算法（全部可单测）
/// 1. 取画面**四条边的平均色/亮度**当背景参考
/// 2. 每个格子算「跟背景有多不一样」→ 显著度图（luma 差 + 色度差，取较大者）
/// 3. 阈值二值化 → 3×3 多数滤波去噪 → 取**最大连通块** = 主体
/// 4. 输出归一化矩形 + 置信度
///
/// ## 诚实边界
/// 主体和背景颜色接近时算不出来。这时 [SubjectDetection.found] 为 false，
/// **绝不瞎猜一个框**，UI 要老实说「没找到主体，先用通用构图建议」。

/// 一张缩小的 RGB 网格，供检测算法使用。
class RgbGrid {
  RgbGrid(this.r, this.g, this.b, this.width, this.height)
      : assert(r.length == width * height),
        assert(g.length == width * height),
        assert(b.length == width * height);

  /// 行优先，值域 0–1。
  final Float32List r;
  final Float32List g;
  final Float32List b;
  final int width;
  final int height;

  int get length => width * height;

  /// 感知亮度（Rec.709）。
  double lumaAt(int i) => 0.2126 * r[i] + 0.7152 * g[i] + 0.0722 * b[i];

  double at(int x, int y) => lumaAt(y * width + x);

  Float32List luma() {
    final out = Float32List(length);
    for (var i = 0; i < length; i++) {
      out[i] = lumaAt(i);
    }
    return out;
  }
}

/// 检测结果。
class SubjectDetection {
  const SubjectDetection({
    required this.found,
    this.box,
    this.confidence = 0,
    this.reason = '',
    this.coverage = 0,
  });

  /// 有没有找到主体。false 时 [box] 必须是 null —— 不瞎猜。
  final bool found;

  /// 归一化包围盒（0–1）。
  final Rect01? box;

  /// 置信度 0–1（背景差异强度）。
  final double confidence;

  /// 为什么没找到 / 怎么找到的（给用户和排错看）。
  final String reason;

  /// 主体占画面比例（0–1）。
  final double coverage;

  static const notFound = SubjectDetection(
    found: false,
    reason: '主体和背景颜色接近，本地认不出来',
  );
}

/// 阈值集中管理，方便按真机效果调，也方便测试直接引用。
class DetectorThresholds {
  const DetectorThresholds({
    this.salienceCut = 0.12,
    this.minCoverage = 0.01,
    this.maxCoverage = 0.90,
    this.minConfidence = 0.10,
    this.borderRing = 1,
  });

  /// 显著度阈值：低于它算背景。
  final double salienceCut;

  /// 太小（噪点）或太大（整张都是主体）都判为不可信。
  final double minCoverage;
  final double maxCoverage;

  /// 置信度门槛。
  final double minConfidence;

  /// 取背景参考时，从外往里取几圈像素。
  final int borderRing;

  static const standard = DetectorThresholds();
}

/// 纯算法入口：给网格，返回主体框。无 IO 无 isolate。
SubjectDetection detectSubject(
  RgbGrid grid, {
  DetectorThresholds thresholds = DetectorThresholds.standard,
}) {
  final w = grid.width;
  final h = grid.height;
  if (w < 3 || h < 3) {
    return SubjectDetection(
      found: false,
      reason: '网格太小（${w}x$h），算不出主体',
    );
  }

  // ---- 1. 背景参考：取外圈均值 ----
  var bgR = 0.0, bgG = 0.0, bgB = 0.0, n = 0;
  final ring = thresholds.borderRing;
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final onBorder = x < ring || y < ring || x >= w - ring || y >= h - ring;
      if (!onBorder) continue;
      final i = y * w + x;
      bgR += grid.r[i];
      bgG += grid.g[i];
      bgB += grid.b[i];
      n++;
    }
  }
  if (n == 0) return SubjectDetection.notFound;
  bgR /= n;
  bgG /= n;
  bgB /= n;
  final bgLuma = 0.2126 * bgR + 0.7152 * bgG + 0.0722 * bgB;

  // ---- 2. 显著度 ----
  final salience = Float32List(grid.length);
  for (var i = 0; i < grid.length; i++) {
    final dl = (grid.lumaAt(i) - bgLuma).abs();
    // 色度距离：对色相差异敏感，对亮度不敏感的部分补上
    final dc = math.sqrt(
      math.pow(grid.r[i] - bgR, 2) +
          math.pow(grid.g[i] - bgG, 2) +
          math.pow(grid.b[i] - bgB, 2),
    );
    salience[i] = math.max(dl, dc * 0.75);
  }

  // ---- 3. 二值化 + 3×3 多数滤波 ----
  final mask = Uint8List(grid.length);
  for (var i = 0; i < grid.length; i++) {
    mask[i] = salience[i] >= thresholds.salienceCut ? 1 : 0;
  }
  final cleaned = _majority(mask, w, h);

  // 强显著度均值 → 置信度（用滤波后的掩码，避免噪声抬高）
  var sum = 0.0;
  var count = 0;
  for (var i = 0; i < grid.length; i++) {
    if (cleaned[i] == 1 && salience[i] >= thresholds.salienceCut) {
      sum += salience[i];
      count++;
    }
  }
  if (count == 0) {
    return SubjectDetection(
      found: false,
      reason: '没有跟背景明显不同的区域（背景太杂或主体太小）',
    );
  }
  final confidence = (sum / count).clamp(0.0, 1.0);
  if (confidence < thresholds.minConfidence) {
    return SubjectDetection(
      found: false,
      confidence: confidence,
      reason: '主体和背景差异太小（${confidence.toStringAsFixed(2)}），认不准',
    );
  }

  // ---- 4. 最大连通块 ----
  final comp = _largestComponent(cleaned, w, h);
  if (comp.size == 0) return SubjectDetection.notFound;

  final coverage = comp.size / grid.length;
  if (coverage < thresholds.minCoverage) {
    return SubjectDetection(
      found: false,
      confidence: confidence,
      coverage: coverage,
      reason: '找到的区块太小（${(coverage * 100).toStringAsFixed(1)}%），可能是噪点',
    );
  }
  if (coverage > thresholds.maxCoverage) {
    return SubjectDetection(
      found: false,
      confidence: confidence,
      coverage: coverage,
      reason: '整张画面都像主体（${(coverage * 100).toStringAsFixed(0)}%），说明背景太乱',
    );
  }

  final box = Rect01(
    comp.minX / w,
    comp.minY / h,
    (comp.maxX - comp.minX + 1) / w,
    (comp.maxY - comp.minY + 1) / h,
  );
  return SubjectDetection(
    found: true,
    box: box,
    confidence: confidence,
    coverage: coverage,
    reason: '占画面 ${(coverage * 100).toStringAsFixed(0)}%，'
        '差异度 ${confidence.toStringAsFixed(2)}',
  );
}

/// 3×3 多数滤波：去孤立噪点，补小洞。
Uint8List _majority(Uint8List mask, int w, int h) {
  final out = Uint8List(mask.length);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      var on = 0;
      var total = 0;
      for (var dy = -1; dy <= 1; dy++) {
        for (var dx = -1; dx <= 1; dx++) {
          final nx = x + dx;
          final ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          total++;
          on += mask[ny * w + nx];
        }
      }
      out[y * w + x] = (on * 2 >= total) ? 1 : 0;
    }
  }
  return out;
}

class _Component {
  int size = 0;
  int minX = 1 << 30;
  int minY = 1 << 30;
  int maxX = -1;
  int maxY = -1;
}

/// 4 邻域连通块，返回最大的那个（用迭代栈，避免大图递归爆栈）。
_Component _largestComponent(Uint8List mask, int w, int h) {
  final seen = Uint8List(mask.length);
  var best = _Component();
  final stack = <int>[];

  for (var start = 0; start < mask.length; start++) {
    if (mask[start] == 0 || seen[start] == 1) continue;
    final cur = _Component();
    stack.add(start);
    seen[start] = 1;
    while (stack.isNotEmpty) {
      final i = stack.removeLast();
      final x = i % w;
      final y = i ~/ w;
      cur.size++;
      if (x < cur.minX) cur.minX = x;
      if (y < cur.minY) cur.minY = y;
      if (x > cur.maxX) cur.maxX = x;
      if (y > cur.maxY) cur.maxY = y;

      // 四邻域
      if (x > 0) _push(mask, seen, stack, i - 1);
      if (x < w - 1) _push(mask, seen, stack, i + 1);
      if (y > 0) _push(mask, seen, stack, i - w);
      if (y < h - 1) _push(mask, seen, stack, i + w);
    }
    if (cur.size > best.size) best = cur;
  }
  return best;
}

void _push(Uint8List mask, Uint8List seen, List<int> stack, int i) {
  if (mask[i] == 1 && seen[i] == 0) {
    seen[i] = 1;
    stack.add(i);
  }
}

// ---------------------------------------------------------------------------
// 解码：JPEG/PNG 字节 → RgbGrid
// ---------------------------------------------------------------------------

/// 把图片字节解码 + 缩样成 RGB 网格。
RgbGrid gridFromBytes(
  Uint8List bytes, {
  int gridW = 48,
  int gridH = 48,
}) {
  if (bytes.isEmpty) {
    throw const FormatException('图片数据为空');
  }
  final img.Image? decoded;
  try {
    decoded = img.decodeImage(bytes);
  } catch (e) {
    throw FormatException('图片解码失败：$e');
  }
  if (decoded == null) {
    throw const FormatException('无法解码图片（不是常见图片格式？）');
  }
  return gridFromImage(decoded, gridW: gridW, gridH: gridH);
}

/// 从已解码图像缩样（测试可以直接造 img.Image，省掉编码解码）。
RgbGrid gridFromImage(img.Image image, {int gridW = 48, int gridH = 48}) {
  final scale = gridW / gridH;
  var outW = gridW;
  var outH = gridH;
  // 保持长宽比：把目标框裁成跟原图同比例，避免把人拉扁
  final srcRatio = image.width / image.height;
  if (srcRatio > scale) {
    outH = math.max(3, (gridW / srcRatio).round());
  } else if (srcRatio < scale) {
    outW = math.max(3, (gridH * srcRatio).round());
  }

  final small = img.copyResize(
    image,
    width: outW,
    height: outH,
    interpolation: img.Interpolation.average,
  );

  final r = Float32List(outW * outH);
  final g = Float32List(outW * outH);
  final b = Float32List(outW * outH);
  for (var y = 0; y < outH; y++) {
    for (var x = 0; x < outW; x++) {
      final p = small.getPixel(x, y);
      final i = y * outW + x;
      r[i] = (p.r / 255.0).clamp(0.0, 1.0);
      g[i] = (p.g / 255.0).clamp(0.0, 1.0);
      b[i] = (p.b / 255.0).clamp(0.0, 1.0);
    }
  }
  return RgbGrid(r, g, b, outW, outH);
}

class _GridRequest {
  const _GridRequest(this.bytes, this.w, this.h);
  final Uint8List bytes;
  final int w;
  final int h;
}

RgbGrid _gridEntry(_GridRequest req) =>
    gridFromBytes(req.bytes, gridW: req.w, gridH: req.h);

/// 对外入口。
class SubjectDetector {
  const SubjectDetector({
    this.thresholds = DetectorThresholds.standard,
    this.gridW = 48,
    this.gridH = 48,
    this.useIsolate = true,
  });

  final DetectorThresholds thresholds;
  final int gridW;
  final int gridH;

  /// 大图解码会卡界面 → 丢 isolate。测试里关掉更可控。
  final bool useIsolate;

  SubjectDetection detectFromGrid(RgbGrid grid) =>
      detectSubject(grid, thresholds: thresholds);

  /// 公开取网格，让调用方**复用同一帧的像素**做别的本地判断
  /// （例如实时要素探针）—— 否则为了拿网格要再解一次图。
  Future<RgbGrid> gridOf(Uint8List bytes) => _grid(bytes);

  Future<SubjectDetection> detectFromBytes(Uint8List bytes) async {
    final grid = await _grid(bytes);
    return detectFromGrid(grid);
  }

  Future<RgbGrid> _grid(Uint8List bytes) async {
    if (!useIsolate) {
      return gridFromBytes(bytes, gridW: gridW, gridH: gridH);
    }
    try {
      final req = _GridRequest(Uint8List.fromList(bytes), gridW, gridH);
      return await Isolate.run(() => _gridEntry(req));
    } catch (_) {
      return gridFromBytes(bytes, gridW: gridW, gridH: gridH);
    }
  }
}
