import 'dart:async';
import 'dart:isolate';
import 'dart:typed_data';

import 'package:image/image.dart' as img;

import 'video_input.dart';

/// 抽帧器：把「时间点」翻译成「JPEG 字节」。
///
/// 分两层是为了**可测**：
/// - [VideoFrameSource]：跟原生打交道（video_player），测试里换假的
/// - [VideoFrameExtractor]：规划时间点 + 编码 JPEG + 兜错，纯逻辑
class VideoFrameExtractor {
  const VideoFrameExtractor({
    required this.source,
    this.maxFrames = 3,
    this.maxSide = 1024,
    this.quality = 80,
  });

  final VideoFrameSource source;

  /// 抽几帧。默认 3（见 video_input.dart 的策略说明）。
  final int maxFrames;

  /// 单帧长边上限 —— 跟图片链路一致，省 token、省流量。
  final int maxSide;
  final int quality;

  Future<List<VideoFrame>> extract(String videoPath) async {
    if (videoPath.trim().isEmpty) {
      throw VideoInputException('视频路径是空的');
    }

    final Duration total;
    try {
      total = await source.duration(videoPath);
    } catch (e) {
      throw VideoInputException('读不到视频时长（文件损坏或格式不支持）：$e');
    }

    if (total.inMilliseconds <= 0) {
      throw VideoInputException('视频时长是 0，没什么可分析的');
    }

    final times = planFrameTimes(total, maxFrames: maxFrames);

    // 逐帧取；单帧失败跳过，不毁掉整段视频
    final raw = <RawFrame>[];
    final failures = <String>[];
    for (final t in times) {
      try {
        raw.add(await source.frameAt(videoPath, t));
      } catch (e) {
        failures.add('${t.inMilliseconds}ms: $e');
      }
    }

    if (raw.isEmpty) {
      throw VideoInputException(
        '这个视频里没抽到画面（试了 ${times.length} 个时间点都失败'
        '${failures.isEmpty ? "" : "：${failures.first}"}）',
      );
    }

    final out = <VideoFrame>[];
    for (final r in raw) {
      final bytes = await _encode(r);
      if (bytes == null) continue; // 单帧编码失败不该毁掉整段视频
      out.add(VideoFrame(
        bytes: bytes,
        index: out.length,
        at: r.at,
        totalDuration: r.totalDuration,
      ));
    }

    if (out.isEmpty) {
      throw VideoInputException('抽到的 ${raw.length} 帧全都无法编码');
    }
    return out;
  }

  /// 缩放到 [maxSide] 以内并编码成 JPEG。
  /// 失败返回 null（调用方跳过这一帧）。
  Future<Uint8List?> _encode(RawFrame frame) async {
    try {
      final req = _EncodeRequest(frame.rgba, frame.width, frame.height,
          maxSide: maxSide, quality: quality);
      // 大图编码会卡界面 → 丢 isolate；不支持就同线程
      try {
        return await Isolate.run(() => _encodeEntry(req));
      } catch (_) {
        return _encodeEntry(req);
      }
    } catch (_) {
      return null;
    }
  }
}

class _EncodeRequest {
  const _EncodeRequest(this.rgba, this.width, this.height,
      {required this.maxSide, required this.quality});
  final Uint8List rgba;
  final int width;
  final int height;
  final int maxSide;
  final int quality;
}

/// 顶层函数（isolate 要求）。
Uint8List? _encodeEntry(_EncodeRequest req) {
  return encodeRgbaToJpeg(
    req.rgba,
    req.width,
    req.height,
    maxSide: req.maxSide,
    quality: req.quality,
  );
}

/// RGBA 原始像素 → 缩放后的 JPEG 字节。纯函数，可单测。
///
/// 为什么单独拎出来：原生的视频解码大多给 RGBA，但**测试里造不出真视频**；
/// 把这段纯逻辑抽出来就能直接喂合成的像素验证，不用跑原生。
Uint8List? encodeRgbaToJpeg(
  Uint8List rgba,
  int width,
  int height, {
  int maxSide = 1024,
  int quality = 80,
}) {
  if (width <= 0 || height <= 0) return null;
  final expected = width * height * 4;
  if (rgba.length < expected) return null;

  final image = img.Image(width: width, height: height);
  for (var y = 0; y < height; y++) {
    for (var x = 0; x < width; x++) {
      final i = (y * width + x) * 4;
      image.setPixelRgb(x, y, rgba[i], rgba[i + 1], rgba[i + 2]);
    }
  }

  final longest = width > height ? width : height;
  final out = longest <= maxSide
      ? image
      : img.copyResize(
          image,
          width: (width * maxSide / longest).round(),
          height: (height * maxSide / longest).round(),
          interpolation: img.Interpolation.average,
        );

  return Uint8List.fromList(img.encodeJpg(out, quality: quality));
}
