import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:image/image.dart' as img;

/// 上传前压缩：长边压到 [maxSide]，JPEG 质量 [quality]。
///
/// 为什么必须压：图片会转成 token 计费，且弱网上传慢。
/// 压缩失败时返回原图（宁可多花 token，也不能让功能直接挂）。
class ImagePayload {
  const ImagePayload({
    required this.bytes,
    required this.mimeType,
    required this.width,
    required this.height,
    required this.compressed,
  });

  final Uint8List bytes;
  final String mimeType;
  final int width;
  final int height;

  /// false 表示压缩失败、用的是原图。
  final bool compressed;

  String toDataUrl() =>
      'data:$mimeType;base64,${base64Encode(bytes)}';

  int get byteSize => bytes.length;
}

class ImageCompressor {
  const ImageCompressor({this.maxSide = 1024, this.quality = 80});

  final int maxSide;
  final int quality;

  Future<ImagePayload> compressFile(File file) async {
    final raw = await file.readAsBytes();
    return compressBytes(raw);
  }

  ImagePayload compressBytes(Uint8List raw) {
    try {
      final decoded = img.decodeImage(raw);
      if (decoded == null) {
        return _passthrough(raw, '原图解码失败（非图片或格式不支持）');
      }
      final resized = _resize(decoded);
      final jpg = img.encodeJpg(resized, quality: quality);
      return ImagePayload(
        bytes: Uint8List.fromList(jpg),
        mimeType: 'image/jpeg',
        width: resized.width,
        height: resized.height,
        compressed: true,
      );
    } catch (_) {
      return _passthrough(raw, '压缩异常');
    }
  }

  img.Image _resize(img.Image src) {
    final longest = src.width > src.height ? src.width : src.height;
    if (longest <= maxSide) return src;
    final scale = maxSide / longest;
    return img.copyResize(
      src,
      width: (src.width * scale).round(),
      height: (src.height * scale).round(),
      interpolation: img.Interpolation.average,
    );
  }

  ImagePayload _passthrough(Uint8List raw, String _) => ImagePayload(
        bytes: raw,
        mimeType: 'image/jpeg',
        width: 0,
        height: 0,
        compressed: false,
      );
}
