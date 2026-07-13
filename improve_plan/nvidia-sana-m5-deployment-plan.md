# NVIDIA Sana — M5 Pro 部署方案

> 调研时间: 2026-07-13 | 目标机型: MacBook Pro M5 (48GB)
> Todo: `SANA-RESEARCH` | 状态: 📋 方案已出，待执行

---

## 一、为什么选 Sana

NVIDIA + MIT 联合出品的线性 Diffusion Transformer，用 1/20 的参数达到接近 FLUX-12B 的质量。

| 模型 | 参数 | 速度 (vs FLUX) | 质量 | MPS 兼容 |
|:-----|:----:|:--------------:|:----:|:--------:|
| **Sana-0.6B** | 0.6B | **39×** 快于 FLUX-12B | DPG-Bench 接近 | ✅ 已验证 M4 1.9 it/s |
| **Sana-1.6B** | 1.6B | **23×** 快于 FLUX-12B | GenEval 持平 | ✅ 预期更快 |
| **SANA-Sprint** | 0.6B/1.6B | 单步生成, 0.1s on H100 | FID 7.04 > FLUX-schnell 7.94 | ⏳ 待验证 |
| **FLUX.2 [dev]** (当前) | 12B | 50步=40分钟 (MPS) | 最好 | ⚠️ MPS 全黑图 BUG |

---

## 二、图像生成部署

### 2.1 前置条件

```
✅ PyTorch 2.8.0 + MPS 可用
✅ 磁盘 293GB 空闲
✅ Python 3.11 (系统中)
```

### 2.2 步骤

```bash
# Step 1: 克隆仓库
git clone https://github.com/NVlabs/SANA.git ~/Desktop/Sana
cd ~/Desktop/Sana

# Step 2: 环境
python3.11 -m venv .venv-sana
source .venv-sana/bin/activate
pip install -r requirements.txt

# Step 3: MPS 补丁 (6处)
# 3a. device 选择: cuda → mps
# 3b. MPS-safe 随机生成器
# 3c. 屏蔽 hard CUDA import (3处)
# 3d. 清缓存

# Step 4: 下载权重
huggingface-cli download Efficient-Large-Model/SANA-1.6B

# Step 5: 运行
python scripts/run_t2i.py \
  --model SANA-1.6B \
  --prompt "your prompt" \
  --resolution 1024 1024
```

### 2.3 速度预期

| 模型 | 分辨率 | M4 (64GB) | M5 Pro (48GB) |
|:-----|:------:|:---------:|:-------------:|
| Sana-0.6B | 512×512 | ~3 it/s | ~5 it/s |
| Sana-0.6B | 1024×1024 | ~1.9 it/s | ~3-4 it/s |
| Sana-1.6B | 1024×1024 | ~1 it/s | ~2 it/s |

---

## 三、视频生成部署 (SANA-WM)

### 3.1 简介

SANA-WM: 2.6B 可控世界模型
- 720p 分辨率
- 最长 1 分钟视频
- 6-DoF 相机轨迹控制 (双分支相机控制)
- 单 GPU 可跑

### 3.2 步骤

```bash
# Step 1: 克隆 Apple Silicon 移植版
git clone https://huggingface.co/junafinity/SANA-WM-Bidirectional-on-Apple-Silicon
cd SANA-WM-Bidirectional-on-Apple-Silicon

# Step 2: 环境
python3.11 -m venv .venv-sana-wm
source .venv-sana-wm/bin/activate
pip install -r requirements-mps.txt

# Step 3: 下载权重 (两个模型)
huggingface-cli download Efficient-Large-Model/SANA-WM_bidirectional \
  --local-dir models/SANA-WM_bidirectional
huggingface-cli download google/gemma-2-2b-it \
  --local-dir models/gemma-2-2b-it

# Step 4: 环境变量
export SANA_WM_PR_ROOT=$(pwd)
export SANA_WM_MODEL_ROOT=$(pwd)/models/SANA-WM_bidirectional
export SANA_GEMMA_2_2B_IT_ROOT=$(pwd)/models/gemma-2-2b-it
export PYTORCH_ENABLE_MPS_FALLBACK=1
export SANA_USE_LIGER=0
export GDN_DISABLE_COMPILE=1

# Step 5: 运行 (图片→视频)
python run_sana_wm.py \
  --input image.jpg \
  --trajectory camera_path.json \
  --output output.mp4
```

### 3.3 M5 Pro 48GB 内存策略

SANA-WM 采用 **分阶段加载**（staged subprocesses）——视觉编码器、文本编码器、refiner 不同时驻留内存。官方实测 M3 Max 128GB 跑 20秒 720p，你 48GB 应可跑 5-10 秒片段。

对应策略：
- 短片段 (5-10秒): 直接跑
- 长片段 (20秒+): 降低分辨率到 540p 或减少帧数

---

## 四、MPS 补丁清单

从 Medium 文章和 HF 博客总结的改动点：

### 图像生成 (6处)

| # | 位置 | 改动 |
|:-:|:-----|:-----|
| 1 | `device = torch.device('cuda')` | → `torch.device('mps')` |
| 2 | `torch.Generator('cuda')` | → MPS-safe 生成器 |
| 3 | `torch.cuda.empty_cache()` | → 跳过或替换 |
| 4 | `from flash_attn import ...` | → 条件导入 (仅在 CUDA 时) |
| 5 | `from xformers import ...` | → 条件导入 |
| 6 | `torch.float64` RoPE | → `torch.float32` (MPS 不支持 float64) |

### 视频生成 (已在移植版中解决)

移植版 `junafinity/SANA-WM-Bidirectional-on-Apple-Silicon` 已包含所有补丁，无需手动改。

---

## 五、与现有方案对比

| 场景 | 现有方案 | 痛点 | Sana 方案 |
|:-----|:---------|:-----|:----------|
| 文生图 | FLUX.2 + ComfyUI | 50步40分钟, 全黑图 BUG | **Sana-0.6B/1.6B 秒级出图** |
| 文生图 | SDXL + MPS | 全黑图, 不稳定 | **Sana 架构稳定** |
| 视频 | LTX-Video CLI | --two-stage BUG, 43分钟 | **SANA-WM 2.6B 分钟级** |
| 视频 | Wan (待审批) | 大模型, 未部署 | **SANA-WM 已验证 MPS** |
| 视频 | ComfyUI 工作流 | 复杂配置 | **单命令运行** |

---

## 六、风险与前置

| 风险 | 影响 | 应对 |
|:-----|:-----|:-----|
| PyTorch 2.8 MPS op 覆盖不全 | Sana 某些 op 可能不支持 | 升级到 2.10+ 或设 `PYTORCH_ENABLE_MPS_FALLBACK=1` |
| SANA-WM 48GB 内存限制 | 长片段会 OOM | 分阶段加载已实现, 降低分辨率 |
| Gemma-2-2B 额外 ~4GB | 总内存占用增加 | 48GB 足够 |
| HF 网络不稳定 (Aurora VPN) | 下载慢 | 用 `-sk` 跳过 SSL |

---

## 七、执行计划

- [ ] Step 1: 升级 PyTorch (如需)
- [ ] Step 2: Clone NVlabs/Sana + MPS 补丁
- [ ] Step 3: 下载 Sana-0.6B/1.6B 权重
- [ ] Step 4: 测试文生图 (MPS)
- [ ] Step 5: Clone SANA-WM Apple Silicon 移植版
- [ ] Step 6: 下载 SANA-WM + Gemma 权重
- [ ] Step 7: 测试图生视频 (MPS)

---

## 八、参考链接

- [NVlabs/Sana (GitHub, 8.5K⭐)](https://github.com/NVlabs/SANA)
- [SANA-WM 官方页面](https://nvlabs.github.io/Sana/WM/)
- [SANA-WM Apple Silicon 移植 (HF)](https://huggingface.co/blog/junafinity/sana-wm-bidirectional-on-apple-silicon)
- [MPS 部署指南 (Medium)](https://medium.com/data-science-collective/running-nvidia-sana-on-apple-silicon-ai-image-and-video-generation-on-a-mac-no-cuda-no-nvidia-78a0288ecf03)
- [Sana 论文 (MIT HAN Lab)](https://hanlab.mit.edu/projects/sana)
