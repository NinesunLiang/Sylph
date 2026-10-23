import 'pose.dart';

/// 姿势指导的「人话」翻译表（v0.9.0 环境&机位&姿势 指导）。
///
/// 为什么需要它：`PoseGuidance` 里的 低机位/平机位/四分之三侧/全身 是**术语**。
/// 参考照本身已经演示了效果，但**拍摄者**（往往不是被拍的人）需要知道
/// 手机**具体放哪、怎么拿**才能复现。这张表把术语翻成动作指令：
///
/// - 机位 → 手机高度（相对被拍人的身体部位）
/// - 方向 → 拍摄者站位 + 被拍者朝向（给可操作的「人转/你转」指令）
/// - 景别 → 站位距离（按常见手机镜头的粗略经验值）
///
/// 距离数字是**经验值**（不是光学计算），所以一律用「约」和「左右」表述，
/// 最终站位以拍摄页的实时距离刻度（DistanceAdvice）为准——那是量出来的。

/// 机位 → 手机放多高（相对被拍人）。
Map<String, String> cameraHeightPlain = {
  '低机位': '手机放低到**腰部以下**（蹲下或半蹲，从下往上拍）',
  '平机位': '手机举到**胸口到脸之间**的高度，平着拍，别翘别压',
  '高机位': '手机举到**头顶上方**，从下往上压着拍',
};

/// 朝向 → 谁转、怎么转。
///
/// 术语描述的是**人相对镜头**的朝向，但小白只知道「我站着、你拿着手机」，
/// 所以给指令时说清「人转」还是「你绕」——两者效果相同，任选。
Map<String, String> directionPlain = {
  '正面': '人正对镜头（或者你绕到人的正前方）',
  '四分之三侧': '人身体转 45°（或你绕到人的斜前方 45° 拍）',
  '正侧面': '人侧身 90° 朝镜头（或你绕到人的正侧面）',
  '背面': '人背对镜头（拍的是背影）',
  '背影回头': '人背对镜头、回头看向镜头方向',
};

/// 景别 → 站多远（经验值；最终听拍摄页距离刻度的）。
Map<String, String> framingPlain = {
  '全身': '站远一点，**约 2~3 米**，让头到脚都进画面',
  '七分身': '站到**约 1.5~2 米**，膝盖以上进画面',
  '半身': '近一点，**约 1 米**，腰部以上进画面',
};

/// 一条人话指令（label + 文本）。
class GuidanceLine {
  const GuidanceLine(this.label, this.text);
  final String label;
  final String text;
}


/// 把 [PoseGuidance] 翻成一列人话指令行（详情页「这张怎么拍」卡）。
///
/// 顺序 = 拍摄时的操作顺序：先放手机（高度）→ 再定站位（朝向）→ 再退/进（距离）。
List<GuidanceLine> poseGuidanceLines(PoseGuidance g) {
  final lines = <GuidanceLine>[
    GuidanceLine(
      '机位',
      '${g.cameraHeight} —— ${cameraHeightPlain[g.cameraHeight] ?? ''}',
    ),
  ];
  final dir = directionPlain[g.direction];
  if (dir != null) {
    lines.add(GuidanceLine('站位', '${g.direction} —— $dir'));
  }
  final frame = framingPlain[g.framing];
  if (frame != null) {
    lines.add(GuidanceLine('距离', '${g.framing} —— $frame'));
  }
  return lines;
}
