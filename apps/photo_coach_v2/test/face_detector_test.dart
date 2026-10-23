import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:photo_coach_v2/features/analysis/face_detector.dart';
import 'package:photo_coach_v2/features/guidance/subject_detector.dart';

/// 造一张网格（与 subject_detector_test 同款约定）。
RgbGrid makeGrid({
  int w = 32,
  int h = 32,
  List<double> bg = const [0.4, 0.4, 0.4],
  List<double>? fg,
  int? boxX,
  int? boxY,
  int? boxW,
  int? boxH,
}) {
  final bx = boxX ?? (w * 0.4).round();
  final by = boxY ?? (h * 0.3).round();
  final bw = boxW ?? (w * 0.2).round();
  final bh = boxH ?? (h * 0.4).round();
  final r = Float32List(w * h);
  final g = Float32List(w * h);
  final b = Float32List(w * h);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final inBox = x >= bx && x < bx + bw && y >= by && y < by + bh;
      final c = (inBox && fg != null) ? fg : bg;
      final i = y * w + x;
      r[i] = c[0];
      g[i] = c[1];
      b[i] = c[2];
    }
  }
  return RgbGrid(r, g, b, w, h);
}

void main() {
  group('isSkin —— 肤色判定（0-1 输入）', () {
    test('中等肤色 → 是', () {
      // (189,135,97)/255 —— 典型中等肤色
      expect(isSkin(189 / 255, 135 / 255, 97 / 255), isTrue);
    });

    test('较浅肤色 → 是', () {
      expect(isSkin(224 / 255, 176 / 255, 132 / 255), isTrue);
    });

    test('纯灰（无偏色）→ 不是', () {
      expect(isSkin(0.4, 0.4, 0.4), isFalse);
    });

    test('蓝色衣服 → 不是', () {
      expect(isSkin(30 / 255, 60 / 255, 160 / 255), isFalse);
    });

    test('纯黑 → 不是', () {
      expect(isSkin(0.05, 0.04, 0.03), isFalse);
    });
  });

  group('detectFaceHeuristic —— 肤色区域启发式（纯 Dart，可单测）', () {
    test('灰背景 + 中间一块肤色 → 找到框，位置大致对', () {
      // 32x32 网格，肤色块 x 12..21、y 8..21
      final grid = makeGrid(
        fg: [189 / 255, 135 / 255, 97 / 255],
        boxX: 12,
        boxY: 8,
        boxW: 10,
        boxH: 14,
      );
      final d = detectFaceHeuristic(grid);
      expect(d.found, isTrue);
      expect(d.source, 'heuristic');
      expect(d.box, isNotNull);
      expect(d.box!.centerX, closeTo(17 / 32, 0.10));
      expect(d.box!.centerY, closeTo(15 / 32, 0.10));
      expect(d.confidence, greaterThanOrEqualTo(0.5));
    });

    test('均匀画面（无肤色）→ 诚实 notFound，不瞎猜', () {
      final d = detectFaceHeuristic(makeGrid());
      expect(d.found, isFalse);
      expect(d.box, isNull);
    });

    test('只有 1-2 个肤色噪点 → 面积太小，notFound', () {
      final grid = makeGrid();
      // 在 (5,5) 塞一个肤色像素
      final i = 5 * 32 + 5;
      grid.r[i] = 189 / 255;
      grid.g[i] = 135 / 255;
      grid.b[i] = 97 / 255;
      final d = detectFaceHeuristic(grid);
      expect(d.found, isFalse);
    });

    test('肤色占 80% 画面 → 不是「一张脸」，notFound', () {
      final grid = makeGrid(
        bg: [189 / 255, 135 / 255, 97 / 255], // 整张都是肤色
        fg: null,
      );
      final d = detectFaceHeuristic(grid);
      expect(d.found, isFalse);
    });

    test('肤色条被拉成 3:1 长条 → 宽高比不成立，notFound', () {
      final grid = makeGrid(
        fg: [189 / 255, 135 / 255, 97 / 255],
        boxX: 4,
        boxY: 14,
        boxW: 24, // 宽 24 高 4 → 6:1
        boxH: 4,
      );
      final d = detectFaceHeuristic(grid);
      expect(d.found, isFalse);
    });
  });

  group('FaceDetector —— 门面（字节入口，供教练页接线）', () {
    test('detectFromBytes：真实图片解码 → 肤色块能被找到', () async {
      // 造一张 96x96 小图：灰背景 + 中间肤色矩形
      final image = img.Image(width: 96, height: 96);
      for (var y = 0; y < 96; y++) {
        for (var x = 0; x < 96; x++) {
          image.setPixelRgb(x, y, 0x66, 0x66, 0x66);
        }
      }
      for (var y = 24; y < 70; y++) {
        for (var x = 33; x < 63; x++) {
          image.setPixelRgb(x, y, 0xBD, 0x87, 0x61); // 189,135,97
        }
      }
      final bytes = img.encodeJpg(image, quality: 90);
      final d = await FaceDetector(useIsolate: false).detectFromBytes(bytes);
      expect(d.found, isTrue);
      expect(d.box, isNotNull);
      expect(d.box!.centerX, closeTo(0.5, 0.08));
    });

    test('detectFromBytes：无肤色 → notFound（诚实边界）', () async {
      final image = img.Image(width: 64, height: 64);
      for (var y = 0; y < 64; y++) {
        for (var x = 0; x < 64; x++) {
          image.setPixelRgb(x, y, 0x66, 0x66, 0x66);
        }
      }
      final d = await FaceDetector(useIsolate: false)
          .detectFromBytes(img.encodeJpg(image, quality: 90));
      expect(d.found, isFalse);
    });
  });
}
