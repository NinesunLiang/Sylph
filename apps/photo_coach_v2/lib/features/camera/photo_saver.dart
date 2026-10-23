import 'package:gal/gal.dart';

/// 把拍下来的照片存进**系统相册**。
///
/// 为什么要抽象成接口：存相册要走平台通道（`gal` 插件），单测里跑不了。
/// 抽出来之后，「拍完到底有没有交给存档」这件事就能用假实现锁死 ——
/// 而这正是之前**完全没做**的事：拍完的照片只落在系统临时缓存目录里，
/// 系统随时会清掉。用户以为拍到了，其实什么都没留下
/// （连「后续姿势功能要用这些照片」都无从谈起）。
abstract class PhotoSaver {
  /// 把 [path] 指向的图片存进相册。失败要抛 [PhotoSaveException]。
  Future<void> save(String path);
}

/// 存不进去的原因（`message` 已经是给用户看的中文）。
class PhotoSaveException implements Exception {
  const PhotoSaveException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// 真机实现 —— 用 [`gal`](https://pub.dev/packages/gal) 插件。
///
/// **权限要求（照 gal 官方 README，别凭记忆改）**：
/// - Android **API ≤ 29**：需要 `WRITE_EXTERNAL_STORAGE`，且按官方要求写
///   `android:maxSdkVersion="29"`；API 29 还要求在 `<application>` 上加
///   `android:requestLegacyExternalStorage="true"`。
///   **API ≥ 30 走 MediaStore，不需要任何存储权限。**
/// - iOS：需要 `NSPhotoLibraryAddUsageDescription`（只写入时用）；
///   要存进指定相册才另需 `NSPhotoLibraryUsageDescription`。
///   两个键本项目 `ios/Runner/Info.plist` 都已经有了。
class GalleryPhotoSaver implements PhotoSaver {
  const GalleryPhotoSaver();

  @override
  Future<void> save(String path) async {
    try {
      await Gal.putImage(path);
    } on GalException catch (e) {
      if (e.type != GalExceptionType.accessDenied) {
        throw PhotoSaveException(_why(e.type));
      }
      // 第一次被拒：申请一次权限，再试一遍（用户会看到系统弹窗）。
      //
      // ⚠️ 顺序是「先存、被拒才申请」而不是「先查权限」：API ≥ 30 不需要
      // 任何存储权限，先查 `hasAccess()` 在有些机型上会返回 false，
      // 那样就会白白拦住一次本来能成功的保存。
      final granted = await Gal.requestAccess();
      if (!granted) {
        throw const PhotoSaveException(
            '没有相册权限 —— 去「设置 → 应用 → 摄影助手 → 权限」里打开');
      }
      try {
        await Gal.putImage(path);
      } on GalException catch (e2) {
        throw PhotoSaveException(_why(e2.type));
      }
    }
  }

  static String _why(GalExceptionType t) => switch (t) {
        GalExceptionType.accessDenied => '没有相册权限',
        GalExceptionType.notEnoughSpace => '存储空间不够',
        GalExceptionType.notSupportedFormat => '这个格式相册不收',
        GalExceptionType.unexpected => '相册写入失败',
      };
}
