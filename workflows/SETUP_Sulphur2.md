# Sulphur 2 本地部署工作流配置

> 来源: https://www.freedidi.com/24142.html
> 模型: Sulphur 2 (无审查 AI 视频模型)
> 前端: ComfyUI + LTX-Video 2.3

---

## 概述

这是一个基于 **ComfyUI + LTX-Video 2.3** 的 Sulphur 2 视频生成工作流，支持：
- **文生视频** (Text-to-Video) — 下载的工作流
- **图生视频** (Image-to-Video) — ComfyUI 内置模板

最低显存要求: **8G**（使用 GGUF 蒸馏版模型）

---

## 文件清单

```
workflows/
├── sulphur2_ltxv_t2v.json       # 文生视频工作流（已下载）
└── sulphur2_ltxv_i2v.json       # 图生视频工作流（见下文指引）
```

## 部署步骤

### 1. 安装 ComfyUI

下载最新版 ComfyUI 客户端：
- 官网: https://comfy.org/
- 夸克网盘备用: https://pan.quark.cn/s/5ffd1cfd41e8

安装后建议升级到最新版本。

### 2. 下载 Sulphur 2 模型

**满血版**（需 32G+ 显存）:
- HuggingFace: https://huggingface.co/SulphurAI/Sulphur-2-base
- 夸克网盘: https://pan.quark.cn/s/a25fdae551e7

**蒸馏版 (GGUF)**（8G+ 显存，推荐）:
- HuggingFace: https://huggingface.co/vantagewithai/LTX2.3-10Eros-GGUF
- 夸克网盘: https://pan.quark.cn/s/885d0d39ed60

模型放置路径:
```
ComfyUI/models/checkpoints/ltx-av-step-1751000_vocoder_24K.safetensors
```

### 3. 文生视频工作流

1. 打开 ComfyUI
2. 将 `workflows/sulphur2_ltxv_t2v.json` 拖入 ComfyUI 界面
3. 在文本输入框中填写你的提示词
4. 点击生成

### 4. 图生视频工作流

1. 在 ComfyUI 中，点击菜单 → 模板 → 视频
2. 选择 **LTX-2.3:图生视频** 模板
3. 加载后，将默认的主模型切换为 Sulphur 2 模型
4. 上传图片，点击生成

---

## 工作流节点详解

### 文生视频 (video_ltx2_3_t2v.json)

共 **26 个 API 节点** + **46 个子图节点**

| # | 节点名称 | 类型 | 关键参数 |
|---|---------|------|---------|
| 1 | Load Checkpoint | CheckpointLoaderSimple | 模型: `ltx-av-step-1751000_vocoder_24K.safetensors` |
| 2 | Gemma 3 Model Loader | LTXVGemmaCLIPModelLoader | max_length: 1024 |
| 3 | CLIP Text Encode (正) | CLIPTextEncode | 输入你的正面提示词 |
| 4 | CLIP Text Encode (负) | CLIPTextEncode | `blurry, low quality, still frame...` |
| 8 | KSamplerSelect | KSamplerSelect | sampler: `euler` |
| 9 | LTXVScheduler | LTXVScheduler | steps: 20, max_shift: 2.05, base_shift: 0.95 |
| 11 | RandomNoise | RandomNoise | seed: 10 |
| 12 | VAE Decode | VAEDecode | - |
| 13 | Audio VAE Loader | LTXVAudioVAELoader | 同主模型 |
| 14 | Audio VAE Decode | LTXVAudioVAEDecode | - |
| 15 | Video Combine | VHS_VideoCombine | format: h264-mp4, fps: 25 |
| 17 | Multimodal Guider | MultimodalGuider | skip_blocks: 29 |
| 18 | Guider Params (Video) | GuiderParameters | cfg: 3, modality: VIDEO |
| 19 | Guider Params (Audio) | GuiderParameters | cfg: 7, modality: AUDIO |
| 22 | LTXVConditioning | LTXVConditioning | frame_rate: 25 |
| 23 | Float Constant | FloatConstant | value: 25 (fps) |
| 26 | Empty Latent Audio | LTXVEmptyLatentAudio | batch: 1 |
| 27 | INT Constant | INTConstant | value: 105 (帧数) |
| 28 | Concat AV Latent | LTXVConcatAVLatent | 合并视频+音频潜空间 |
| 29 | Separate AV Latent | LTXVSeparateAVLatent | 分离视频+音频潜空间 |
| 41 | SamplerCustomAdvanced | SamplerCustomAdvanced | 核心采样器 |
| 43 | Empty Latent Video | EmptyLTXVLatentVideo | 768x512, 105帧 |
| 44 | MultiGPU Patcher | LTXVSequenceParallelMultiGPUPatcher | torch_compile: True |

### 输出尺寸
- **视频**: 768 x 512, 105 帧 (~4.2s @ 25fps)
- **格式**: H.264 MP4
- **音频**: 同步生成

---

## 下载链接汇总

| 资源 | 链接 | 说明 |
|------|------|------|
| ComfyUI | https://comfy.org/ | 最新版客户端 |
| ComfyUI (备用) | https://pan.quark.cn/s/5ffd1cfd41e8 | 夸克网盘 |
| Sulphur 2 满血版 | https://huggingface.co/SulphurAI/Sulphur-2-base | 需32G显存 |
| Sulphur 2 满血版(备用) | https://pan.quark.cn/s/a25fdae551e7 | 夸克网盘 |
| Sulphur 2 GGUF 蒸馏版 | https://huggingface.co/vantagewithai/LTX2.3-10Eros-GGUF | 8G显存可用 |
| Sulphur 2 GGUF(备用) | https://pan.quark.cn/s/885d0d39ed60 | 夸克网盘 |
| 文生视频工作流 | `workflows/sulphur2_ltxv_t2v.json` | 已下载到本地 |
