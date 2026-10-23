import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app_session.dart';
import 'pose.dart';
import 'pose_guidance_text.dart';

/// F3 姿势集：**真实参考照**（性別 → 姿态 两级分类）。
///
/// v0.4.0：火柴人库按用户要求删除（`PoseCatalog.builtIn` 已置空），
/// 这个页面只发参考照库。
/// 参考照库两级分类不变：一级性別（女/男），二级姿态（女：站/坐/躺；男：站/坐）。
///
/// 点开参考照 → 详情页，**点一下图翻面**，背面就是镜头/方向/景别/动作/表情/
/// 为什么好看。
///
/// 详情页「送到拍摄页，照着摆」：选中的参考照会半透明叠到拍摄页实时画面上
/// （PoseOverlayView），用户看着照片摆好位置光线，再点快门跳系统相机拍。
class PosesPage extends StatefulWidget {
  const PosesPage({super.key, this.session, this.onSendToCamera});

  /// 跨页共享状态（可空，测试里可以不传）。
  final AppSession? session;

  /// 点「送到拍摄页」时回调（由 AppShell 负责切 tab）。
  final void Function(Pose pose)? onSendToCamera;

  @override
  @override
  State<PosesPage> createState() => _PosesPageState();
}

/// 图片模式（F3.8）：**左右滑看参考照**。
///
/// 需求（人类原话）：姿势进入图片模式后，左右滑能切换；**退出后不能再左右切换**。
///
/// 设计（把「模式」变成同页状态，不是两个页面）：
/// - 姿势列表 = 当前筛选（性別/姿态/搜索词）下的参考照，顺序即库顺序；
/// - 点卡片 → 进入图片模式：整页换成 PageView，当前照片放大居中，
///   左右滑 = 切到筛选列表里的下一张 / 上一张；
/// - 点「退出图片模式」→ 回到网格。**回网格后左右滑不切换任何东西**
///   （网格只有纵向滚动 + 点卡片，横向手势没有绑定——需求里的硬边界，单测锁死）。
///
/// 为什么不用「详情页加 PageView」：详情页是 push 的路由页，它里面的
/// 横向手势会和「点图翻面」打架；而且路由语义里「退出」= pop，
/// 用户会以为 App 退出了。同页切状态最干净，也最符合「退出后不切」。
class PhotoSwipePage extends StatefulWidget {
  const PhotoSwipePage({
    super.key,
    required this.poses,
    required this.initialIndex,
    required this.onExit,
    this.session,
    this.onSendToCamera,
  });

  /// 当前筛选结果（图片模式里左右滑就是在这个列表里走）。
  final List<Pose> poses;

  /// 从哪张开始（用户点的是第几张卡片）。
  final int initialIndex;

  /// 退出图片模式（回网格）。
  final VoidCallback onExit;

  final AppSession? session;
  final void Function(Pose pose)? onSendToCamera;

  @override
  State<PhotoSwipePage> createState() => _PhotoSwipePageState();
}

class _PhotoSwipePageState extends State<PhotoSwipePage> {
  /// 当前页索引（左右滑改它）。
  int _index = 0;

  /// PageView 控制器：翻页由它同步回 [_index]。
  late PageController _page;

  @override
  void initState() {
    super.initState();
    _index = widget.initialIndex.clamp(0, math.max(0, widget.poses.length - 1));
    _page = PageController(initialPage: _index);
    _page.addListener(_onPageChanged);
  }

  @override
  void dispose() {
    _page.dispose();
    super.dispose();
  }

  void _onPageChanged() {
    if (_page.hasClients) {
      final i = _page.page!.round();
      if (i >= 0 && i < widget.poses.length && i != _index) {
        setState(() => _index = i);
      }
    }
  }

  bool get _atEdge =>
      _index <= 0 || _index >= widget.poses.length - 1;

  void _sendToCamera() {
    if (_index < 0 || _index >= widget.poses.length) return;
    final pose = widget.poses[_index];
    final messenger = ScaffoldMessenger.maybeOf(context);
    widget.session?.sendPoseToCamera(pose);
    widget.onSendToCamera?.call(pose);
    messenger?.showSnackBar(
        SnackBar(content: Text('已送到拍摄页：${pose.title}')));
  }

  @override
  Widget build(BuildContext context) {
    if (widget.poses.isEmpty) {
      // 防御：列表空了（筛选在图片模式期间被改）→ 显示空态，不崩。
      return Scaffold(
        appBar: AppBar(
          title: const Text('图片模式'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_ios_new),
            tooltip: '退出图片模式',
            onPressed: widget.onExit,
          ),
        ),
        body: const Center(child: Text('没有可看的位置')),
      );
    }
    final pose = widget.poses[_index];
    return Scaffold(
      appBar: AppBar(
        title: Text(
          '${pose.title}（${_index + 1}/${widget.poses.length}）',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        leading: IconButton(
          key: const ValueKey('swipe-exit-appbar'),
          icon: const Icon(Icons.arrow_back_ios_new),
          tooltip: '退出图片模式（回网格）',
          onPressed: widget.onExit,
        ),
      ),
      body: Stack(
        fit: StackFit.expand,
        children: [
          // 左右滑 = 切参考照。PageView 自带横向拖动手势，
          // 边界上滑不动（自然不翻页），所以不需要额外锁。
          PageView.builder(
            key: const ValueKey('photo-swipe'),
            controller: _page,
            itemCount: widget.poses.length,
            itemBuilder: (context, i) => _SwipePhoto(pose: widget.poses[i]),
          ),
          // 左右边缘方向箭头：中间位置显示，给不爱滑的用户一条路。
          // ⚠️ 边界上不显示——那里没东西可切，箭头只会骗用户。
          if (!_atEdge) ...[
            Positioned(
              left: 8,
              top: 0,
              bottom: 0,
              child: Center(
                child: _EdgeArrow(
                  direction: -1,
                  onTap: () => _swipe(-1),
                ),
              ),
            ),
            Positioned(
              right: 8,
              top: 0,
              bottom: 0,
              child: Center(
                child: _EdgeArrow(
                  direction: 1,
                  onTap: () => _swipe(1),
                ),
              ),
            ),
          ],
        ],
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: Row(
          children: [
            OutlinedButton.icon(
              key: const ValueKey('swipe-exit'),
              onPressed: widget.onExit,
              icon: const Icon(Icons.grid_view, size: 18),
              label: const Text('退出图片模式'),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton.icon(
                onPressed: _sendToCamera,
                icon: const Icon(Icons.camera_alt, size: 20),
                label: const Text('送到拍摄页'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 左右滑一步：切到筛选列表里的上一张 / 下一张。
  /// 越界直接忽略（PageView 也不会翻过去）。
  void _swipe(int delta) {
    final next = _index + delta;
    if (next < 0 || next >= widget.poses.length) return;
    _page.animateToPage(
      next,
      duration: const Duration(milliseconds: 260),
      curve: Curves.easeOutCubic,
    );
  }
}

/// 图片模式里放大显示的单张照片（3:4，和详情页同一口径）。
class _SwipePhoto extends StatelessWidget {
  const _SwipePhoto({required this.pose});

  final Pose pose;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Center(
        child: AspectRatio(
          aspectRatio: 3 / 4,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: pose.hasPhoto
                ? Image.asset(
                    pose.imagePath!,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const ColoredBox(
                      color: Colors.black26,
                      child: Center(
                        child: Icon(Icons.broken_image_outlined,
                            color: Colors.white24),
                      ),
                    ),
                  )
                : const ColoredBox(
                    color: Colors.black26,
                    child: Center(
                      child: Icon(Icons.broken_image_outlined,
                          color: Colors.white24),
                    ),
                  ),
          ),
        ),
      ),
    );
  }
}

/// 左右边缘的方向箭头（点它也能切，给不爱滑的用户一条路）。
class _EdgeArrow extends StatelessWidget {
  const _EdgeArrow({required this.direction, required this.onTap});

  /// -1 = 左箭头（上一张），+1 = 右箭头（下一张）。
  final int direction;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      key: ValueKey(direction < 0 ? 'swipe-prev' : 'swipe-next'),
      onTap: onTap,
      child: Container(
        width: 34,
        height: 34,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: Colors.black54,
        ),
        child: Icon(
          direction < 0 ? Icons.chevron_left : Icons.chevron_right,
          color: Colors.white70,
          size: 24,
        ),
      ),
    );
  }
}

class _PosesPageState extends State<PosesPage> {
  // 参考照：性別（一级）+ 姿态（二级）+ 景别（三级，v0.9.0）
  String _gender = '全部';
  String _posture = '全部';

  /// 景别筛选（v0.9.0 环境&机位&姿势 指导）：全身/七分身/半身。
  /// 为什么加：250 张参考照里景别分布 138/79/33，小白最大的困惑是
  /// 「我到底要拍全身还是半身」——筛选出来一眼就能对比同类。
  String _framing = '全部';

  /// 图片模式（F3.8）：非 null = 正处在「左右滑看参考照」状态。
  ///
  /// 需求硬边界：退出（置回 null）之后，网格内**没有任何**左右滑切换
  /// —— 网格只有纵向滚动 + 点卡片。
  PhotoSwipePage? _photoMode;

  String _query = '';

  List<Pose> get _visible =>
      PoseCatalog.searchPhotos(_query)
          .where((p) =>
              (_gender == '全部' || p.gender == _gender) &&
              (_posture == '全部' || p.posture == _posture) &&
              (_framing == '全部' || p.guidance?.framing == _framing))
          .toList();

  List<String> get _postureOptions => PoseCatalog.posturesOf(_gender);

  /// 进入图片模式（F3.8）：用当前筛选列表 + 点击位置建一个 [PhotoSwipePage]。
  ///
  /// ⚠️ 快照而不是 getter：进入图片模式后用户可能改筛选（搜索/性別），
  /// 网格那边变，但图片模式里应该看的是**进入时**的那份列表——
  /// 退出后网格用最新筛选重建，两边互不干扰。
  void _enterPhotoMode(int index) {
    setState(() {
      _photoMode = PhotoSwipePage(
        poses: _visible,
        initialIndex: index,
        onExit: () => setState(() => _photoMode = null),
        session: widget.session,
        onSendToCamera: widget.onSendToCamera,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    // 图片模式优先：非 null 就整页换成左右滑视图。
    // 退出（_photoMode = null）后这里回网格，网格本身不响应横向手势。
    if (_photoMode != null) {
      return _photoMode!;
    }
    final poses = _visible;
    return Scaffold(
      appBar: AppBar(title: const Text('姿势集')),
      body: Column(
        children: [
          ...[
            _ChipRow(
              label: '性別',
              options: PoseCatalog.genders,
              selected: _gender,
              onPick: (g) => setState(() {
                _gender = g;
                // 换性別后二级分类可能不存在了（比如「男」没有「躺」），
                // 这里必须回落，否则会停在一个选不中的死状态上。
                if (!_postureOptions.contains(_posture)) _posture = '全部';
              }),
            ),
            _ChipRow(
              label: '姿态',
              options: _postureOptions,
              selected: _posture,
              onPick: (p) => setState(() => _posture = p),
            ),
            _ChipRow(
              label: '景别',
              options: const ['全部', '全身', '七分身', '半身'],
              selected: _framing,
              onPick: (f) => setState(() => _framing = f),
            ),
          ],
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: TextField(
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search),
                hintText: '搜动作 / 表情 / 为什么好看',
                isDense: true,
                border: const OutlineInputBorder(),
              ),
              onChanged: (v) => setState(() => _query = v),
            ),
          ),
          Expanded(
            child: poses.isEmpty
                ? const Center(child: Text('没有匹配的姿势'))
                : GridView.builder(
                    padding: const EdgeInsets.all(16),
                    gridDelegate:
                        const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 200,
                      // 0.78 → 0.68：标题允许两行 + 图区留内边距之后，
                      // 卡片需要更高。这是跑测试调出来的值，不是猜的。
                      childAspectRatio: 0.68,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                    ),
                    itemCount: poses.length,
                    itemBuilder: (context, i) => _PoseCard(
                      pose: poses[i],
                      onTap: () => _enterPhotoMode(i),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

/// 一行横向筛选 chip。
///
/// ⚠️ 保留原来的坑与修法：横向 ListView 里 chip 只给 minWidth 会被压到
/// 只剩一个字宽（"站姿" 显示成 "站"），所以必须给**确定宽度**。
class _ChipRow extends StatelessWidget {
  const _ChipRow({
    required this.options,
    required this.selected,
    required this.onPick,
    this.label,
  });

  final List<String> options;
  final String selected;
  final void Function(String) onPick;
  final String? label;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 46,
      child: Row(
        children: [
          if (label != null)
            Padding(
              padding: const EdgeInsets.only(left: 16, right: 2),
              child: Text(label!,
                  style: const TextStyle(fontSize: 12, color: Colors.white54)),
            ),
          Expanded(
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                for (final c in options)
                  Padding(
                    padding: const EdgeInsets.only(right: 8, top: 4, bottom: 4),
                    child: SizedBox(
                      width: 80,
                      child: ChoiceChip(
                        label: SizedBox(
                          width: double.infinity,
                          child: Text(
                            c,
                            textAlign: TextAlign.center,
                            maxLines: 1,
                            softWrap: false,
                            overflow: TextOverflow.clip,
                            style: const TextStyle(fontSize: 13),
                          ),
                        ),
                        labelPadding:
                            const EdgeInsets.symmetric(horizontal: 4),
                        padding: const EdgeInsets.symmetric(horizontal: 6),
                        selected: selected == c,
                        onSelected: (_) => onPick(c),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PoseCard extends StatelessWidget {
  const _PoseCard({required this.pose, required this.onTap});

  final Pose pose;
  final VoidCallback onTap;

  /// 副标题：有指导数据 → 机位信息；没有 → 退回旧文案（防御）。
  static String _cardMeta(Pose pose) {
    final g = pose.guidance;
    if (g == null) {
      return pose.hasPhoto ? '${pose.gender}·${pose.posture}' : pose.category;
    }
    return '${g.cameraHeight} · ${g.direction} · ${g.framing}';
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          children: [
            Expanded(
              child: Container(
                color: Colors.black26,
                // v0.4.0 起库里只剩参考照；无照片的脏数据退回占位图标。
                child: pose.hasPhoto
                    ? Image.asset(
                        pose.imagePath!,
                        fit: BoxFit.cover,
                        width: double.infinity,
                        // 素材缺失时不要整页红屏，退回到占位。
                        errorBuilder: (_, __, ___) => const Center(
                          child: Icon(Icons.broken_image_outlined,
                              color: Colors.white24),
                        ),
                      )
                    : const Icon(Icons.broken_image_outlined,
                        color: Colors.white24),
              ),
            ),
            // 图区和标题之间留 2pt 间隔。实测原布局只差 8pt（人形区底 323.4，
            // 标题顶 331.4），视觉上很挤，容易误看成"重叠"。
            const SizedBox(height: 2),
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 6, 8, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ⚠️ 必须允许 2 行。
                  // 之前是 maxLines:1 + ellipsis，浏览器实测发现
                  // 「自然站姿（重心一条腿）」被截成「自然站姿（重心一…」。
                  // 更有意思的是：**单测当时全绿** —— 因为我只断言了
                  // 「标题 ≤ 24 字」（数据层合规），没断言「布局放得下」。
                  // 后来补的布局断言一次抓出 6 个被截的标题，不是 1 个。
                  Text(
                    pose.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 13,
                        height: 1.25,
                        fontWeight: FontWeight.w600),
                  ),
                  // v0.9.0：副标题从「女·站 点开看指导」改成机位信息
                  // 「平机位 · 四分之三侧 · 全身」—— 小白选姿势时真正要对比的
                  // 是镜头参数，不是「点开看」这种废话。
                  Text(
                    _cardMeta(pose),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 11, height: 1.3, color: Colors.white54),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 详情页：看图 + **点一下翻面**看指导。
class PoseDetailPage extends StatefulWidget {
  const PoseDetailPage({
    super.key,
    required this.pose,
    this.session,
    this.onSendToCamera,
  });

  final Pose pose;
  final AppSession? session;
  final void Function(Pose pose)? onSendToCamera;

  @override
  State<PoseDetailPage> createState() => _PoseDetailPageState();
}

class _PoseDetailPageState extends State<PoseDetailPage>
    with SingleTickerProviderStateMixin {
  /// 翻面动画。0 = 正面（照片），1 = 背面（指导）。
  late final AnimationController _flip = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 420),
  );

  bool get _flipped => _flip.value >= 0.5;

  @override
  void dispose() {
    _flip.dispose();
    super.dispose();
  }

  void _toggleFlip() {
    if (_flip.isAnimating) {
      return; // 动画中不叠新的，防连点抖动
    }
    _flip.value < 0.5 ? _flip.forward() : _flip.reverse();
  }

  /// F3.7：把这个姿势送到拍摄页，半透明叠在实时取景框上照着摆。
  ///
  /// ⚠️ 之前这里写错了：`onSendToCamera == null` 时**直接 return**，
  /// 于是**连 session 都不写**。结果是「只给了共享状态、没给回调」的场景下
  /// 这个功能**完全失效**（姿势送不过去，用户白点）。
  /// 正确做法：两件事互不依赖 —— 写共享状态、通知外面切页，各自独立做。
  void _sendToCamera() {
    final pose = widget.pose;
    final session = widget.session;
    final onSend = widget.onSendToCamera;

    // ⚠️ 先把 messenger / navigator 拿到手：下面要 pop 掉本页，
    // pop 之后 context 就失效了（真机上表现为"点完什么都没发生"）。
    final messenger = ScaffoldMessenger.maybeOf(context);
    final navigator = Navigator.of(context);

    // 1) 写共享状态（拍摄页靠它把参考照叠上去）
    session?.sendPoseToCamera(pose);

    // 2) 通知外面（AppShell 靠它切到拍摄页）
    onSend?.call(pose);

    // 3) 给用户反馈。一件都没做成才说"没接上"。
    if (session == null && onSend == null) {
      messenger?.showSnackBar(
        const SnackBar(content: Text('当前环境没有接到拍摄页')),
      );
      return;
    }
    messenger?.showSnackBar(
      SnackBar(content: Text('已送到拍摄页：${pose.title}')),
    );

    // 4) 🔴 **收起本页** —— 这是关键一步。
    // AppShell 确实会切到拍摄页，但本页是 push 在 shell **之上**的：
    // 底下换了 tab，用户眼前还是这张详情页，表现就是"只弹了一句提示、
    // 人还在原地"（人类 2026-09-21 的实机反馈）。
    if (navigator.canPop()) navigator.pop();
  }

  /// 翻面按钮永远在**卡片外面**。
  ///
  /// 为什么不让用户"点图翻回去"：卡片转到背面之后，点图这个手势落在
  /// 3D 变换过的子树里，实测点不动（翻不回来）。按钮放在卡片下方就与
  /// 变换无关，正反面都能点，而且是明确的可见入口，不用用户猜。
  ///
  /// 必须用 AnimatedBuilder 包住：`_flipped` 读的是动画值，不监听的话
  /// 文案永远停在「翻面看细节」——按钮点得动、字不变，看着像坏了。
  Widget _flipButton() => AnimatedBuilder(
        animation: _flip,
        builder: (context, _) => OutlinedButton.icon(
          onPressed: _toggleFlip,
          icon: const Icon(Icons.flip, size: 18),
          label: Text(_flipped ? '翻回看照片' : '翻面看细节（镜头 / 动作 / 表情）'),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final pose = widget.pose;
    final g = pose.guidance;

    return Scaffold(
      appBar: AppBar(title: Text(pose.title)),
      // 「送到拍摄页」放**底部固定条**：
      // 以前它在内容最上面，手机上一只手够不着，还会随内容滚走。
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: SizedBox(
          height: 50,
          child: FilledButton.icon(
            onPressed: _sendToCamera,
            icon: const Icon(Icons.camera_alt, size: 20),
            label: const Text('送到拍摄页'),
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          AspectRatio(
            aspectRatio: 3 / 4,
            child: GestureDetector(
              onTap: _toggleFlip,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: AnimatedBuilder(
                      animation: _flip,
                        builder: (context, _) {
                          final t = _flip.value;
                          // 0→0.5 转正面，0.5→1 转背面；各自只在自己那半程可见，
                          // 于是看起来就是同一张卡片翻了过去。
                          final angle = t * math.pi;
                          final showFront = t < 0.5;
                          return Transform(
                            alignment: Alignment.center,
                            transform: Matrix4.identity()
                              ..setEntry(3, 2, 0.0012)
                              ..rotateY(angle),
                            child: showFront
                                ? _Front(
                                    pose: pose,
                                    hint: '点一下翻面看怎么拍',
                                  )
                                : Transform(
                                    alignment: Alignment.center,
                                    // 背面镜像回来，否则字是反的
                                    transform: Matrix4.identity()
                                      ..rotateY(math.pi),
                                    child: _Back(pose: pose),
                                  ),
                          );
                        },
                      ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          _flipButton(),
          const SizedBox(height: 12),
          // v0.9.0 环境&机位&姿势 指导：指导卡提到**最前**（原来排在「拍摄要点」
          // 后面，小白得先翻完要点才看到怎么拍），并把机位术语翻成人话。
          if (g != null) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('这张怎么拍',
                        style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    for (final line in poseGuidanceLines(g))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              width: 52,
                              child: Text(
                                line.label,
                                style: const TextStyle(
                                    fontSize: 12,
                                    color: Colors.white54,
                                    fontWeight: FontWeight.w600),
                              ),
                            ),
                            Expanded(
                              child: Text(line.text,
                                  style:
                                      const TextStyle(fontSize: 13, height: 1.45)),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
          ],
          if (g != null) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('这张为什么好看',
                        style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 6),
                    Text(g.why, style: const TextStyle(height: 1.5)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
          ],
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('拍摄要点',
                      style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 6),
                  for (final t in pose.tips)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('· '),
                          Expanded(child: Text(t)),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// 翻面卡片的正面：照片本身。
class _Front extends StatelessWidget {
  const _Front({required this.pose, required this.hint});

  final Pose pose;
  final String hint;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        // 无照片的姿势（脏数据 / 将来混进的火柴人）退回占位图 ——
        // 不然 `imagePath!` 直接崩详情页（v1 就有过类似崩溃史）。
        pose.hasPhoto
            ? Image.asset(
                pose.imagePath!,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => const ColoredBox(
                  color: Colors.black26,
                  child: Center(
                    child:
                        Icon(Icons.broken_image_outlined, color: Colors.white24),
                  ),
                ),
              )
            : const ColoredBox(
                color: Colors.black26,
                child: Center(
                  child:
                      Icon(Icons.broken_image_outlined, color: Colors.white24),
                ),
              ),
        Align(
          alignment: Alignment.bottomCenter,
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 10),
            color: Colors.black54,
            child: Text(
              hint,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12, color: Colors.white70),
            ),
          ),
        ),
      ],
    );
  }
}

/// 翻面卡片的背面：镜头 / 方向 / 景别 / 动作 / 表情 / 为什么好看。
class _Back extends StatelessWidget {
  const _Back({required this.pose});

  final Pose pose;

  @override
  Widget build(BuildContext context) {
    final g = pose.guidance;
    if (g == null) {
      return const ColoredBox(
        color: Colors.black26,
        child: Center(child: Text('这张没有指导数据')),
      );
    }
    Widget row(String k, String v) => Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 56,
                child: Text(k,
                    style: const TextStyle(
                        fontSize: 12,
                        color: Colors.white54,
                        fontWeight: FontWeight.w600)),
              ),
              Expanded(
                child: Text(v, style: const TextStyle(fontSize: 13, height: 1.45)),
              ),
            ],
          ),
        );

    return Container(
      color: const Color(0xFF1E1E24),
      padding: const EdgeInsets.fromLTRB(14, 16, 14, 12),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            row('镜头', '${g.cameraHeight} · ${g.direction} · ${g.framing}'),
            row('动作', g.action),
            row('表情', g.expression),
            row('好看', g.why),
          ],
        ),
      ),
    );
  }
}
