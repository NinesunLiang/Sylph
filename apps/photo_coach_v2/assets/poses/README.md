# assets/poses/

这里放**真实参考照**（jpg/png）。

v0 的姿势集是**代码里画的矢量火柴人**（见 `lib/features/poses/pose.dart`），
所以这个目录现在是空的、也是可以的 —— 只要目录存在，pubspec 的 assets
声明就不会报错。

要换成真实照片时：

1. 把图片按 `{pose_id}.jpg` 命名放进来，例如 `stand_relaxed.jpg`
2. 在 `pose.dart` 里给对应 `Pose` 填 `imagePath: 'assets/poses/stand_relaxed.jpg'`
3. UI 会自动优先用图片，没有图片才回退到画线条

⚠️ 版权：只用你有权使用的照片。别直接扒图。
