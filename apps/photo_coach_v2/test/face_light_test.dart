import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/analysis/face_detector.dart';
import 'package:photo_coach_v2/features/analysis/face_light.dart';
import 'package:photo_coach_v2/features/coach/suggestion.dart' show Rect01;
import 'package:photo_coach_v2/features/guidance/subject_detector.dart';

/// 造一张网格：背景 [bg]，中间一块矩形区域，像素值由 [boxColor] 决定。
/// [boxColor] 支持「整块一色」(长度3) 或「按像素函数」(返回 0-1 三元组的闭包，
/// 以 (x, y, 归一化 u,v) 取值 —— 用来造渐变测侧光)。
RgbGrid makeGrid({
  int w = 32,
  int h = 32,
  List<double> bg = const [0.3, 0.3, 0.3],
  List<double>? boxColor,
  List<double> Function(int x, int y, double u, double v)? boxColorFn,
  int? boxX,
  int? boxY,
  int? boxW,
  int? boxH,
}) {
  final bx = boxX ?? (w * 0.35).round();
  final by = boxY ?? (h * 0.25).round();
  final bw = boxW ?? (w * 0.3).round();
  final bh = boxH ?? (h * 0.5).round();

  final r = Float32List(w * h);
  final g = Float32List(w * h);
  final b = Float32List(w * h);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final inBox = x >= bx && x < bx + bw && y >= by && y < by + bh;
      final c = inBox && boxColorFn != null
          ? boxColorFn(x, y, x / w, y / h)
          : inBox && boxColor != null
              ? [boxColor[0], boxColor[1], boxColor[2]]
              : bg;
      final i = y * w + x;
      r[i] = c[0];
      g[i] = c[1];
      b[i] = c[2];
    }
  }
  return RgbGrid(r, g, b, w, h);
}

Rect01 boxOf(int w, int h, int x, int y, int bw, int bh) =>
    Rect01(x / w, y / h, bw / w, bh / h);

void main() {
  final analyzer = const FaceLightAnalyzer();

  group('FaceLightAnalyzer —— 五类光影判定', () {
    test('逆光：脸比背景暗得多 → backlight，建议含补光/曝光补偿', () {
      final grid = makeGrid(
        bg: const [0.7, 0.7, 0.7], // 亮背景
        boxColor: const [0.18, 0.18, 0.18], // 暗脸
      );
      final rep = analyzer.analyze(
        grid,
        const FaceDetection(
          found: true,
          box: Rect01(0.35, 0.25, 0.3, 0.5),
          source: 'test',
        ),
      );
      expect(rep.faceFound, isTrue);
      expect(rep.verdict, FaceLightVerdict.backlight);
      expect(rep.stats, isNotNull);
      expect(rep.stats!.faceLuma, lessThan(rep.stats!.bgLuma));
      // 建议要可执行：补光 或 曝光补偿 或 站回亮处，至少占两条方向
      final joined = rep.advice.join(' ');
      expect(joined, contains('补光'));
      expect(joined, contains('曝光补偿'));
      expect(joined, contains('亮处'));
    });

    test('过曝：脸非常亮 → overexposed', () {
      final grid = makeGrid(
        bg: const [0.5, 0.5, 0.5],
        boxColor: const [0.92, 0.92, 0.92],
      );
      final rep = analyzer.analyze(
        grid,
        const FaceDetection(
          found: true,
          box: Rect01(0.35, 0.25, 0.3, 0.5),
          source: 'test',
        ),
      );
      expect(rep.verdict, FaceLightVerdict.overexposed);
      expect(rep.advice.join(' '), contains('曝光补偿'));
    });

    test('欠曝：整张都暗 → underexposed', () {
      final grid = makeGrid(
        bg: const [0.3, 0.3, 0.3],
        boxColor: const [0.15, 0.15, 0.15],
      );
      final rep = analyzer.analyze(
        grid,
        const FaceDetection(
          found: true,
          box: Rect01(0.35, 0.25, 0.3, 0.5),
          source: 'test',
        ),
      );
      expect(rep.verdict, FaceLightVerdict.underexposed);
      expect(rep.advice.join(' '), contains('曝光补偿'));
    });

    test('侧光：脸左右亮度差明显 → sideLight', () {
      final grid = makeGrid(
        bg: const [0.3, 0.3, 0.3], // 背景不亮 → 不触发逆光
        boxX: 6,
        boxY: 8,
        boxW: 16,
        boxH: 16,
        // 按**块中心**（x=14）分左右半：左 0.40 / 右 0.15 → 差 0.25
        boxColorFn: (x, y, u, v) =>
            x < 14 ? const [0.4, 0.4, 0.4] : const [0.15, 0.15, 0.15],
      );
      final rep = analyzer.analyze(
        grid,
        FaceDetection(found: true, box: boxOf(32, 32, 6, 8, 16, 16)),
      );
      expect(rep.verdict, FaceLightVerdict.sideLight);
      expect(rep.stats!.sideGradient, greaterThan(0.2));
      expect(rep.stats!.leftLuma, greaterThan(rep.stats!.rightLuma));
    });

    test('平光：脸亮度适中、均匀、无明显方向差 → flatLight', () {
      final grid = makeGrid(
        bg: const [0.5, 0.5, 0.5],
        boxColor: const [0.5, 0.5, 0.5],
      );
      final rep = analyzer.analyze(
        grid,
        const FaceDetection(
          found: true,
          box: Rect01(0.35, 0.25, 0.3, 0.5),
          source: 'test',
        ),
      );
      expect(rep.verdict, FaceLightVerdict.flatLight);
      expect(rep.advice, isNotEmpty);
    });

    test('混合：都不算典型 → mixed，给通用建议', () {
      final grid = makeGrid(
        bg: const [0.2, 0.2, 0.2], // 背景偏暗（不触发逆光）
        boxColor: const [0.3, 0.3, 0.3], // 脸也偏暗（到不了欠曝线）
      );
      final rep = analyzer.analyze(
        grid,
        const FaceDetection(
          found: true,
          box: Rect01(0.35, 0.25, 0.3, 0.5),
          source: 'test',
        ),
      );
      expect(rep.verdict, FaceLightVerdict.mixed);
      expect(rep.advice, isNotEmpty);
    });

    test('没找到脸 → 诚实说不评，给通用建议，不编测量值', () {
      final grid = makeGrid();
      final rep = analyzer.analyze(grid, FaceDetection.notFound);
      expect(rep.faceFound, isFalse);
      expect(rep.stats, isNull);
      expect(rep.verdict, FaceLightVerdict.mixed);
      expect(rep.summary, contains('没找到'));
      expect(rep.advice, isNotEmpty);
    });
  });

  group('FaceLightStats —— 测量值口径', () {
    test('左右梯度 = |L-R| / max(L,R)', () {
      final grid = makeGrid(
        bg: const [0.3, 0.3, 0.3],
        boxX: 6,
        boxY: 8,
        boxW: 16,
        boxH: 16,
        // 块中心 x=14 为界：左 0.40 / 右 0.20
        boxColorFn: (x, y, u, v) =>
            x < 14 ? const [0.4, 0.4, 0.4] : const [0.2, 0.2, 0.2],
      );
      final rep = analyzer.analyze(
        grid,
        FaceDetection(found: true, box: boxOf(32, 32, 6, 8, 16, 16)),
      );
      final s = rep.stats!;
      // 缩进后仍保持 0.4 / 0.2 两半（缩进 15% 不越中线）
      expect(s.leftLuma, closeTo(0.4, 0.01));
      expect(s.rightLuma, closeTo(0.2, 0.01));
      expect(s.sideGradient, closeTo(0.5, 0.01));
    });

    test('promptText 带测量值，可供模型参考', () {
      final grid = makeGrid(
        bg: const [0.6, 0.6, 0.6],
        boxColor: const [0.25, 0.25, 0.25],
      );
      final rep = analyzer.analyze(
        grid,
        const FaceDetection(
          found: true,
          box: Rect01(0.35, 0.25, 0.3, 0.5),
          source: 'test',
        ),
      );
      final text = rep.stats!.promptText;
      expect(text, contains('脸'));
      expect(text, contains('背景'));
      expect(text, isNot(contains('null')));
    });
  });
}
