import 'package:flutter/material.dart';

import '../coach/suggestion.dart';
import '../poses/pose.dart';
import 'guidance_overlay.dart';

/// F3 用：把某个姿势半透明叠在相机预览上，并保留 F2 的引导图层。
///
/// 这个组件是 F2 和 F3 的交叉点：
/// - [pose] 来自姿势集
/// - [suggestion] 来自构图教练（可为空）
class PoseOverlayView extends StatelessWidget {
  const PoseOverlayView({
    super.key,
    required this.pose,
    this.suggestion,
    this.sourceImage,
    this.poseOpacity = 0.35,
  });

  final Pose pose;
  final Suggestion? suggestion;
  final ImageProvider? sourceImage;
  final double poseOpacity;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Stack(
      fit: StackFit.expand,
      children: [
        if (sourceImage != null)
          Image(image: sourceImage!, fit: BoxFit.cover),
        Opacity(
          opacity: poseOpacity,
          // 参考照姿势没有火柴人线条，只能叠**照片本身**。
          //
          // 这里不叠照片的话，用户从姿势集选了张参考照、点「送到预览页」，
          // 到了预览页只会看到一片空白 —— 没有线条也没有照片。
          // （曾经更糟：`strokes` 为空会让 PoseFigurePainter 抛
          //   `Bad state: No element`，直接把 App 画崩。）
          child: pose.hasPhoto
              ? Image.asset(
                  pose.imagePath!,
                  fit: BoxFit.contain,
                  // 素材缺失时不要整页红屏，退回到什么都不画。
                  errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                )
              : CustomPaint(
                  painter: PoseFigurePainter(
                    pose: pose,
                    color: scheme.primary,
                    strokeWidth: 3,
                  ),
                ),
        ),
        if (suggestion != null) GuidanceOverlay(suggestion: suggestion!),
      ],
    );
  }
}
