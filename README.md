# 🚀 Pre-Munin Skills

**Skills agnósticas para AMD ROCm — que funcionan en Claude Code, OpenCode, Codex, Cursor y más.**

## Skills

| Skill | Descripción |
|-------|-------------|
| `rocm-setup` | Instalación y verificación de ROCm en host AMD |
| `rocm-docker` | Docker con GPU AMD, preflight checks |
| `vllm-rocm-deploy` | Deploy vLLM + modelos multimodales en ROCm |
| `yolo-rocm-deploy` | YOLOv8x con PyTorch ROCm, benchmark |

## Instalación

```bash
# Listar skills disponibles
npx skills add munin/skills --list

# Instalar una skill
npx skills add munin/skills --skill rocm-setup --agent opencode --yes
```

## Licencia

Apache 2.0
