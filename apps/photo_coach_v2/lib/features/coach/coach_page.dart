import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../app_session.dart';
import '../analysis/face_light.dart';
import '../analysis/body_facts.dart';
import '../analysis/body_scanner.dart';
import '../params/exposure_knowledge.dart';
import '../poses/pose.dart';
import '../params/parameter_advisor.dart';
import '../params/parameter_card.dart';
import '../params/shot_exif.dart';
import 'analyzer.dart';
import 'critique_card.dart';
import 'llm_client.dart';
import 'model_config.dart';
import 'model_config_card.dart';
import 'secrets_page.dart';
import 'suggestion.dart';
import 'video_frame_extractor.dart';
import 'video_frame_source_impl.dart';
import 'video_input.dart';

/// F2 教练页：选图 → 调模型 → 显示格式化建议 → 在图上画虚拟引导。
///
/// v2 S4 迁入后的状态（诚实标注）：
/// - 契约、解析、兜底、渲染 已完成，可用测试证明。
/// - 模型配置（Key/模型/接口地址）**在本页输入，只存你手机本地**
///   （SharedPreferences）——不打进 APK、不进 git、不上传。
///   默认直连 DeepSeek 官方接口（个人自用）；没配 Key 就自动走离线规则，
///   并在界面上明确显示「本地规则」。
/// - 人体测量占位 [NoopBodyScanner]（v1 的谷歌姿态插件在无谷歌服务机型
///   启动即崩，v2 依赖层已排除）→ 本版本没有"端上测量"卡片，不编。
class CoachPage extends StatefulWidget {
  const CoachPage({
    super.key,
    this.config,
    this.session,
    this.frameSource,
    this.bodyScanner = const NoopBodyScanner(),
    this.onNavigateToShoot,
  });

  /// 允许外部注入配置（测试用）。不注入时从本机 SharedPreferences 读
  /// 用户在页面上保存的配置；还没保存过 = 未配置（离线兜底）。
  final ApiConfig? config;

  /// 抽帧来源（测试可注入假的）。默认是「未接解码」的占位实现。
  final VideoFrameSource? frameSource;

  /// 端上人体扫描器（给"量出来的"姿势数据用）。
  final BodyScanner bodyScanner;

  /// 跨页共享状态（可空）。分析成功后会把建议写进去，
  /// 这样「拍摄页的实时引导」能用上 AI 给的目标框；
  /// v0.4.0 起还负责收拍摄页跳系统相机拍完送回来的照片。
  final AppSession? session;

  /// v0.5.0：出方案后的「发送到拍摄页」——点了就切到拍摄 tab。
  /// 由 AppShell 注入；独立运行（测试）时不传，按钮自动隐藏。
  final VoidCallback? onNavigateToShoot;

  @override
  State<CoachPage> createState() => _CoachPageState();
}

class _CoachPageState extends State<CoachPage> {
  final _picker = ImagePicker();
  File? _image;
  AnalysisResult? _result;
  bool _running = false;

  /// 拍摄意图（决定该给什么快门/ISO —— 没有它就没有唯一最优解）。
  ShootingIntent _intent = ShootingIntent.portrait;

  /// 这张照片**实测用过**的 ISO/快门/光圈（EXIF）。读不到就是 null。
  ShotExif? _shot;

  /// **端上量出来的人体事实**。v2 是 Noop 占位 → 永远为 null，
  /// 「端上测量」卡片因此从不显示（数据不存在就不显示，不编）。
  BodyFacts? _bodyFacts;

  /// **这次分析用的目标姿势**（从姿势页送过来的）。
  /// 有了它，AI 给的拍摄方案才是"为了拍出这个姿势"的，而不是泛泛的建议。
  Pose? _analyzedPose;

  /// 上一次已经处理过的「送教练点评」序号（v0.4.0 系统相机回流）。
  int _handledShotSeq = 0;

  // ---- F2.12b 视频 ----
  File? _video;
  MergedVideoAnalysis? _videoResult;
  String? _videoError;
  bool _videoRunning = false;

  // ---- 模型配置（v0.4.0：共享存储 —— 设置页开放了第二个入口）----

  /// 共享模型配置存储：注入了 AppSession 就用它的实例（设置页保存后
  /// 本页立即生效，两页在 IndexedStack 里并存）；否则用本地实例
  /// （独立运行 / 测试，此时 [_ownsStore] 为真，离屏由本页释放）。
  late final ModelConfigStore _store;

  bool _ownsStore = false;

  /// 生效配置：外部注入（测试）> 共享存储（本机已存值；没存过 = 未配置，
  /// 走离线规则兜底）。
  ApiConfig get _config => widget.config ?? _store.effective;

  @override
  void initState() {
    super.initState();
    // v0.4.0：共享 store（读回/保存/监听都由 ModelConfigCard 负责，
    // 这里只决定用谁的实例）；本地实例要由本页释放。
    final injected = widget.session?.modelConfig;
    _store = injected ?? ModelConfigStore();
    _ownsStore = injected == null;
    // v0.4.0：监听拍摄页「送教练点评」（系统相机拍完回来送的那张）。
    // 记录当前序号，之后序号变大才处理，避免 initState 时旧请求重放。
    _handledShotSeq = widget.session?.shotSeq ?? 0;
    widget.session?.addListener(_onSharedChanged);
  }

  @override
  void dispose() {
    widget.session?.removeListener(_onSharedChanged);
    if (_ownsStore) _store.dispose();
    super.dispose();
  }

  /// 共享状态变了。目前只关心一件事：拍摄页送来的照片（v0.4.0）。
  void _onSharedChanged() {
    final shared = widget.session;
    if (shared == null) return;
    if (shared.shotSeq == _handledShotSeq) return;
    _handledShotSeq = shared.shotSeq;
    final file = shared.pendingShot;
    if (file == null) return;
    if (!mounted) return;
    setState(() {
      _image = file;
      _result = null;
      _shot = null;
    });
    // 收走了就清掉，免得下次进页面又弹一次同一张。
    shared.clearPendingShot();
    // 顺势把实测参数读出来（读不到就保持 null，界面上如实说"算不出"）。
    _readShotExif();
    // 一键送教练 = 自动开始点评。只在**模型 Key 已保存**时自动跑：
    // 没保存就留着图，界面上如实显示"未配置模型"，由用户自己点「分析」。
    if (_config.apiKey.isNotEmpty) _analyze();
  }

  Future<void> _pick(ImageSource source) async {
    final picked = await _picker.pickImage(source: source);
    if (picked == null) return;
    setState(() {
      _image = File(picked.path);
      _result = null;
      _shot = null;
    });
    // 顺手把这张照片**实测用过的** ISO/快门/光圈读出来 —— 参数建议要靠它
    // 当基准（读不到就保持 null，界面上会如实说"算不出 ISO"，不猜）。
    await _readShotExif();
  }

  /// 读这张照片的 EXIF（实测用过的 ISO/快门/光圈）。读不到就保持 null。
  Future<void> _readShotExif() async {
    final image = _image;
    if (image == null) return;
    ShotExif? shot;
    try {
      shot = ShotExif.fromBytes(await image.readAsBytes());
    } catch (_) {
      shot = null; // 读不了就是读不了，不能让"选图"这条路挂掉
    }
    if (!mounted) return;
    setState(() => _shot = shot);
  }

  /// 本机能自动设上的参数（给参数卡用；值是实际值，不是建议值）。
  ///
  /// 只给"有具体值"的那一项 —— 卡片上只留一行小字，别堆说明。
  List<String> _appCanSet(AnalysisResult? result) {
    final ev = result?.suggestion.exposure.ev;
    return [
      if (ev != null)
        '曝光补偿 ${ev >= 0 ? '+' : ''}${ev.toStringAsFixed(1)} EV',
    ];
  }

  Future<void> _analyze() async {
    final image = _image;
    if (image == null) return;
    // 姿势页送过来的目标姿势 —— 有为它，拍摄方案才针对那个姿势
    final targetPose = widget.session?.activePose;
    setState(() {
      _running = true;
      _analyzedPose = targetPose;
    });
    // 先过一遍人体扫描器，再连同测量值一起送模型。
    // v2 是 Noop 占位 → 恒为 null → 模型只看图（界面不显示"端上测量"卡）。
    // 将来接纯本地姿态引擎（无谷歌依赖）后，这里自动生效，调用方不用改。
    final facts = await widget.bodyScanner.scanFile(image.path);
    if (!mounted) return;
    setState(() => _bodyFacts = facts);

    final analyzer = SuggestionAnalyzer(config: _config);
    try {
      final result = await analyzer.analyzeFile(image,
          targetPose: targetPose,
          bodyFacts: facts,
          lightDirection: widget.session?.lightDirection);
      if (!mounted) return;
      setState(() => _result = result);
      // 把建议同步到共享状态：拍摄页的实时引导会用它当目标框
      widget.session?.setSuggestion(result.suggestion);
    } finally {
      analyzer.dispose();
      if (mounted) setState(() => _running = false);
    }
  }

  /// 选一段视频。
  Future<void> _pickVideo() async {
    final picked = await _picker.pickVideo(source: ImageSource.gallery);
    if (picked == null) return;
    setState(() {
      _video = File(picked.path);
      _videoResult = null;
      _videoError = null;
    });
  }

  /// 抽帧 → 逐帧分析 → 合并。
  Future<void> _analyzeVideo() async {
    final video = _video;
    if (video == null) return;
    setState(() {
      _videoRunning = true;
      _videoError = null;
    });

    final extractor = VideoFrameExtractor(
      source: widget.frameSource ?? const UnverifiedVideoFrameSource(),
    );
    final analyzer = SuggestionAnalyzer(config: _config);
    try {
      final frames = await extractor.extract(video.path);
      final merged = await analyzer.analyzeFrames(frames);
      if (!mounted) return;
      setState(() {
        _videoResult = merged;
        _videoRunning = false;
      });
      widget.session?.setSuggestion(merged.suggestion);
    } on VideoInputException catch (e) {
      if (!mounted) return;
      setState(() {
        _videoError = e.message;
        _videoRunning = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _videoError = '分析视频时出错：$e';
        _videoRunning = false;
      });
    } finally {
      analyzer.dispose();
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    return Scaffold(
      appBar: AppBar(
        title: const Text('构图教练'),
        actions: [
          IconButton(
            tooltip: '从相册选',
            onPressed: _running ? null : () => _pick(ImageSource.gallery),
            icon: const Icon(Icons.photo_library_outlined),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // v0.6.0 拍照秘诀：纯本地 6 招（3 句话 + 示意图），不烧 token
          const SecretsEntryCard(),
          const SizedBox(height: 16),
          ModelConfigCard(store: _store),
          const SizedBox(height: 16),
          _SourceCard(
            image: _image,
            running: _running,
            onCamera: _running ? null : () => _pick(ImageSource.camera),
            onGallery: _running ? null : () => _pick(ImageSource.gallery),
            onAnalyze: _image == null || _running ? null : _analyze,
          ),
          const SizedBox(height: 16),
          _VideoCard(
            video: _video,
            running: _videoRunning,
            error: _videoError,
            result: _videoResult,
            onPick: _videoRunning ? null : _pickVideo,
            onAnalyze: _video == null || _videoRunning ? null : _analyzeVideo,
          ),
          if (_image != null) ...[
            const SizedBox(height: 16),
            IntentPicker(
              value: _intent,
              onChanged: (v) => setState(() => _intent = v),
            ),
            const SizedBox(height: 8),
            ParameterCard(
              advice: adviseParameters(intent: _intent, shot: _shot),
              appCanSet: _appCanSet(result),
            ),
          ],
          const SizedBox(height: 16),
          if (result != null) ...[
            _SourceBadge(result: result),
            if (_bodyFacts != null) _MeasuredCard(facts: _bodyFacts!),
            if (_analyzedPose != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text('已结合姿势「${_analyzedPose!.title}」给方案',
                    style: const TextStyle(
                        fontSize: 11, color: Colors.lightBlueAccent)),
              ),
            const SizedBox(height: 8),
            // 核心产出先放最前：该站哪 / 朝哪拍 / 优缺点 / 更优怎么拍
            CritiqueCard(s: result.suggestion),
            if (result.suggestion.faceLight != null)
              _FaceLightCard(report: result.suggestion.faceLight!),
            if (widget.onNavigateToShoot != null) ...[
              const SizedBox(height: 8),
              // v0.5.0：方案（站哪/去哪/方向/光/目标框）已经写进共享状态，
              // 拍摄页会自动画上目标框 —— 这里只负责把人带过去。
              FilledButton.icon(
                onPressed: widget.onNavigateToShoot,
                icon: const Icon(Icons.camera_alt),
                label: const Text('发送到拍摄页'),
              ),
            ],
            const SizedBox(height: 8),
            MoveSummary(s: result.suggestion),
            const SizedBox(height: 8),
            _TipsCard(s: result.suggestion),
            if (result.warnings.isNotEmpty) ...[
              const SizedBox(height: 8),
              _WarningsCard(warnings: result.warnings, error: result.error),
            ],
          ] else
            const _EmptyHint(),
        ],
      ),
    );
  }
}

/// F2.12b 视频区块：选视频 → 抽帧分析 → 显示合并结果和每帧情况。
class _VideoCard extends StatelessWidget {
  const _VideoCard({
    required this.video,
    required this.running,
    required this.error,
    required this.result,
    required this.onPick,
    required this.onAnalyze,
  });

  final File? video;
  final bool running;
  final String? error;
  final MergedVideoAnalysis? result;
  final VoidCallback? onPick;
  final VoidCallback? onAnalyze;

  @override
  Widget build(BuildContext context) {
    final r = result;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.videocam_outlined, size: 18),
                const SizedBox(width: 8),
                // 同上：Row 里放裸 Text 不会换行，窄屏上会被裁掉
                const Expanded(
                  child: Text('视频分析（抽帧，最多 3 帧）',
                      style: TextStyle(fontWeight: FontWeight.w600)),
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text('逐帧分析会烧很多 token，所以只抽开头/中间/结尾三帧。',
                style: TextStyle(fontSize: 11, color: Colors.white54)),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: onPick,
                  icon: const Icon(Icons.video_library_outlined, size: 18),
                  label: Text(video == null ? '选一段视频' : '换一个'),
                ),
                FilledButton.icon(
                  onPressed: onAnalyze,
                  icon: running
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.auto_awesome, size: 18),
                  label: Text(running ? '抽帧分析中…' : '分析视频'),
                ),
              ],
            ),
            if (video != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text('已选：${video!.path.split('/').last}',
                    style: const TextStyle(fontSize: 11, color: Colors.white54)),
              ),
            if (error != null)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.orange.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.info_outline,
                          size: 16, color: Colors.orangeAccent),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(error!,
                            style: const TextStyle(fontSize: 12)),
                      ),
                    ],
                  ),
                ),
              ),
            if (r != null) ...[
              const SizedBox(height: 10),
              Text(
                '合并结果（成功 ${r.successCount}/${r.frames.length} 帧）',
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
              ),
              const SizedBox(height: 6),
              for (final n in r.notes)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 1),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('· ', style: TextStyle(color: Colors.white54)),
                      Expanded(
                        child: Text(n,
                            style: const TextStyle(
                                fontSize: 11, color: Colors.white70)),
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 8),
              // ⚠️ 以前这里只显示"合并结果 + 备注"，**建议正文根本没画出来**
              // （只送去了共享状态）。人类明确要求视频也要给出拍摄点/方向/站位，
              // 所以这里补上核心卡。
              const SizedBox(height: 2),
              CritiqueCard(s: r.suggestion),
              const SizedBox(height: 8),
              MoveSummary(s: r.suggestion),
              const SizedBox(height: 8),
              _TipsCard(s: r.suggestion),
              const SizedBox(height: 8),
              // 每帧一行，失败的也列出来（不藏）
              for (final f in r.frames)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 1),
                  child: Row(
                    children: [
                      Icon(
                        f.ok ? Icons.check_circle_outline : Icons.error_outline,
                        size: 13,
                        color: f.ok ? Colors.lightGreenAccent : Colors.orangeAccent,
                      ),
                      const SizedBox(width: 6),
                      Text(f.frame.label,
                          style: const TextStyle(fontSize: 11)),
                      if (!f.ok) ...[
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(f.error ?? '失败',
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  fontSize: 11, color: Colors.orangeAccent)),
                        ),
                      ],
                    ],
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _SourceCard extends StatelessWidget {
  const _SourceCard({
    required this.image,
    required this.running,
    required this.onCamera,
    required this.onGallery,
    required this.onAnalyze,
  });

  final File? image;
  final bool running;
  final VoidCallback? onCamera;
  final VoidCallback? onGallery;
  final VoidCallback? onAnalyze;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          // ⚠️ 空态和有图必须是**两套尺寸**。
          //
          // 之前两种情况共用 `AspectRatio(3/4)`：空态在 500pt 宽的窗口里
          // 撑到 667pt 高，把「拍一张 / 从相册选 / 让 AI 给建议」
          // 全挤到首屏之外（实测按钮底部 735 > 视口 717）。
          // 用户第一眼看到的是巨大空框，很容易以为这页坏了。
          //
          // 教训："能滚到" ≠ "看得见"。空态要紧凑，让操作入口一眼可见。
          if (image == null)
            Container(
              height: 170,
              width: double.infinity,
              margin: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white24),
              ),
              child: const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.add_photo_alternate_outlined,
                        size: 32, color: Colors.white38),
                    SizedBox(height: 8),
                    Text('还没选图',
                        style: TextStyle(color: Colors.white54)),
                    SizedBox(height: 4),
                    Text('选一张照片，我告诉你构图怎么改',
                        style:
                            TextStyle(color: Colors.white24, fontSize: 11)),
                  ],
                ),
              ),
            )
          else
            AspectRatio(
              aspectRatio: 4 / 3,
              child: Image.file(image!, fit: BoxFit.cover),
            ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: onCamera,
                  icon: const Icon(Icons.photo_camera_outlined, size: 18),
                  label: const Text('拍一张'),
                ),
                OutlinedButton.icon(
                  onPressed: onGallery,
                  icon: const Icon(Icons.photo_library_outlined, size: 18),
                  label: const Text('从相册选'),
                ),
                FilledButton.icon(
                  onPressed: onAnalyze,
                  icon: running
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.auto_awesome, size: 18),
                  label: Text(running ? '分析中…' : '让 AI 给建议'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// 面部光影卡片（v0.7.0）。
///
/// 和 [_MeasuredCard] 同一原则：端上**量出来的数字**和模型的判断分开显示。
/// 脸框来自端上检测（默认启发式网格，YuNet 未验证时自动回退），
/// 亮度/对比在手机本地算，不依赖模型。
class _FaceLightCard extends StatelessWidget {
  const _FaceLightCard({required this.report});

  final FaceLightReport report;

  @override
  Widget build(BuildContext context) {
    final src = report.detectorSource;
    final note = report.detectorNote;
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('📐 面部光影（手机量出来的，不是模型判断）',
              style: TextStyle(fontSize: 11, color: Colors.lightGreenAccent)),
          const SizedBox(height: 2),
          Text('${report.verdict.icon} ${report.verdict.label}：${report.summary}',
              style: const TextStyle(fontSize: 12, color: Colors.white)),
          Text('· ${report.measurementLine}',
              style: const TextStyle(fontSize: 11, color: Colors.white70)),
          for (final a in report.advice.take(3))
            Text('· $a',
                style: const TextStyle(fontSize: 11, color: Colors.white70)),
          if (src.isNotEmpty)
            Text('· 脸框来源：$src${note.isNotEmpty ? '（$note）' : ''}',
                style: const TextStyle(fontSize: 10, color: Colors.white38)),
        ],
      ),
    );
  }
}

/// 端上测量值卡片。
///
/// ⚠️ 必须和"模型的判断"**分开显示**：这些是手机姿态模型量出来的数字，
/// 不是审美意见 —— 混在一起会让人以为是 AI 的主观评价。
class _MeasuredCard extends StatelessWidget {
  const _MeasuredCard({required this.facts});

  final BodyFacts facts;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('📐 端上测量（手机量出来的，不是模型判断）',
              style: TextStyle(fontSize: 11, color: Colors.lightGreenAccent)),
          const SizedBox(height: 2),
          for (final l in facts.toFactLines())
            Text('· $l',
                style: const TextStyle(fontSize: 11, color: Colors.white70)),
        ],
      ),
    );
  }
}

class _SourceBadge extends StatelessWidget {
  const _SourceBadge({required this.result});

  final AnalysisResult result;

  @override
  Widget build(BuildContext context) {
    final remote = result.isRemote;
    return Row(
      children: [
        Icon(
          remote ? Icons.auto_awesome : Icons.offline_bolt,
          size: 16,
          color: remote ? Colors.lightBlueAccent : Colors.orangeAccent,
        ),
        const SizedBox(width: 6),
        Text(
          '${result.suggestion.source.label}'
          '${result.elapsed != null ? ' · ${result.elapsed!.inMilliseconds}ms' : ''}'
          '${result.imageBytes > 0 ? ' · 图 ${(result.imageBytes / 1024).toStringAsFixed(0)}KB' : ''}',
          style: const TextStyle(fontSize: 12, color: Colors.white70),
        ),
      ],
    );
  }
}

class MoveSummary extends StatelessWidget {
  const MoveSummary({super.key, required this.s});

  final Suggestion s;

  @override
  Widget build(BuildContext context) {
    final m = s.cameraMove;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.view_in_ar_outlined, size: 18),
                const SizedBox(width: 8),
                // ⚠️ 必须 Expanded：Row 给非弹性子节点的是**无界宽度**约束，
                // 裸 Text 只会排一行、永不换行，超出部分被裁掉
                // （真机实测：右边溢出 550px，「…别放」后面整句看不见）。
                Expanded(
                  child: Text(
                      '怎么动：${m.hint.isEmpty ? "保持不动" : m.hint}',
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '左右摇 ${m.panDeg.toStringAsFixed(1)}° · '
              '上下抬 ${m.tiltDeg.toStringAsFixed(1)}° · '
              '前后走 ${m.dollyM.toStringAsFixed(2)}m · '
              '变焦 ${m.zoom.toStringAsFixed(2)}x',
              style: const TextStyle(fontSize: 12, color: Colors.white70),
            ),
            const SizedBox(height: 6),
            Text(
              '构图：${s.composition.rule}'
              '（把握 ${(s.composition.confidence * 100).toStringAsFixed(0)}%）'
              '${s.composition.horizonTiltDeg.abs() > 1 ? ' · 地平线歪 ${s.composition.horizonTiltDeg.toStringAsFixed(1)}°' : ''}',
              style: const TextStyle(fontSize: 12, color: Colors.white70),
            ),
            const SizedBox(height: 6),
            Text(
              '曝光：EV ${s.exposure.ev >= 0 ? '+' : ''}${s.exposure.ev.toStringAsFixed(1)}'
              '${s.exposure.reason.isEmpty ? '' : ' —— ${s.exposure.reason}'}',
              style: const TextStyle(fontSize: 12, color: Colors.white70),
            ),
          ],
        ),
      ),
    );
  }
}

class _TipsCard extends StatelessWidget {
  const _TipsCard({required this.s});

  final Suggestion s;

  @override
  Widget build(BuildContext context) {
    if (s.tips.isEmpty) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('要点', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            for (final t in s.tips)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('· ', style: TextStyle(color: Colors.white54)),
                    Expanded(child: Text(t)),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _WarningsCard extends StatelessWidget {
  const _WarningsCard({required this.warnings, this.error});

  final List<String> warnings;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.orange.withValues(alpha: 0.12),
      child: ExpansionTile(
        leading: const Icon(Icons.warning_amber, color: Colors.orangeAccent),
        title: Text('有 ${warnings.length} 条降级/解析提示',
            style: const TextStyle(fontSize: 13)),
        subtitle: const Text('点开看细节（不藏问题）',
            style: TextStyle(fontSize: 11, color: Colors.white54)),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        children: [
          for (final w in warnings)
            Align(
              alignment: Alignment.centerLeft,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text('· $w', style: const TextStyle(fontSize: 12)),
              ),
            ),
          if (error != null)
            Align(
              alignment: Alignment.centerLeft,
              child: Text('error: $error',
                  style: const TextStyle(fontSize: 11, color: Colors.white38)),
            ),
        ],
      ),
    );
  }
}

class _EmptyHint extends StatelessWidget {
  const _EmptyHint();

  @override
  Widget build(BuildContext context) {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('怎么用', style: TextStyle(fontWeight: FontWeight.w600)),
            SizedBox(height: 8),
            Text('1. 选一张参考图（或现场拍一张）\n'
                '2. 点「让 AI 给建议」\n'
                '3. 点「发送到拍摄页」\n'
                '4. 到拍摄页，把人放到目标框里，觉得好了按快门'),
            SizedBox(height: 10),
            Text('没配 API Key 也能用，会走本地规则兜底，界面会标明。',
                style: TextStyle(fontSize: 12, color: Colors.white54)),
          ],
        ),
      ),
    );
  }
}
