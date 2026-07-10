# 🚀 AMD ROCm Agent Skills

> The first collection of agent skills for AMD ROCm GPU workloads. Compatible with Claude Code, OpenCode, Codex, Cursor, and more.

[![Skills](https://img.shields.io/badge/skills-10-green)]()
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)]()
[![GPU](https://img.shields.io/badge/GPU-AMD%20ROCm-red)]()
[![Agents](https://img.shields.io/badge/agents-6%2B-compatible)]()

## Why?

NVIDIA has 428+ agent skills on [skills.sh](https://skills.sh). AMD has **zero**. This repo fills that gap with 10 production-ready skills for AMD ROCm GPU workloads — from setup to deployment to industrial safety.

## Skills

| # | Skill | Category | Description |
|---|-------|----------|-------------|
| 1 | `rocm-setup` | Core | Install and verify ROCm on AMD GPUs |
| 2 | `rocm-docker` | Core | Docker with AMD GPU passthrough |
| 3 | `vllm-rocm-deploy` | Core | Deploy vLLM + multimodal models on ROCm |
| 4 | `yolo-rocm-deploy` | Core | YOLOv8 with PyTorch ROCm, benchmark |
| 5 | `video-pipeline-rocm` | Pipeline | Video processing pipeline with ROCm |
| 6 | `vlm-rocm-inference` | Pipeline | VLM inference with ROCm backend |
| 7 | `rocm-benchmark` | Pipeline | GPU benchmarking and monitoring |
| 8 | `ppe-detection-pipeline` | Industrial | PPE detection for industrial safety |
| 9 | `ds132-compliance` | Industrial | DS 132 mining compliance (Chile) |
| 10 | `rocm-troubleshoot` | Industrial | Diagnostics and troubleshooting |

## Compatibility

| Agent | Supported |
|-------|-----------|
| Claude Code | ✅ |
| OpenCode | ✅ |
| Codex | ✅ |
| Cursor | ✅ |
| Gemini CLI | ✅ |
| Kiro CLI | ✅ |

## Multi-GPU Support

All skills support **AMD ROCm**, **NVIDIA CUDA**, and **CPU fallback** with automatic detection:

| Component | AMD ROCm | NVIDIA CUDA | CPU |
|-----------|----------|-------------|-----|
| PyTorch | `torch.cuda` | `torch.cuda` | `device='cpu'` |
| vLLM | `vllm-openai-rocm` | `vllm-openai` | `--device cpu` |
| Docker | `--device /dev/kfd` | `--gpus all` | No flags |

## Installation

```bash
# List available skills
npx skills add yechua-silva/amd-rocm-skills --list

# Install a skill
npx skills add yechua-silva/amd-rocm-skills --skill rocm-setup --agent opencode --yes

# Install in multiple agents
npx skills add yechua-silva/amd-rocm-skills -a claude-code -a opencode -a cursor --yes
```

## Structure

```
amd-rocm-skills/
├── skills/
│   ├── rocm-setup/           # Core
│   ├── rocm-docker/          # Core
│   ├── vllm-rocm-deploy/     # Core
│   ├── yolo-rocm-deploy/     # Core
│   ├── video-pipeline-rocm/  # Pipeline
│   ├── vlm-rocm-inference/   # Pipeline
│   ├── rocm-benchmark/       # Pipeline
│   ├── ppe-detection-pipeline/ # Industrial
│   ├── ds132-compliance/     # Industrial
│   └── rocm-troubleshoot/    # Industrial
└── docs/
```

## Roadmap

| Feature | Status |
|---------|--------|
| 10 core skills | ✅ Complete |
| Multi-GPU support | ✅ Complete |
| 6+ agent compatibility | ✅ Complete |
| Publish to skills.sh | 📋 Planned |
| English translations | 📋 Planned |
| Additional industrial skills | 📋 Planned |

## License

Apache 2.0

## Credits

- **AMD Developer Hackathon Act II** — Pista Unicornio
- **Yechua Silva** — Developer
