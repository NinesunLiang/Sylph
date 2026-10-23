import 'dart:ui' show PictureRecorder;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/guidance/pose_overlay_view.dart';
import 'package:photo_coach_v2/features/poses/pose.dart';

/// 回归测试：**真实参考照姿势（strokes 为空）不能把 App 画崩**。
///
/// 背景（这是一个真实的崩溃）：
/// 参考照姿势的 `strokes` 是空列表（它们靠 `imagePath` 显示照片）。
/// 但 `PoseFigurePainter` 里有一句 `pose.strokes.first`，
/// 空列表取 `.first` 会抛 `Bad state: No element`。
///
/// 触发路径：姿势集 → 参考照 → 点开一张 → 「送到拍摄页，照着摆」
/// → 拍摄页用 `PoseFigurePainter` 画这个姿势 → **崩溃**。
///
/// 之前的测试没抓住，是因为「送到拍摄页」那条链路只用 `PoseCatalog.builtIn`
/// （火柴人，strokes 非空）测过，**从来没用真实参考照跑过**。
void main() {
  group('参考照姿势不许把画面画崩', () {
    test('前提：参考照姿势的 strokes 确实是空的', () {
      final photo = photoPoses.first;
      expect(photo.hasPhoto, isTrue);
      expect(photo.strokes, isEmpty,
          reason: '参考照靠照片显示，不该有火柴人线条 —— 前提变了就要重看这个测试');
    });

    test('前提：火柴人库 v0.4.0 已删（接口保留，恒为空）', () {
      // 这版之前这里断言「火柴人姿势 strokes 非空」；
      // v0.4.0 按用户要求把火柴人库删了（只留真实参考照），
      // 所以契约变成：builtIn 恒为空 —— 但 strokes 防御分支仍要留，
      // 防止将来又混进无照片的姿势。
      expect(PoseCatalog.builtIn, isEmpty);
    });

    test('PoseFigurePainter 直接画参考照姿势不抛异常', () {
      final photo = photoPoses.first;
      // 不经过 widget 层，直接调画家 —— 崩的就是这里
      expect(
        () => PoseFigurePainter(pose: photo, color: Colors.white)
            .paint(Canvas(PictureRecorder()), const Size(300, 400)),
        returnsNormally,
        reason: '参考照（strokes 为空）把 PoseFigurePainter 画崩了',
      );
    });

    testWidgets('PoseOverlayView 渲染参考照姿势不抛异常（拍摄页叠加用）', (tester) async {
      tester.view.physicalSize = const Size(390, 900) * 3;
      tester.view.devicePixelRatio = 3;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: Scaffold(
          body: PoseOverlayView(pose: photoPoses.first),
        ),
      ));
      await tester.pump();

      expect(tester.takeException(), isNull,
          reason: '拍摄页叠加参考照姿势时崩了 —— 这就是用户看到的"屡次停止运行"');
    });

    testWidgets('男姿参考照同样不崩', (tester) async {
      final male = PoseCatalog.photos(gender: '男').first;
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: Scaffold(body: PoseOverlayView(pose: male)),
      ));
      await tester.pump();
      expect(tester.takeException(), isNull);
    });

    testWidgets('火柴人姿势照旧能画（不能因为修 bug 把老功能弄坏）', (tester) async {
      // v0.4.0 火柴人库已删，改用合成姿势覆盖「strokes 非空」这条分支。
      const stick = Pose(
        id: 'stick_test',
        title: '合成火柴人',
        category: '站姿',
        strokes: [
          PoseStroke(0.5, 0.1, 0.5, 0.6), // 躯干
          PoseStroke(0.5, 0.2, 0.3, 0.5), // 左臂
          PoseStroke(0.5, 0.2, 0.7, 0.5), // 右臂
          PoseStroke(0.5, 0.6, 0.35, 0.95), // 左腿
          PoseStroke(0.5, 0.6, 0.65, 0.95), // 右腿
        ],
      );
      await tester.pumpWidget(MaterialApp(
        theme: ThemeData.dark(),
        home: Scaffold(body: PoseOverlayView(pose: stick)),
      ));
      await tester.pump();
      expect(tester.takeException(), isNull,
          reason: '有线条的火柴人姿势画崩了 —— 修参考照的 bug 把老功能弄坏了');
    });
  });
}
