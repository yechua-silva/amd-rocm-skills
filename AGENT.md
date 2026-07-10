# 🚀 AMD ROCm Agent Skills

## ⚠️ REGLAS
1. **Repo público** en GitHub: `git@github.com:yechua-silva/amd-rocm-skills.git`
2. Skills agnósticas — compatibles con Claude Code, OpenCode, Codex, Cursor, Gemini CLI, Kiro CLI
3. Formato agentskills.io (SKILL.md con frontmatter YAML)
4. Multi-backend: AMD ROCm + NVIDIA CUDA + CPU fallback
5. Bilingüe: Español + Inglés

## 📊 Estado: COMPLETO ✅

| Métrica | Valor |
|---------|-------|
| Skills | 10/10 validadas |
| Archivos | 73 |
| Líneas | ~32,000 |
| Compatibilidad | 6+ agentes |

## 📦 Catálogo

### Core (4)
rocm-setup, rocm-docker, vllm-rocm-deploy, yolo-rocm-deploy

### Pipeline (3)
video-pipeline-rocm, vlm-rocm-inference, rocm-benchmark

### Industrial (3)
ppe-detection-pipeline, ds132-compliance, rocm-troubleshoot

## 🧠 Stack
- Formato: agentskills.io (SKILL.md + frontmatter YAML)
- CLI: `npx skills add`
- Hardware: AMD MI300X (ROCm 7.2.4) / NVIDIA CUDA / CPU
- Target: Munin Industrial Vision Agent

## 📝 Formato SKILL.md
```yaml
---
name: skill-name
description: |
  Bilingual description with activation keywords.
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: "Munin Project"
  tags: [amd, rocm, gpu]
compatibility:
  - claude-code
  - opencode
  - codex
  - cursor
---
```

Reglas: NO campos exclusivos de Claude Code. Compatibility como lista. Multi-backend documentado.

## 🚀 Publicación
1. Repo público: `github.com/yechua-silva/amd-rocm-skills`
2. skills.sh detecta automáticamente repos con `skills/` directory
3. Verificar: `npx skills add yechua-silva/amd-rocm-skills --list`

## 📌 Notas
- Skills bilingües para mercado minero LatAm
- Primer repo de skills AMD ROCm en el ecosistema
- Diferenciación: NVIDIA 428 skills vs AMD 10 skills (first movers)
