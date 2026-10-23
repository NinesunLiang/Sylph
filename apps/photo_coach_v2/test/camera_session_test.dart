import 'dart:io' show PathNotFoundException;

import 'package:camera_platform_interface/camera_platform_interface.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_coach_v2/features/camera/camera_session.dart';
import 'package:photo_coach_v2/features/camera/photo_saver.dart';

import 'support/fake_camera_platform.dart';
import 'support/fake_photo_saver.dart';

/// CameraSession 的测试。
///
/// **能测什么、不能测什么（诚实说明）**：
/// - 不能测：真实摄像头行为（要真机）。`CameraController.initialize()` 需要
///   平台实现，单元测试环境里没有。
/// - **能测**：所有「相机不可用 / 未就绪」时的守卫路径、状态复位、
///   超时逻辑、错误分类、通知语义。这些恰恰是之前连环出 bug 的地方
///   （切前置死锁、重试死锁）——它们全都发生在
///   "相机没准备好或刚失败"的时刻。
///
/// **2026-10-11 三模块职责重构**：EV/变焦/闪光的 setter 与范围查询已删除
/// （出片在系统相机，App 内预览调参数无用）。本文件里对应的
/// 参数 clamp、能力置灰、曝光补偿回归用例一并删除；保留对焦与拍照存相册。
///
/// 所以这个文件的价值：**把失败路径锁死**，防止再退回「一直转圈」。

void main() {
  group('CameraSession —— 未初始化时的守卫（不该崩、不该发疯）', () {
    test('刚构造出来时状态干净', () {
      final s = CameraSession();
      expect(s.isReady, isFalse);
      expect(s.error, isNull);
      expect(s.note, isNull);
      expect(s.initializing, isFalse);
      expect(s.stuck, isFalse);
      expect(s.progress, isEmpty);
      expect(s.controller, isNull);
      expect(s.cameras, isEmpty);
      s.dispose();
    });

    test('默认「不支持手动 ISO/快门」（诚实：官方插件做不到）', () {
      final s = CameraSession();
      expect(s.canManualIso, isFalse);
      expect(s.canManualShutter, isFalse);
      s.dispose();
    });

    test('相机没准备好时，setter 不崩（状态照改，只是没设到相机上）', () async {
      final s = CameraSession();
      await s.setFocusMode(FocusMode.locked);
      await s.tapToFocus(const Offset(0.3, 0.4));
      await s.applyAll();

      expect(s.focusMode, FocusMode.locked);
      expect(s.error, isNull, reason: '相机没准备好不该报错，只是没设上');
      s.dispose();
    });

    test('takePicture 在相机不可用时返回 null，不抛异常', () async {
      final s = CameraSession();
      final r = await s.takePicture();
      expect(r, isNull, reason: '不该抛异常，UI 层会崩');
      s.dispose();
    });

    test('grabFrame（给实时引导用）也不抛异常', () async {
      final s = CameraSession();
      expect(await s.grabFrame(), isNull);
      s.dispose();
    });

    test('isBusy / ready / busy 在没相机时是安全值', () {
      final s = CameraSession();
      expect(s.isBusy, isFalse);
      expect(s.ready, isFalse);
      expect(s.busy, isFalse);
      s.dispose();
    });

    test('switchCamera 在没相机时不崩（静默返回）', () async {
      final s = CameraSession();
      await s.switchCamera();
      expect(s.error, isNull);
      s.dispose();
    });
  });

  group('CameraSession —— initialize 失败路径', () {
    test('测试环境里没有摄像头 → 给出可读错误，且状态复位（不卡在转圈）', () async {
      final s = CameraSession();
      await s.initialize();

      // 关键：不管成功失败，绝不能卡在「正在初始化」
      expect(s.initializing, isFalse, reason: '卡在 initializing 就是 UI 永久转圈');
      expect(s.progress, isEmpty, reason: '进度文字要清掉');
      expect(s.stuck, isFalse);

      // 没有摄像头时应该给出错误（而不是假装成功）
      if (!s.isReady) {
        expect(s.error, isNotNull, reason: '失败了就该有错误信息给用户看');
      }
      s.dispose();
    });

    test('initialize 失败后能再次调用（重试不该死锁）', () async {
      final s = CameraSession();
      await s.initialize();
      await s.initialize();
      await s.initialize();
      expect(s.initializing, isFalse, reason: '连续重试后仍在初始化 = 死锁');
      s.dispose();
    });

    test('initialize 会先清掉上一次的错误（重试是干净的开始）', () async {
      final s = CameraSession();
      await s.initialize();
      final firstError = s.error;
      if (firstError != null) {
        // 再试一次，过程中不该还留着上次的错误文案
        final f = s.initialize();
        expect(s.error, isNull, reason: '重试开始时该清掉旧错误');
        await f;
      }
      s.dispose();
    });

    test('初始化过程中会发出通知（UI 才能显示进度）', () async {
      final s = CameraSession();
      var notifications = 0;
      s.addListener(() => notifications++);
      await s.initialize();
      expect(notifications, greaterThan(0));
      s.dispose();
    });

    test('dispose 之后 initialize 的收尾不产生未捕获异常', () async {
      final s = CameraSession();
      final f = s.initialize();
      s.dispose();
      // initialize 内部在 finally 里会 notifyListeners()，
      // 而 dispose 之后 notify 会触发 Flutter 断言。这是**预期**的：
      // 单测环境里它就是会报，这里只要求它是「已销毁」类断言，
      // 而不是别的随机崩溃（真机上页面销毁时会同时取消订阅，不会走到这）。
      Object? err;
      try {
        await f;
      } catch (e) {
        err = e;
      }
      if (err != null) {
        expect(err.toString().toLowerCase(), contains('dispos'),
            reason: '应该是"已销毁"断言，而不是别的随机崩溃');
      }
    });

    test('并发调用 initialize 不会互相踩（至少不崩）', () async {
      final s = CameraSession();
      await Future.wait([s.initialize(), s.initialize()]);
      expect(s.initializing, isFalse);
      s.dispose();
    });
  });

  group('CameraSession —— 对焦（本模块剩下的唯一参数）', () {
    test('tapToFocus 把坐标限制在 0–1（防止点屏幕外传给相机）', () async {
      final s = CameraSession();
      await s.tapToFocus(const Offset(-3, 7));
      final p = s.focusPoint;
      expect(p, isNotNull);
      expect(p!.dx, inInclusiveRange(0.0, 1.0));
      expect(p.dy, inInclusiveRange(0.0, 1.0));
      s.dispose();
    });

    test('设回自动对焦会清掉手动对焦点（不然会一直锁在旧位置）', () async {
      final s = CameraSession();
      await s.tapToFocus(const Offset(0.2, 0.2));
      expect(s.focusPoint, isNotNull);
      await s.setFocusMode(FocusMode.auto);
      expect(s.focusPoint, isNull, reason: '回到自动对焦必须清掉手动点');
      s.dispose();
    });
  });

  group('CameraSession —— 能力标记（UI 据此置灰）', () {
    test('默认能力都是 false —— 没探测过就不敢说"支持"', () {
      final s = CameraSession();
      expect(s.canSetFocus, isFalse);
      expect(s.canSetExposureMode, isFalse);
      expect(s.capabilitiesLoaded, isFalse);
      s.dispose();
    });

    test('hasLimitedCapabilities 在没探测前是 false（不误报）', () {
      final s = CameraSession();
      expect(s.hasLimitedCapabilities, isFalse);
      s.dispose();
    });

    test('lastUnsupported 初始为空，不会返回 null 炸掉 UI', () {
      final s = CameraSession();
      expect(s.lastUnsupported, isEmpty);
      s.dispose();
    });
  });

  group('CameraSession —— 通知语义（防止 UI 白刷或漏刷）', () {
    test('setFocusMode / tapToFocus 都会通知', () async {
      final s = CameraSession();
      var n = 0;
      s.addListener(() => n++);
      await s.setFocusMode(FocusMode.locked);
      await s.tapToFocus(const Offset(0.5, 0.5));
      expect(n, greaterThanOrEqualTo(2), reason: '每次改参数都该通知 UI');
      s.dispose();
    });

    test('dispose 之后再改参数不会抛（防止 use-after-dispose）', () async {
      final s = CameraSession();
      s.dispose();
      // Flutter 的 ChangeNotifier 在 dispose 后 notify 会抛断言；
      // 这里期望「不崩」—— 若崩了说明 dispose 后还有回调在跑。
      Object? err;
      try {
        await s.setFocusMode(FocusMode.locked);
      } catch (e) {
        err = e;
      }
      // 允许 Flutter 自身的断言（debug 模式），但不允许随机异常
      if (err != null) {
        expect(err.toString(), contains('disposed'),
            reason: '应该是明确的"已销毁"断言，而不是别的错');
      }
    });
  });

  // =====================================================================
  // 前置摄像头 / 切换摄像头
  //
  // 这一段是**针对一个真实 bug** 写的：人类在华为 OCE-AN50 上报
  //   「关闭重新进去可以看到后置摄像头，但是一旦切换为前置时就报错了」
  // 根因是 _open() 先建新控制器、后释放旧的 —— 华为把摄像头当独占资源，
  // 两个同时存在就让 initialize() 永远不返回（死锁，界面一直转圈）。
  //
  // 修复是「先释放、再打开」。**但当时没法验证** —— 因为
  // CameraPlatform.instance 是真实方法通道，单测环境没有平台实现。
  // 现在有了 FakeCameraPlatform，这段逻辑第一次被测到。
  // =====================================================================

  group('CameraSession —— 前/后摄像头切换（真机 bug 的回归测试）', () {
    late FakeCameraPlatform fake;

    CameraDescription back() => const CameraDescription(
        name: 'back', lensDirection: CameraLensDirection.back, sensorOrientation: 90);
    CameraDescription front() => const CameraDescription(
        name: 'front', lensDirection: CameraLensDirection.front, sensorOrientation: 270);

    setUp(() {
      fake = FakeCameraPlatform(cameras: [back(), front()]);
      CameraPlatform.instance = fake;
    });

    test('能列出前后两个摄像头', () async {
      final s = CameraSession();
      await s.initialize();
      expect(s.cameras.length, 2);
      expect(s.error, isNull, reason: '初始化不该失败：${s.error}');
      expect(s.isReady, isTrue);
      s.dispose();
    });

    test('切到前置：先释放旧的再打开新的（防死锁的关键）', () async {
      final s = CameraSession();
      await s.initialize();
      fake.calls.clear();

      await s.switchCamera();

      final disposedAt = fake.calls.indexWhere((c) => c.startsWith('dispose#'));
      final createdAt =
          fake.calls.lastIndexWhere((c) => c.startsWith('createCamera#front'));
      expect(disposedAt, greaterThanOrEqualTo(0), reason: '旧的没被释放');
      expect(createdAt, greaterThanOrEqualTo(0), reason: '前置没被打开');
      expect(disposedAt, lessThan(createdAt),
          reason: '顺序错了：必须**先释放**再打开，'
              '否则华为这类独占摄像头的设备会死锁。实际顺序：${fake.calls}');
      expect(s.isReady, isTrue, reason: '切完应该可用');
      s.dispose();
    });

    test('切到前置再切回后置，都不断链', () async {
      final s = CameraSession();
      await s.initialize();
      await s.switchCamera(); // → 前置
      expect(s.isReady, isTrue, reason: '切前置后应可用');
      await s.switchCamera(); // → 后置
      expect(s.isReady, isTrue, reason: '切回来后应可用');
      expect(s.error, isNull, reason: '不该累计错误：${s.error}');
      s.dispose();
    });

    test('连续切 5 次也不死锁（每次都先释放）', () async {
      final s = CameraSession();
      await s.initialize();
      for (var i = 0; i < 5; i++) {
        await s.switchCamera();
      }
      expect(s.isReady, isTrue);
      // 每次切换都应该恰好 dispose 一个（没有泄漏）
      final disposes = fake.calls.where((c) => c.startsWith('dispose#')).length;
      expect(disposes, greaterThanOrEqualTo(5),
          reason: '切 5 次至少释放 5 次，实际 $disposes —— 少了就是泄漏');
      s.dispose();
    });

    test('切的时候不会同时存在两个活着的摄像头', () async {
      final s = CameraSession();
      await s.initialize();
      await s.switchCamera();
      // 释放和创建的配对：活着的应该只有 1 个
      expect(fake.liveCameraIds.length, lessThanOrEqualTo(1),
          reason: '同时活着 ${fake.liveCameraIds.length} 个摄像头 = 死锁风险');
      s.dispose();
    });

    test('切摄像头时把当时的设置也应用过去（不是切完就不管）', () async {
      final s = CameraSession();
      await s.initialize();
      await s.tapToFocus(const Offset(0.5, 0.5));
      fake.calls.clear();
      await s.switchCamera();
      // 切完要重新走一遍能力探测 + 应用设置
      expect(fake.calls.any((c) => c.startsWith('setFocus')) ||
              fake.calls.any((c) => c.startsWith('setExposurePoint')),
          isTrue,
          reason: '切完没重新应用设置，实际调用：${fake.calls}');
      s.dispose();
    });

    test('只有前置一个摄像头时也能初始化（不假设一定有后置）', () async {
      fake = FakeCameraPlatform(cameras: [front()]);
      CameraPlatform.instance = fake;
      final s = CameraSession();
      await s.initialize();
      expect(s.isReady, isTrue, reason: '只有前置也该能用');
      expect(s.error, isNull);
      s.dispose();
    });

    test('切换时设备打不开 → 给出可读错误，不卡在转圈', () async {
      fake = FakeCameraPlatform(
        cameras: [back(), front()],
        failInitializeFor: {2}, // 前置（id 2）打不开
      );
      CameraPlatform.instance = fake;

      final s = CameraSession();
      await s.initialize();
      await s.switchCamera(); // → 前置，会失败

      expect(s.initializing, isFalse, reason: '不能卡在初始化态（那会永久转圈）');
      expect(s.error, isNotNull, reason: '失败了要告诉用户');
      s.dispose();
    });
  });

  group('CameraSession —— 假平台下的基础行为', () {
    test('拍照返回文件（假平台给的路径）', () async {
      final fake = FakeCameraPlatform(
        cameras: [
          const CameraDescription(
              name: 'only', lensDirection: CameraLensDirection.back, sensorOrientation: 90)
        ],
      );
      CameraPlatform.instance = fake;
      final s = CameraSession();
      await s.initialize();
      final f = await s.takePicture();
      expect(f, isNotNull);
      expect(fake.calls.any((c) => c.startsWith('takePicture#')), isTrue);
      s.dispose();
    });
  });

  // =====================================================================
  // 真机（华为 OCE-AN50）暴露的问题 —— 回归锁死
  //
  // 现象：点「对焦：锁定」后整页变成「相机没能用起来」，预览消失。
  // 根因不是「华为不支持」，是我们的错误分类没匹配上异常类名。
  // （曝光补偿相关的两条回归用例已随 EV setter 删除。）
  // =====================================================================
  group('设置失败不能冒充「相机坏了」（真机回归）', () {
    Future<CameraSession> initWith(FakeCameraPlatform fake) async {
      CameraPlatform.instance = fake;
      final s = CameraSession();
      addTearDown(s.dispose);
      await s.initialize();
      return s;
    }

    FakeCameraPlatform singleCam() => FakeCameraPlatform(
          cameras: [
            const CameraDescription(
                name: 'back',
                lensDirection: CameraLensDirection.back,
                sensorOrientation: 90)
          ],
        );

    test('对焦锁定抛 IllegalArgumentException → 只置灰对焦，绝不整页报错', () async {
      // 真机实测：华为 OCE-AN50 上 setFocusMode(locked) 抛
      // CameraException('IllegalArgumentException')（Pigeon 把 Java 异常类名
      // 当错误码传回来）。旧代码因为 'illegalargument' 里没有 'invalid'，
      // 分类器没匹配上 → 记进 _error → 整页变错误框、预览消失。
      final fake = singleCam()
        ..customFailures['setFocusMode'] = CameraException(
            'IllegalArgumentException', 'Focus mode not supported');
      final s = await initWith(fake);

      expect(s.error, isNull,
          reason: '相机是好的！不该让页面变成「相机没能用起来」');
      expect(s.isReady, isTrue, reason: '相机仍然可用 —— 预览必须还在');
      expect(s.canSetFocus, isFalse, reason: '这一项确实做不到，控件该置灰');
      expect(s.note, contains('对焦模式'),
          reason: '要用中性提示说明是哪一项不支持');
    });

    test('未知错误码 → 挂警告，但相机仍可用（不是 _error）', () async {
      final fake = singleCam()
        ..customFailures['setFocusMode'] =
            CameraException('SomethingWeird', '闻所未闻的失败');
      final s = await initWith(fake);

      expect(s.error, isNull, reason: '一次参数失败不等于相机坏了');
      expect(s.warning, contains('对焦模式'), reason: '要明确告诉用户是哪一项');
      expect(s.isReady, isTrue);
    });
  });

  // =====================================================================
  // F1.11 拍照存相册
  //
  // 之前**完全没这个能力**：拍完的照片只落在系统临时缓存目录，
  // 系统随时会清掉 —— 用户以为拍到了，其实什么都没留下。
  // =====================================================================
  group('拍照存相册（F1.11）', () {
    FakeCameraPlatform cam() => FakeCameraPlatform(
          cameras: [
            const CameraDescription(
                name: 'back',
                lensDirection: CameraLensDirection.back,
                sensorOrientation: 90)
          ],
        );

    Future<(CameraSession, FakePhotoSaver)> ready(
        FakePhotoSaver saver) async {
      CameraPlatform.instance = cam();
      final s = CameraSession(saver: saver);
      addTearDown(s.dispose);
      await s.initialize();
      return (s, saver);
    }

    test('按快门拍的照片会交给存档（进相册）', () async {
      final saver = FakePhotoSaver();
      final (s, _) = await ready(saver);

      final f = await s.captureAndSave();

      expect(f, isNotNull);
      expect(saver.saved, [f!.path],
          reason: '拍下来的照片没交给存档 —— 它只会烂在临时目录里');
      expect(s.lastShotSaved, isTrue);
      expect(s.warning, isNull);
    });

    test('实时引导取帧**绝不能**存相册（否则一秒往相册灌一张）', () async {
      final saver = FakePhotoSaver();
      final (s, _) = await ready(saver);

      // 模拟实时引导连续取帧。
      // 假平台故意返回一个不存在的路径（它自己的注释就写了），所以
      // readAsBytes 会抛 PathNotFoundException —— 与本用例无关，忽略。
      for (var i = 0; i < 5; i++) {
        try {
          await s.grabFrame();
        } on PathNotFoundException {
          // 只关心「有没有顺手存相册」，不关心假文件读不读得到
        }
      }

      expect(saver.saved, isEmpty,
          reason: 'grabFrame 走了存相册 —— 开一分钟实时引导，'
              '用户相册里会多出上百张连拍废照片');
      expect(s.lastShotSaved, isNull,
          reason: '取帧不是「用户拍了一张」，不该改存档状态');
    });

    test('相机没起来时按快门 → 不存、不崩', () async {
      final saver = FakePhotoSaver();
      final s = CameraSession(saver: saver);
      addTearDown(s.dispose);
      // 故意不 initialize
      expect(await s.captureAndSave(), isNull);
      expect(saver.saved, isEmpty);
    });

    test('存不进去：挂警告说明原因，但照片和相机都不受影响', () async {
      final saver = FakePhotoSaver(
          failWith: const PhotoSaveException('没有相册权限'));
      final (s, _) = await ready(saver);

      final f = await s.captureAndSave();

      expect(f, isNotNull, reason: '存相册失败不该把这张照片也搞没');
      expect(s.lastShotSaved, isFalse);
      expect(s.error, isNull, reason: '存相册失败 ≠ 相机坏了，不能整页报错');
      expect(s.isReady, isTrue);
      expect(s.warning, contains('相册'),
          reason: '要明确告诉用户「没存进去」，否则他以为存好了');
    });

    test('下次存成功后，上一次的存档警告要消失', () async {
      final saver = FakePhotoSaver(
          failWith: const PhotoSaveException('没有相册权限'));
      final (s, _) = await ready(saver);

      await s.captureAndSave();
      expect(s.warning, contains('相册'));

      saver.failWith = null; // 用户在系统设置里给了权限
      await s.captureAndSave();

      expect(s.lastShotSaved, isTrue);
      expect(s.warning, isNull, reason: '过期的警告一直挂在界面上会误导用户');
    });
  });
}
