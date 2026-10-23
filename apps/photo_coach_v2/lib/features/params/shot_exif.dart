import 'dart:typed_data';

import 'package:image/image.dart' as img;

/// 一张照片**真实用过**的曝光三要素 —— 从 JPEG 的 EXIF 里读出来。
///
/// 为什么这个很重要：手机 App 设不了 ISO/快门，但它**知道**相机实际用了多少。
/// 有了这个真实基准，就能反推场景光强度，进而算出「换成别的快门/光圈需要多少
/// ISO」—— 这就是「通过照片自动给最优值」的地基（全程是数学，不是猜）。
///
/// 读不到就返回 `null`，**绝不**用默认值糊过去（那会让算出来的参数全错）。
class ShotExif {
  const ShotExif({
    required this.iso,
    required this.shutterSeconds,
    required this.aperture,
  });

  /// 实际使用的 ISO。
  final double iso;

  /// 实际使用的快门（秒）。
  final double shutterSeconds;

  /// 实际使用的光圈值（f/N 里的 N）。
  final double aperture;

  /// EXIF 标签号（`image` 包的 `IfdDirectory.data` 是按标签号存的）。
  static const int _tagIsoSpeed = 0x8827;
  static const int _tagExposureTime = 0x829a;
  static const int _tagFNumber = 0x829d;

  /// 从 JPEG 字节里读。缺任何一项都返回 null。
  ///
  /// 说明：`decodeJpg` 会把整张图解出来，比只看头部慢；但这是 `image` 包里
  /// 唯一**公开文档化**的拿 EXIF 的路子（`Image.exif`），
  /// 不为了快一点去碰内部 API。
  static ShotExif? fromBytes(Uint8List bytes) {
    final img.Image? decoded;
    try {
      decoded = img.decodeJpg(bytes);
    } catch (_) {
      return null; // 不是 JPEG / 解不开 → 读不到就是读不到
    }
    if (decoded == null) return null;

    final exif = decoded.exif;
    // 曝光三要素都在 Exif 子目录里（`exif_data.dart:42` 的 exifIfd）。
    final dir = exif.exifIfd;

    final iso = dir.data[_tagIsoSpeed]?.toDouble();
    final exposureTime = dir.data[_tagExposureTime]?.toDouble();
    final fNumber = dir.data[_tagFNumber]?.toDouble();

    if (iso == null || exposureTime == null || fNumber == null) return null;
    if (iso <= 0 || exposureTime <= 0 || fNumber <= 0) return null;

    return ShotExif(
      iso: iso,
      shutterSeconds: exposureTime,
      aperture: fNumber,
    );
  }

  /// 这个场景的光强度（EV100）。见 [sceneEv100]。
  @override
  String toString() =>
      'ShotExif(ISO ${iso.toStringAsFixed(0)}, '
      '${shutterSeconds >= 1 ? '${shutterSeconds.toStringAsFixed(1)}s' : '1/${(1 / shutterSeconds).round()}s'}, '
      'f/${aperture.toStringAsFixed(1)})';
}
