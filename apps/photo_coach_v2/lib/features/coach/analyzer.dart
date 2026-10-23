import 'dart:io';

import 'image_compressor.dart';
import 'llm_client.dart';
import 'offline_tip_engine.dart';
import 'prompt.dart';
import '../analysis/body_facts.dart';
import '../analysis/face_detector.dart';
import '../analysis/face_light.dart';
import '../poses/pose.dart';
import 'suggestion.dart';
import 'video_input.dart';

/// 分析结果：永远带一个可渲染的 [suggestion]，绝不抛异常给 UI。
class AnalysisResult {
  const AnalysisResult({
    required this.suggestion,
    required this.warnings,
    required this.usedFallback,
    this.imageBytes = 0,
    this.imageSize = '',
    this.error,
    this.elapsed,
  });

  final Suggestion suggestion;

  /// 解析/降级过程中的警告，UI 上可展开给用户看（不藏事）。
  final List<String> warnings;

  /// true = 模型这条路失败了，用的是离线规则。
  final bool usedFallback;

  final int imageBytes;
  final String imageSize;
  final String? error;
  final Duration? elapsed;

  bool get isRemote => !usedFallback && suggestion.source == SuggestionSource.visionModel;
}

/// F2 的编排器：压缩 → 调模型 → 解析 JSON → （失败则）离线兜底。
///
/// 单一职责，UI 只调这一个入口。
class SuggestionAnalyzer {
  SuggestionAnalyzer({
    required this.config,
    PromptProvider? promptProvider,
    this.compressor = const ImageCompressor(),
    this.offline = const OfflineTipEngine(),
    VisionLlmClient? client,
  })  : _prompts = promptProvider ?? const BuiltInPromptProvider(),
        _client = client ??
            (config.isUsable ? VisionLlmClient(config: config) : null);

  final ApiConfig config;
  final PromptProvider _prompts;
  final ImageCompressor compressor;
  final OfflineTipEngine offline;
  final VisionLlmClient? _client;

  Future<AnalysisResult> analyzeFile(File file,
      {Pose? targetPose,
      BodyFacts? bodyFacts,
      FaceLightChoice? lightDirection,
      FaceDetector faceDetector = const FaceDetector()}) async {
    final payload = await compressor.compressFile(file);
    // v0.7.0 拍后教练页闭环：本地量面部光影（YuNet/启发式 → 网格 → 五档判定）。
    // 只走图像流：任何异常 → null，功能静默缺席，主流程不受影响。
    FaceLightReport? faceLight;
    try {
      final (grid, det) =
          await faceDetector.detectWithGrid(payload.bytes);
      faceLight = faceLightAnalyzer.analyze(grid, det);
    } catch (_) {
      faceLight = null;
    }
    return analyzePayload(payload,
        targetPose: targetPose,
        bodyFacts: bodyFacts,
        faceLight: faceLight,
        lightDirection: lightDirection);
  }

  /// [targetPose] = 用户想拍的姿势。给了它，模型给的拍摄方案就会**服务于这个
  /// 姿势**（人站哪/你站哪/朝哪拍/光怎么用）—— 这是 pose 教程 × 拍摄方案的打通点。
  /// [faceLight] = 端上量出来的面部光影报告（由 [analyzeFile] 算好传入）。
  /// 视频帧流（[analyzeFrames]）不传 → 提示词与 v0.6.0 逐字一致。
  ///
  /// 无论模型这条路成不成（兜底/解析失败/异常），报告都挂到 suggestion 上：
  /// 它是**本地测量**，不依赖模型在线。
  /// [lightDirection] = 用户在拍摄页声明的光线方向（v0.9.0；null = 没选，
  /// 视频帧流不传 → 提示词与 v0.8.x 逐字一致）。
  Future<AnalysisResult> analyzePayload(ImagePayload payload,
      {Pose? targetPose,
      BodyFacts? bodyFacts,
      FaceLightReport? faceLight,
      FaceLightChoice? lightDirection}) async {
    final sw = Stopwatch()..start();
    final meta = {
      'imageBytes': payload.byteSize,
      'imageSize': payload.width > 0 ? '${payload.width}x${payload.height}' : '原始尺寸',
    };

    final client = _client;
    if (client == null) {
      sw.stop();
      return AnalysisResult(
        suggestion: offline.suggest(
          reason: '还没接上 AI 模型',
          detail: 'no_api_config: endpoint=${config.endpoint.isEmpty ? "(空)" : "已填"} '
              'mode=${config.mode.name}',
        ).withFaceLight(faceLight),
        warnings: const ['未配置 API（endpoint/apiKey 为空），已走离线规则'],
        usedFallback: true,
        error: 'no_api_config',
        elapsed: sw.elapsed,
        imageBytes: meta['imageBytes']! as int,
        imageSize: meta['imageSize']! as String,
      );
    }

    try {
      final prompt = CompositionPrompt.resolve(await _prompts.load()) +
          CompositionPrompt.poseSection(targetPose) +
          CompositionPrompt.bodyFactsSection(bodyFacts) +
          CompositionPrompt.faceLightSection(faceLight) +
          CompositionPrompt.lightDirectionSection(lightDirection);
      final raw = await client.analyzeImage(
        dataUrl: payload.toDataUrl(),
        prompt: prompt,
      );
      final (suggestion, warnings) =
          Suggestion.parse(raw.decodedJson, rawText: raw.text);
      sw.stop();

      if (raw.decodedJson == null) {
        // 模型回了话但抠不出 JSON —— 这是提示词/模型的问题，必须暴露
        warnings.insert(0, '模型输出无法解析成 JSON，已改用离线规则');
        return AnalysisResult(
          suggestion: offline.suggest(
            reason: 'AI 返回的内容不符合约定格式',
            detail: 'unparsable_model_output: ${_truncateText(raw.text)}',
          ).withFaceLight(faceLight),
          warnings: warnings,
          usedFallback: true,
          error: 'unparsable_model_output',
          elapsed: sw.elapsed,
          imageBytes: meta['imageBytes']! as int,
          imageSize: meta['imageSize']! as String,
        );
      }

      return AnalysisResult(
        suggestion: suggestion.withFaceLight(faceLight),
        warnings: warnings,
        usedFallback: false,
        elapsed: sw.elapsed,
        imageBytes: meta['imageBytes']! as int,
        imageSize: meta['imageSize']! as String,
      );
    } catch (e) {
      sw.stop();
      return AnalysisResult(
        suggestion: offline.suggest(
          reason: 'AI 服务暂时不可用',
          detail: '$e',
        ).withFaceLight(faceLight),
        warnings: ['线上调用异常：$e'],
        usedFallback: true,
        error: e.toString(),
        elapsed: sw.elapsed,
        imageBytes: meta['imageBytes']! as int,
        imageSize: meta['imageSize']! as String,
      );
    }
  }

  void dispose() => _client?.close();

  /// F2.12b：分析视频抽出来的多帧，合并成一条建议。
  ///
  /// 每帧走跟单图完全一样的链路（压缩 → 模型 → 解析 → 兜底），
  /// 然后由 [mergeSuggestions] 合并。合并规则见 video_input.dart。
  Future<MergedVideoAnalysis> analyzeFrames(List<VideoFrame> frames) async {
    final results = <FrameAnalysis>[];
    for (final frame in frames) {
      try {
        final payload = ImagePayload(
          bytes: frame.bytes,
          mimeType: 'image/jpeg',
          width: 0, // 抽帧时已经缩放过了，这里不用再压
          height: 0,
          compressed: true,
        );
        final r = await analyzePayload(payload);
        results.add(FrameAnalysis(
          frame: frame,
          suggestion: r.usedFallback ? null : r.suggestion,
          error: r.usedFallback ? (r.error ?? '降级到本地规则') : null,
          usedFallback: r.usedFallback,
        ));
      } catch (e) {
        results.add(FrameAnalysis(frame: frame, error: '$e'));
      }
    }
    return mergeSuggestions(results);
  }
}

/// 把长文本截断，避免把整段模型输出塞进 errorCode（日志会爆）。
String _truncateText(String s, {int max = 200}) {
  final t = s.trim();
  if (t.length <= max) return t;
  return '${t.substring(0, max)}…（共 ${t.length} 字）';
}
