import '../analysis/body_facts.dart';
import '../analysis/face_light.dart';
import '../poses/pose.dart';
import 'suggestion.dart';

/// 提示词 skill —— F2 的「大脑说明书」。
///
/// ⚠️ 这里有一份 [defaultPrompt] 作为内置兜底；正式环境应该由服务端下发
/// （[PromptProvider]），这样调提示词不用重新发版 App。
///
/// 契约：模型必须只输出 suggestion.dart 里定义的 JSON 结构。
/// 改这里 = 改契约，必须同步改 [Suggestion.parse]。
class CompositionPrompt {
  static const schemaSpec = '''
{
  "schema_version": "1.0",
  "shooting_plan": {
    "lighting": "现在光是什么情况 + 怎么利用（光源方位/硬柔/顺侧逆光）",
    "position": "拍摄点：你站到哪 + 相机什么高度",
    "direction": "机位方向：朝哪个方向、什么角度拍",
    "subject_position": "被拍的人站到哪、面朝哪"
  },
  "pros": ["这张已经做对了什么（1-2 条）"],
  "critiques": [ { "problem": "差在哪", "better": "更优的选择：具体怎么改" } ],
  "elements": [
    { "name": "要素名（中文，见下表）", "verdict": "good|problem|unclear", "advice": "problem 时必填：更优怎么做" }
  ],
  "composition": { "rule": "rule_of_thirds|centered|leading_lines|symmetry|golden_ratio|other", "confidence": 0.0-1.0, "horizon_tilt_deg": number },
  "subject": { "label": "string", "current_box": [left, top, width, height], "target_box": [left, top, width, height] },
  "camera_move": { "pan_deg": number, "tilt_deg": number, "dolly_m": number, "zoom": number, "hint": "中文一句话" },
  "exposure": { "ev": number, "reason": "中文一句话" },
  "tips": ["中文短句", "中文短句"]
}''';

  static const defaultPrompt = '''
你是一位严谨的摄影指导。用户给你一张参考照片，你要输出「怎么拍得更好」的可执行建议。

【最重要的事（先回答这四项，顺序不能乱）】
用户最需要、也最难自己看出来的，是「光怎么用、人站哪、我去哪拍、朝哪拍」。
1. shooting_plan.lighting：先判断光 —— 光源在哪个方位、是硬光还是柔光、
   顺光/侧光/逆光。再给一句怎么利用（例如「光从左窗进来，侧光；让人侧脸对光」）。
2. shooting_plan.subject_position：**被拍的人**站到哪、面朝哪
   （例如「往窗边挪半步，脸朝窗户 45°」）。这是由光照推出来的。
3. shooting_plan.position：**你（拍摄者）**站到哪、手机放什么高度
   （站直 / 半蹲 / 蹲下 / 举高过头）。例如「站到人斜前方两步，手机降到胸口高度」。
4. shooting_plan.direction：机位朝哪个方向、什么角度（正面 / 侧面 / 45° / 背身；
   平视 / 俯拍 / 仰拍）。
四项必须**互相一致**：光照决定人站哪，人站哪+你的位置决定机位方向。
每项一句话，具体到能照着做，不超过 30 字。
然后给 critiques：**差在哪 + 更优怎么做**（1-3 条，problem 说清问题，
better 给出可执行动作）；用 pros 写出这张**已经做对了什么**（1-2 条，要具体）。

【最后：逐项体检整套"拍好照片的要素"（elements）】
从上表里挑**这张照片里看得出来的**要素逐项表态，最多 8 项：
  光（光源方位/硬柔/顺侧逆光）、机位、方向、构图、姿势、表情、眼神、
  背景杂物、清晰度、色彩、时机/瞬间、服装道具
- verdict 只有三种：good（做得好）/ problem（有问题）/ unclear（看不出来或
  这张里没有这一项）。
- **problem 必须给 advice**（具体怎么改）；good 可以不给。
- unclear 是**允许且鼓励**的答案：看不出来就写 unclear，**不许为了凑满清单而编**。
- 如果这一项在画面上有**具体位置**，请给 anchor = [left, top, width, height]
  （0-1 归一化，左上角为原点）：例如「背景杂物」框住那个垃圾桶、
  「构图」框住主体。**约定：`眼神` 的 anchor 给"应该看向"的位置**，
  而不是眼睛现在的位置（这样 App 才能在画面上画一个箭头指过去）。
  给不出位置就省略 anchor，不要瞎给。
- 这一项和 pros/critiques 的分工：pros/critiques 只放**最重要的那几条**，
  elements 是**完整清单**。

【输出格式】只输出一个 JSON 对象，禁止任何解释文字、禁止 markdown 代码围栏。结构如下：
$schemaSpec

【坐标规则】
- 所有坐标是 0-1 归一化，[left, top, width, height]，左上角为 (0,0)。
- current_box = 你在这张图里看到的主体所在位置。
- target_box = 按你推荐的构图，主体应该移动到什么位置。

【判定规则】
- pan_deg：相机需要左右摇动多少度才能达到 target_box，向左为负。
- tilt_deg：相机需要上下抬多少度，向上为正。
- dolly_m：相机需要前后移动多少米，向后退为负。
- zoom：建议的变焦倍率，1.0 表示不变。
- exposure.ev：曝光补偿建议，正数更亮，负数更暗；并给出理由。
- 如果当前构图已经很好，camera_move 全部填 0 / 1.0，并在 hint 里说明「保持不动」。
- 不要编造你看不见的东西。看不清主体就如实降低 confidence；
  pros / critiques / shooting_plan 看不清就少写或不写，**不许编**。

【风格】
- 所有 hint / reason / tips / pros / critiques 用简体中文，短、具体、可执行。
- shooting_plan 的四项（lighting / position / direction / subject_position）
  各自不超过 30 字。
- position **必须包含手机的具体高度**（例如「降到胸口高度」「举到头顶」），
  只说「站到哪」不算数 —— 高度是新手最容易猜错的参数。
- tips 最多 3 条。
''';

  /// 提示词来源：内置 或 服务端下发。
  static String resolve(String? remotePrompt) {
    final p = remotePrompt?.trim();
    if (p == null || p.isEmpty) return defaultPrompt;
    return p;
  }

  /// 把**端上量出来的人体事实**拼进提示词。
  ///
  /// 这是"用 ML Kit 而不是让模型瞎猜"的落点：模型看到的不是照片里那个人，
  /// 而是"肩线倾斜 6.2°、眼睛在画面 22% 高度"这类**测量值**。
  static String bodyFactsSection(BodyFacts? facts) {
    if (facts == null || facts.isEmpty) return '';
    return '\n${facts.toPromptText()}';
  }

  /// 把「用户想拍的姿势」拼进提示词 —— **pose 教程 × 拍摄方案的打通点**。
  ///
  /// 没有这段时，模型给的只是"这张照片怎么改"；有了这段，拍摄方案必须
  /// **服务于"怎么拍出这个姿势"**：人站哪、你站哪、朝哪拍、光怎么用。
  /// 把**端上量出来的面部光影**拼进提示词（v0.7.0 拍后教练页闭环）。
  ///
  /// 传 null 返回空串 —— 视频帧流不传，行为与 v0.6.0 完全一致。
  /// 有脸：给出 9 项测量值，让模型在 shooting_plan.lighting 上**基于测量**判断；
  /// 无脸：只给一句话，请模型自行判断（不编测量值）。
  static String faceLightSection(FaceLightReport? report) {
    if (report == null) return '';
    final s = report.stats;
    final body = s != null
        ? '${s.promptText}\n'
              '请让 shooting_plan.lighting 与 elements 的「光」这一项**以上面的测量值为准**'
              '（不要凭目测推翻测量）；如果是逆光，subject_position 给出可执行的人站位调整。'
        : '【本地测量·面部光影】没找到人脸。'
              '请让 shooting_plan.lighting 基于你对照片的目测判断'
              '（看不清就写 unclear，不许编测量值）。';
    return '\n$body';
  }

  /// 把「用户声明的光线方向」拼进提示词（v0.9.0 环境指导）。
  ///
  /// 来自拍摄页的顺光/侧光/逆光按钮。没选 → 空串，prompt 与之前逐字一致。
  static String lightDirectionSection(FaceLightChoice? choice) {
    if (choice == null) return '';
    return '\n${choice.promptText}';
  }

  static String poseSection(Pose? pose) {
    if (pose == null) return '';
    final tips = pose.tips.isEmpty ? '' : '\n姿势要点：${pose.tips.join('；')}';
    return '''

【用户想拍的姿势 —— 拍摄方案必须服务于它】
姿势：${pose.title}
场景：${pose.scene}$tips
请让 shooting_plan 的四项都**针对这个姿势**说清楚：
- subject_position：要摆出这个姿势，**被拍的人**站到哪、面朝哪
- position：**你**站到哪、手机举多高（这个姿势常需要特定高度，例如要显腿长就得放低）
- direction：机位朝哪个方向、什么角度；并用 lighting 说明光怎么用
- elements 里**必须**包含「姿势」这一项：当前照片的姿势和目标姿势差在哪、怎么摆。
''';
  }
}

/// 提示词可插拔，方便以后从服务端热更。
abstract class PromptProvider {
  Future<String> load();
}

class BuiltInPromptProvider implements PromptProvider {
  const BuiltInPromptProvider();

  @override
  Future<String> load() async => CompositionPrompt.defaultPrompt;
}
