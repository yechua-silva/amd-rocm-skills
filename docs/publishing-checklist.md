# Publishing Checklist — AMD ROCm Agent Skills

## Pre-Publishing Checklist

### Format Compliance (agentskills.io)

- [ ] Each skill has `SKILL.md` with YAML frontmatter
- [ ] `name` field is kebab-case and matches directory name
- [ ] `description` is 1-1024 chars with keywords and trigger phrases
- [ ] `compatibility` is a string (NOT a YAML list)
- [ ] `license` is `Apache-2.0`
- [ ] `metadata.version` follows semantic versioning
- [ ] `metadata.author` is set
- [ ] No Claude Code-specific fields (`context`, `agent`, `model`, `hooks`, `paths`)

### Content Quality

- [ ] SKILL.md is under 1000 lines
- [ ] `scripts/` directory with executable Python/Bash scripts
- [ ] `references/` directory with technical documentation
- [ ] Cross-references to related skills in `## Related Skills` section
- [ ] Trigger phrases in description ("Use when..." / "Keywords: ...")
- [ ] No references to specific projects (keep skills agnostic)
- [ ] No hardcoded secrets or API keys

### Multi-GPU Support

- [ ] Scripts detect AMD ROCm via `torch.version.hip`
- [ ] Scripts detect NVIDIA CUDA via `torch.version.cuda`
- [ ] CPU fallback implemented
- [ ] Docker examples for both AMD and NVIDIA
- [ ] Environment variables documented for each backend

### Technical

- [ ] Scripts have `#!/usr/bin/env python3` or `#!/usr/bin/env bash` shebang
- [ ] Scripts are executable (`chmod +x`)
- [ ] No `__pycache__/` directories committed
- [ ] `.gitignore` excludes `__pycache__/`, `*.pyc`, `.env`

### Publishing to skills.sh

1. Ensure repo is public on GitHub
2. Verify `skills/` directory exists at root
3. Run: `npx skills add yechua-silva/amd-rocm-skills --list`
4. If skills appear, they are indexed automatically by skills.sh
5. Add badge to README: `[![skills.sh](https://skills.sh/b/yechua-silva/amd-rocm-skills)](https://skills.sh/yechua-silva/amd-rocm-skills)`
6. Share the repo link in dev communities

### Post-Publishing

- [ ] Test installation: `npx skills add yechua-silva/amd-rocm-skills --skill rocm-setup --agent opencode --yes`
- [ ] Monitor skills.sh for install counts
- [ ] Respond to community issues and PRs
- [ ] Update versions when skills are improved
