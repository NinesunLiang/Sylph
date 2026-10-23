library;

import 'dart:isolate';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:image/image.dart' as img;

import '../coach/suggestion.dart' show Rect01;
import '../guidance/subject_detector.dart' show RgbGrid, gridFromImage;

/// 人脸/脸区域检测 —— 教练页「面部光影」的入口。
///
/// ## 分层设计（诚实边界写死在类型里）
/// 1. **原生后端（可插拔，可选）**：[FaceDetector.nativeBackend] 预留了给
///    真·人脸检测（YuNet/opencv_dart）的插座。给了就先用它；它没找到或
///    加载失败（比如华为机没有能跑的环境）就**自动落到 2**。
/// 2. **肤色区域启发式**（[detectFaceHeuristic]，纯 Dart，永远可用）：
///    找画面里最大的一块「像肤色」的连通区域，当脸。
///
/// ## 诚实边界（绝不瞎猜）
/// 肤色启发式认的是「肤色区域」，不是真脸：
/// - 画面没有集中肤色（无脸/远景/深色皮肤在暗光下）→ [FaceDetection.found] = false，
///   [FaceDetection.reason] 说明原因，UI 如实显示「没找到脸」；
/// - 面积/宽高比/置信度任一不成立 → 同样 notFound，**不返回一个假框**。
///
/// 为什么不用 ML Kit：google_mlkit 在华为无 GMS 的机器上会直接崩（红线，
/// `tool/check_no_google.sh` 机器验证）。YuNet 走 opencv_dart 纯原生，不碰红线；
/// 启发式是它的兜底，保证任何机器上这个功能至少「不崩」。

/// 经典肤色判定（阈值来自公开文献的 skin-color heuristic，输入 0-1）。
///
/// 覆盖浅色/中等肤色；深肤色或极暗/极亮光下可能不成立 —— 那时走 notFound
/// 或交给原生后端，**不硬猜**。
bool isSkin(double r, double g, double b) {
  final R = r * 255.0;
  final G = g * 255.0;
  final B = b * 255.0;
  final maxC = math.max(R, math.max(G, B));
  final minC = math.min(R, math.min(G, B));
  return R > 95 &&
      G > 40 &&
      B > 20 &&
      (maxC - minC) > 15 &&
      (R - G).abs() > 15 &&
      R > G &&
      R > B;
}

/// 一次脸检测的结果。
class FaceDetection {
  const FaceDetection({
    required this.found,
    this.box,
    this.confidence = 0,
    this.reason = '',
    this.source = '',
  });

  /// 有没有找到。false 时 [box] 必须 null —— 不瞎猜。
  final bool found;

  /// 归一化脸框（0-1）。
  final Rect01? box;

  /// 置信度 0-1（启发式 = 块内肤色像素占比）。
  final double confidence;

  /// 为什么没找到 / 怎么找到的（给用户与排错看）。
  final String reason;

  /// 检测方式：`heuristic`（肤色启发式）/ `yunet`（原生模型）/ 其它。
  final String source;

  static const notFound = FaceDetection(
    found: false,
    reason: '画面里没找到脸（没有明显的肤色区域）',
  );
}

/// 阈值集中管理，方便按真机效果调，也方便测试直接引用。
class FaceDetectorThresholds {
  const FaceDetectorThresholds({
    this.minCoverage = 0.005,
    this.maxCoverage = 0.40,
    this.maxAspect = 2.5,
    this.minConfidence = 0.55,
  });

  /// 脸至少要占画面 0.5%（再小 = 噪点）。
  final double minCoverage;

  /// 超过 40% 就不是「一张脸」了（整块肤色 = 别的东西）。
  final double maxCoverage;

  /// 脸框宽高比上限（脸不会拉成 3:1 的条）。
  final double maxAspect;

  /// 块内至少这么多比例是肤色才算「确实像一块肤色」。
  final double minConfidence;

  static const standard = FaceDetectorThresholds();
}

/// 纯算法入口：给网格，返回脸框（或诚实的 notFound）。无 IO。
FaceDetection detectFaceHeuristic(
  RgbGrid grid, {
  FaceDetectorThresholds thresholds = FaceDetectorThresholds.standard,
}) {
  final w = grid.width;
  final h = grid.height;
  if (w < 3 || h < 3) {
    return FaceDetection(
      found: false,
      reason: '网格太小（${w}x$h），量不出脸',
    );
  }

  // ---- 1. 肤色 mask ----
  final n = w * h;
  final mask = Uint8List(n);
  for (var i = 0; i < n; i++) {
    if (isSkin(grid.r[i], grid.g[i], grid.b[i])) mask[i] = 1;
  }

  // ---- 2. 3×3 多数滤波去噪（边缘/散点消掉）----
  final filtered = Uint8List(n);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      var votes = 0;
      for (var dy = -1; dy <= 1; dy++) {
        for (var dx = -1; dx <= 1; dx++) {
          final nx = x + dx;
          final ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          votes += mask[ny * w + nx];
        }
      }
      if (votes >= 5) filtered[y * w + x] = 1;
    }
  }

  // ---- 3. 连通块（4 邻域，迭代泛洪）→ 取最大 ----
  final seen = Uint8List(n);
  var bestSize = 0;
  var bestSkin = 0;
  var x0 = 0, y0 = 0, x1 = 0, y1 = 0;
  final stack = <int>[];

  for (var i = 0; i < n; i++) {
    if (filtered[i] != 1 || seen[i] == 1) continue;
    stack.clear();
    stack.add(i);
    seen[i] = 1;
    var size = 0;
    var skin = 0;
    var minX = w, maxX = -1, minY = h, maxY = -1;
    while (stack.isNotEmpty) {
      final c = stack.removeLast();
      final cx = c % w;
      final cy = c ~/ w;
      size++;
      if (mask[c] == 1) skin++;
      if (cx < minX) minX = cx;
      if (cx > maxX) maxX = cx;
      if (cy < minY) minY = cy;
      if (cy > maxY) maxY = cy;
      // 四邻域
      if (cx > 0) _push(stack, seen, filtered, (cy * w) + cx - 1);
      if (cx < w - 1) _push(stack, seen, filtered, (cy * w) + cx + 1);
      if (cy > 0) _push(stack, seen, filtered, (cy - 1) * w + cx);
      if (cy < h - 1) _push(stack, seen, filtered, (cy + 1) * w + cx);
    }
    if (size > bestSize) {
      bestSize = size;
      bestSkin = skin;
      x0 = minX;
      y0 = minY;
      x1 = maxX;
      y1 = maxY;
    }
  }

  if (bestSize == 0) return FaceDetection.notFound;

  // ---- 4. 合理性体检：面积 / 宽高比 / 置信度，任一不成立 = 诚实 notFound ----
  final coverage = bestSize / n;
  if (coverage < thresholds.minCoverage) {
    return FaceDetection(
      found: false,
      reason: '肤色区域太小（占 ${(coverage * 100).toStringAsFixed(1)}%），'
          '不像一张脸',
    );
  }
  if (coverage > thresholds.maxCoverage) {
    return FaceDetection(
      found: false,
      reason: '肤色占了画面 ${(coverage * 100).toStringAsFixed(0)}%，'
          '不是「一张脸」',
    );
  }
  final bw = x1 - x0 + 1;
  final bh = y1 - y0 + 1;
  final aspect = bw / bh;
  if (aspect > thresholds.maxAspect || aspect < 1 / thresholds.maxAspect) {
    return FaceDetection(
      found: false,
      reason: '区域形状（${aspect.toStringAsFixed(1)}:1）不像脸，'
          '可能是脖子/手臂/肤色衣物',
    );
  }
  final confidence = bestSkin / bestSize;
  if (confidence < thresholds.minConfidence) {
    return FaceDetection(
      found: false,
      reason: '这块区域肤色占比 ${((1 - confidence) * 100).toStringAsFixed(0)}%'
          ' 不是肤色，判为误报',
    );
  }

  return FaceDetection(
    found: true,
    box: Rect01(x0 / w, y0 / h, bw / w, bh / h),
    confidence: confidence,
    reason: '肤色区域（启发式）',
    source: 'heuristic',
  );
}

void _push(
  List<int> stack,
  Uint8List seen,
  Uint8List filtered,
  int idx,
) {
  if (filtered[idx] == 1 && seen[idx] == 0) {
    seen[idx] = 1;
    stack.add(idx);
  }
}

/// 原生后端的接口：给它解好的图，返回检测（null = 这后端搞不定）。
/// 加载/运行失败请抛异常，[FaceDetector] 会捕获后落到启发式。
typedef FaceNativeBackend = Future<FaceDetection?> Function(img.Image image);

/// 门面：字节 → 脸检测。教练页只跟这一个入口打交道。
///
/// 顺序：**原生后端（若插了）→ 肤色启发式兜底**，任何一步失败都不抛给 UI。
class FaceDetector {
  const FaceDetector({
    this.gridW = 48,
    this.gridH = 48,
    this.useIsolate = true,
    this.thresholds = FaceDetectorThresholds.standard,
    this.nativeBackend,
  });

  final int gridW;
  final int gridH;

  /// 大图解码丢 isolate，不卡界面；测试里可关掉。
  final bool useIsolate;

  final FaceDetectorThresholds thresholds;

  /// 可选原生后端（YuNet）。null = 纯启发式。
  final FaceNativeBackend? nativeBackend;

  Future<FaceDetection> detectFromBytes(Uint8List bytes) async {
    final img.Image? image = await _decode(bytes);
    if (image == null) {
      return const FaceDetection(
        found: false,
        reason: '图片解码失败，没法找脸',
      );
    }

    // 1) 原生后端：能用就用，失败/找不到 → 落启发式
    if (nativeBackend != null) {
      try {
        final d = await nativeBackend!(image);
        if (d != null && d.found) return d;
      } catch (_) {
        // 原生加载失败（例如缺 .so / 缺模型文件）→ 静默降级
      }
    }

    // 2) 肤色启发式兜底：永远在
    final grid = useIsolate
        ? await _gridIsolate(image, gridW, gridH)
        : gridFromImage(image, gridW: gridW, gridH: gridH);
    return detectFaceHeuristic(grid, thresholds: thresholds);
  }

  Future<img.Image?> _decode(Uint8List bytes) {
    final copy = Uint8List.fromList(bytes);
    if (useIsolate) {
      try {
        return Isolate.run(() => img.decodeImage(copy));
      } catch (_) {
        return _decodeMain(copy);
      }
    }
    return _decodeMain(copy);
  }

  Future<img.Image?> _decodeMain(Uint8List bytes) async {
    try {
      return img.decodeImage(bytes);
    } catch (_) {
      return null;
    }
  }

  Future<RgbGrid> _gridIsolate(img.Image image, int gw, int gh) async {
    try {
      final i = image;
      return await Isolate.run(() =>
          gridFromImage(i, gridW: gw, gridH: gh));
    } catch (_) {
      return gridFromImage(image, gridW: gw, gridH: gh);
    }
  }

  /// 教练页一次拿全：字节 → （网格, 脸）。解码只做一次。
  ///
  /// 网格与脸来自同一次解码，天然对齐；[gridW]/[gridH] 默认 64
  /// （光影测量比脸框定位需要更细）。
  Future<(RgbGrid, FaceDetection)> detectWithGrid(
    Uint8List bytes, {
    int gridW = 64,
    int gridH = 64,
    FaceDetectorThresholds? thresholds,
    FaceNativeBackend? nativeBackend,
    bool useIsolate = true,
  }) async {
    final t = thresholds ?? this.thresholds;
    final backend = nativeBackend ?? this.nativeBackend;

    late final img.Image? image;
    if (useIsolate) {
      image = await _decode(Uint8List.fromList(bytes));
    } else {
      image = await _decodeMain(bytes);
    }
    if (image == null) {
      return (
        RgbGrid(Float32List(0), Float32List(0), Float32List(0), 1, 1),
        const FaceDetection(found: false, reason: '图片解码失败')
      );
    }
    final im = image;

    FaceDetection face;
    if (backend != null) {
      try {
        final d = await backend(im);
        face = (d != null && d.found)
            ? d
            : detectFaceHeuristic(
                await _grid(im, gridW, gridH, useIsolate),
                thresholds: t,
              );
      } catch (_) {
        face = detectFaceHeuristic(
          await _grid(im, gridW, gridH, useIsolate),
          thresholds: t,
        );
      }
    } else {
      face = detectFaceHeuristic(
        await _grid(im, gridW, gridH, useIsolate),
        thresholds: t,
      );
    }

    final grid = await _grid(im, gridW, gridH, useIsolate);
    return (grid, face);
  }

  Future<RgbGrid> _grid(
    img.Image image,
    int gw,
    int gh,
    bool useIsolate,
  ) =>
      useIsolate
          ? _gridIsolate(image, gw, gh)
          : Future.value(
              gridFromImage(image, gridW: gw, gridH: gh),
            );
}
