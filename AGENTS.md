# AMD ROCm Agent Skills

## Overview

The first collection of agent skills for AMD ROCm GPU workloads. 10 production-ready skills compatible with Claude Code, OpenCode, Codex, Cursor, Cline, Roo Code, Windsurf, Gemini CLI, and Kiro CLI.

## Skill Format

All skills follow the [agentskills.io](https://agentskills.io/specification) specification:
- `SKILL.md` with YAML frontmatter (`name`, `description`, `license`, `compatibility`, `metadata`)
- `scripts/` directory with executable Python and Bash scripts
- `references/` directory with technical documentation

## Multi-GPU Support

All skills support **AMD ROCm**, **NVIDIA CUDA**, and **CPU fallback** with automatic detection.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0
