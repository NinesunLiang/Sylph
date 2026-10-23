import 'package:flutter/material.dart';

import 'live_element_probe.dart';
import '../coach/suggestion.dart';
import '../poses/pose.dart';
import 'alignment.dart';

/// 虚拟引导图层：在取景框上画网格、主体目标框、移动箭头、倾斜提示。
///
/// 两种数据源都支持：
/// - `suggestion`（F2 的静态建议）→ 画目标框和「现在在哪」
/// - `liveBox` / `liveFeedback`（F2.12 的实时检测）→ 画实际检测到的主体 + 实时提示
///
/// 本组件只做「换算 + 画」，不含业务判断（判断在 alignment.dart，可单测）。
class GuidanceOverlay extends StatelessWidget {
  const GuidanceOverlay({
    super.key,
    required this.suggestion,
    this.showGrid = true,
    this.showBanners = true,
    this.targetImage,
    this.targetImageOpacity = 0.35,
    this.liveBox,
    this.liveFeedback,
    this.liveIssue,
    this.liveStatus = '',
    this.poseHint,
  });

  final Suggestion suggestion;

  /// 三分法参考线。
  final bool showGrid;

  /// 是否画文字提示条（_LiveBanner + _HintBanner）。
  /// 拍摄页把它关掉，把提示挪到取景框外面（不挡主体）。
  final bool showBanners;

  /// F3：要叠加的姿势参考图（半透明）。
  final ImageProvider? targetImage;
  final double targetImageOpacity;

  /// F2.12：本地实时检测到的主体框（每秒刷新）。为空表示这次没测到。
  final Rect01? liveBox;

  /// F2.12：实时对位反馈（往左/靠近/保持不动）。
  final AlignFeedback? liveFeedback;

  /// 本地要素探针给出的最该处理的那一条（过曝/背景乱/主体贴边）。
  /// 完全本地算出来的，不联网。
  final LiveIssue? liveIssue;

  /// 没测到主体时的原因说明。
  final String liveStatus;

  /// F3.7：当前正在照着摆的姿势（有就在提示条上写一行）。
  final Pose? poseHint;

  // 注意：status 非空也算「开了实时」—— 没测到主体时必须让用户看到原因，
  // 否则界面上什么都不显示，用户会以为功能坏了。
  bool get _hasLive =>
      liveBox != null || liveFeedback != null || liveStatus.isNotEmpty;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        if (targetImage != null)
          Opacity(
            opacity: targetImageOpacity,
            child: Image(image: targetImage!, fit: BoxFit.contain),
          ),
        CustomPaint(
          painter: _GuidancePainter(
            suggestion: suggestion,
            showGrid: showGrid,
            color: Theme.of(context).colorScheme.primary,
            warnColor: Theme.of(context).colorScheme.error,
            liveBox: liveBox,
            liveAligned: liveFeedback?.aligned ?? false,
            liveAction: liveFeedback?.action,
            liveIssue: liveIssue,
          ),
        ),
        if (showBanners)
          Positioned(
            left: 12,
            right: 12,
            bottom: 12,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_hasLive)
                  _LiveBanner(
                    feedback: liveFeedback,
                    status: liveStatus,
                    liveBox: liveBox,
                    poseHint: poseHint,
                    issue: liveIssue,
                  ),
                _HintBanner(suggestion: suggestion),
              ],
            ),
          ),
      ],
    );
  }
}

/// F2.12 实时反馈条：一句话告诉用户现在该干嘛。
class _LiveBanner extends StatelessWidget {
  const _LiveBanner({
    this.issue,
    required this.feedback,
    required this.status,
    required this.liveBox,
    this.poseHint,
  });

  final AlignFeedback? feedback;
  final String status;
  final Rect01? liveBox;
  final Pose? poseHint;

  /// 本地要素提示（过曝/背景乱/主体贴边）。
  final LiveIssue? issue;

  @override
  Widget build(BuildContext context) {
    final f = feedback;
    final aligned = f?.aligned ?? false;
    final color = aligned ? Colors.greenAccent : Colors.amberAccent;

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.7), width: 1.5),
      ),
      child: Row(
        children: [
          Icon(
            aligned ? Icons.check_circle : _iconFor(f?.action),
            size: 22,
            color: color,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  f?.message ?? '还没测到主体',
                  style: TextStyle(
                    fontSize: 15,
                    color: color,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (f == null && status.isNotEmpty)
                  Text(
                    status,
                    style: const TextStyle(fontSize: 11, color: Colors.white60),
                  )
                else if (liveBox != null)
                  Text(
                    '主体占画面 ${(liveBox!.width * liveBox!.height * 100).toStringAsFixed(1)}%'
                    '${poseHint == null ? '' : ' · 照着「${poseHint!.title}」'}',
                    style: const TextStyle(fontSize: 11, color: Colors.white54),
                  ),
                // 本地要素提示：过曝 / 背景乱 / 主体贴边。
                // 它和"对位"是两件事，所以**另起一行**，不抢主提示的位置。
                if (issue != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 3),
                    child: Text(
                      '${issue!.kind.label}：${issue!.text}',
                      style: const TextStyle(
                          fontSize: 11, color: Colors.orangeAccent),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static IconData _iconFor(AlignAction? a) => switch (a) {
        AlignAction.stable => Icons.check_circle,
        AlignAction.moveLeft => Icons.west,
        AlignAction.moveRight => Icons.east,
        AlignAction.moveUp => Icons.north,
        AlignAction.moveDown => Icons.south,
        AlignAction.moveCloser => Icons.zoom_in,
        AlignAction.moveBack => Icons.zoom_out,
        null => Icons.search_off,
      };
}

/// 提示词卡片（可折叠/展开）。
///
/// v0.9.3：点击标题行折叠详情（角度/EV 那些数字），只留一句话主提示。
class _HintBanner extends StatefulWidget {
  const _HintBanner({required this.suggestion});

  final Suggestion suggestion;

  @override
  State<_HintBanner> createState() => _HintBannerState();
}

class _HintBannerState extends State<_HintBanner> {
  bool _collapsed = false;

  @override
  Widget build(BuildContext context) {
    final s = widget.suggestion;
    final move = s.cameraMove;
    final offline = s.source == SuggestionSource.ruleFallback;
    return GestureDetector(
      onTap: () => setState(() => _collapsed = !_collapsed),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Icon(
                  offline ? Icons.offline_bolt : Icons.auto_awesome,
                  size: 16,
                  color: offline ? Colors.orangeAccent : Colors.lightBlueAccent,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    s.source.label,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 12,
                      color: Colors.white70,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    s.composition.rule,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.right,
                    style: const TextStyle(fontSize: 12, color: Colors.white54),
                  ),
                ),
                Icon(
                  _collapsed
                      ? Icons.expand_more
                      : Icons.expand_less,
                  size: 16,
                  color: Colors.white54,
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              move.hint.isEmpty ? '按提示微调' : move.hint,
              style: const TextStyle(fontSize: 14, color: Colors.white),
            ),
            if (!_collapsed) ...[
              const SizedBox(height: 4),
              Text(
                '↔ ${move.panDeg.toStringAsFixed(1)}°   '
                '↕ ${move.tiltDeg.toStringAsFixed(1)}°   '
                '⇔ ${move.dollyM.toStringAsFixed(2)}m   '
                '⤢ ${move.zoom.toStringAsFixed(2)}x   '
                'EV ${s.exposure.ev >= 0 ? '+' : ''}${s.exposure.ev.toStringAsFixed(1)}',
                style: const TextStyle(fontSize: 12, color: Colors.white70),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _GuidancePainter extends CustomPainter {
  _GuidancePainter({
    required this.suggestion,
    required this.showGrid,
    required this.color,
    required this.warnColor,
    this.liveIssue,
    this.liveBox,
    this.liveAligned = false,
    this.liveAction,
  });

  final Suggestion suggestion;
  final bool showGrid;
  final Color color;
  final Color warnColor;

  /// F2.12：本地实时检测到的主体框。
  final Rect01? liveBox;
  final bool liveAligned;
  final AlignAction? liveAction;
  final LiveIssue? liveIssue;

  @override
  void paint(Canvas canvas, Size size) {
    if (showGrid) _paintThirds(canvas, size);

    final tilt = suggestion.composition.horizonTiltDeg;
    if (tilt.abs() > 1.0) _paintHorizonTilt(canvas, size, tilt);

    final subj = suggestion.subject;
    // 有实时数据时以实时为准（静态建议里的 current_box 只是"模型看到的那一帧"）
    final cur = liveBox ?? subj.currentBox;
    final tgt = subj.targetBox;

    if (cur != null) {
      _paintBox(
        canvas,
        size,
        cur,
        liveAligned ? Colors.greenAccent : warnColor,
        dashed: !liveAligned,
        label: liveBox != null ? '实时' : '现在',
      );
    }
    if (tgt != null) {
      // v0.9.3：目标框太小（<40% 画面面积）时放大到 ~2/3 画面高度，
      // 让小白有一个明显的大区域可以瞄准（原来 18% 的小框没人看得清）。
      // 只改渲染，对齐计算仍用原始框。
      final area = tgt.width * tgt.height;
      Rect01 displayTarget = tgt;
      if (area < 0.4) {
        final targetH = 2.0 / 3.0;
        final scale = targetH / tgt.height;
        final newW = (tgt.width * scale).clamp(0.0, 1.0);
        final newH = targetH;
        final cx = tgt.centerX;
        final cy = tgt.centerY;
        displayTarget = Rect01(
          (cx - newW / 2).clamp(0.0, 1.0),
          (cy - newH / 2).clamp(0.0, 1.0),
          newW,
          newH,
        );
      }
      _paintBox(canvas, size, displayTarget, color, dashed: false, label: '目标');
    }
    if (cur != null && tgt != null) {
      _paintArrow(canvas, size, cur, tgt, liveAligned ? Colors.greenAccent : color);
    }

    // 实时要素问题：把它**画在画面上的那个位置**（位置是本地算出来的，不是猜的）
    final li = liveIssue;
    if (li != null && li.rect != null) {
      _paintBox(
        canvas,
        size,
        li.rect!,
        warnColor,
        dashed: true,
        label: li.kind.label,
      );
    }

    // 「要素体检」的画面锚点：把文字问题落到画面上的具体位置。
    // 编号和图下的清单一致 —— 用户才知道"第 2 条"说的是画面哪儿。
    // ⚠️ 只在有锚点时画；模型没给位置就只显示文字，不硬画。
    for (final (no, e) in anchoredElements(suggestion)) {
      // 眼神/视线类的锚点：给一支**箭头**从主体指过去 ——
      // "眼神该看哪"光有一个框看不懂，箭头才是一句话能照做的指令。
      final isGaze = e.name.contains('眼神') ||
          e.name.contains('视线') ||
          e.name.contains('目光');
      if (isGaze && cur != null) {
        _paintArrow(canvas, size, cur, e.anchor!, Colors.lightBlueAccent);
      }
      _paintBox(
        canvas,
        size,
        e.anchor!,
        e.verdict == ElementVerdict.problem ? warnColor : color,
        dashed: true,
        label: '$no ${e.name}',
      );
    }
    if (liveBox == null && liveAction != null) {
      _paintDirectionCue(canvas, size, liveAction!, Colors.amberAccent);
    }
  }

  /// 没测到主体框时的方向提示：在画面边缘画一个大箭头。
  void _paintDirectionCue(Canvas canvas, Size size, AlignAction action, Color c) {
    final center = Offset(size.width / 2, size.height / 2);
    final r = size.shortestSide * 0.18;
    final (Offset from, Offset to) = switch (action) {
      AlignAction.moveLeft => (
          center + Offset(r, 0),
          center + Offset(-r, 0),
        ),
      AlignAction.moveRight => (
          center + Offset(-r, 0),
          center + Offset(r, 0),
        ),
      AlignAction.moveUp => (
          center + Offset(0, r),
          center + Offset(0, -r),
        ),
      AlignAction.moveDown => (
          center + Offset(0, -r),
          center + Offset(0, r),
        ),
      AlignAction.moveCloser => (
          center + Offset(-r, r),
          center + Offset(r * 0.4, r * 0.4),
        ),
      AlignAction.moveBack => (
          center + Offset(r * 0.4, r * 0.4),
          center + Offset(-r, r),
        ),
      AlignAction.stable => (center, center),
    };
    if (from == to) return;
    final paint = Paint()
      ..color = c
      ..strokeWidth = 5
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(from, to, paint);
    final angle = (to - from).direction;
    const head = 18.0;
    final p1 = to - Offset.fromDirection(angle - 0.5, head);
    final p2 = to - Offset.fromDirection(angle + 0.5, head);
    canvas.drawPath(
      Path()
        ..moveTo(to.dx, to.dy)
        ..lineTo(p1.dx, p1.dy)
        ..lineTo(p2.dx, p2.dy)
        ..close(),
      Paint()..color = c,
    );
  }

  void _paintThirds(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.28)
      ..strokeWidth = 1;
    for (var i = 1; i <= 2; i++) {
      final dx = size.width * i / 3;
      final dy = size.height * i / 3;
      canvas.drawLine(Offset(dx, 0), Offset(dx, size.height), paint);
      canvas.drawLine(Offset(0, dy), Offset(size.width, dy), paint);
    }
    // 交叉点小圆点
    final dot = Paint()..color = Colors.white.withValues(alpha: 0.5);
    for (final x in [1, 2]) {
      for (final y in [1, 2]) {
        canvas.drawCircle(
          Offset(size.width * x / 3, size.height * y / 3),
          3,
          dot,
        );
      }
    }
  }

  void _paintHorizonTilt(Canvas canvas, Size size, double deg) {
    canvas.save();
    canvas.translate(size.width / 2, size.height / 2);
    canvas.rotate(deg * 3.14159265 / 180);
    canvas.translate(-size.width / 2, -size.height / 2);
    final paint = Paint()
      ..color = Colors.amberAccent.withValues(alpha: 0.8)
      ..strokeWidth = 2;
    canvas.drawLine(
      Offset(0, size.height / 2),
      Offset(size.width, size.height / 2),
      paint,
    );
    canvas.restore();
  }

  void _paintBox(
    Canvas canvas,
    Size size,
    Rect01 r,
    Color color, {
    required bool dashed,
    required String label,
  }) {
    final rect = Rect.fromLTWH(
      r.left * size.width,
      r.top * size.height,
      r.width * size.width,
      r.height * size.height,
    );
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = dashed ? 1.5 : 3;
    if (dashed) {
      _drawDashedRect(canvas, rect, paint);
    } else {
      canvas.drawRect(rect, paint);
    }
    _paintLabel(canvas, rect.topLeft, label, color);
  }

  void _drawDashedRect(Canvas canvas, Rect rect, Paint paint) {
    const dash = 10.0;
    const gap = 6.0;
    void line(Offset a, Offset b) {
      final total = (b - a).distance;
      if (total <= 0) return;
      final dir = (b - a) / total;
      var travelled = 0.0;
      while (travelled < total) {
        final end = (travelled + dash).clamp(0.0, total);
        canvas.drawLine(a + dir * travelled, a + dir * end, paint);
        travelled = end + gap;
      }
    }

    line(rect.topLeft, rect.topRight);
    line(rect.topRight, rect.bottomRight);
    line(rect.bottomRight, rect.bottomLeft);
    line(rect.bottomLeft, rect.topLeft);
  }

  void _paintArrow(Canvas canvas, Size size, Rect01 from, Rect01 to, Color color) {
    final start = Offset(from.centerX * size.width, from.centerY * size.height);
    final end = Offset(to.centerX * size.width, to.centerY * size.height);
    if ((end - start).distance < 8) return;

    final paint = Paint()
      ..color = color
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(start, end, paint);

    // 箭头头部
    final dir = (end - start);
    final angle = dir.direction;
    const headLen = 14.0;
    const headAngle = 0.5;
    final p1 = end -
        Offset.fromDirection(angle - headAngle, headLen);
    final p2 = end -
        Offset.fromDirection(angle + headAngle, headLen);
    final head = Path()
      ..moveTo(end.dx, end.dy)
      ..lineTo(p1.dx, p1.dy)
      ..lineTo(p2.dx, p2.dy)
      ..close();
    canvas.drawPath(head, Paint()..color = color);
  }

  void _paintLabel(Canvas canvas, Offset at, String text, Color color) {
    final tp = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, at + const Offset(2, -16));
  }

  @override
  bool shouldRepaint(covariant _GuidancePainter old) =>
      old.suggestion != suggestion ||
      old.showGrid != showGrid ||
      old.liveBox != liveBox ||
      old.liveAligned != liveAligned ||
      old.liveAction != liveAction;
}
