/// F2 的「接口契约」——大模型输出 ↔ 手机端渲染之间的唯一数据格式。
///
/// 设计要点：
/// - 坐标一律 0–1 归一化（与分辨率解耦，换摄像头/换分辨率不用改）。
/// - 所有字段可缺省，解析失败绝不抛异常给 UI，缺失项由规则兜底填。
/// - `schema_version` 用于将来改格式时做兼容分支。
///
/// 对应提示词（服务端托管，见 server/prompts/composition.md）必须要求模型
/// 只输出该结构的 JSON。
library;

import '../analysis/face_light.dart';

/// 归一化矩形：left/top/width/height ∈ [0,1]。
class Rect01 {
  const Rect01(this.left, this.top, this.width, this.height);

  final double left;
  final double top;
  final double width;
  final double height;

  double get right => left + width;
  double get bottom => top + height;
  double get centerX => left + width / 2;
  double get centerY => top + height / 2;

  /// 解析 `[left, top, width, height]`。
  ///
  /// **契约优先**：提示词（`prompt.dart` 与 `server/prompts/composition.md`）
  /// 明确要求第 3/4 个数是 **width/height**，所以先按这个读 ——
  /// 只要它成立（w>0、h>0、left+w≤1、top+h≤1）就采用。
  ///
  /// ⚠️ 以前这里是反的：只要「第 3 个数 > left」就当成「右边界」，
  /// 于是**大多数守规矩的框都被算错**。真模型实测抓到：
  /// 模型按约定输出人物框 `[0.225, 0.358, 0.113, 0.367]`（宽 0.113、高 0.367），
  /// 旧实现因为 `0.367 > 0.358` 把它当"下边界"，算出**高 0.009** ——
  /// 主体框变成一条细线，实时引导的「现在在哪 / 大小比」全错。
  /// 旧注释写着"提示词要求 width/height，所以牺牲少数派"，
  /// 但代码牺牲的恰恰是**守规矩的多数派**，和注释相反。
  ///
  /// 少数模型确实会写 `[left, top, right, bottom]`。那种情况在
  /// width/height 读法**不成立**时才回退 —— 例如 `[0.2, 0.3, 0.9, 0.8]`：
  /// left+width = 1.1 > 1 不成立 → 按右/下边界读成宽 0.7、高 0.5。
  static Rect01? tryParse(Object? raw) {
    if (raw is! List || raw.length < 4) return null;
    final nums = raw.map(_toDouble).toList();
    if (nums.any((n) => n == null)) return null;
    final l = nums[0]!;
    final t = nums[1]!;
    final a = nums[2]!;
    final b = nums[3]!;

    // 1) 契约读法：[left, top, width, height]（首选）
    if (a > 0 && b > 0 && l + a <= 1.0 && t + b <= 1.0) {
      return Rect01(
        l.clamp(0.0, 1.0),
        t.clamp(0.0, 1.0),
        a.clamp(0.0, 1.0),
        b.clamp(0.0, 1.0),
      );
    }

    // 2) 回退读法：[left, top, right, bottom]（少数模型会这么给）
    final w = a - l;
    final h = b - t;
    if (w > 0 && h > 0 && a <= 1.0 && b <= 1.0) {
      return Rect01(
        l.clamp(0.0, 1.0),
        t.clamp(0.0, 1.0),
        w.clamp(0.0, 1.0),
        h.clamp(0.0, 1.0),
      );
    }

    // 两种读法都不成立 → 返回 null，让调用方走兜底（不编造一个框）
    return null;
  }

  List<double> toJson() => [left, top, width, height];

  static double? _toDouble(Object? v) {
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }

  @override
  String toString() =>
      'Rect01(${left.toStringAsFixed(2)}, ${top.toStringAsFixed(2)}, '
      '${width.toStringAsFixed(2)}, ${height.toStringAsFixed(2)})';
}

/// 构图判定。
class CompositionHint {
  const CompositionHint({
    required this.rule,
    this.confidence = 0.5,
    this.horizonTiltDeg = 0,
  });

  /// 例：rule_of_thirds / centered / leading_lines / symmetry / golden_ratio
  final String rule;
  final double confidence;

  /// 地平线倾斜角，正数=向右倾斜。
  final double horizonTiltDeg;

  static CompositionHint fromJson(Map<String, Object?> j) => CompositionHint(
        rule: (j['rule'] as String?)?.trim().isNotEmpty == true
            ? (j['rule'] as String).trim()
            : 'unknown',
        confidence: _d(j['confidence']) ?? 0.5,
        horizonTiltDeg: _d(j['horizon_tilt_deg']) ?? 0,
      );

  Map<String, Object?> toJson() => {
        'rule': rule,
        'confidence': confidence,
        'horizon_tilt_deg': horizonTiltDeg,
      };
}

/// 主体（人/物）当前位置与建议位置。
class SubjectHint {
  const SubjectHint({
    this.label = 'subject',
    this.currentBox,
    this.targetBox,
  });

  final String label;

  /// 当前在画面里的位置（模型观看到的）。
  final Rect01? currentBox;

  /// 建议移动到的位置。
  final Rect01? targetBox;

  static SubjectHint fromJson(Map<String, Object?> j) => SubjectHint(
        label: (j['label'] as String?) ?? 'subject',
        currentBox: Rect01.tryParse(j['current_box']),
        targetBox: Rect01.tryParse(j['target_box']),
      );

  Map<String, Object?> toJson() => {
        'label': label,
        if (currentBox != null) 'current_box': currentBox!.toJson(),
        if (targetBox != null) 'target_box': targetBox!.toJson(),
      };
}

/// 相机该怎么动。手机端把它画成箭头和提示文字。
class CameraMoveHint {
  const CameraMoveHint({
    this.panDeg = 0,
    this.tiltDeg = 0,
    this.dollyM = 0,
    this.zoom = 1.0,
    this.hint = '',
  });

  /// 左右摇（负=向左）。
  final double panDeg;

  /// 上下摇（正=向上抬）。
  final double tiltDeg;

  /// 前后走（负=向后退）。
  final double dollyM;

  final double zoom;
  final String hint;

  bool get isNoop =>
      panDeg.abs() < 0.5 &&
      tiltDeg.abs() < 0.5 &&
      dollyM.abs() < 0.02 &&
      (zoom - 1.0).abs() < 0.02;

  static CameraMoveHint fromJson(Map<String, Object?> j) => CameraMoveHint(
        panDeg: _d(j['pan_deg']) ?? 0,
        tiltDeg: _d(j['tilt_deg']) ?? 0,
        dollyM: _d(j['dolly_m']) ?? 0,
        zoom: _d(j['zoom']) ?? 1.0,
        hint: (j['hint'] as String?) ?? '',
      );

  Map<String, Object?> toJson() => {
        'pan_deg': panDeg,
        'tilt_deg': tiltDeg,
        'dolly_m': dollyM,
        'zoom': zoom,
        'hint': hint,
      };
}

/// 曝光建议。直接接到 F1 的相机参数面板。
class ExposureHint {
  const ExposureHint({this.ev = 0, this.reason = ''});

  /// 曝光补偿，单位 EV。
  final double ev;
  final String reason;

  static ExposureHint fromJson(Map<String, Object?> j) => ExposureHint(
        ev: _d(j['ev']) ?? 0,
        reason: (j['reason'] as String?) ?? '',
      );

  Map<String, Object?> toJson() => {'ev': ev, 'reason': reason};
}

/// 一条完整的建议。
/// 一个拍照要素的体检结论。
enum ElementVerdict {
  /// 这一项做得好。
  good('✅'),

  /// 这一项有问题（必须给 advice）。
  problem('⚠️'),

  /// 看不清 / 这张照片里没有这一项 —— **不评**，别硬凑。
  unclear('—');

  const ElementVerdict(this.mark);

  final String mark;

  /// 严重程度（problem > good > unclear）。多帧合并时"取更严重的那个"用。
  int get severity => switch (this) {
        ElementVerdict.problem => 2,
        ElementVerdict.good => 1,
        ElementVerdict.unclear => 0,
      };

  static ElementVerdict parse(Object? v) {
    final s = v is String ? v.trim().toLowerCase() : '';
    return switch (s) {
      'good' || 'ok' || 'fine' => ElementVerdict.good,
      'problem' || 'bad' || 'issue' => ElementVerdict.problem,
      _ => ElementVerdict.unclear,
    };
  }
}

/// 「拍好照片的要素」逐项体检。
///
/// 人类 2026-09-20：「就是要把拍好照片的要素都做好」。
/// 要素就那十来项（光/机位/方向/构图/姿势/表情/眼神/背景/清晰度/色彩/时机…），
/// App 本地只能测出其中几项，其余靠**模型看图**来判 —— 所以这里要的是
/// 「逐项表态」，而不是泛泛的几句建议。
///
/// ⚠️ [verdict] 为 [ElementVerdict.unclear] 时表示"看不出来/没有这一项"，
/// 这是**允许且鼓励**的答案：不许为了凑满清单而编。
class ElementCheck {
  const ElementCheck({
    required this.name,
    required this.verdict,
    this.advice,
    this.anchor,
  });

  /// 要素名（模型给的中文名，直接显示）。
  final String name;

  final ElementVerdict verdict;

  /// 有问题时**必须**给「更优怎么做」。
  final String? advice;

  /// **画面锚点**（0-1 归一化框）：这一项在画面上的位置。
  ///
  /// 有了它，"背景右边有杂物" 才能真的**画在右边**，而不是只留一句文字。
  /// 约定：`眼神` 的锚点给的是「**应该看向**的位置」，不是眼睛现在的位置。
  /// 给不出位置就不给（null）—— 那样只在清单里显示文字。
  final Rect01? anchor;

  factory ElementCheck.fromJson(Map<String, Object?> j) => ElementCheck(
        name: _str(j['name']) ?? '',
        verdict: ElementVerdict.parse(j['verdict']),
        advice: _str(j['advice']),
        anchor: Rect01.tryParse(j['anchor']),
      );

  Map<String, Object?> toJson() => {
        'name': name,
        'verdict': verdict.name,
        'advice': advice,
        'anchor': anchor == null
            ? null
            : [anchor!.left, anchor!.top, anchor!.width, anchor!.height],
      };
}

/// 带画面锚点的要素，编号从 **1** 开始（编号 = 它在完整清单里的序号）。
///
/// 叠加引导（画框）和结果清单（列文字）都用这一个函数取编号，
/// 这样"图上第 2 个框"和"清单第 2 条"永远是同一件事。
List<(int, ElementCheck)> anchoredElements(Suggestion s) {
  final out = <(int, ElementCheck)>[];
  for (var i = 0; i < s.elements.length; i++) {
    final e = s.elements[i];
    if (e.anchor != null) out.add((i + 1, e));
  }
  return out;
}

/// AI 给的「站哪、举多高、朝哪个方向拍」。
///
/// 这是 App 的**核心建议**（人类 2026-09-20 明确定位：拍摄建议 = 拍摄位置
/// （位置和高度）+ 拍摄方向；相机参数只是基础初始化）。
/// 相机参数能设的就那几项，而"你该站到哪"才是一张照片成败的关键 ——
/// 也是用户自己最难看出来、机器最容易算明白的部分。
class ShootingPlan {
  const ShootingPlan({
    this.lighting,
    this.position,
    this.direction,
    this.subjectPosition,
  });

  /// **光照**：现在光是什么情况（光源方位 / 硬光柔光 / 顺侧逆光）+ 怎么利用。
  ///
  /// 它是另外三项的**依据** —— 所以排在最前，让用户看懂"为什么站那儿"。
  final String? lighting;

  /// **拍摄点**：站到哪 + 相机放在什么高度（例如「退后一步，手机降到胸口高度」）。
  final String? position;

  /// **机位方向**：朝哪个方向/角度拍（例如「从主体左前方 45°，平视」）。
  final String? direction;

  /// **被拍人物的站位**：人站到哪、面朝哪（例如「让人往窗边挪半步，侧脸对光」）。
  final String? subjectPosition;

  bool get isEmpty =>
      _blank(lighting) &&
      _blank(position) &&
      _blank(direction) &&
      _blank(subjectPosition);

  static bool _blank(String? s) => s == null || s.trim().isEmpty;

  factory ShootingPlan.fromJson(Map<String, Object?> j) => ShootingPlan(
        lighting: _str(j['lighting']),
        position: _str(j['position']),
        direction: _str(j['direction']),
        subjectPosition: _str(j['subject_position']),
      );

  Map<String, Object?> toJson() => {
        'lighting': lighting,
        'position': position,
        'direction': direction,
        'subject_position': subjectPosition,
      };
}

/// 一条「差在哪 + 更优怎么做」。
///
/// [problem] 是问题（客观描述），[better] 是**更优的选择**（可执行的动作）。
/// 两者都必须来自模型的判断，因此界面上要明确标注这是「模型判断」。
class CritiqueItem {
  const CritiqueItem({required this.problem, required this.better});

  final String problem;
  final String better;

  factory CritiqueItem.fromJson(Map<String, Object?> j) => CritiqueItem(
        problem: _str(j['problem']) ?? '',
        better: _str(j['better']) ?? '',
      );

  Map<String, Object?> toJson() => {
        'problem': problem,
        'better': better,
      };
}

String? _str(Object? v) {
  if (v is! String) return null;
  final t = v.trim();
  return t.isEmpty ? null : t;
}

class Suggestion {
  const Suggestion({
    this.schemaVersion = '1.0',
    required this.composition,
    required this.subject,
    required this.cameraMove,
    required this.exposure,
    this.tips = const [],
    this.shootingPlan = const ShootingPlan(),
    this.pros = const [],
    this.critiques = const [],
    this.elements = const [],
    this.source = SuggestionSource.ruleFallback,
    this.rawModelText,
    this.errorCode,
    this.faceLight,
  });

  final String schemaVersion;
  final CompositionHint composition;
  final SubjectHint subject;
  final CameraMoveHint cameraMove;
  final ExposureHint exposure;
  final List<String> tips;

  /// **核心**：该站哪、什么高度、朝哪个方向拍。
  final ShootingPlan shootingPlan;

  /// 这张照片**已经做对了什么**（模型判断）。
  final List<String> pros;

  /// **差在哪 + 更优怎么做**（模型判断）。
  final List<CritiqueItem> critiques;

  /// **全部要素的逐项体检**（模型判断）—— 这是"把拍好照片的要素都做好"的落点。
  /// 界面默认只显示最关键的两三条，其余收起来可展开。
  final List<ElementCheck> elements;

  /// 这条建议是谁给的：真模型 / 本地规则兜底。
  /// 必须显示给用户，不能让兜底结果冒充模型结论。
  final SuggestionSource source;

  /// 模型原始文本，排错用。
  final String? rawModelText;

  /// 技术性的错误/降级原因（如 `HTTP 500`、`no_api_config`）。
  ///
  /// **这是给开发者排查用的，不是给用户看的。**
  /// 用户可见的文案在 [tips] 里，必须是中文人话。
  /// 分开存的原因见 `test/offline_tip_engine_tdd_test.dart`：
  /// 之前把技术错误原文直接拼进 tips，用户在"给建议"卡片里
  /// 看到的是 `SocketException: Failed host lookup`。
  final String? errorCode;

  /// **本地测量**的面部光影报告（v0.7.0，拍后教练页闭环）。
  ///
  /// 这是**纯本地**产物：由 `face_light.dart` 从 RgbGrid 算出，
  /// 与模型判断无关 —— 所以**不进 toJson/parse**（模型契约零改动），
  /// 也不进 S2 的 5 规则之外的任何通道。视频帧流不测（S2 范围：只做图像流）。
  final FaceLightReport? faceLight;

  /// 附带本地面部光影报告，返回新实例（Suggestion 不可变，无 copyWith）。
  ///
  /// 模型兜底路径也要带上它：卡片展示不依赖模型是否在线。
  Suggestion withFaceLight(FaceLightReport? f) => Suggestion(
        schemaVersion: schemaVersion,
        composition: composition,
        subject: subject,
        cameraMove: cameraMove,
        exposure: exposure,
        tips: tips,
        shootingPlan: shootingPlan,
        pros: pros,
        critiques: critiques,
        elements: elements,
        source: source,
        rawModelText: rawModelText,
        errorCode: errorCode,
        faceLight: f,
      );

  /// 容错解析：字段缺失就用默认值补齐，永远返回一个可渲染的 Suggestion。
  /// 返回 (suggestion, 解析警告列表)。
  static (Suggestion, List<String>) parse(Object? decoded,
      {String? rawText}) {
    final warnings = <String>[];
    if (decoded is! Map) {
      warnings.add('顶层不是 JSON 对象，已整体走兜底');
      return (
        Suggestion.fallback(reason: '模型输出无法解析为 JSON'),
        warnings,
      );
    }
    final j = decoded.cast<String, Object?>();

    final version = (j['schema_version'] as String?) ?? '1.0';
    if (version != '1.0') {
      warnings.add('schema_version=$version 与客户端 1.0 不一致，按 1.0 尽力解析');
    }

    final comp = j['composition'];
    final subj = j['subject'];
    final move = j['camera_move'];
    final exp = j['exposure'];
    final rawTips = j['tips'];
    final rawPlan = j['shooting_plan'];
    final rawPros = j['pros'];
    final rawCritiques = j['critiques'];

    if (comp is! Map) warnings.add('缺 composition，用默认值');
    if (subj is! Map) warnings.add('缺 subject，用默认值');
    if (move is! Map) warnings.add('缺 camera_move，用默认值');
    if (exp is! Map) warnings.add('缺 exposure，用默认值');
    // 新增字段缺失**不算问题**（老提示词/老模型不会给），静默用空值即可 ——
    // 但绝不替它编内容。
    if (rawPlan != null && rawPlan is! Map) {
      warnings.add('shooting_plan 不是对象，已忽略');
    }

    final tips = <String>[];
    if (rawTips is List) {
      for (final t in rawTips) {
        if (t is String && t.trim().isNotEmpty) tips.add(t.trim());
      }
    } else if (rawTips != null) {
      warnings.add('tips 不是数组，已忽略');
    }

    final pros = <String>[];
    if (rawPros is List) {
      for (final t in rawPros) {
        if (t is String && t.trim().isNotEmpty) pros.add(t.trim());
      }
    }

    final critiques = <CritiqueItem>[];
    if (rawCritiques is List) {
      for (final c in rawCritiques) {
        if (c is Map) {
          final item = CritiqueItem.fromJson(c.cast<String, Object?>());
          // problem 和 better 都为空 = 模型给了个空壳，直接丢掉
          if (item.problem.isNotEmpty || item.better.isNotEmpty) {
            critiques.add(item);
          }
        }
      }
    }

    final elements = <ElementCheck>[];
    final rawElements = j['elements'];
    if (rawElements is List) {
      for (final e in rawElements) {
        if (e is Map) {
          final item = ElementCheck.fromJson(e.cast<String, Object?>());
          // 没名字的空壳直接丢掉（宁可少一条，也不给用户看空白行）
          if (item.name.isNotEmpty) elements.add(item);
        }
      }
    }

    final s = Suggestion(
      schemaVersion: '1.0',
      composition: comp is Map
          ? CompositionHint.fromJson(comp.cast<String, Object?>())
          : const CompositionHint(rule: 'unknown'),
      subject: subj is Map
          ? SubjectHint.fromJson(subj.cast<String, Object?>())
          : const SubjectHint(),
      cameraMove: move is Map
          ? CameraMoveHint.fromJson(move.cast<String, Object?>())
          : const CameraMoveHint(),
      exposure: exp is Map
          ? ExposureHint.fromJson(exp.cast<String, Object?>())
          : const ExposureHint(),
      tips: tips,
      shootingPlan: rawPlan is Map
          ? ShootingPlan.fromJson(rawPlan.cast<String, Object?>())
          : const ShootingPlan(),
      pros: pros,
      critiques: critiques,
      elements: elements,
      source: SuggestionSource.visionModel,
      rawModelText: rawText,
    );
    return (s, warnings);
  }

  Map<String, Object?> toJson() => {
        'schema_version': schemaVersion,
        'shooting_plan': shootingPlan.toJson(),
        'pros': pros,
        'critiques': [for (final c in critiques) c.toJson()],
        'elements': [for (final e in elements) e.toJson()],
        'composition': composition.toJson(),
        'subject': subject.toJson(),
        'camera_move': cameraMove.toJson(),
        'exposure': exposure.toJson(),
        'tips': tips,
      };

  /// 兜底：模型不可用时也给出「至少不误导」的建议。
  static Suggestion fallback({String reason = ''}) => Suggestion(
        composition: const CompositionHint(rule: 'rule_of_thirds'),
        subject: const SubjectHint(),
        cameraMove: const CameraMoveHint(
          hint: '把主体放在画面左/右三分之一线上，头顶留一点空隙',
        ),
        exposure: const ExposureHint(ev: 0, reason: '未知测光，建议先拍一张再调'),
        tips: [
          if (reason.isNotEmpty) '（规则兜底：$reason）',
          '手机端会画网格线，把主体对到交叉点上',
          '地平线尽量放平，或放在上/下三分之一处',
        ],
        source: SuggestionSource.ruleFallback,
      );
}

enum SuggestionSource {
  /// 线上视觉模型给的。
  visionModel,

  /// 本地规则兜底（模型挂了/没配 key）。
  ruleFallback;

  String get label => switch (this) {
        SuggestionSource.visionModel => 'AI 建议',
        SuggestionSource.ruleFallback => '本地规则（离线兜底）',
      };
}

double? _d(Object? v) {
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v);
  return null;
}
