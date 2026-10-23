import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 首次 3 步 onboarding（v0.9.2）：光线 → 机位 → 距离。
///
/// 设计意图：小白第一次打开 App，30 秒 × 3 步建立「拍好照片 = 光线 + 机位 + 距离」
/// 的心智模型。之后不再弹出（SharedPreferences 持久化）。
///
/// 为什么不用 onboarding_carousel 等第三方包：
/// 3 步 × 纯文字 + 图标 = 手写 200 行 < 引一个包 + 学 API + 维护升级。
class OnboardingPage extends StatefulWidget {
  const OnboardingPage({super.key, required this.onFinish});

  /// 用户完成（或跳过）后回调 → 父组件移除本页。
  final VoidCallback onFinish;

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage>
    with SingleTickerProviderStateMixin {
  static const _steps = _OnboardingStep.values;
  int _index = 0;

  late final AnimationController _ctrl;
  late final Animation<double> _fade;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _fade = CurvedAnimation(parent: _ctrl, curve: Curves.easeOut);
    _ctrl.forward();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _next() {
    if (_index < _steps.length - 1) {
      setState(() => _index++);
      _ctrl
        ..reset()
        ..forward();
    } else {
      _finish();
    }
  }

  void _skip() => _finish();

  void _finish() {
    markOnboarded();
    widget.onFinish();
  }

  @override
  Widget build(BuildContext context) {
    final step = _steps[_index];
    return Scaffold(
      body: FadeTransition(
        opacity: _fade,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 进度指示
                Row(
                  children: [
                    for (var i = 0; i < _steps.length; i++)
                      AnimatedContainer(
                        duration: const Duration(milliseconds: 250),
                        margin: const EdgeInsets.only(right: 8),
                        width: i == _index ? 32 : 12,
                        height: 12,
                        decoration: BoxDecoration(
                          color: i == _index
                              ? Theme.of(context).colorScheme.primary
                              : Theme.of(context)
                                  .colorScheme
                                  .onSurface
                                  .withValues(alpha: 0.3),
                          borderRadius: BorderRadius.circular(6),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 40),
                // 图标
                Center(
                  child: Container(
                    width: 96,
                    height: 96,
                    decoration: BoxDecoration(
                      color: Theme.of(context)
                          .colorScheme
                          .primary
                          .withValues(alpha: 0.15),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      step.icon,
                      size: 48,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                // 标题
                Center(
                  child: Text(
                    step.title,
                    style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
                  ),
                ),
                const SizedBox(height: 16),
                // 正文
                Center(
                  child: Text(
                    step.body,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 16,
                      height: 1.6,
                      color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.7),
                    ),
                  ),
                ),
                const SizedBox(height: 48),
                // 按钮
                Row(
                  children: [
                    TextButton(
                      onPressed: _skip,
                      child: const Text('跳过'),
                    ),
                    const Spacer(),
                    FilledButton(
                      onPressed: _next,
                      child: Text(
                        _index == _steps.length - 1 ? '开始拍照' : '下一步',
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// 3 步内容。
enum _OnboardingStep {
  light(
    icon: Icons.light_mode,
    title: '先看光线',
    body: '举起手机，看看你面对的光：\n\n'
        '· 顺光 — 光从你身后照过来，脸最亮\n'
        '· 侧光 — 光从侧面来，有立体感\n'
        '· 逆光 — 光在你面前，剪影氛围\n\n'
        '拍摄页顶部的「光」按钮，就是标记你现在面对哪种光。',
  ),
  camera(
    icon: Icons.cameraswitch,
    title: '再调机位',
    body: '手机举多高、从哪个角度拍，决定照片的气质：\n\n'
        '· 平视 — 手机和眼睛齐平，最自然\n'
        '· 略仰 — 手机比下巴低，显高显气场\n'
        '· 略俯 — 手机在头顶上方，显脸小\n\n'
        '选姿势时会提示该用哪种机位，照着举就行。',
  ),
  distance(
    icon: Icons.straighten,
    title: '最后看距离',
    body: '站多远，决定照片里人占多少比例：\n\n'
        '· 全身 — 站远（约 2~3 米），把环境拍进去\n'
        '· 七分身 — 膝盖以上，最常用\n'
        '· 半身 — 站近（约 1 米），突出表情\n\n'
        '拍摄页的距离条会实时告诉你「该再近一点」还是「刚刚好」。',
  );

  const _OnboardingStep({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;
}

/// ── 持久化 ──────────────────────────────────────────────────────────

const _kOnboarded = 'onboarding.done';

/// 标记 onboarding 已完成（写入 SharedPreferences）。
/// 测试环境没有插件 → 静默失败（当作未完成，下次还会弹）。
Future<void> markOnboarded() async {
  try {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kOnboarded, true);
  } catch (_) {}
}

/// 读取是否已完成 onboarding。
Future<bool> isOnboarded() async {
  try {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kOnboarded) ?? false;
  } catch (_) {
    return false;
  }
}

/// 清除 onboarding 标记（「重新看新手引导」入口用）。
Future<void> resetOnboarding() async {
  try {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kOnboarded);
  } catch (_) {}
}
