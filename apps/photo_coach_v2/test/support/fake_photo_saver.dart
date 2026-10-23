import 'package:photo_coach_v2/features/camera/photo_saver.dart';

/// 假存档：只记录「被要求存了哪些路径」，不碰真相册。
///
/// [failWith] 可以中途改（先让它失败、再清掉验证"下次成功后警告要消失"）。
class FakePhotoSaver implements PhotoSaver {
  FakePhotoSaver({this.failWith});

  /// 非 null 时 `save` 抛这个错 —— 用来测「存不进去」的路径。
  PhotoSaveException? failWith;

  final List<String> saved = [];

  @override
  Future<void> save(String path) async {
    final f = failWith;
    if (f != null) throw f;
    saved.add(path);
  }
}
