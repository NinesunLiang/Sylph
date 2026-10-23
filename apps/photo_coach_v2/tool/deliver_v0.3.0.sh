#!/usr/bin/env bash
# 摄影助手 v2 · v0.3.0 交付脚本
#
# 作用：把仓库里构建好的 APK 复制到交付文件夹 ~/Desktop/app/，
#       并更新版本记录（add-only，不覆盖旧文件）。幂等：重复跑安全。
#
# 用法（任何目录）：
#   bash ~/Desktop/Sylph/Carror_Base_OS/apps/photo_coach_v2/tool/deliver_v0.3.0.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && /bin/pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && /bin/pwd)"
SRC_APK="$APP_DIR/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk"
DEST_DIR="$HOME/Desktop/app"
DEST_APK="$DEST_DIR/versions/摄影助手v2-v0.3.0.apk"

[ -f "$SRC_APK" ] || { echo "❌ 找不到构建产物：$SRC_APK"; echo "   先跑: bash $APP_DIR/tool/build_apk.sh"; exit 1; }
mkdir -p "$DEST_DIR/versions"

cp "$SRC_APK" "$DEST_APK"
SHA=$(shasum -a 256 "$DEST_APK" | awk '{print $1}')
SIZE_MB=$(ls -la "$DEST_APK" | awk '{printf "%.1f", $5/1000000}')
echo "✅ 已复制 $DEST_APK （${SIZE_MB} MB, sha256 $SHA ）"

cat > "$DEST_DIR/versions/摄影助手v2-v0.3.0.txt" <<EOF
摄影助手 v2 · v0.3.0 (build 2003)
========================================

⚠️ 这是 v2 App 的**覆盖升级**（同包名 com.photocoach.photo_coach_v2）
  直接安装即可，会覆盖 v0.2.0，数据不受影响。

代码版本: $(cd "$APP_DIR/../../.." && git rev-parse --short HEAD 2>/dev/null || echo 未知)（分支 photo-coach-v2-rebuild）
sha256:   $SHA
测试:     485 个用例全过 / flutter analyze 0 issue
红线审计: 无谷歌依赖审计通过（依赖层 / 合并清单层 / 原生库层 三层全查）
权限:     本版新增 INTERNET（教练要联网调 DeepSeek，仅直连/中转时用）

这一版有什么（v2 渐进迁移第 4 站：教练页上线）
------------------------------------------------

1. **教练 tab 活了**（v0.1.0/v0.2.0 里是「迁移中」占位）：
   · 拍照 → 出 AI 点评卡（构图建议 + 逐条说明）
   · 也支持录 5 秒视频再点评（取帧分析）
   · **没填 Key 也能用**：走本地规则兜底，卡上会标「本地规则（离线兜底）」

2. 模型配置卡（教练页顶部，默认收起一行，点「模型配置」展开）：
   · 在这里填你的 API Key → 只存在这台手机上（SharedPreferences），
     **不打进 APK、不进代码仓库**，一次填写长期有效
   · 默认模型 deepseek-v4-flash（和 dsh 同款）+ DeepSeek 官方接口直连；
     模型名、接口地址都可改
   · 想走 Mac 中转：接口地址填 http://<Mac的IP>:8787/analyze，
     检测到 http:// 开头会自动切中转模式（Key 改存 Mac 侧，
     手机不用存 Key，手机和 Mac 需同一 WiFi）

3. 中转服务（可选，不装也能用）：
   cd apps/photo_coach_v2/server
   cp .env.example .env   # 把 DeepSeek Key 填进 .env
   node server.mjs        # 监听 8787

4. 拍摄 / 姿势 / 实时引导 功能与 v0.2.0 相同（回归不变）。

还没有的（按里程碑继续）：
   · v0.5.0 端上测量（无谷歌的骨架测量实现，红线项）
   · v1.0.0 与旧版 v0.19.2 功能对齐

装完试（这一版请在华为上验这 6 件事，逐条回报）：
  1. 点图标 → 能打开、不闪退（和之前一样的底线）
  2. 拍摄 tab → 还能正常拍照（回归：v0.2.0 的东西没坏）
  3. 教练 tab 拍一张 → 出点评卡（没填 Key 应带「本地规则（离线兜底）」标）
  4. 展开「模型配置」→ 填真实 Key → 保存 → 状态变「已配置 —— 直连 DeepSeek」
  5. 再拍一张 → 点评卡是 AI 出的（离线标消失，内容有具体建议）
  6. 教练 tab 录 5 秒视频 → 也能出点评

另外：v0.2.0 那次请验的 6 件事（打开/取景/对焦/存相册/实时引导/姿势联动）
      如果还没回报，方便的话这次一起带一句。
EOF

# 更新「最新版本」指针（这个文件是给人看的入口，直接改写）
cat > "$DEST_DIR/最新版本.txt" <<EOF
当前最新版本：v2 v0.3.0 (build 2003)  ← 教练页上线版

要装的 APK：
  versions/摄影助手v2-v0.3.0.apk
  （同包名覆盖升级 v0.2.0，直接装即可）

这个版本改了什么：
  versions/摄影助手v2-v0.3.0.txt

全部版本历史：
  RELEASES.md

sha256（校验文件没坏）：
  $SHA

⚠️ 教练要用 AI 的话，在教练页「模型配置」卡里填一次 API Key
  （只存这台手机）。不填也能用（本地规则兜底，卡上会标注）。
  这一版验收 6 件事：打开 / 拍摄回归 / 教练出卡 / 填 Key / 再拍 / 视频点评。
EOF

# RELEASES.md 追加 v2 v0.3.0 段落（add-only）
V2_SECTION=$(cat <<EOF

---

## 【v2 重建】v0.3.0 (build 2003) —— $(date '+%Y-%m-%d %H:%M')

> 渐进迁移第 4 站：教练（F2 AI 点评链路）。Key 处理经用户拍板改为
> 客户端自助：教练页「模型配置」卡填 Key → SharedPreferences 只存本机，
> 不进 APK、不进 git；中转服务（server/server.mjs）保留为可选项。

- **APK**: \`versions/摄影助手v2-v0.3.0.apk\`（${SIZE_MB} MB，arm64-v8a）
- **sha256**: \`${SHA}\`
- **测试**: 485 pass / analyze 0 issue（v0.2.0 的 299 基础上，迁回教练/LLM 相关 7 个测试文件 + 新增 4 个配置卡用例）
- **红线审计**: 无谷歌依赖审计通过（tool/check_no_google.sh，三层）
- **权限**: 新增 INTERNET（教练直连/中转需要）；新增 network_security_config
  （允许局域网明文 HTTP，仅中转场景用；官方直连是 HTTPS 不受影响）
- **Key 安全**: 客户端输入 → shared_preferences 本机存储；无 --dart-define 烘焙、
  无硬编码；APK 审计无 Key 痕迹

### 这一版有什么

教练 tab 上线：拍照/录 5s 视频 → DeepSeek（默认 deepseek-v4-flash）出构图点评卡；
无 Key 时本地规则离线兜底（带标注）。模型配置卡可折叠（默认收起，首屏按钮可见性纪律）。
端上测量（骨架）留 v0.5.0。
EOF
)
if grep -q "【v2 重建】v0.3.0" "$DEST_DIR/RELEASES.md" 2>/dev/null; then
  echo "RELEASES.md 已有 v0.3.0 段落，跳过追加（幂等）"
else
  printf '%s\n' "$V2_SECTION" >> "$DEST_DIR/RELEASES.md"
  echo "✅ 已追加 v0.3.0 段落 → RELEASES.md"
fi

echo
echo "完成。现在可以装包了："
echo "  adb install -r \"$DEST_APK\"    （或 Android Studio / 数据线拖装）"
echo
echo "装完请在华为上验 6 件事（详见 versions/摄影助手v2-v0.3.0.txt 末尾）："
echo "  打开 / 拍摄回归 / 教练出卡 / 填 Key / 再拍 / 视频点评"
