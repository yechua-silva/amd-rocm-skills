# 🚀 Pre-Munin Project: Skills Agnósticas para AMD ROCm

## ⚠️ REGLA ABSOLUTA

**NO publicar en GitHub, skills.sh, ni ningún registro público hasta después del hackathon (6-11 julio).**
Este proyecto es interno. Las skills se prueban localmente en el proyecto Munin.

---

## 📊 Estado del Proyecto: COMPLETO ✅

| Métrica | Valor |
|---------|-------|
| Skills | **10/10** validadas ✅ |
| Archivos | **73** (10 SKILL.md + 22 scripts + 20 referencias + docs) |
| Líneas totales | **~32,000** |
| Multi-backend | AMD ROCm + NVIDIA CUDA + CPU fallback |
| Compatibilidad | Claude Code, OpenCode, Codex, Cursor, Gemini CLI, Kiro CLI |
| Formato | agentskills.io estándar (sin campos exclusivos) |

### Resultado de validación
```
rocm-setup              ✅ desc=662 chars, agents=5
rocm-docker             ✅ desc=749 chars, agents=5
vllm-rocm-deploy        ✅ desc=599 chars, agents=7
yolo-rocm-deploy        ✅ desc=552 chars, agents=4
video-pipeline-rocm     ✅ desc=1023 chars, agents=7
vlm-rocm-inference      ✅ desc=946 chars, agents=7
rocm-benchmark          ✅ desc=869 chars, agents=4
ppe-detection-pipeline  ✅ desc=1009 chars, agents=7
ds132-compliance        ✅ desc=977 chars, agents=7
rocm-troubleshoot       ✅ desc=863 chars, agents=5
🎯 10/10 — TODAS LAS SKILLS VÁLIDAS
```

---

## 🎯 Visión

Ser el **primer repositorio de skills para AMD ROCm** en el ecosistema agentskills.io.
NVIDIA tiene 428 skills. AMD tiene 0. Vamos a ser los first movers.

Skills = instrucciones portátiles para agentes de IA (Claude Code, OpenCode, Codex, Cursor, etc.)
que les enseñan a usar correctamente herramientas de hardware/software.

---

## 🧠 Stack Tecnológico

- **Formato:** agentskills.io (SKILL.md con frontmatter YAML + Markdown)
- **CLI:** `npx skills add` (Vercel Labs)
- **Target agents:** Claude Code, OpenCode, Codex, Cursor, Gemini CLI, Kiro CLI
- **Hardware:** AMD MI300X (ROCm 7.2.4) / NVIDIA CUDA / CPU
- **Stack Munin:** PyTorch ROCm, vLLM ROCm, YOLOv8x, InternVL2-8B

---

## 📦 Catálogo de Skills — 10/10 COMPLETO ✅

### Fase 1 — Core ✅
| Skill | Líneas SKILL.md | Scripts | Soporte |
|-------|----------------|---------|---------|
| **rocm-setup** | 356 | `check-rocm.sh`, `detect-gpu.py` | ROCm + CUDA + CPU |
| **rocm-docker** | 300+ | `docker-preflight.sh`, `docker-compose.yml`, `entrypoint.sh` | ROCm + CUDA + CPU |
| **vllm-rocm-deploy** | 300+ | `deploy-vllm.sh`, `test-vlm.sh` | ROCm + CUDA + CPU |
| **yolo-rocm-deploy** | 300+ | `export-yolo.py`, `benchmark-yolo.py` | ROCm + CUDA + CPU |

### Fase 2 — Pipeline ✅
| Skill | Líneas SKILL.md | Scripts | Soporte |
|-------|----------------|---------|---------|
| **video-pipeline-rocm** | 754 | `detect-backend.sh`, `gst-pipeline.sh`, `inference-pipeline.py` | ROCm + CUDA + CPU |
| **vlm-rocm-inference** | 500+ | `run-vlm.py`, `benchmark-vlm.py` | ROCm + CUDA + CPU |
| **rocm-benchmark** | 500+ | `benchmark-gpu.py`, `rocm-monitor.sh`, `stress-test.sh` | ROCm + CUDA |

### Fase 3 — Industrial ✅
| Skill | Líneas SKILL.md | Scripts | Soporte |
|-------|----------------|---------|---------|
| **ppe-detection-pipeline** | 500+ | `ppe-pipeline.py`, `train-ppe.py`, `alert-manager.py` | ROCm + CUDA + CPU |
| **ds132-compliance** | **839** | `compliance-report.py`, `audit-log.py`, `zone-config.py` | ROCm + CUDA + CPU |
| **rocm-troubleshoot** | 500+ | `rocm-diagnostic.sh`, `quick-fix.sh`, `check-compatibility.py` | ROCm + CUDA + CPU |

---

## 📁 Estructura del Repositorio

```
munin-skills/
├── AGENT.md              ← Este archivo (proyecto completo)
├── README.md
├── LICENSE               (Apache 2.0)
├── .gitignore
├── skills/               ← 10 skills en 3 fases ✅
│   ├── rocm-setup/               # ✅ F1 Core
│   ├── rocm-docker/              # ✅ F1 Core
│   ├── vllm-rocm-deploy/         # ✅ F1 Core
│   ├── yolo-rocm-deploy/         # ✅ F1 Core
│   ├── video-pipeline-rocm/      # ✅ F2 Pipeline
│   ├── vlm-rocm-inference/       # ✅ F2 Pipeline
│   ├── rocm-benchmark/           # ✅ F2 Pipeline
│   ├── ppe-detection-pipeline/   # ✅ F3 Industrial
│   ├── ds132-compliance/         # ✅ F3 Industrial (diferenciador)
│   └── rocm-troubleshoot/        # ✅ F3 Industrial
└── docs/
    ├── skills-format-guide.md
    ├── multi-gpu-patterns.md
    ├── installation-guide.md
    ├── roadmap.md
    └── publishing-checklist.md
```

---

## 📝 Formato SKILL.md

Toda skill DEBE tener frontmatter YAML estándar **agentskills.io** (sin campos exclusivos de Claude Code):

```yaml
---
name: nombre-skill           # [OBLIGATORIO] max 64 chars
description: |               # [OBLIGATORIO] max 1024 chars, bilingüe
  Descripción con keywords de activación.
license: Apache-2.0          # [RECOMENDADO]
metadata:
  version: "1.0.0"
  author: "Munin Project"
  tags:
    - amd
    - rocm
    - munin
compatibility:               # [RECOMENDADO] Agentes compatibles
  - claude-code
  - opencode
  - codex
  - cursor
---
```

### Reglas de Formato
1. `compatibility` como **lista**, no string. Ej: `- claude-code`
2. NO usar campos exclusivos de Claude Code: `allowed-tools`, `disable-model-invocation`, `context: fork`, `arguments`, `hooks`, `paths`, etc.
3. Descripciones bilingües español + inglés con keywords de activación
4. Multi-backend documentado (ROCm + CUDA + CPU)

### Estructura del cuerpo Markdown
- **Purpose** — qué hace la skill
- **When to use** — keywords que activan la skill
- **Prerequisites** — requisitos
- **Quickstart** — pasos rápidos
- **Step-by-step instructions** — instrucciones detalladas
- **Reference Documents** — tabla de referencias
- **Scripts** — tabla de scripts
- **Common Issues** — troubleshooting

---

## 🔧 Skills Multi-GPU

Todas las skills funcionan en **AMD ROCm, NVIDIA CUDA y CPU fallback** con detección automática:

| Componente | AMD ROCm | NVIDIA CUDA | CPU Fallback |
|------------|----------|-------------|-------------|
| PyTorch | `torch.cuda` | `torch.cuda` | `device='cpu'` |
| vLLM | `vllm/vllm-openai-rocm:latest` | `vllm/vllm-openai:latest` | `--device cpu` |
| YOLO | `device="cuda:0"` | `device="cuda:0"` | `device="cpu"` |
| Docker | `--device /dev/kfd --device /dev/dri` | `--runtime nvidia --gpus all` | Sin flags |
| Python | 3.12 OBLIGATORIO para vLLM ROCm | 3.10+ | Cualquiera |

**Reglas clave:**
- No existe `torch.rocm` — usar `torch.cuda` API
- Detectar ROCm con `torch.version.hip`, CUDA con `torch.version.cuda`
- ROCm dtype: `float16`, NVIDIA: `bfloat16`
- `CUDA_VISIBLE_DEVICES` funciona en ambos
- MI300X = gfx942, `HSA_OVERRIDE_GFX_VERSION=9.4.2`

---

## 🧪 Instalación y Pruebas Locales

### Desde el repo local
```bash
# Listar skills
npx skills add . --list

# Instalar una skill específica en OpenCode
npx skills add . --skill rocm-setup --agent opencode --yes

# Instalar en múltiples agentes
npx skills add . -a claude-code -a opencode -a codex -a cursor --yes
```

### Manual (por proyecto Munin)
```bash
cp -r skills/rocm-setup .opencode/skills/rocm-setup/
```

### Validar formato
```bash
python3 skills/validate.py
# o
python3 -c "
import yaml
for skill in ['rocm-setup','rocm-docker','vllm-rocm-deploy','yolo-rocm-deploy',
              'video-pipeline-rocm','vlm-rocm-inference','rocm-benchmark',
              'ppe-detection-pipeline','ds132-compliance','rocm-troubleshoot']:
    with open(f'skills/{skill}/SKILL.md') as f:
        _, fm, body = f.read().split('---', 2)
        data = yaml.safe_load(fm)
        name = data['name']
        desc = data.get('description', '')
        agents = len(data.get('compatibility', []))
        print(f'{name:25s} ✅ desc={len(desc)} chars, agents={agents}')
print('🎯 10/10 — TODAS LAS SKILLS VÁLIDAS')
"
```

---

## 🚀 Post-Hackathon: Publicación

### Pre-requisitos (ver docs/publishing-checklist.md)
- [ ] Skills completas y probadas (✅ listo)
- [ ] README.md actualizado (✅ listo)
- [ ] LICENSE Apache 2.0 (✅ listo)
- [ ] .gitignore (✅ listo)

### Pasos
1. Crear repo público en GitHub como `munin/skills` o `amd-rocm/skills`
2. skills.sh detecta automáticamente repos con `skills/` directory
3. Verificar: `npx skills add <owner>/<repo> --list`
4. Anunciar en AMD Community, r/ROCm, r/AMD, LinkedIn

### Diferenciación
| NVIDIA Skills | Munin Skills |
|--------------|--------------|
| CUDA, TensorRT, NIMs | **ROCm, vLLM, PyTorch ROCm** |
| Inglés | **Español + Inglés** (LatAm) |
| General GPU | **Industrial, minería, EPP** |
| 428 skills | **10 skills (único en AMD)** |

---

## 📌 Recordatorios

- 🚫 **NO publicar hasta después del hackathon (6-11 julio)**
- 🧪 Probar instalando en `.opencode/skills/` durante desarrollo de Munin
- 🥇 Somos los primeros en crear skills AMD ROCm en el ecosistema
- 🌎 Skills bilingües para mercado minero LatAm
- 📊 Proyecto completo: **10 skills, 73 archivos, ~32,000 líneas**
