# Guía de Instalación de Skills Munin — Local y Multi-Agente

> Documento consolidado de investigación Fase 0 para el proyecto Munin.
> Cubre instalación local, validación de formato, rutas por agente y troubleshooting.

---

## 1. Instalación Local (Desarrollo)

### 1.1 Listar Skills del Proyecto

```bash
# Desde la raíz de munin-skills/
npx skills add . --list

# Salida esperada:
# 📦 Skills disponibles en .:
#   ── rocm-setup ──
#      Configura y verifica el entorno AMD ROCm para PyTorch
#   ── multi-gpu-deploy ──
#      Despliega modelos multi-GPU con detección automática de backend
#   ── perf-tune ──
#      Ajuste de rendimiento para inferencia en GPUs AMD/NVIDIA
```

### 1.2 Instalar una Skill Específica

```bash
# Instalar rocm-setup en OpenCode
npx skills add . --skill rocm-setup --agent opencode --yes

# Instalar en múltiples agentes
npx skills add . --skill rocm-setup -a claude-code -a opencode -a codex

# Instalar TODAS las skills del proyecto
npx skills add . -a claude-code -a opencode -a codex --yes
```

### 1.3 Instalación Manual (sin npx skills)

**Para OpenCode (global):**
```bash
# Copiar directorio completo
cp -r skills/rocm-setup ~/.config/opencode/skills/rocm-setup
```

**Para OpenCode (local al proyecto):**
```bash
mkdir -p .opencode/skills
cp -r skills/rocm-setup .opencode/skills/rocm-setup
```

**Para Claude Code (local al proyecto):**
```bash
mkdir -p .claude/skills
cp -r skills/rocm-setup .claude/skills/rocm-setup
```

**Para Claude Code (global):**
```bash
mkdir -p ~/.claude/skills
cp -r skills/rocm-setup ~/.claude/skills/rocm-setup
```

**Para Codex (local al proyecto):**
```bash
mkdir -p .codex/skills
cp -r skills/rocm-setup .codex/skills/rocm-setup
```

**Para Cursor (local al proyecto):**
```bash
mkdir -p .cursor/skills
cp -r skills/rocm-setup .cursor/skills/rocm-setup
```

### 1.4 Instalación Cross-Client (Recomendada)

El directorio `.agents/skills/` es reconocido por Claude Code, OpenCode, Codex y Cursor:

```bash
# Crear directorio cross-client
mkdir -p .agents/skills

# Copiar skills
cp -r skills/rocm-setup .agents/skills/rocm-setup
cp -r skills/multi-gpu-deploy .agents/skills/multi-gpu-deploy
cp -r skills/perf-tune .agents/skills/perf-tune
```

Esto hace que las skills estén disponibles en todos los agentes sin configuración adicional.

---

## 2. Validación de Formato

### 2.1 Script Python de Validación

```python
#!/usr/bin/env python3
"""
Validador de formato SKILL.md para skills de Munin.
Uso: python validate_skill.py <ruta-al-skill>
Ejemplo: python validate_skill.py skills/rocm-setup
"""

import os
import sys
import yaml


def validate_skill(skill_path: str) -> bool:
    """
    Valida que un directorio de skill cumpla con el formato agentskills.io.
    
    Args:
        skill_path: Ruta al directorio de la skill
    
    Returns:
        True si la skill es válida, False en caso contrario
    """
    errors = []
    
    # ── Verificar que existe SKILL.md ──
    skill_file = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_file):
        errors.append(f"❌ No se encuentra SKILL.md en {skill_path}")
        for e in errors:
            print(e)
        return False
    
    # ── Leer y parsear frontmatter ──
    with open(skill_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Verificar delimitadores YAML
    if not content.startswith("---"):
        errors.append("❌ SKILL.md debe comenzar con '---' (frontmatter YAML)")
    
    # Extraer frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("❌ SKILL.md debe tener frontmatter YAML entre '---' ... '---'")
        for e in errors:
            print(e)
        return False
    
    frontmatter_str = parts[1].strip()
    
    try:
        data = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        errors.append(f"❌ Error parseando YAML: {e}")
        for e in errors:
            print(e)
        return False
    
    if not isinstance(data, dict):
        errors.append("❌ Frontmatter YAML debe ser un diccionario")
        for e in errors:
            print(e)
        return False
    
    # ── Validar name ──
    name = data.get("name")
    if not name:
        errors.append("❌ Falta campo obligatorio: 'name'")
    elif not isinstance(name, str):
        errors.append("❌ 'name' debe ser un string")
    else:
        import re
        if not re.match(r'^[a-z0-9][a-z0-9-]{0,63}$', name):
            errors.append(f"❌ 'name'='{name}' debe ser lowercase+digits+hyphens, max 64 chars")
        elif len(name) > 64:
            errors.append(f"❌ 'name' demasiado largo: {len(name)} chars (max 64)")
    
    # ── Validar description ──
    description = data.get("description")
    if not description:
        errors.append("❌ Falta campo obligatorio: 'description'")
    elif not isinstance(description, str):
        errors.append("❌ 'description' debe ser un string")
    elif len(description) > 1024:
        errors.append(f"❌ 'description' demasiado larga: {len(description)} chars (max 1024)")
    
    # ── Validar estructura de directorio (opcional) ──
    dirs = os.listdir(skill_path)
    valid_dirs = {"SKILL.md", "scripts", "references", "assets"}
    unknown = [d for d in dirs if d not in valid_dirs and os.path.isdir(os.path.join(skill_path, d))]
    if unknown:
        errors.append(f"⚠️  Directorios extra en skill: {unknown}")
    
    # ── Resultado ──
    if errors:
        print(f"\n📋 Validación de: {skill_path}")
        for e in errors:
            print(f"  {e}")
        return False
    
    print(f"\n✅ {name}: skill válida")
    print(f"   Descripción: {description[:80]}...")
    return True


def validate_all_skills(base_path: str = "skills") -> bool:
    """Valida todas las skills en un directorio."""
    if not os.path.isdir(base_path):
        print(f"❌ No se encuentra el directorio '{base_path}'")
        return False
    
    skills = [d for d in os.listdir(base_path) 
              if os.path.isdir(os.path.join(base_path, d))
              and not d.startswith(".")]
    
    if not skills:
        print(f"⚠️  No se encontraron skills en '{base_path}'")
        return False
    
    print(f"🔍 Validando {len(skills)} skill(s) en '{base_path}/'...\n")
    
    all_valid = True
    for skill_name in sorted(skills):
        skill_path = os.path.join(base_path, skill_name)
        if not validate_skill(skill_path):
            all_valid = False
        print()
    
    if all_valid:
        print("🎉 Todas las skills son válidas")
    else:
        print("⚠️  Algunas skills tienen errores")
    
    return all_valid


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isdir(path):
            validate_skill(path)
        else:
            print(f"❌ Ruta no encontrada: {path}")
            sys.exit(1)
    else:
        validate_all_skills()
```

**Uso:**

```bash
# Validar una skill específica
python validate_skill.py skills/rocm-setup

# Validar todas las skills del proyecto
python validate_skill.py

# Salida típica:
# 🔍 Validando 3 skill(s) en 'skills/'...
# 
# ✅ multi-gpu-deploy: skill válida
#    Descripción: Despliega modelos multi-GPU con detección automática de backen...
#
# ✅ perf-tune: skill válida
#    Descripción: Ajuste de rendimiento para inferencia en GPUs AMD/NVIDIA...
#
# ✅ rocm-setup: skill válida
#    Descripción: Configura y verifica el entorno AMD ROCm para PyTorch...
#
# 🎉 Todas las skills son válidas
```

### 2.2 Validación con skills-ref (si está disponible)

```bash
# skills-ref es un validador oficial del ecosistema agentskills.io

# Instalar
npm install -g skills-ref

# Validar una skill
skills-ref validate ./skills/rocm-setup

# Validar todas las skills del proyecto
skills-ref validate ./skills
```

### 2.3 Validación Manual del Frontmatter

```bash
# Verificar que el YAML es válido
python3 -c "
import yaml
with open('skills/rocm-setup/SKILL.md') as f:
    content = f.read()
    _, fm, _ = content.split('---', 2)
    data = yaml.safe_load(fm)
    assert data['name'], 'Missing name'
    assert data['description'], 'Missing description'
    assert len(data['name']) <= 64, 'Name too long'
    assert len(data['description']) <= 1024, 'Description too long'
    print(f'✅ {data[\"name\"]} valid')
"
```

---

## 3. Rutas de Instalación por Agente

### 3.1 Tabla Completa de Rutas

| Agente | Por Proyecto (local) | Global | Archivo de Proyecto |
|--------|----------------------|--------|---------------------|
| **Claude Code** | `.claude/skills/<name>/` | `~/.claude/skills/<name>/` | `CLAUDE.md` |
| **OpenCode** | `.opencode/skills/<name>/` o `.agents/skills/<name>/` | `~/.config/opencode/skills/<name>/` | `AGENTS.md` u `opencode.json` |
| **Codex CLI** | `.codex/skills/<name>/` o `.agents/skills/<name>/` | `~/.agents/skills/<name>/` o `~/.codex/skills/<name>/` | `AGENTS.md` |
| **Cursor** | `.cursor/skills/<name>/` o `.agents/skills/<name>/` | `~/.cursor/skills/<name>/` | `.cursor/rules/` (YAML) |
| **Cline** | `.cline/skills/<name>/` | `~/.cline/skills/<name>/` | `.clinerules` |
| **Roo Code** | `.roo/skills/<name>/` | `~/.roo/skills/<name>/` | `.roorules` |
| **Windsurf** | `.windsurf/skills/<name>/` | `~/.windsurf/skills/<name>/` | `.windsurfrules` |
| **Continue** | `.continue/skills/<name>/` | `~/.continue/skills/<name>/` | `continue.json` |
| **Augment** | `.augment/skills/<name>/` | `~/.augment/skills/<name>/` | `.augment/config.json` |
| **Copilot** | `.github/copilot-instructions.md` | N/A | `copilot-instructions.md` |

### 3.2 Instalación Global vs Local

**Instalación local (por proyecto):**
```bash
# Las skills viven dentro del repositorio del proyecto
# Se comparten via git con el equipo
npx skills add . --skill rocm-setup --agent opencode
# → .opencode/skills/rocm-setup/
```

**Instalación global (usuario):**
```bash
# Las skills están disponibles en TODOS los proyectos
# No se comparten via git
npx skills add owner/repo --skill rocm-setup --global
# → ~/.config/opencode/skills/rocm-setup/ (OpenCode)
# → ~/.claude/skills/rocm-setup/ (Claude Code)
```

### 3.3 Prioridad de Rutas

Los agentes cargan skills en el siguiente orden de prioridad:

1. **Local (proyecto)**: `./.agents/skills/` → mayor prioridad
2. **Local (agente específico)**: `./.opencode/skills/` → media prioridad
3. **Global**: `~/.config/opencode/skills/` → menor prioridad

Si la misma skill existe en múltiples rutas, gana la de mayor prioridad.

---

## 4. Flujo Recomendado para el Hackathon

### 4.1 Paso 1: Desarrollar Skills en el Repo

Todas las skills se desarrollan en `skills/<name>/SKILL.md` dentro del repositorio `munin-skills/`:

```
munin-skills/
├── skills/
│   ├── rocm-setup/
│   │   └── SKILL.md
│   ├── multi-gpu-deploy/
│   │   └── SKILL.md
│   └── perf-tune/
│       └── SKILL.md
```

### 4.2 Paso 2: Validar con Script Python

```bash
# Validación rápida
python docs/validate_skill.py
```

### 4.3 Paso 3: Instalar Localmente en OpenCode

```bash
# Instalar para pruebas inmediatas
npx skills add . --skill rocm-setup --agent opencode --yes
```

### 4.4 Paso 4: Probar y Replicar en Otros Agentes

```bash
# Una vez funciona en OpenCode, instalar en Claude Code y Codex
npx skills add . --skill rocm-setup -a claude-code -a codex --yes

# O instalar en TODOS los agentes compatibles
npx skills add . -a claude-code -a opencode -a codex -a cursor --yes
```

### 4.5 Paso 5: Publicación Post-Hackathon

```bash
# 1. Subir repo a GitHub
git remote add origin https://github.com/munin-org/munin-skills.git
git push -u origin main

# 2. El repositorio es detectado automáticamente por skills.sh
#    skills.sh escanea repositorios GitHub con skills/ en la raíz

# 3. Para publicación manual en skills.sh:
#    https://skills.sh/add?repo=munin-org/munin-skills

# 4. Los usuarios pueden instalar directamente:
npx skills add munin-org/munin-skills --skill rocm-setup
```

---

## 5. Comando de Instalación Rápida

### 5.1 Instalar Todas las Skills en un Solo Comando

```bash
# Instalar TODAS las skills del proyecto en TODOS los agentes
npx skills add . -a claude-code -a opencode -a codex --yes
```

### 5.2 Script de Instalación Completa

```bash
#!/bin/bash
# install-all.sh — Instala todas las skills de Munin en todos los agentes
# Uso: bash install-all.sh [--global]

set -e

MODE="${1:---local}"
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 Munin — Instalación de Skills"
echo "================================="
echo "Modo: $MODE"
echo "Repo: $BASE_DIR"
echo ""

# Detectar skills disponibles
SKILLS=()
for dir in "$BASE_DIR/skills/"*/; do
    name=$(basename "$dir")
    if [ -f "$dir/SKILL.md" ]; then
        SKILLS+=("$name")
    fi
done

echo "📦 Skills encontradas: ${SKILLS[*]}"
echo ""

# Instalar cada skill
for skill in "${SKILLS[@]}"; do
    echo "── Instalando: $skill ──"
    
    if [ "$MODE" == "--global" ]; then
        # Instalación global
        for agent in claude-code opencode codex cursor; do
            echo "  → $agent (global)"
            npx skills add "$BASE_DIR" --skill "$skill" -a "$agent" -g --yes 2>/dev/null || {
                echo "  ⚠️  Falló instalación en $agent (puede no estar configurado)"
            }
        done
    else
        # Instalación local
        npx skills add "$BASE_DIR" \
            --skill "$skill" \
            -a claude-code \
            -a opencode \
            -a codex \
            -a cursor \
            --yes 2>/dev/null || {
            echo "  ⚠️  Falló instalación en algunos agentes"
        }
    fi
    
    echo ""
done

echo "✅ Instalación completada"
echo ""
echo "📋 Skills instaladas:"
for skill in "${SKILLS[@]}"; do
    echo "  • $skill"
done

echo ""
echo "🔍 Verifica con: ls .agents/skills/ .opencode/skills/ .claude/skills/"
```

**Uso:**
```bash
# Instalación local (por proyecto) — recomendado para desarrollo
bash scripts/install-all.sh --local

# Instalación global (usuario) — recomendado para producción
bash scripts/install-all.sh --global

# Después de instalar, verificar:
ls -la .agents/skills/
ls -la .opencode/skills/
```

---

## 6. Troubleshooting de Instalación

### 6.1 La Skill no Aparece

**Síntoma**: La skill se instaló pero el agente no la encuentra.

**Soluciones:**
```bash
# 1. Reiniciar el agente (necesario para detectar nuevas skills)
#    Cerrar y abrir terminal, o:
exit  # y volver a abrir

# 2. Verificar que la skill está en la ruta correcta
ls -la .agents/skills/rocm-setup/
# Debe mostrar: SKILL.md, scripts/, references/

# 3. Verificar los permisos
chmod -R +r .agents/skills/rocm-setup/

# 4. Verificar el formato del frontmatter
python3 -c "
import yaml
with open('.agents/skills/rocm-setup/SKILL.md') as f:
    print(f.read()[:500])  # Mostrar inicio
"
```

### 6.2 allowed-tools no Funciona

**Síntoma**: El campo `allowed-tools` en el frontmatter es ignorado.

**Causa**: `allowed-tools` es un campo **exclusivo de Claude Code**. OpenCode, Codex y Cursor lo ignoran.

**Solución:**
```yaml
# ✅ CORRECTO — Solo usar allowed-tools si el target ES Claude Code
---
name: rocm-setup
description: Configura ROCm para PyTorch
allowed-tools:
  - Bash
  - Read
  - Edit
---
```

```yaml
# ✅ RECOMENDADO para skills multi-agente — No usar allowed-tools
---
name: rocm-setup
description: Configura ROCm para PyTorch
---
```

### 6.3 El Frontmatter YAML Falla

**Síntoma**: Error al parsear el frontmatter, la skill no carga.

**Causas comunes:**
```
# ❌ ERROR: Sin delimitadores ---
name: rocm-setup
description: algo

# ❌ ERROR: YAML mal indentado
metadata:
  tags: [rocm, amd]
    category: environment  # ← indentación incorrecta

# ❌ ERROR: Caracteres especiales sin escapar
description: Usa &, <, > en texto  # ← & es especial en YAML

# ❌ ERROR: name con mayúsculas
name: ROCm-Setup  # ← solo lowercase permitido
```

**Solución:**
```yaml
# ✅ CORRECTO: Usar description con pipe o quote
---
name: rocm-setup
description: >
  Configura y verifica el entorno AMD ROCm para PyTorch.
  Detecta GPUs AMD, instala dependencias ROCm.
metadata:
  tags:
    - rocm
    - amd
  category: environment
---
```

### 6.4 El CLI npx skills add no Instala Correctamente

**Síntoma**: El comando se ejecuta pero la skill no aparece en el directorio destino.

**Soluciones:**
```bash
# 1. Verificar versión de Node.js (requiere >=18)
node --version

# 2. Intentar instalación explícita
npx skills add . --skill rocm-setup --agent opencode --yes --verbose

# 3. Instalación manual como fallback
cp -r skills/rocm-setup .opencode/skills/rocm-setup

# 4. Verificar que el directorio skills/ existe
ls skills/

# 5. Limpiar caché de npx
npx clear-npx-cache 2>/dev/null || true
```

### 6.5 Conflictos entre Skills del Mismo Nombre

**Síntoma**: Una skill instalada globalmente tiene el mismo nombre que una local, y se carga la incorrecta.

**Regla**: Los agentes priorizan: skills locales del proyecto > skills globales del usuario.

```bash
# Verificar qué skill se está cargando
# Para Claude Code:
ls -la .claude/skills/rocm-setup/       # Local (mayor prioridad)
ls -la ~/.claude/skills/rocm-setup/     # Global (menor prioridad)

# Solución: Remover la skill conflictiva
rm -rf .claude/skills/rocm-setup/       # Usar la global
# O
rm -rf ~/.claude/skills/rocm-setup/    # Usar la local
```

### 6.6 Skills No Detectadas por Cursor

Cursor no usa el sistema SKILL.md nativamente. Usa `.cursor/rules/` con formato YAML propio:

```yaml
# .cursor/rules/rocm-setup.mdc
---
description: Configura ROCm para PyTorch en GPUs AMD
glob: "*.py"
---
Ejecuta `python scripts/detect-gpu.py` para verificar el backend.
Usa `torch.cuda.is_available()` para detectar GPU.
```

Para compatibilidad con Cursor, crear un symlink o copiar manualmente:

```bash
# Convertir skill Munin a regla de Cursor
ln -s ../../skills/rocm-setup/SKILL.md .cursor/rules/rocm-setup.md
```

### 6.7 Tabla Rápida de Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| Skill no aparece | Agente no reiniciado | Reiniciar terminal o agente |
| Skill no aparece | Ruta incorrecta | Verificar `ls .agents/skills/<name>/` |
| allowed-tools ignorado | No es Claude Code | Usar solo en skills dedicadas a Claude Code |
| YAML error | Sintaxis YAML inválida | Validar con `python -c "import yaml; yaml.safe_load(open('SKILL.md').read().split('---')[1])"` |
| npx skills add falla | Node.js < 18 | Actualizar Node.js o instalar manualmente |
| Skill duplicada | Global + local | Remover la que no se necesita |
| Cursor no reconoce | Formato incompatible | Usar `.cursor/rules/` con formato `.mdc` |
| Descripción muy larga | > 1024 chars | Acortar descripción |

---

## Referencias

- [skills.sh — Skill Registry](https://skills.sh)
- [agentskills.io — Specification](https://agentskills.io)
- [npx skills add — CLI Reference](https://github.com/agentskills/skills-cli)
- [OpenCode Skills Docs](https://opencode.jina.ai/docs/skills)
- [Claude Code Skills](https://docs.anthropic.com/en/docs/claude-code/skills)
