import 'package:flutter/material.dart';

import 'app_session.dart';
import 'shell/app_shell.dart';

/// 摄影助手 v2 —— 无谷歌依赖重建版。
///
/// 为什么有这个 app：v1（apps/photo_coach）引入 `google_mlkit_pose_detection` 后，
/// 包内 `MlKitInitProvider`（ContentProvider，进程启动即执行，Dart 层拦不住）
/// 在无谷歌服务机型（华为）上初始化失败 → 启动即崩，v0.15.0–v0.19.1 全部中招。
/// v2 从依赖层排除全部谷歌系包，该类崩溃在结构上不可能再发生
/// （每次构建由 tool/check_no_google.sh 机器验证）。
/// 功能面按 S2→S6 渐进迁移回 v1（见 .omc/tasks/20261010/photo-coach-v2-rebuild/）。
void main() {
  runApp(PhotoCoachV2App());
}

class PhotoCoachV2App extends StatefulWidget {
  const PhotoCoachV2App({super.key});

  @override
  State<PhotoCoachV2App> createState() => _PhotoCoachV2AppState();
}

class _PhotoCoachV2AppState extends State<PhotoCoachV2App> {
  /// 跨页共享状态（姿势页 → 预览页）。放在 App 根部，三个 tab 共用一份。
  final AppSession _session = AppSession();

  @override
  void dispose() {
    _session.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF3D5AFE);
    return MaterialApp(
      title: '摄影助手 v2',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.dark,
        ),
      ),
      home: AppShell(session: _session),
    );
  }
}
