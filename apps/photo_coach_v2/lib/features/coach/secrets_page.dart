import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

/// 拍照秘诀（v0.6.0）：6 招，每招 3 句话 + 1 张示意图。
///
/// 内容来源：通用手机摄影基础（光线/角度/距离/构图/机位高度/时机），
/// 写成「照着做就行」的三句话，不堆术语。
/// 数据直接内置在本文件 = 本地数据库，零网络、零配置、启动即有。
class SecretsTip {
  const SecretsTip({
    required this.title,
    required this.summary,
    required this.svg,
    required this.points,
    this.goodImage,
    this.badImage,
  });

  final String title;

  /// 列表卡片上的「一句话」预告（详情里再展开 3 句）。
  final String summary;

  /// 示意图资源（assets/secrets/*.svg，已注册 pubspec assets）。
  final String svg;

  /// 三句话，直接读、直接做。
  final List<String> points;

  /// 正确做法示例图（jpg 路径，null = 用 SVG 占位）。
  final String? goodImage;

  /// 错误做法示例图（jpg 路径，null = 用 SVG 占位）。
  final String? badImage;
}

const List<SecretsTip> kSecretsTips = [
  SecretsTip(
    title: '光',
    summary: '人面朝光，脸好看',
    svg: 'assets/secrets/lighting.svg',
    goodImage: 'assets/secrets/examples/lighting_good.jpg',
    badImage: 'assets/secrets/examples/lighting_bad.jpg',
    points: [
      '让人面朝光源站：脸上有光，怎么拍都好看；背光站，脸就发黑。',
      '在家里就用窗户：请人坐窗边，光从正前方或斜侧面打在脸上。',
      '太阳太狠的时候（中午前后），把人挪到树荫或屋檐下的散光里。',
    ],
  ),
  SecretsTip(
    title: '角度',
    summary: '平视最上镜，仰拍显高',
    svg: 'assets/secrets/angle.svg',
    goodImage: 'assets/secrets/examples/angle_good.jpg',
    badImage: 'assets/secrets/examples/angle_bad.jpg',
    points: [
      '拍人：手机举到对方眼睛的高度，或稍微高一点，正面平拍最耐看。',
      '拍食物：斜上方 45° 俯拍，质感最清楚，餐桌上的菜最出片。',
      '想拍得「有气势」：把手机放低一点、微微仰拍，人会显得更高。',
    ],
  ),
  SecretsTip(
    title: '距离',
    summary: '别捏屏幕，用脚变焦',
    svg: 'assets/secrets/distance.svg',
    goodImage: 'assets/secrets/examples/distance_good.jpg',
    badImage: 'assets/secrets/examples/distance_bad.jpg',
    points: [
      '数码变焦是清晰度的大敌：别在屏幕上捏大，往前走两三步更清楚。',
      '拍合照：站远一点、手机放低微仰拍，人不会漏，脸也不会变形。',
      '想要背景虚化：离被拍的人近一点，人和背景的距离越开越好。',
    ],
  ),
  SecretsTip(
    title: '构图',
    summary: '先做减法，再谈高级',
    svg: 'assets/secrets/composition.svg',
    goodImage: 'assets/secrets/examples/composition_good.jpg',
    badImage: 'assets/secrets/examples/composition_bad.jpg',
    points: [
      '最省心的构图：主体放中间，背景尽量干净，一张就成立。',
      '在相机设置里打开「网格线」，把主体压在交叉点上，立刻有专业感。',
      '觉得画面乱，就退一步再拍：构图第一原则是做减法，把干扰项拿掉。',
    ],
  ),
  SecretsTip(
    title: '手机高度',
    summary: '机位跟着人的眼睛走',
    svg: 'assets/secrets/height.svg',
    goodImage: 'assets/secrets/examples/height_good.jpg',
    badImage: 'assets/secrets/examples/height_bad.jpg',
    points: [
      '拍站着的成年人：手机举到对方胸口高度拍；蹲在腰下拍，腿会变短。',
      '拍小孩：蹲下来，把手机放到和他眼睛齐平的高度——用他的世界看他。',
      '拍满桌菜：站起来斜俯拍；直上直下拍，桌子会显得很平、没层次。',
    ],
  ),
  SecretsTip(
    title: '快门时机',
    summary: '好照片是等出来的',
    svg: 'assets/secrets/timing.svg',
    goodImage: 'assets/secrets/examples/timing_good.jpg',
    badImage: 'assets/secrets/examples/timing_bad.jpg',
    points: [
      '拍人最出片的瞬间，常在动作发生前或发生后：甩头发、迈步、大笑的中间。',
      '先点一下屏幕对焦锁定，等那个瞬间出现，再按快门。',
      '拿不准就用连拍：连按三张，出好片的概率比只按一张高得多。',
    ],
  ),
];

/// 拍照秘诀列表页（教练 tab 入口 → 进这里）。
class SecretsPage extends StatelessWidget {
  const SecretsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('拍照秘诀'),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 12),
            child: Text('6 招', style: TextStyle(fontSize: 12, color: Colors.white54)),
          ),
        ],
      ),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: kSecretsTips.length,
        itemBuilder: (context, i) {
          final t = kSecretsTips[i];
          return Card(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            margin: const EdgeInsets.only(bottom: 12),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => SecretsDetailPage(tip: t, index: i),
                ),
              ),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SvgPicture.asset(t.svg, width: 56, height: 56),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '招 ${i + 1} · ${t.title}',
                            style: const TextStyle(
                                fontWeight: FontWeight.w700, fontSize: 15),
                          ),
                          Text(t.summary,
                              style: const TextStyle(
                                  fontSize: 12, color: Colors.white54)),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right,
                        size: 20, color: Colors.white38),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

/// 教练 tab 上的入口卡片：点开进「拍照秘诀」列表页。
class SecretsEntryCard extends StatelessWidget {
  const SecretsEntryCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(builder: (_) => const SecretsPage()),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              const Icon(Icons.auto_awesome, color: Colors.amberAccent),
              const SizedBox(width: 8),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('拍照秘诀',
                        style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                    Text('6 招 · 不靠天赋，照着做',
                        style: TextStyle(fontSize: 12, color: Colors.white54)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, size: 18, color: Colors.white38),
            ],
          ),
        ),
      ),
    );
  }
}

/// 单招详情页：正确/错误对比图 + 三句话说明。
class SecretsDetailPage extends StatelessWidget {
  const SecretsDetailPage({super.key, required this.tip, required this.index});

  final SecretsTip tip;
  final int index;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('招 ${index + 1} · ${tip.title}'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // 正确 / 错误 对比图（上下竖排，9:16 和拍摄页一样大）
          _ExampleColumn(
            label: '✓ 正确',
            labelColor: Colors.greenAccent,
            imagePath: tip.goodImage,
            placeholder: 'assets/secrets/examples/good_placeholder.svg',
          ),
          const SizedBox(height: 16),
          _ExampleColumn(
            label: '✗ 错误',
            labelColor: Colors.redAccent,
            imagePath: tip.badImage,
            placeholder: 'assets/secrets/examples/bad_placeholder.svg',
          ),
          const SizedBox(height: 24),
          // 三句话
          for (final p in tip.points)
            Padding(
              padding: const EdgeInsets.only(top: 8, bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('· ',
                      style: TextStyle(
                          color: Colors.amberAccent,
                          fontWeight: FontWeight.w700,
                          fontSize: 15)),
                  Expanded(child: Text(p, style: const TextStyle(fontSize: 14))),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

/// 单张示例图（标签 + 9:16 竖版图，和拍摄页取景框同比例）。
class _ExampleColumn extends StatelessWidget {
  const _ExampleColumn({
    required this.label,
    required this.labelColor,
    required this.imagePath,
    required this.placeholder,
  });

  final String label;
  final Color labelColor;
  final String? imagePath;
  final String placeholder;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Text(
            label,
            style: TextStyle(
              color: labelColor,
              fontWeight: FontWeight.w700,
              fontSize: 14,
            ),
          ),
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: AspectRatio(
            aspectRatio: 9 / 16,
            child: imagePath != null
                ? Image.asset(
                    imagePath!,
                    fit: BoxFit.cover,
                    width: double.infinity,
                  )
                : SvgPicture.asset(
                    placeholder,
                    fit: BoxFit.cover,
                    width: double.infinity,
                  ),
          ),
        ),
      ],
    );
  }
}
