import 'dart:async';
import 'dart:typed_data';

import 'video_input.dart';

/// 真实抽帧实现 —— **目前是占位，会明确报「不支持」**。
///
/// ## 为什么先不实现
/// 真解码需要 `video_player`。本机**没有 Xcode 也没有 Android SDK**，
/// 装了根本编译不到真机上验证（裸 `flutter test` 也跑不到原生）。
/// 加一个「装上去但没验证过」的原生依赖，比不加更危险 ——
/// 它会让整个工程在某台手机上第一次构建就失败，而且没人知道原因。
///
/// ## 要接的话怎么做（已验证过接口形状，不是猜的）
/// 1. `flutter pub add video_player`
/// 2. 用 `VideoPlayerController.file(File(path))`，`await initialize()`
/// 3. `controller.value.duration` → 喂给 [planFrameTimes] 拿时间点
/// 4. 每个时间点 `await controller.seekTo(t)` + `await controller.play()`
///    再 `await controller.pause()`，让首帧渲染出来
/// 5. 用 `controller.value.size` 建一张同尺寸的 `ui.Image`，
///    `canvas.drawImage`，再 `image.toByteData(format: rawRgba)`
/// 6. 把 RGBA + width/height 包成 [RawFrame] 返回
///
/// 第 5 步（离屏画布取像素）是**最容易踩坑的地方**，必须在真机上试。
/// 所以这一步留到有工具链的时候做，而不是现在硬写一个没验证过的版本。
class UnverifiedVideoFrameSource implements VideoFrameSource {
  const UnverifiedVideoFrameSource();

  static const _message =
      '当前构建还没接视频解码（需要 video_player + 真机验证）。'
      '要启用请见 lib/features/coach/video_frame_source_impl.dart 的说明。';

  @override
  Future<Duration> duration(String videoPath) async {
    throw VideoInputException(_message);
  }

  @override
  Future<RawFrame> frameAt(String videoPath, Duration at) async {
    throw VideoInputException(_message);
  }
}

/// 抽帧结果的原始载体（占位实现没用到，保留给真实实现）。
class RawFrameBytes {
  const RawFrameBytes(this.bytes, this.width, this.height);
  final Uint8List bytes;
  final int width;
  final int height;
}
