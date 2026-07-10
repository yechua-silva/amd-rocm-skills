# Contributing to AMD ROCm Agent Skills

Thank you for your interest in contributing! This repo aims to be the definitive collection of agent skills for AMD ROCm GPU workloads.

## Quick Start

```bash
git clone https://github.com/yechua-silva/amd-rocm-skills.git
cd amd-rocm-skills
```

## Skill Structure

Each skill lives in `skills/<skill-name>/` and must contain:

```
skills/<skill-name>/
├── SKILL.md          # Required: frontmatter YAML + instructions
├── scripts/          # Required: executable scripts (Python/Bash)
└── references/       # Optional: technical documentation
```

## SKILL.md Frontmatter Requirements

### Required Fields

```yaml
---
name: my-skill          # kebab-case, must match directory name, max 64 chars
description: >           # 1-1024 chars, describe WHAT + WHEN + keywords
  What this skill does and when to use it. Include keywords for agent matching.
license: Apache-2.0
---
```

### Optional Fields

```yaml
compatibility: >         # String (NOT list), max 500 chars
  Compatible with Claude Code, OpenCode, Codex, Cursor. Requires Linux with GPU.
metadata:
  version: "1.0.0"       # Semantic versioning
  author: your-github-username
```

### Fields to AVOID (Claude Code-specific, reduce portability)

- `context: fork` — Claude Code only
- `agent: Explore` — Claude Code only
- `model: claude-sonnet-*` — Claude Code only
- `hooks:` — Claude Code only
- `paths:` — Claude Code only
- `disable-model-invocation` — Claude Code only

## Naming Conventions

- **Skill names:** `kebab-case` (lowercase, hyphens, no underscores)
- **Directory name MUST match `name` field in frontmatter**
- **Scripts:** `snake_case.py` or `kebab-case.sh`
- **References:** `kebab-case.md`

## Multi-GPU Support

All skills MUST support three backends with automatic detection:
1. **AMD ROCm** (primary) — `torch.cuda` with `torch.version.hip`
2. **NVIDIA CUDA** (secondary) — `torch.cuda` with `torch.version.cuda`
3. **CPU fallback** — `device='cpu'`

Use `torch.version.hip` to distinguish AMD from NVIDIA. Both use `torch.cuda` API.

## Quality Checklist

Before submitting a PR:

- [ ] `name` field matches directory name
- [ ] `description` includes keywords for agent matching
- [ ] `description` includes trigger phrases ("Use when...")
- [ ] `compatibility` is a string, not a YAML list
- [ ] No Claude Code-specific fields (context, agent, model, hooks)
- [ ] Scripts are executable (`chmod +x`)
- [ ] Scripts use `#!/usr/bin/env python3` or `#!/usr/bin/env bash`
- [ ] No hardcoded secrets or API keys
- [ ] No references to specific projects (keep it agnostic)
- [ ] Related skills are cross-referenced in `## Related Skills` section
- [ ] SKILL.md is under 1000 lines (use `references/` for deep content)

## Testing

```bash
# Validate structure
npx skills add yechua-silva/amd-rocm-skills --list

# Install a skill to test
npx skills add yechua-silva/amd-rocm-skills --skill <skill-name> --agent opencode --yes
```

## Pull Request Process

1. Fork the repo
2. Create a branch: `git checkout -b feat/my-new-skill`
3. Add your skill in `skills/<skill-name>/`
4. Run the quality checklist
5. Submit PR with a description of what the skill does and which GPU backends it supports

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
