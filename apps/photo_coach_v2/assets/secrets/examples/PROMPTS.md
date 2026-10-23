# 拍照秘诀 6 招 — ComfyUI 生图规格

每招需要 **2 张图**（正确 ✓ / 错误 ✗），统一风格。

## 通用规格

| 项 | 值 |
|---|---|
| 尺寸 | 540×960（9:16 竖版，和拍摄页取景框同比例） |
| 风格 | 写实手机摄影模拟（模拟手机后置相机拍摄效果，轻微噪点，自然色温） |
| 画面 | 单张完整照片，不是拼贴；一张正面（正确），一张反面（错误） |
| 主体 | 年轻女性，穿简单休闲装（避免品牌 logo），户外/室内自然场景 |
| 构图 | 竖构图 9:16（模拟手机竖拍），人物占画面 60-70% |
| 标注 | 不加任何文字/水印/箭头，纯照片（标注由 App UI 叠加） |

## 文件命名

```
assets/secrets/examples/
  lighting_good.jpg    光 · 正确
  lighting_bad.jpg     光 · 错误
  angle_good.jpg       角度 · 正确
  angle_bad.jpg        角度 · 错误
  distance_good.jpg    距离 · 正确
  distance_bad.jpg     距离 · 错误
  composition_good.jpg 构图 · 正确
  composition_bad.jpg  构图 · 错误
  height_good.jpg      手机高度 · 正确
  height_bad.jpg       手机高度 · 错误
  timing_good.jpg      快门时机 · 正确
  timing_bad.jpg       快门时机 · 错误
```

## 每招详细 Prompt

### 1. 光（lighting）

**正确 `lighting_good.jpg`**
```
A young woman standing by a large bright window indoors, facing the window, soft natural light illuminating her face evenly, warm golden tone, gentle shadows, she is smiling naturally, shallow depth of field, background is a cozy living room with plants, shot on phone camera, vertical 3:4 aspect ratio, photorealistic, 35mm equivalent
```
要点：人面朝窗，脸上光均匀，背景虚化。

**错误 `lighting_bad.jpg`**
```
A young woman standing with her back to a bright window, face in deep shadow and silhouette, blown-out background, face completely dark and unreadable, harsh backlight creating halo around hair, shot on phone camera, vertical 3:4 aspect ratio, photorealistic
```
要点：人背对窗（逆光），脸全黑，看不清五官。

---

### 2. 角度（angle）

**正确 `angle_good.jpg`**
```
A young woman standing outdoors in a park, photographed from eye-level at a straight-on angle, phone held at her eye height, natural flattering proportions, full body visible from knees up, green blurred background, soft afternoon light, shot on phone camera, vertical 3:4 aspect ratio, photorealistic
```
要点：手机举到对方眼睛高度，正面平拍，比例自然。

**错误 `angle_bad.jpg`**
```
A young woman photographed from a very low angle looking up (phone held at waist level pointing up), her face is distorted with wide jaw and small head, unflattering perspective distortion, she looks hunched, shot on phone camera, vertical 3:4 aspect ratio, photorealistic
```
要点：手机放很低仰拍，下巴突出、头变小、比例失调。

---

### 3. 距离（distance）

**正确 `distance_good.jpg`**
```
A young woman at a restaurant table, phone held 1.5 meters away at 45-degree angle above the table, a plate of colorful food is sharp and detailed, background slightly blurred, natural warm restaurant lighting, appetizing food photography, vertical 3:4 aspect ratio, photorealistic
```
要点：合理距离 + 45° 俯拍食物，主体清晰。

**错误 `distance_bad.jpg`**
```
A young woman at a restaurant table, food photographed with extreme digital zoom (3x or 4x pinch-zoom on phone), image is grainy, blurry, noisy, low resolution crop of a small portion of the plate, visible compression artifacts, shot on phone camera, vertical 3:4 aspect ratio
```
要点：捏屏数码变焦，画面糊、噪点大、裁切感明显。

---

### 4. 构图（composition）

**正确 `composition_good.jpg`**
```
A young woman standing in a clean minimal space, single subject centered, simple uncluttered background (plain wall or solid color), rule-of-thirds grid lines visible as subtle overlay, she occupies the central intersection point, negative space balanced, shot on phone camera, vertical 3:4 aspect ratio, photorealistic, editorial style
```
要点：主体居中/三分线交点，背景干净无杂物。

**错误 `composition_bad.jpg````
A young woman in a busy street scene, crowded background with many people, signs, trash, power lines, and clutter, subject small and lost in the frame, visual chaos, no clear focal point, shot on phone camera, vertical 3:4 aspect ratio, photorealistic
```
要点：背景杂乱（路人/招牌/电线），主体淹没，没有焦点。

---

### 5. 手机高度（height）

**正确 `height_good.jpg`**
```
A young woman standing, photographed with phone at her chest height (slightly below eye level), natural proportions, legs look long, shoulders balanced, full body from mid-thigh up, clean background, soft light, shot on phone camera, vertical 3:4 aspect ratio, photorealistic
```
要点：手机在胸口高度（略低于眼睛），比例自然显腿长。

**错误 `height_bad.jpg`**
```
A young woman standing, photographed with phone at knee height looking straight up, her legs appear very short, body looks stubby and distorted, unflattering low angle making her look squat, shot on phone camera, vertical 3:4 aspect ratio, photorealistic
```
要点：手机在膝盖高度仰拍，腿短、身体矮胖、比例失调。

---

### 6. 快门时机（timing）

**正确 `timing_good.jpg`**
```
A young woman mid-laugh, hair slightly flowing from a natural breeze, caught at the peak of the smile with eyes crinkled, genuine joyful expression frozen in time, soft bokeh background, golden hour warm light, shot on phone camera, vertical 3:4 aspect ratio, photorealistic, candid
```
要点：大笑/甩发的高光瞬间，表情自然生动。

**错误 `timing_bad.jpg`**
```
A young woman mid-blink, eyes half-closed, caught in an awkward frozen moment, expression is blank and unengaged, hair static, stiff pose, flat lighting, shot on phone camera, vertical 3:4 aspect ratio, photorealistic, candid
```
要点：半闭眼/僵硬/表情空洞，时机不对。

---

## App 端 UI 说明

详情页布局（从列表卡片点进去，上下竖排）：

```
┌─────────────────────────────────┐
│ ←  招 1 · 光                    │  ← AppBar
├─────────────────────────────────┤
│ ✓ 正确                          │  ← 标签（左对齐）
│ ┌─────────────────────────────┐ │
│ │                             │ │
│ │     good.jpg (9:16)         │ │  ← 和拍摄页取景框同尺寸
│ │                             │ │
│ └─────────────────────────────┘ │
│                                 │
│ ✗ 错误                          │
│ ┌─────────────────────────────┐ │
│ │                             │ │
│ │     bad.jpg (9:16)          │ │
│ │                             │ │
│ └─────────────────────────────┘ │
├─────────────────────────────────┤
│  · 让人面朝光源站…             │
│  · 在家里就用窗户…             │  ← 三句话
│  · 太阳太狠的时候…             │
└─────────────────────────────────┘
```

- 图片未就位前显示 SVG 占位（站位符号）
- 图片就位后直接 `Image.asset()` 加载
- pubspec assets 已注册 `assets/secrets/`（递归包含 examples/）
