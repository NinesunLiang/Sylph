import 'package:flutter/material.dart';

import '../coach/model_config.dart';
import '../coach/model_config_card.dart';

/// 设置页 —— 入口是**拍摄页右上角的齿轮**。
///
/// 这里只有**模型配置**（API Key / 模型 / 接口地址）。「模型配置」卡片
/// 与教练页是同一个共享实例（[ModelConfigStore] 挂在 AppSession 上，
/// 见 [modelConfig]）—— 本页保存后教练页立即生效。
///
/// **没有「拍摄参数」入口**：2026-10-11 三模块职责重构后，曝光/变焦/闪光灯
/// 归教练（镜头语言），拍摄页只管取景对位。App 内预览调参数也带不到最终
/// 出片（出片在系统相机里），所以整个 App 不残留参数控件。
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key, this.modelConfig});

  /// 共享模型配置存储（AppSession 的实例；不注入时用本地实例，
  /// 独立运行 / 测试场景，此时由本页负责释放）。
  final ModelConfigStore? modelConfig;

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late final ModelConfigStore _store =
      widget.modelConfig ?? ModelConfigStore();
  late final bool _ownsStore = widget.modelConfig == null;

  @override
  void dispose() {
    if (_ownsStore) _store.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: ListView(
        children: [
          // v0.4.0：模型配置（API Key / 模型 / 接口地址）。放在最上面 ——
          // 用户进设置页多半就是来配这个的，直接开表单少一步。
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
            child: ModelConfigCard(store: _store, initiallyExpanded: true),
          ),
          const Divider(height: 1),
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 20, 16, 6),
            child: Text('说明',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Text(
              '· 拍下的照片会存进**系统相册**，不上传任何服务器。',
              style: TextStyle(fontSize: 12, color: Colors.white70),
            ),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Text(
              '· 构图建议接的是 DeepSeek 模型，需要联网。API Key 在上面的'
              '「模型配置」填一次即可（教练页里也有同一处），只存你这台手机'
              '（不进包、不上传）。没填/连不上时会自动改用本地规则兜底，'
              '并在结果上标注「本地规则（离线兜底）」，不会假装是 AI 给的。',
              style: TextStyle(fontSize: 12, color: Colors.white70),
            ),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 0, 16, 20),
            child: Text(
              '· 手动 ISO / 快门速度：官方相机插件不支持，需要自己写原生代码，'
              '目前拍不了就是拍不了，界面上不放假控件。',
              style: TextStyle(fontSize: 12, color: Colors.white70),
            ),
          ),
        ],
      ),
    );
  }
}
