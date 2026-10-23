#!/usr/bin/env bash
# 摄影助手 v2 · v0.4.0 交付脚本
#
# 作用：把仓库里构建好的 APK 复制到交付文件夹 ~/Desktop/app/，
#       并更新版本记录（add-only，不覆盖旧文件）。幂等：重复跑安全。
#
# 用法（任何目录）：
#   bash ~/Desktop/Sylph/Carror_Base_OS/apps/photo_coach_v2/tool/deliver_v0.4.0.sh
#
# v0.4.0 第二次交付说明：同版本号同 build（2004），内容多了两处修复
#   （设置页 API Key 配置 / 预览左右黑边）。同 build 号直接覆盖安装。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && /bin/pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && /bin/pwd)"
SRC_APK="$APP_DIR/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk"
DEST_DIR="$HOME/Desktop/app"
DEST_APK="$DEST_DIR/versions/摄影助手v2-v0.4.0.apk"

[ -f "$SRC_APK" ] || { echo "❌ 找不到构建产物：$SRC_APK"; echo "   先跑: bash $APP_DIR/tool/build_apk.sh"; exit 1; }
mkdir -p "$DEST_DIR/versions"

cp "$SRC_APK" "$DEST_APK"
SHA=$(shasum -a 256 "$DEST_APK" | awk '{print $1}')
SIZE_MB=$(ls -la "$DEST_APK" | awk '{printf "%.1f", $5/1000000}')
echo "✅ 已复制 $DEST_APK （${SIZE_MB} MB, sha256 $SHA ）"

cat > "$DEST_DIR/versions/摄影助手v2-v0.4.0.txt" <<EOF
摄影助手 v2 · v0.4.0 (build 2004)
========================================

⚠️ 这是 v2 App 的**覆盖升级**（同包名 com.photocoach.photo_coach_v2）
  直接安装即可，会覆盖 v0.3.0，数据不受影响。

代码版本: $(cd "$APP_DIR/../../.." && git rev-parse --short HEAD 2>/dev/null || echo 未知)（分支 photo-coach-v2-rebuild）
sha256:   $SHA
测试:     503 个用例全过 / flutter analyze 0 issue
红线审计: 无谷歌依赖审计通过（依赖层 / 合并清单层 / 原生库层 三层全查）
权限:     本版无新增（读相册权限 v0.3.0 已有，正好用来接系统相机拍的照片）

这一版有什么（v2 渐进迁移第 5 站：预览 + 系统相机分工）
------------------------------------------------

1. 「拍摄」tab 改名「预览」：
   · App 内取景的一切功能**原样保留**（点按对焦 / 曝光 / 九宫格 /
     实时引导 / 姿势叠层）——这一版只是改了"快门"的用途

2. 快门按钮从「拍照」变成「打开系统相机」：
   · 在预览里把位置、光线、pose 都调好了 → 点快门 →
     App 静默退到后台，拉起**系统相机**
   · 产品逻辑：取景和姿势调整用 App 内的实时引导 + 姿势叠层，
     最后那一张交给系统相机拍（对焦、防抖、画质都更好）——
     App 不跟系统相机抢活，只做引导和点评

3. 拍完回来自动接图：
   · 从系统相机回到 App → 自动从相册捞刚拍的那张 →
     弹出「系统相机拍好了」卡（照片 + 一键送教练点评 + 重拍）

4. 取消了也没事：
   · 系统相机里没拍直接退出 → App 显示「没检测到新照片」，
     预览继续可用，可以重新调

5. 教练 / 姿势 tab 功能与 v0.3.0 相同（回归不变）。

这次重发修了两个问题（你上次的反馈）：
6. **设置页可以填 API Key 了**：预览右上角齿轮 → 设置 →
   最上面就是「模型配置」（表单直接展开）。填 Key 保存 →
   教练页立刻能用 AI 点评，不用再翻教练页找入口。
   Key 只存你这台手机（不进包、不上传）。
7. **预览不再有左右黑边**：画面撑满屏幕宽度（上下留黑是
   相机取景的正常样子）。

还没有的（按里程碑继续）：
  · v0.5.0 端上测量（无谷歌的骨架测量实现，红线项）
  · v1.0.0 与旧版 v0.19.2 功能对齐

装完试（这一版请在华为上验这 9 件事，逐条回报）：
  1. 点图标 → 能打开、不闪退（和之前一样的底线）
  2. 预览 tab → App 内取景回归正常（点按对焦 / 曝光 / 九宫格 /
     实时引导 / 姿势叠层 —— 和 v0.3.0 一样没坏）
  3. 预览调好 → 点快门 → App 退后台、系统相机打开（App 界面变暗）
  4. 系统相机里拍一张 → 回 App → 自动弹「系统相机拍好了」卡
  5. 再点一次快门 → 这次系统相机里不拍，直接退出 →
     显示「没检测到新照片」，预览还能继续
  6. 结果卡上点「送教练点评」→ 出点评卡（没填 Key 带
     「本地规则（离线兜底）」标；填过 Key 出 AI 点评）
  7. 教练 / 姿势 tab 随便点一下 → 正常（回归）
  8. 预览右上角齿轮 → 设置页 → 「模型配置」表单在最上面 →
     填一个 DeepSeek Key 保存 → 状态变「已配置 —— 直连 DeepSeek
     （deepseek-v4-flash，Key 存本机）」（没有 Key 的话跳过这条，
     看状态是「未配置 —— 点这里填 API Key…」就算过）
  9. 回到教练页送一张照片点评 → 出 **AI 点评**（证明 Key 跨页生效，
     不用再回设置页找）；另外留意预览画面**左右没有黑边**

另外：v0.3.0 那次请验的 6 件事（打开 / 拍摄回归 / 教练出卡 / 填 Key / 再拍 / 视频点评）
        和 v0.2.0 的 6 件事，如果还没回报，方便的话这次一起带一句。
EOF

# 更新「最新版本」指针（这个文件是给人看的入口，直接改写）
cat > "$DEST_DIR/最新版本.txt" <<EOF
当前最新版本：v2 v0.4.0 (build 2004)  ← 预览 · 系统相机版（重发）

要装的 APK：
  versions/摄影助手v2-v0.4.0.apk
  （同包名覆盖升级，直接装即可）

这个版本改了什么：
  · 预览 · 系统相机分工（快门跳系统相机，回来自动接图）
  · 重发修复：设置页可直接填 API Key（保存后教练页 AI 立即可用）
  · 重发修复：预览左右黑边消除（撑满屏宽）
  详情：versions/摄影助手v2-v0.4.0.txt

全部版本历史：
  RELEASES.md

sha256（校验文件没坏）：
  $SHA

⚠️ 这一版的核心流程：预览里调好光线/姿势/构图 → 点快门 →
  系统相机拍 → 回来自动接图 → 一键送教练点评。
验收 9 件事：打开 / 预览回归 / 快门跳系统相机 / 回来接图 /
  取消路径 / 送教练 / 教练姿势回归 / 设置页填 Key 出 AI 点评 / 预览无左右黑边。
EOF

# RELEASES.md 追加 v2 v0.4.0 段落（add-only）
V2_SECTION=$(cat <<EOF

---

## 【v2 重建】v0.4.0 (build 2004) —— $(date '+%Y-%m-%d %H:%M')

> 渐进迁移第 5 站：拍摄流程重构（F1）。用户拍板的设计：
> 「拍摄模块功能不变，名字改为预览，用户在预览区域觉得可以拍摄后，
> 点击拍摄按钮跳转原生相机；app 后台静默……在预览时调整 pose，
> 觉得位置光线 pose 都好了之后，跳到原生相机拍照。」
> 拍完回来 → 自动从 MediaStore 捞最新照片 → 展示 + 一键送教练点评。
> 同 build 重发（build 2004）修复：设置页 API Key 配置入口 + 预览左右黑边。

- **APK**: \`versions/摄影助手v2-v0.4.0.apk\`（${SIZE_MB} MB，arm64-v8a）
- **sha256**: \`${SHA}\`
- **测试**: 503 pass / analyze 0 issue（新增设置页 Key 用例 4 条：
  未配置展开 / 输入保存写 SharedPreferences / 已存读回收起 / 中转状态；
  camera_page_test 35 条不变；Kotlin 原生桥 MethodChannel
  photo_coach.v2/native_camera：launchNativeCamera / latestImageSince）
- **红线审计**: 无谷歌依赖审计通过（tool/check_no_google.sh，三层）
- **权限**: 无新增（READ_MEDIA_IMAGES v0.3.0 已申请，正好用于读回系统相机照片）

### 这一版有什么

「拍摄」→「预览」：App 内取景功能全保留（对焦/曝光/九宫格/实时引导/姿势叠层），
快门改跳系统相机；回来自动接图（MediaStore 按 DATE_ADDED 捞 since 时刻后的最新张，
拷入缓存目录展示）；取消路径给明确提示。端上测量（骨架）留 v0.5.0。

重发修复（用户实机反馈）：模型配置卡抽成共享组件，设置页顶部直接可填 Key
（AppSession 持有 ModelConfigStore，教练页与设置页同实例，保存即双向生效，
Pref Key 名与 v0.3.0 完全一致，老 Key 无缝续用）；预览分辨率改用保证强制 4:3 的
低档（ResolutionPreset.low，横屏传感器 4:3 与竖屏 contain 严丝合缝，消除左右黑边，
代价是预览画质降为取景辅助级别——出片走系统相机，不影响成片）。
EOF
)
if grep -q "【v2 重建】v0.4.0" "$DEST_DIR/RELEASES.md" 2>/dev/null; then
  if grep -qF "$SHA" "$DEST_DIR/RELEASES.md" 2>/dev/null; then
    echo "RELEASES.md 已有 v0.4.0 段落且 sha 一致，跳过（幂等）"
  else
    # 同 build 号重发：段落已存在但记录的是旧 sha → 原地刷新 sha + 段落时间，
    # 不重复追加（add-only 指的是不覆盖**别的版本**的记录）。
    # 测试数一行不动：它描述的是「当次构建时的测试结果」，重发内容变化
    # 由 txt 文件（每次重写）如实记录，这里不假装重写历史。
    awk -v sha="$SHA" -v now="$(date '+%Y-%m-%d %H:%M')" '
      /^## 【v2 重建】v0.4.0 / { insec = 1 }
      insec && /^## / && $0 !~ /^## 【v2 重建】v0.4.0 / { insec = 0 }
      insec && $0 ~ /^## 【v2 重建】v0.4.0 / {
        sub(/ —— .*/, " —— " now)
        print; next
      }
      insec && $0 ~ /^- \*\*sha256\*\*/ {
        printf "- **sha256**: `%s`\n", sha; next
      }
      { print }
    ' "$DEST_DIR/RELEASES.md" > "$DEST_DIR/RELEASES.md.tmp" && mv "$DEST_DIR/RELEASES.md.tmp" "$DEST_DIR/RELEASES.md"
    echo "✅ RELEASES.md v0.4.0 段落已原地刷新（同 build 2004 重发，sha 更新为本次构建）"
  fi
else
  printf '%s\n' "$V2_SECTION" >> "$DEST_DIR/RELEASES.md"
  echo "✅ 已追加 v0.4.0 段落 → RELEASES.md"
fi

echo
echo "完成。现在可以装包了："
echo "  adb install -r \"$DEST_APK\"    （或 Android Studio / 数据线拖装）"
echo
echo "装完请在华为上验 9 件事（详见 versions/摄影助手v2-v0.4.0.txt 末尾）："
echo "  打开 / 预览回归 / 快门跳系统相机 / 回来接图 / 取消路径 / 送教练 /"
echo "  教练姿势回归 / 设置页填 Key 出 AI 点评 / 预览无左右黑边"
