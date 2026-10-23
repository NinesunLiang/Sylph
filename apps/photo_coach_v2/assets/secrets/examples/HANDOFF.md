# 拍照秘诀 6 招 — ComfyUI 生图交接文档

> 本文档给本地 AI 用：照着生成 12 张图，放到指定路径，App 即自动加载。

## 输出规格（所有图统一）

| 项 | 值 |
|---|---|
| 尺寸 | **540 × 960 px**（9:16 竖版） |
| 格式 | JPG，质量 90+ |
| 风格 | 写实手机摄影（模拟手机后置摄像头，轻微 JPEG 噪点，自然色温，不要过度 HDR） |
| 主体 | 年轻亚洲女性，25 岁左右，穿简单休闲装（纯色 T 恤/连衣裙，**无品牌 logo、无文字**） |
| 禁止 | 不加任何文字、水印、箭头、边框、标注（标注由 App UI 叠加） |
| 构图 | 人物占画面 60-70%，背景虚化或自然 |

## 文件命名与放置路径

```
apps/photo_coach_v2/assets/secrets/examples/
├── lighting_good.jpg
├── lighting_bad.jpg
├── angle_good.jpg
├── angle_bad.jpg
├── distance_good.jpg
├── distance_bad.jpg
├── composition_good.jpg
├── composition_bad.jpg
├── height_good.jpg
├── height_bad.jpg
├── timing_good.jpg
└── timing_bad.jpg
```

生成完成后，把 12 张 jpg 放到上面目录。

## App 侧接入（生成完图片后执行）

编辑 `lib/features/coach/secrets_page.dart` 中的 `kSecretsTips` 列表，给每招填上路径：

```dart
SecretsTip(
  title: '光',
  summary: '人面朝光，脸好看',
  svg: 'assets/secrets/lighting.svg',
  goodImage: 'assets/secrets/examples/lighting_good.jpg',
  badImage: 'assets/secrets/examples/lighting_bad.jpg',
  points: [...],
),
```

6 招都填完后 `flutter build apk --release` 出包。pubspec assets 已注册 `assets/secrets/`（递归），无需额外配置。

---

## 12 张图详细 Prompt

### 1. 光 · 正确 — `lighting_good.jpg`

**场景**：室内窗边，自然光正面打脸。

**Prompt (EN)：**
```
A young Asian woman in her mid-20s, wearing a simple white crew-neck t-shirt, standing by a large bright window indoors, facing the window directly, soft natural window light illuminating her face evenly from the front, warm golden tone, gentle soft shadows on her face, she is smiling naturally with relaxed expression, shallow depth of field, background is a cozy living room with green plants slightly blurred, shot on iPhone rear camera, 35mm equivalent, natural color science, slight JPEG noise, 540x960 vertical
```

**要点**：人面朝窗 → 脸上光均匀明亮 → 五官清晰可读。

---

### 2. 光 · 错误 — `lighting_bad.jpg`

**场景**：同一人，但背对窗（逆光），脸全黑。

**Prompt (EN)：**
```
A young Asian woman in her mid-20s, wearing a simple white crew-neck t-shirt, standing with her back to a large bright window, face completely in dark shadow and unreadable, blown-out bright white background, harsh backlight creating a halo around her hair, her facial features are completely lost in darkness, silhouette effect, shot on iPhone rear camera, 35mm equivalent, natural color science, 540x960 vertical
```

**要点**：人背对窗 → 脸全黑看不清 → 背景过曝。对比图里一眼看出"反了"。

---

### 3. 角度 · 正确 — `angle_good.jpg`

**场景**：户外公园，手机举到对方眼睛高度，正面平拍。

**Prompt (EN)：**
```
A young Asian woman in her mid-20s, wearing a simple light blue casual dress, standing outdoors in a green park, photographed from straight-on at eye level, camera at her eye height, natural flattering body proportions, visible from mid-thigh up, soft afternoon sunlight, green foliage background with shallow depth of field bokeh, relaxed confident posture, shot on iPhone rear camera, 35mm equivalent, 540x960 vertical
```

**要点**：手机 = 对方眼睛高度 → 正面平拍 → 比例自然、显精神。

---

### 4. 角度 · 错误 — `angle_bad.jpg`

**场景**：同一人同地点，但手机放很低（腰以下）仰拍。

**Prompt (EN)：**
```
A young Asian woman in her mid-20s, wearing a simple light blue casual dress, standing outdoors in a green park, photographed from a very low angle looking up (camera at waist level pointing upward), her jaw appears wide and prominent, head looks small relative to body, unflattering perspective distortion, she appears to be looking down at camera, green park background, shot on iPhone rear camera, 24mm wide angle equivalent, 540x960 vertical
```

**要点**：手机很低仰拍 → 下巴突出、头身比失调 → 显矮显笨。

---

### 5. 距离 · 正确 — `distance_good.jpg`

**场景**：餐厅餐桌，手机在 1.5 米外 45° 俯拍一盘菜。

**Prompt (EN)：**
```
A colorful plate of food (stir-fried vegetables with shrimp) on a wooden restaurant table, photographed from 45 degrees above at about 1.5 meters distance, the food is sharp and detailed with visible textures, warm ambient restaurant lighting, background shows a blurred restaurant interior with soft bokeh, appetizing food photography, shot on iPhone rear camera, 35mm equivalent, 540x960 vertical
```

**要点**：合理距离 + 45° 俯拍 → 食物清晰有质感 → 背景自然虚化。

---

### 6. 距离 · 错误 — `distance_bad.jpg`

**场景**：同一桌菜，但用了 4x 数码变焦（捏屏放大）。

**Prompt (EN)：**
```
A plate of food on a restaurant table, photographed with extreme 4x digital zoom (pinch-to-zoom on phone), the image is grainy, blurry, and noisy, visible compression artifacts and pixelation, only a small cropped portion of the plate is visible, sharpness is very poor, warm restaurant lighting, shot on iPhone rear camera with 4x digital zoom, 540x960 vertical
```

**要点**：数码变焦 → 糊、噪点大、裁切感 → 和正确图对比明显。

---

### 7. 构图 · 正确 — `composition_good.jpg`

**场景**：干净极简背景，主体居中，大量留白。

**Prompt (EN)：**
```
A young Asian woman in her mid-20s, wearing a simple black turtleneck, standing centered in a clean minimal space with a plain warm beige wall behind her, no clutter, no other objects, large areas of negative space around her, she is the sole focal point, soft diffused lighting, editorial photography style, shot on iPhone rear camera, 50mm equivalent, 540x960 vertical
```

**要点**：主体居中 + 背景干净 → 一眼看到人 → 高级感。

---

### 8. 构图 · 错误 — `composition_bad.jpg`

**场景**：同一个人，但站在杂乱街道，背景满是干扰。

**Prompt (EN)：**
```
A young Asian woman in her mid-20s, wearing a simple black turtleneck, standing in a very busy cluttered street scene, background is chaotic with many pedestrians, colorful shop signs, power lines, trash cans, parked bicycles, and visual noise everywhere, the subject appears small and lost in the busy frame, no clear focal point, harsh midday lighting, shot on iPhone rear camera, 28mm equivalent, 540x960 vertical
```

**要点**：背景杂乱 → 主体淹没 → 眼睛不知道看哪里。

---

### 9. 手机高度 · 正确 — `height_good.jpg`

**场景**：拍站立女性，手机在对方胸口高度（略低于眼睛）。

**Prompt (EN)：**
```
A young Asian woman in her mid-20s, wearing a simple white top and jeans, standing in a clean indoor space, photographed with camera at chest height (slightly below eye level), natural flattering proportions, legs appear long, shoulders balanced, full body visible from mid-thigh up, soft even lighting, minimal background, shot on iPhone rear camera, 35mm equivalent, 540x960 vertical
```

**要点**：手机在胸口高度 → 比例自然 → 腿显得长。

---

### 10. 手机高度 · 错误 — `height_bad.jpg`

**场景**：同一人，手机在膝盖高度仰拍。

**Prompt (EN)：**
```
A young Asian woman in her mid-20s, wearing a simple white top and jeans, standing in a clean indoor space, photographed from knee height looking straight up, her legs appear very short, body looks stubby and compressed, unflattering extreme low angle making her look squat, wide-angle distortion at the bottom of frame, soft even lighting, minimal background, shot on iPhone rear camera, 24mm wide angle, 540x960 vertical
```

**要点**：手机在膝盖 → 腿短、身体压缩 → 比例失调。

---

### 11. 快门时机 · 正确 — `timing_good.jpg`

**场景**：大笑的巅峰瞬间，头发微动，表情生动。

**Prompt (EN)：**
```
A young Asian woman in her mid-20s, wearing a simple casual outfit, caught mid-laugh at the peak of genuine joy, eyes crinkled with happiness, hair slightly flowing from a natural breeze, frozen at the most expressive moment, golden hour warm backlight creating a rim light on her hair, soft bokeh background, candid photography feel, shot on iPhone rear camera, 35mm equivalent, 540x960 vertical
```

**要点**：大笑巅峰 + 头发微动 → 生动、有生命力 → "等出来的好照片"。

---

### 12. 快门时机 · 错误 — `timing_bad.jpg`

**场景**：半闭眼 / 表情僵硬的尴尬瞬间。

**Prompt (EN)：**
```
A young Asian woman in her mid-20s, wearing a simple casual outfit, caught mid-blink with eyes half-closed, expression is blank and unengaged, hair completely static, stiff rigid pose, flat uninteresting lighting, the photo looks like an awkward frozen moment that nobody would keep, candid photography feel, shot on iPhone rear camera, 35mm equivalent, 540x960 vertical
```

**要点**：半闭眼 + 僵硬 → 尴尬 → "时机不对"的典型。

---

## 验收 Checklist

生成完成后逐项确认：

- [ ] 12 张图全部 540×960 px
- [ ] 每张都是完整单张照片（不是拼贴/对比图）
- [ ] 无文字、无水印、无箭头
- [ ] 正确图和错误图是**同一场景/同一人**（只有拍法不同）——这样对比才有说服力
- [ ] 正确图看起来"好看/专业"，错误图看起来"明显有问题"
- [ ] 文件命名完全匹配上面列表
- [ ] 文件放在 `assets/secrets/examples/` 目录

## 生图参数建议（ComfyUI）

| 参数 | 建议值 |
|---|---|
| 采样器 | DPM++ 2M Karras 或 UniPC |
| 步数 | 25-35 |
| CFG | 5-7（写实风不要太高） |
| 分辨率 | 先 512×896 生成，再 upscale 到 540×960（或用 2x upscale 节点） |
| 负面提示（通用） | `cartoon, illustration, painting, drawing, 3d render, text, watermark, logo, arrow, border, frame, split screen, multiple people, deformed hands, extra fingers, blurry face` |
| 模型建议 | 写实向 checkpoint（如 Juggernaut XL / RealVis XL / 或你本地已有的写实模型） |

> ⚠️ 如果一次生成的图"正确/错误"不够对比明显，可以微调 prompt 中夸张程度（比如错误图把 distortion 写得更极端）。

## 完成后回传

生成完 12 张图后，把文件放到路径即可。如果需要我帮忙接入（填 `goodImage`/`badImage` 字段 + 出包），说一声。
