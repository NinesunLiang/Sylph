import 'package:flutter/material.dart';

import 'llm_client.dart';
import 'model_config.dart';

/// 模型配置卡片（教练页 + 设置页共用，v0.4.0）。
///
/// 从教练页私有类 `_ApiConfigCard` 原样移植（v0.3.0）：可折叠的原因
/// （首屏纪律：空态「拍一张/从相册选」按钮和预览框要首屏可见）、
/// 三个输入框的布局、状态行文案全部保持不变 ——
/// coach_page_test 守着的契约（点「模型配置」→ 3 个输入框 → 保存 →
/// 落 SharedPreferences）由本类继续承接。
///
/// 唯一变化：数据来源从「教练页 State 私有输入框」换成共享的
/// [ModelConfigStore] —— 保存后教练页/设置页都能看到新状态（两页在
/// IndexedStack 里并存，不依赖重建）；输入框生命周期归本组件管。
class ModelConfigCard extends StatefulWidget {
  const ModelConfigCard({
    super.key,
    required this.store,
    this.initiallyExpanded = false,
  });

  /// 共享配置存储（教练页/设置页经 AppSession 拿同一实例）。
  final ModelConfigStore store;

  /// 是否一进来就展开表单。
  /// 教练页用默认（收起）：首屏不能被表单占掉；
  /// 设置页传 true —— 用户就是来配置的，直接开表单少一步。
  final bool initiallyExpanded;

  @override
  State<ModelConfigCard> createState() => _ModelConfigCardState();
}

class _ModelConfigCardState extends State<ModelConfigCard> {
  final _keyController = TextEditingController();
  final _modelController = TextEditingController();
  final _endpointController = TextEditingController();

  /// 默认收起。未配置的用户看到琥珀色提示行，点一下就展开表单。
  late bool _expanded;

  /// 上一次已知「是否已存 Key」（驱动「保存成功 → 收起」的过渡动画）。
  bool _wasSaved = false;

  String get _statusText {
    final config = widget.store.effective;
    if (!config.isUsable) {
      return '未配置 —— 点这里填 API Key（不填则用本地规则兜底）';
    }
    if (config.mode == ProxyMode.server) {
      // authority = host:port（中转常用非常规端口，只写 host 会误导）
      final host =
          Uri.tryParse(config.endpoint)?.authority ?? config.endpoint;
      return '已配置 —— 走中转 $host（Key 存中转侧）';
    }
    return '已配置 —— 直连 DeepSeek（${config.model}，Key 存本机）';
  }

  Color get _statusColor => widget.store.effective.isUsable
      ? Colors.tealAccent
      : Colors.amberAccent.shade400;

  /// 输入框跟随 store（Key 字段不回显 —— v0.3.0 纪律：已存过的只留空框，
  /// 填新值即覆盖；未存过的保留用户已打的草稿）。
  void _syncControllers() {
    _modelController.text = widget.store.model;
    _endpointController.text = widget.store.endpoint;
    if (widget.store.keySaved) _keyController.clear();
  }

  @override
  void initState() {
    super.initState();
    _expanded = widget.initiallyExpanded;
    _wasSaved = widget.store.keySaved;
    _syncControllers();
    // 读回本机已存配置。测试环境没有 SharedPreferences 插件 →
    // load 内部 try/catch 按「未配置」处理，屏幕行为与真机一致。
    widget.store.load();
    widget.store.addListener(_onStoreChanged);
  }

  @override
  void dispose() {
    widget.store.removeListener(_onStoreChanged);
    _keyController.dispose();
    _modelController.dispose();
    _endpointController.dispose();
    super.dispose();
  }

  /// 共享 store 变化（本页保存 / 设置页保存 / load 完成）。
  void _onStoreChanged() {
    if (!mounted) return;
    final nowSaved = widget.store.keySaved;
    setState(() {
      if (!_wasSaved && nowSaved) {
        // 保存成功（从未配置变已配置）→ 收起，让位给首屏主操作。
        _expanded = false;
        _keyController.clear(); // Key 已存好，不回显明文。
      }
      _modelController.text = widget.store.model;
      _endpointController.text = widget.store.endpoint;
    });
    _wasSaved = nowSaved;
  }

  Future<void> _onSave() async {
    await widget.store.save(
      apiKey: _keyController.text,
      model: _modelController.text,
      endpoint: _endpointController.text,
    );
    if (!mounted) return;
    setState(() => _keyController.clear()); // 保存后清 Key 输入框。
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 收起行（也是展开按钮）：状态永远可见，点按展开/收起。
          InkWell(
            onTap: () => setState(() {
              _expanded = !_expanded;
              if (_expanded) _syncControllers();
            }),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              child: Row(
                children: [
                  const Icon(Icons.key_outlined, size: 18,
                      color: Colors.white54),
                  const SizedBox(width: 8),
                  const Text('模型配置',
                      style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _statusText,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 12, color: _statusColor),
                    ),
                  ),
                  Icon(
                    _expanded
                        ? Icons.expand_less
                        : Icons.expand_more,
                    size: 20,
                    color: Colors.white38,
                  ),
                ],
              ),
            ),
          ),
          if (_expanded) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: _keyController,
                    obscureText: true,
                    autocorrect: false,
                    decoration: const InputDecoration(
                      labelText: 'API Key',
                      hintText: 'sk-…（填一次即可，只存你这台手机）',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _modelController,
                          autocorrect: false,
                          decoration: const InputDecoration(
                            labelText: '模型',
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: _endpointController,
                          autocorrect: false,
                          maxLines: null,
                          decoration: const InputDecoration(
                            labelText: '接口地址（默认官方，可改中转）',
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: Text(_statusText,
                            style:
                                TextStyle(fontSize: 12, color: _statusColor)),
                      ),
                      FilledButton(
                        onPressed: _onSave,
                        child: const Text('保存'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
