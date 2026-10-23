import 'package:flutter/material.dart';

import 'exposure_knowledge.dart';
import 'parameter_advisor.dart';

/// 「建议参数」卡片 —— **故意做得很小**。
///
/// 人类反馈：「太复杂了」。所以这里只留两行：
///   第一行：**建议值本身**（大号字，一眼看到，可截图带走）
///   第二行：需要提醒的一句话（只在真会拍坏照片时才出现）
/// 依据出处、计算过程、实测数据**全部收进右上角的 ⓘ**，平时不占地方 ——
/// 想核对的人点一下就有，不想看的人永远不用看见。
class ParameterCard extends StatelessWidget {
  const ParameterCard({
    super.key,
    required this.advice,
    this.appCanSet = const [],
  });

  final ParameterAdvice advice;

  /// 本机能自动设上的（名称+值），作为一行小字。
  final List<String> appCanSet;

  /// 主行：ISO · 快门 · 光圈（按摄影习惯排序）。没有建议值就是 null。
  String? get _mainLine {
    const order = ['ISO', '快门', '光圈'];
    final parts = <String>[];
    for (final name in order) {
      for (final r in advice.recommendations) {
        if (r.name == name) parts.add('${r.name} ${r.value}');
      }
    }
    return parts.isEmpty ? null : parts.join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    final main = _mainLine;
    final headline = advice.headline;

    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 4, 4, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('建议参数 · ${advice.intent.label}',
                      style:
                          const TextStyle(fontSize: 12, color: Colors.white54)),
                ),
                IconButton(
                  tooltip: '依据',
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.info_outline,
                      size: 16, color: Colors.white38),
                  onPressed: () => _showWhy(context),
                ),
              ],
            ),
            if (!advice.covered)
              _big('给不出建议')
            else if (main != null)
              _big(main)
            else if (headline != null)
              _big(headline),
            if (!advice.covered && advice.notCoveredReason != null)
              Padding(
                padding: const EdgeInsets.only(right: 8, top: 2),
                child: Text(advice.notCoveredReason!,
                    style: const TextStyle(fontSize: 11, color: Colors.white54)),
              ),
            if (advice.covered && main != null && headline != null)
              Padding(
                padding: const EdgeInsets.only(right: 8, top: 4),
                child: Text(headline,
                    style: const TextStyle(
                        fontSize: 11, color: Colors.amberAccent)),
              ),
            if (appCanSet.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(right: 8, top: 4),
                child: Text('本机能设：${appCanSet.join(' · ')}',
                    style: const TextStyle(fontSize: 11, color: Colors.white38)),
              ),
          ],
        ),
      ),
    );
  }

  Widget _big(String t) => Text(t,
      style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700));

  /// ⓘ —— 依据、出处、计算过程都在这儿，平时不显示。
  void _showWhy(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${advice.intent.label}：这些数字是怎么来的',
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 10),
              for (final r in advice.recommendations) ...[
                Text('${r.name} ${r.value}',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                if (r.note != null)
                  Text(r.note!,
                      style:
                          const TextStyle(fontSize: 11, color: Colors.white70)),
                const SizedBox(height: 8),
              ],
              if (advice.basis.isNotEmpty) ...[
                const Text('实测依据',
                    style:
                        TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                for (final b in advice.basis)
                  Text('· $b',
                      style: const TextStyle(
                          fontSize: 11, color: Colors.white70)),
                const SizedBox(height: 8),
              ],
              if (advice.notes.isNotEmpty) ...[
                const Text('说明',
                    style:
                        TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                for (final n in advice.notes)
                  Text('· $n',
                      style: const TextStyle(
                          fontSize: 11, color: Colors.white70)),
                const SizedBox(height: 8),
              ],
              if (advice.rules.isNotEmpty) ...[
                const Text('出处（可复制核对）',
                    style:
                        TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                for (final r in advice.rules) ...[
                  Text('· ${r.publisher}',
                      style: const TextStyle(
                          fontSize: 11, fontWeight: FontWeight.w600)),
                  SelectableText(r.statement,
                      style: const TextStyle(
                          fontSize: 11, color: Colors.white70)),
                  SelectableText(r.url,
                      style: const TextStyle(
                          fontSize: 10, color: Colors.blueAccent)),
                  const SizedBox(height: 8),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// 拍摄意图选择器（一行）。
///
/// 为什么必须有：**没有意图，「最优 ISO/快门」在物理上不存在**
/// （同一片水流，冻结水花要 1/1000，丝滑要 2s）。
class IntentPicker extends StatelessWidget {
  const IntentPicker({
    super.key,
    required this.value,
    required this.onChanged,
  });

  final ShootingIntent value;
  final ValueChanged<ShootingIntent> onChanged;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        const Text('拍什么？', style: TextStyle(fontSize: 12, color: Colors.white54)),
        for (final i in ShootingIntent.values)
          ChoiceChip(
            label: Text(i.label, style: const TextStyle(fontSize: 12)),
            visualDensity: VisualDensity.compact,
            selected: value == i,
            onSelected: (_) => onChanged(i),
          ),
      ],
    );
  }
}
