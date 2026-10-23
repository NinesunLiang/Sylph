import 'package:flutter/material.dart';

import 'suggestion.dart';

/// 「拍摄方案（光照/人站哪/拍摄点/机位方向）+ 好在哪 / 差在哪 / 更优怎么拍」卡片。
///
/// 这是 App 的**核心产出**。人类 2026-09-20 的定位：
/// 「核心是 pose 教程和拍摄建议，拍摄建议包括拍摄的位置（位置和高度）、
///   拍摄方向；摄像机参数只是基础的初始化流程。」
/// 随后补充：给一张照片**或视频**，要给出「好的拍摄点（**要考虑光照**）、
///   摄影机的方向、被拍人物的站位」。
///
/// ⚠️ **诚实标注**：这里的优缺点、更优选择都是**模型的判断**（主观意见），
/// 不是可验证的测量结果。所以卡片底部必须写明出处 —— 不能和"本地算出来的
/// 数字"混在一起让人以为是事实。
class CritiqueCard extends StatelessWidget {
  const CritiqueCard({super.key, required this.s});

  final Suggestion s;

  @override
  Widget build(BuildContext context) {
    final plan = s.shootingPlan;
    final hasPlan = !plan.isEmpty;
    final hasBody = hasPlan || s.pros.isNotEmpty || s.critiques.isNotEmpty;

    // 本地规则兜底时什么都没有 —— 不给空壳卡片（那只会让界面变噪）
    if (!hasBody) return const SizedBox.shrink();

    final isModel = s.source == SuggestionSource.visionModel;

    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (hasPlan) ...[
              Row(
                children: [
                  const Icon(Icons.explore_outlined, size: 16),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text('拍摄方案',
                        style: const TextStyle(
                            fontWeight: FontWeight.w700, fontSize: 13)),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              // 顺序就是推导顺序：光 → 人站哪 → 你去哪拍 → 朝哪拍
              if (plan.lighting != null) _kv('💡 光照', plan.lighting!),
              if (plan.subjectPosition != null)
                _kv('🧍 人站哪', plan.subjectPosition!),
              if (plan.position != null) _kv('📍 拍摄点', plan.position!),
              if (plan.direction != null) _kv('🧭 机位方向', plan.direction!),
            ],
            if (s.pros.isNotEmpty) ...[
              const SizedBox(height: 10),
              const Text('✅ 好在哪',
                  style: TextStyle(fontSize: 12, color: Colors.greenAccent)),
              const SizedBox(height: 2),
              for (final p in s.pros) _bullet(p),
            ],
            if (s.critiques.isNotEmpty) ...[
              const SizedBox(height: 10),
              const Text('⚠️ 差在哪 → 更优怎么拍',
                  style: TextStyle(fontSize: 12, color: Colors.amberAccent)),
              const SizedBox(height: 2),
              for (final c in s.critiques) _critique(c),
            ],
            // 「把拍好照片的要素都做好」的落点：整份清单在这儿。
            // ⚠️ 默认**收起**——上面已经有重点了，全清单想看再展开（别再把人淹了）。
            if (s.elements.isNotEmpty) ...[
              const SizedBox(height: 4),
              _elements(),
            ],
            if (isModel) ...[
              const SizedBox(height: 8),
              const Text(
                '以上是模型的判断（主观意见），不是测量出来的结果。',
                style: TextStyle(fontSize: 10, color: Colors.white38),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(k, style: const TextStyle(fontSize: 11, color: Colors.white54)),
            Text(v, style: const TextStyle(fontSize: 13)),
          ],
        ),
      );

  Widget _bullet(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 2),
        child: Text('· $t', style: const TextStyle(fontSize: 12)),
      );

  Widget _critique(CritiqueItem c) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (c.problem.isNotEmpty)
              Text('· ${c.problem}',
                  style: const TextStyle(fontSize: 12, color: Colors.white70)),
            if (c.better.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(left: 10, top: 1),
                child: Text('→ ${c.better}',
                    style: const TextStyle(fontSize: 12)),
              ),
          ],
        ),
      );

  /// 全部要素体检（默认收起）。
  ///
  /// 排序：**有问题的排最前**（这才是用户要动手改的），然后是好的，最后是
  /// "看不出/没有这一项"的 —— 把它们如实列出来，比假装评过更诚实。
  Widget _elements() {
    final problems = [
      for (final e in s.elements)
        if (e.verdict == ElementVerdict.problem) e
    ];
    final goods = [
      for (final e in s.elements)
        if (e.verdict == ElementVerdict.good) e
    ];
    final unclear = [
      for (final e in s.elements)
        if (e.verdict == ElementVerdict.unclear) e
    ];

    return ExpansionTile(
      tilePadding: EdgeInsets.zero,
      childrenPadding: EdgeInsets.zero,
      title: Text('🔍 全部要素体检（${s.elements.length} 项）',
          style: const TextStyle(fontSize: 12, color: Colors.white70)),
      subtitle: Text(
        '⚠️ ${problems.length} 项有问题 · ✅ ${goods.length} 项好 · '
        '— ${unclear.length} 项看不出',
        style: const TextStyle(fontSize: 11, color: Colors.white38),
      ),
      children: [
        for (final e in [...problems, ...goods, ...unclear]) _elementRow(e),
        if (anchoredElements(s).isNotEmpty)
          const Padding(
            padding: EdgeInsets.only(top: 2, bottom: 4),
            child: Text('带编号的项，已经画在画面上了（对应图上的框）',
                style: TextStyle(fontSize: 10, color: Colors.white38)),
          ),
      ],
    );
  }

  Widget _elementRow(ElementCheck e) => Padding(
        padding: const EdgeInsets.only(bottom: 5),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${e.verdict.mark} ${_no(s, e)}${e.name}',
                style: TextStyle(
                  fontSize: 12,
                  color: e.verdict == ElementVerdict.problem
                      ? Colors.amberAccent
                      : Colors.white70,
                )),
            if (e.advice != null && e.advice!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(left: 14, top: 1),
                child: Text('→ ${e.advice}',
                    style: const TextStyle(fontSize: 11, color: Colors.white70)),
              ),
          ],
        ),
      );
}

/// 要素在完整清单里的序号（1 起）。有锚点的项，这个号就是图上的框号。
String _no(Suggestion s, ElementCheck e) {
  final i = s.elements.indexOf(e);
  return i < 0 ? '' : '${i + 1}. ';
}
