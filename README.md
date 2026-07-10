# 🚀 AMD ROCm Agent Skills

> The first open-source collection of agent skills for AMD ROCm GPU workloads. Compatible with 9+ AI coding agents.

[![skills.sh](https://skills.sh/b/yechua-silva/amd-rocm-skills)](https://skills.sh/yechua-silva/amd-rocm-skills)
[![Skills](https://img.shields.io/badge/skills-10-green)]()
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)]()
[![GPU](https://img.shields.io/badge/GPU-AMD%20ROCm-red)]()
[![Agents](https://img.shields.io/badge/agents-9%2B-compatible)]()

## Why?

NVIDIA has 428+ agent skills on [skills.sh](https://skills.sh). AMD has **zero**. This repo fills that gap with 10 production-ready skills for AMD ROCm GPU workloads — from setup to deployment to industrial safety.

## Skills

### Core

| # | Skill | Description |
|---|-------|-------------|
| 1 | [`rocm-setup`](skills/rocm-setup/SKILL.md) | Install and verify ROCm on AMD GPUs |
| 2 | [`rocm-docker`](skills/rocm-docker/SKILL.md) | Docker with AMD GPU passthrough |
| 3 | [`vllm-rocm-deploy`](skills/vllm-rocm-deploy/SKILL.md) | Deploy vLLM + multimodal models on ROCm |
| 4 | [`yolo-rocm-deploy`](skills/yolo-rocm-deploy/SKILL.md) | YOLOv8 with PyTorch ROCm, benchmark |

### Pipeline

| # | Skill | Description |
|---|-------|-------------|
| 5 | [`video-pipeline-rocm`](skills/video-pipeline-rocm/SKILL.md) | Video processing pipeline with ROCm |
| 6 | [`vlm-rocm-inference`](skills/vlm-rocm-inference/SKILL.md) | VLM inference with ROCm backend |
| 7 | [`rocm-benchmark`](skills/rocm-benchmark/SKILL.md) | GPU benchmarking and monitoring |

### Industrial

| # | Skill | Description |
|---|-------|-------------|
| 8 | [`ppe-detection-pipeline`](skills/ppe-detection-pipeline/SKILL.md) | PPE detection for industrial safety |
| 9 | [`ds132-compliance`](skills/ds132-compliance/SKILL.md) | DS 132 mining compliance (Chile) |
| 10 | [`rocm-troubleshoot`](skills/rocm-troubleshoot/SKILL.md) | Diagnostics and troubleshooting |

## Compatibility

All skills follow the [agentskills.io](https://agentskills.io/specification) specification and are compatible with:

| Agent | Supported |
|-------|-----------|
| Claude Code | ✅ |
| OpenCode | ✅ |
| Codex | ✅ |
| Cursor | ✅ |
| Cline | ✅ |
| Roo Code | ✅ |
| Windsurf | ✅ |
| Gemini CLI | ✅ |
| Kiro CLI | ✅ |

## Multi-GPU Support

All skills support **AMD ROCm**, **NVIDIA CUDA**, and **CPU fallback** with automatic detection:

| Component | AMD ROCm | NVIDIA CUDA | CPU |
|-----------|----------|-------------|-----|
| PyTorch | `torch.cuda` + `torch.version.hip` | `torch.cuda` + `torch.version.cuda` | `device='cpu'` |
| vLLM | `vllm-openai-rocm` | `vllm-openai` | `--device cpu` |
| Docker | `--device /dev/kfd` | `--gpus all` | No flags |

## Installation

```bash
# List available skills
npx skills add yechua-silva/amd-rocm-skills --list

# Install a single skill
npx skills add yechua-silva/amd-rocm-skills --skill rocm-setup --agent opencode --yes

# Install all skills in multiple agents
npx skills add yechua-silva/amd-rocm-skills -a claude-code -a opencode -a cursor --yes
```

## Structure

```
amd-rocm-skills/
├── skills/
│   ├── rocm-setup/              # Core
│   ├── rocm-docker/             # Core
│   ├── vllm-rocm-deploy/        # Core
│   ├── yolo-rocm-deploy/        # Core
│   ├── video-pipeline-rocm/     # Pipeline
│   ├── vlm-rocm-inference/      # Pipeline
│   ├── rocm-benchmark/          # Pipeline
│   ├── ppe-detection-pipeline/  # Industrial
│   ├── ds132-compliance/        # Industrial
│   └── rocm-troubleshoot/       # Industrial
├── docs/
│   ├── installation-guide.md
│   ├── multi-gpu-patterns.md
│   ├── skills-format-guide.md
│   ├── publishing-checklist.md
│   └── roadmap.md
├── skills.sh.json               # Groupings for skills.sh
├── CONTRIBUTING.md              # Contribution guidelines
├── CODE_OF_CONDUCT.md           # Community standards
└── AGENTS.md                    # Agent-facing overview
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quality Standards

- All skills must support AMD ROCm + NVIDIA CUDA + CPU fallback
- `SKILL.md` follows [agentskills.io](https://agentskills.io/specification) specification
- `compatibility` field is a string (not a YAML list)
- No agent-specific fields (Claude Code `context`, `agent`, `model`, etc.)
- Scripts must be executable and portable (Python 3.10+ / Bash)
- No references to specific projects — skills are agnostic

## Roadmap

| Feature | Status |
|---------|--------|
| 10 core skills | ✅ Complete |
| Multi-GPU support (ROCm + CUDA + CPU) | ✅ Complete |
| 9+ agent compatibility | ✅ Complete |
| agentskills.io spec compliance | ✅ Complete |
| skills.sh.json groupings | ✅ Complete |
| CONTRIBUTING.md + CODE_OF_CONDUCT.md | ✅ Complete |
| Publish to skills.sh | 📋 Planned |
| Additional industrial skills | 📋 Planned |
| Skill evaluation framework | 📋 Planned |

## License

Apache 2.0

## Credits

- **AMD Developer Hackathon Act II** — Pista Unicornio
- **Yechua Silva** — Developer
- **Contributors** — See [CONTRIBUTING.md](CONTRIBUTING.md)
