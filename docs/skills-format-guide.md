# Guía de Formato Skills — Compatible con Múltiples Agentes

> Documento consolidado de investigación Fase 0 para el proyecto Munin.
> Define el estándar de formato SKILL.md compatible con Claude Code, OpenCode, Codex y Cursor.

---

## 1. Estándar agentskills.io — Formato SKILL.md Unificado

El ecosistema `agentskills.io` define un formato estándar para que una misma skill funcione en múltiples agentes de IA. El archivo principal es `SKILL.md`.

### 1.1 Frontmatter YAML

El archivo `SKILL.md` comienza con un bloque de frontmatter YAML delimitado por `---`. Los campos se dividen en **obligatorios**, **recomendados** y **opcionales**:

| Campo | Obligatorio | Max | Descripción |
|-------|-------------|-----|-------------|
| `name` | ✅ Sí | 64 chars | Identificador único. Solo lowercase, dígitos y guiones. Ej: `rocm-setup` |
| `description` | ✅ Sí | 1024 chars | Texto de activación natural. Incluye keywords y casos de uso. |
| `license` | ❌ No | — | Licencia del skill (ej: MIT, Apache-2.0) |
| `metadata` | ❌ No | — | Objeto con información adicional (tags, categorías) |
| `compatibility` | ❌ No | — | Lista de agentes compatibles |
| `allowed-tools` | ❌ No | — | Solo Claude Code. Lista de herramientas permitidas. |
| `model` | ❌ No | — | Solo Claude Code. Modelo requerido. |
| `when_to_use` | ❌ No | — | Solo Claude Code. Instrucciones de activación. |

**Ejemplo de frontmatter estándar:**

```yaml
---
name: rocm-setup
description: >
  Configura y verifica el entorno AMD ROCm para PyTorch.
  Detecta GPUs AMD, instala dependencias ROCm, configura variables de entorno.
  Útil cuando se trabaja con hardware AMD en tareas de ML/AI.
license: MIT
metadata:
  tags: [rocm, amd, gpu, pytorch, setup]
  category: environment
compatibility:
  - claude-code
  - opencode
  - codex
  - cursor
---
```

### 1.2 Body Markdown

Después del frontmatter, el body contiene instrucciones en Markdown libre. Secciones recomendadas:

- **Descripción detallada** del propósito del skill
- **Cuándo usarlo** (trigger conditions)
- **Requisitos previos** (dependencias, hardware, etc.)
- **Flujo de trabajo** paso a paso
- **Ejemplos** de uso
- **Variables de entorno** relevantes
- **Troubleshooting** común

### 1.3 Estructura de Directorio

Cada skill vive en su propio directorio con la siguiente estructura estándar:

```
skills/<skill-name>/
├── SKILL.md           # Archivo principal (obligatorio)
├── scripts/           # Scripts auxiliares (opcional)
│   ├── setup.sh
│   └── validate.py
├── references/        # Documentación de referencia (opcional)
│   └── arch-diagram.md
└── assets/            # Recursos visuales (opcional)
    └── screenshot.png
```

### 1.4 Progressive Disclosure

El sistema de skills carga de forma progresiva para minimizar el consumo de tokens:

1. **Fase de listado**: Solo se lee `name` y `description` del frontmatter (~100 tokens por skill)
2. **Fase de activación**: Cuando el agente determina que la skill es relevante, carga el body completo

Esto permite tener cientos de skills instaladas sin saturar el contexto del agente.

---

## 2. Compatibilidad por Agente

### 2.1 Tabla Comparativa

| Feature | Claude Code | OpenCode | Codex | Cursor | Notas |
|---------|-------------|----------|-------|--------|-------|
| **Directorio skills** | `.claude/skills/` | `.agents/skills/` o `.opencode/skills/` | `.agents/skills/` o `.codex/skills/` | `.agents/skills/` | El estándar cross-client es `.agents/skills/` |
| **Archivo proyecto** | `CLAUDE.md` | `AGENTS.md` | `AGENTS.md` | `AGENTS.md` | OpenCode y Codex comparten formato |
| **Frontmatter YAML** | ✅ Completo | ✅ Básico | ✅ Básico | ✅ Básico | `---` delimitado |
| **allowed-tools** | ✅ Soporta | ❌ Ignora | ❌ Ignora | ❌ Ignora | Exclusivo de Claude Code |
| **Invocación manual** | `/name` | `/name` | `/name` | `/name` | Estándar en todos los agentes |
| **Invocación automática** | ✅ Por keywords | ✅ Por keywords | ✅ Por keywords | ✅ Por keywords | Basado en `description` |
| **Arguments** | ✅ `{arg}` en body | ❌ No soporta | ❌ No soporta | ❌ No soporta | Solo Claude Code |
| **context:fork** | ✅ Soporta | ❌ No soporta | ❌ No soporta | ❌ No soporta | Crea sub-chat especializado |
| **Dynamic context (!cmd)** | ✅ `!` en prompts | ❌ No soporta | ❌ No soporta | ❌ No soporta | Inline skill invocation |
| **Hooks** | ✅ pre/post | ❌ No soporta | ❌ No soporta | ❌ No soporta | Solo Claude Code |
| **Plugin marketplace** | ❌ No tiene | ❌ Planeado | ❌ No tiene | ✅ .cursor/rules/ | Cursor usa rules en YAML |
| **Rules (Starlark)** | ❌ No | ❌ No | ❌ No | ✅ cursor/rules/ | Cursor tiene sistema propio |

### 2.2 Rutas de Instalación Detalladas

| Agente | Ruta por Proyecto (local) | Ruta Global | Archivo Config Proyecto |
|--------|--------------------------|-------------|------------------------|
| **Claude Code** | `.claude/skills/<name>/` | `~/.claude/skills/<name>/` | `CLAUDE.md` |
| **OpenCode** | `.opencode/skills/<name>/` o `.agents/skills/<name>/` | `~/.config/opencode/skills/<name>/` | `AGENTS.md` u `opencode.json` |
| **Codex** | `.codex/skills/<name>/` o `.agents/skills/<name>/` | `~/.agents/skills/<name>/` o `~/.codex/skills/<name>/` | `AGENTS.md` |
| **Cursor** | `.cursor/skills/<name>/` o `.agents/skills/<name>/` | `~/.cursor/skills/<name>/` | `.cursor/rules/` (YAML) |

### 2.3 Archivos de Proyecto

**CLAUDE.md** (Claude Code):
```markdown
# CLAUDE.md — Configuración de proyecto para Claude Code

## Skills
- rocm-setup: Configura ROCm para PyTorch en GPUs AMD
- multi-gpu-deploy: Despliegue multi-GPU (NVIDIA + AMD)
- perf-tune: Ajuste de rendimiento para inferencia

## Reglas
- Usar /rocm-setup cuando se detecten GPUs AMD
- Preferir torch.compile con backend inductor
```

**AGENTS.md** (OpenCode / Codex):
```markdown
# AGENTS.md — Configuración multi-agente

## Skills
- rocm-setup: Configura ROCm para PyTorch en GPUs AMD
- multi-gpu-deploy: Despliegue multi-GPU (NVIDIA + AMD)
```

---

## 3. Campos Extendidos por Agente

### 3.1 Exclusivos de Claude Code

Los siguientes campos SOLO funcionan en Claude Code. Otros agentes los ignoran silenciosamente:

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `disable-model-invocation` | bool | Impide que la IA se invoque a sí misma | `true` |
| `user-invocable` | bool | Si el usuario puede invocarlo manualmente | `true` |
| `context:fork` | bool | Crea un sub-chat separado para esta skill | `true` |
| `arguments` | dict | Argumentos que acepta la skill | `{"model": {"type": "string"}}` |
| `argument-hint` | string | Hint textual para el usuario | `<model-name>` |
| `model` | string | Modelo específico requerido | `claude-sonnet-4-20250514` |
| `effort` | string | Nivel de esfuerzo (`low`, `medium`, `high`) | `high` |
| `hooks` | dict | Hooks pre/post ejecución | `{"preCommand": "echo starting"}` |
| `paths` | list | Archivos/dirs que la skill puede leer | `["src/", "config.yaml"]` |
| `when_to_use` | string | Condiciones de activación | `Solo cuando el usuario pregunta por ROCm` |
| `shell` | bool | Si necesita acceso a shell | `true` |
| `disallowed-tools` | list | Herramientas prohibidas | `["Bash(rm -rf /)"]` |

**Ejemplo completo con campos Claude Code:**

```yaml
---
name: rocm-debug
description: Debug de GPUs AMD ROCm con diagnósticos avanzados
disable-model-invocation: true
user-invocable: true
context:fork: true
arguments:
  gpu_index:
    type: integer
    description: Índice de GPU a diagnosticar
    default: 0
argument-hint: <gpu-index>
model: claude-sonnet-4-20250514
effort: high
hooks:
  preCommand: rocm-smi --showallinfo
paths:
  - /dev/kfd
  - /dev/dri
when_to_use: El usuario reporta problemas con ROCm o PyTorch no detecta la GPU
shell: true
disallowed-tools:
  - Bash(rm)
  - Bash(shutdown)
---
```

### 3.2 Exclusivos de Codex

Codex soporta un archivo adicional `agents/openai.yaml` para metadatos de UI y dependencias MCP:

```yaml
# .codex/skills/rocm-setup/agents/openai.yaml
metadata:
  ui:
    icon: gpu
    color: red
    display_name: "ROCm Setup"
  dependencies:
    mcp:
      - name: system-info
        url: https://registry.codex.com/mcp/system-info
```

Este archivo es puramente decorativo y no afecta el comportamiento de la skill.

### 3.3 Recomendación: No Usar Campos Exclusivos en Skills Multi-Agente

Para mantener compatibilidad máxima:
- ✅ Usar solo `name`, `description`, `license`, `metadata`, `compatibility`
- ❌ **NO** usar `disable-model-invocation`, `context:fork`, `arguments`, `argument-hint`, `model`, `effort`, `hooks`, `paths`, `when_to_use`, `shell`, `disallowed-tools`, `allowed-tools`

Si necesitas funcionalidad avanzada para Claude Code, crea un archivo separado:
- Skill estándar: `skills/<name>/SKILL.md` (frontmatter mínimo)
- Skill extendida: `skills/<name>/SKILL.claude.md` (con campos Claude Code)

---

## 4. CLI de Instalación — npx skills add

### 4.1 Uso Básico

```bash
# Instalar desde GitHub
npx skills add owner/repo
npx skills add owner/repo --skill skill-name

# Especificar agente(s)
npx skills add owner/repo --skill rocm-setup -a claude-code
npx skills add owner/repo -a claude-code -a opencode -a codex

# Instalar desde path local
npx skills add ./skills/rocm-setup --agent opencode --yes

# Instalar globalmente
npx skills add owner/repo --skill rocm-setup -g

# Listar skills disponibles en un repo
npx skills add . --list
```

### 4.2 Flags Disponibles

| Flag | Alias | Descripción |
|------|-------|-------------|
| `--skill <name>` | `-s` | Skill específica a instalar |
| `--agent <agent>` | `-a` | Agente destino (repetible) |
| `--global` | `-g` | Instalar en directorio global |
| `--list` | `-l` | Listar skills sin instalar |
| `--yes` | `-y` | Omitir confirmación |
| `--help` | `-h` | Ayuda del comando |

### 4.3 Agentes Soportados

El CLI soporta 68+ agentes. Los más relevantes para Munin:

| Agente | Flag | Ruta de instalación |
|--------|------|---------------------|
| Claude Code | `claude-code` | `.claude/skills/` |
| OpenCode | `opencode` | `.opencode/skills/` o `.agents/skills/` |
| Codex CLI | `codex` | `.codex/skills/` o `.agents/skills/` |
| Cursor | `cursor` | `.cursor/skills/` o `.agents/skills/` |
| Cline | `cline` | `.cline/skills/` |
| Roo Code | `roo-code` | `.roo/skills/` |
| Windsurf | `windsurf` | `.windsurf/skills/` |

### 4.4 Formatos Fuente

| Formato | Ejemplo | Descripción |
|---------|---------|-------------|
| GitHub shorthand | `owner/repo` | `https://github.com/owner/repo` |
| GitHub shorthand + subpath | `owner/repo/path` | Subdirectorio dentro del repo |
| URL completa | `https://github.com/owner/repo` | URL git explícita |
| Path local | `./skills/rocm-setup` | Directorio local |
| Path local (proyecto) | `.` | Skills del proyecto actual |

---

## 5. Recomendaciones para Munin

### 5.1 Dirección Primaria

Desarrollar skills en el directorio `skills/<name>/SKILL.md` dentro del repositorio:

```
munin-skills/
├── skills/
│   ├── rocm-setup/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   └── detect-gpu.py
│   │   └── references/
│   │       └── rocm-compat.md
│   ├── multi-gpu-deploy/
│   │   ├── SKILL.md
│   │   └── scripts/
│   └── perf-tune/
│       ├── SKILL.md
│       └── scripts/
├── docs/
│   ├── skills-format-guide.md
│   ├── multi-gpu-patterns.md
│   └── installation-guide.md
├── AGENTS.md
└── README.md
```

### 5.2 Al Instalar

Usar `.agents/skills/` como directorio cross-client. Este directorio es reconocido por Claude Code, OpenCode, Codex y Cursor.

### 5.3 Frontmatter Estándar

Solo incluir `name`, `description`, `license`, `metadata`, `compatibility`:

```yaml
---
name: rocm-setup
description: >
  Configura y verifica el entorno AMD ROCm para PyTorch.
  Detecta GPUs AMD, instala dependencias ROCm, configura variables de entorno.
license: MIT
metadata:
  tags: [rocm, amd, gpu, pytorch, setup]
  category: environment
compatibility:
  - claude-code
  - opencode
  - codex
  - cursor
---
```

### 5.4 Description en Español con Keywords de Activación

La `description` debe incluir:
- **Palabras clave** que el agente usará para activar la skill automáticamente
- **Casos de uso** para que el agente entienda cuándo aplica
- **Formato natural**, como si le explicaras a otro desarrollador

Ejemplo:
```yaml
description: >
  Configura y verifica el entorno AMD ROCm para PyTorch.
  Detecta GPUs AMD, instala dependencias ROCm, configura variables de entorno.
  Útil cuando se trabaja con hardware AMD en tareas de ML/AI.
  Keywords: rocm, amd, gpu, pytorch, setup, hip, mi300, mi250
```

### 5.5 Compatibilidad Declarada

Usar el campo `compatibility` para declarar explícitamente qué agentes soporta la skill:

```yaml
compatibility:
  - claude-code
  - opencode
  - codex
  - cursor
```

Esto permite que el CLI `npx skills add` filtre correctamente y que los agentes sepan si pueden cargar la skill.

---

## Referencias

- [agentskills.io Specification](https://agentskills.io)
- [GitHub: agentskills/skills-format](https://github.com/agentskills/skills-format)
- [Claude Code Skills Documentation](https://docs.anthropic.com/en/docs/claude-code/skills)
- [OpenCode Skills Configuration](https://opencode.jina.io/docs/skills)
