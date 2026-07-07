#!/bin/bash
# ============================================================
# test-vlm.sh — Test Multimodal Inference on vLLM Server
# ============================================================
# Prueba inferencia multimodal (texto + imagen) contra un
# servidor vLLM con API compatible OpenAI.
#
# Uso:
#   ./test-vlm.sh                                          # Defaults
#   ./test-vlm.sh --server http://localhost:8000
#   ./test-vlm.sh --image mi_foto.jpg --prompt "¿Qué ves?"
#   ./test-vlm.sh --model Qwen/Qwen2-VL-7B-Instruct
# ============================================================

set -euo pipefail

# ─── Configuración por defecto ───────────────────────────────
SERVER="http://localhost:8000"
MODEL="OpenGVLab/InternVL2-8B"
IMAGE="test.jpg"
PROMPT="Describe esta imagen en detalle. ¿Qué objetos, personas o escenas reconoces?"
MAX_TOKENS=300
TEMPERATURE=0.7
TIMEOUT=120

# ─── Colores ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()     { echo -e "${RED}[ERROR]${NC} $1"; }
header()  { echo -e "\n${CYAN}━━━ $1 ━━━${NC}"; }
subheader() { echo -e "\n${MAGENTA}--- $1 ---${NC}"; }

# ─── Parseo de argumentos ────────────────────────────────────
usage() {
    cat <<EOF
Uso: $0 [OPCIONES]

Opciones:
  --server <url>     URL del servidor vLLM (default: $SERVER)
  --model <nombre>   Nombre del modelo (default: $MODEL)
  --image <path>     Ruta a la imagen de test (default: $IMAGE)
  --prompt <texto>   Prompt para la inferencia (default: prompt detallado)
  --max-tokens <int> Tokens máximos en respuesta (default: $MAX_TOKENS)
  --temperature <fl> Temperatura de muestreo (default: $TEMPERATURE)
  --timeout <sec>    Timeout para peticiones (default: $TIMEOUT)
  --help, -h         Mostrar ayuda

Ejemplos:
  $0                                              # Test con defaults
  $0 --server http://192.168.1.100:8000           # Servidor remoto
  $0 --image foto.jpg --prompt "¿Qué hay aquí?"  # Imagen personalizada
  $0 --model Qwen/Qwen2-VL-7B-Instruct            # Modelo diferente
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --server)      SERVER="$2"; shift 2 ;;
        --model)       MODEL="$2"; shift 2 ;;
        --image)       IMAGE="$2"; shift 2 ;;
        --prompt)      PROMPT="$2"; shift 2 ;;
        --max-tokens)  MAX_TOKENS="$2"; shift 2 ;;
        --temperature) TEMPERATURE="$2"; shift 2 ;;
        --timeout)     TIMEOUT="$2"; shift 2 ;;
        --help|-h)     usage ;;
        *)
            err "Argumento desconocido: $1"
            usage
            ;;
    esac
done

# ─── Banner ──────────────────────────────────────────────────
echo ""
echo -e "${CYAN}════════════════════════════════════════════${NC}"
echo -e "${CYAN}  VLM Inference Test${NC}"
echo -e "${CYAN}════════════════════════════════════════════${NC}"
echo "  Servidor:  $SERVER"
echo "  Modelo:    $MODEL"
echo "  Imagen:    $IMAGE"
echo "  Prompt:    ${PROMPT:0:60}..."
echo ""

# ─── Verificar dependencias ──────────────────────────────────
header "Verificando Dependencias"

# curl
if ! command -v curl &> /dev/null; then
    err "curl no encontrado. Instala curl."
    exit 1
fi
ok "curl disponible"

# python3
if ! command -v python3 &> /dev/null; then
    err "python3 no encontrado."
    exit 1
fi
ok "python3 disponible"

# requests de Python
if ! python3 -c "import requests" &> /dev/null 2>&1; then
    warn "requests no instalado. Instalando..."
    pip install requests -q
fi
ok "requests instalado"

# PIL para crear imagen de test
if ! python3 -c "from PIL import Image" &> /dev/null 2>&1; then
    warn "Pillow no instalado. Instalando..."
    pip install Pillow -q
fi
ok "Pillow instalado"

# ─── Esperar a que el servidor esté listo ────────────────────
header "Esperando Servidor"

MAX_RETRIES=30
RETRY_INTERVAL=5
READY=false

info "Polling $SERVER/v1/models..."

for i in $(seq 1 "$MAX_RETRIES"); do
    if curl -sf "${SERVER}/v1/models" &> /dev/null; then
        READY=true
        info "Servidor listo (intento $i)"
        break
    fi
    echo -n "."
    sleep "$RETRY_INTERVAL"
done
echo ""

if ! $READY; then
    err "Servidor no disponible después de $((MAX_RETRIES * RETRY_INTERVAL)) segundos."
    err "Verifica que el servidor esté corriendo: curl $SERVER/v1/models"
    exit 1
fi
ok "Servidor listo en $SERVER"

# ─── Crear imagen de test si no existe ────────────────────────
header "Verificando Imagen de Test"

if [[ ! -f "$IMAGE" ]]; then
    info "Imagen no encontrada: $IMAGE"
    info "Creando imagen de test sintética..."
    python3 -c "
from PIL import Image, ImageDraw, ImageFont
import os

w, h = 512, 512
img = Image.new('RGB', (w, h), color='#1a1a2e')
draw = ImageDraw.Draw(img)

# Fondo con gradiente simple
for y in range(h):
    r = int(26 + (y / h) * 30)
    g = int(26 + (y / h) * 20)
    b = int(46 + (y / h) * 40)
    for x in range(w):
        if (x // 50 + y // 50) % 2 == 0:
            img.putpixel((x, y), (r, g, b))

# Sol
draw.ellipse([380, 60, 460, 140], fill='#ffd700', outline='#ffaa00', width=3)

# Montañas
draw.polygon([(0, 350), (100, 180), (200, 300), (300, 150), (400, 280), (512, 200), (512, 512), (0, 512)], fill='#2d5016')
draw.polygon([(200, 350), (300, 220), (400, 300), (512, 250), (512, 512), (200, 512)], fill='#3a6b1e')

# Lago
draw.rectangle([0, 380, 512, 512], fill='#1a5276')

# Árbol
draw.rectangle([60, 280, 75, 360], fill='#5c3a1e')
draw.ellipse([40, 240, 95, 310], fill='#145a32')

# Casa
draw.rectangle([150, 300, 230, 360], fill='#d4a373')
draw.polygon([(140, 300), (190, 260), (240, 300)], fill='#8b4513')
draw.rectangle([180, 320, 200, 360], fill='#5c3a1e')

# Texto
try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
except:
    font = ImageFont.load_default()
draw.text((160, 400), 'TEST', fill='white', font=font)

img.save('$IMAGE')
print(f'Imagen de test creada: $IMAGE ({w}x{h})')
"
    ok "Imagen de test creada: $IMAGE"
else
    # Verificar que la imagen es válida
    if ! python3 -c "from PIL import Image; Image.open('$IMAGE').verify()" 2>/dev/null; then
        err "La imagen $IMAGE no es válida o está corrupta."
        exit 1
    fi
    ok "Imagen encontrada: $IMAGE ($(du -h "$IMAGE" | cut -f1))"
fi

# Obtener dimensiones de la imagen
IMG_INFO=$(python3 -c "
from PIL import Image
img = Image.open('$IMAGE')
print(f'{img.size[0]}x{img.size[1]} ({img.mode})')
")
echo "         Dimensiones: $IMG_INFO"

# ─── Test 1: GET /v1/models ──────────────────────────────────
header "Test 1: GET /v1/models"

START_TIME=$(date +%s%N)
HTTP_CODE=$(curl -s -o /tmp/vllm_test_models.json -w "%{http_code}" "${SERVER}/v1/models")
END_TIME=$(date +%s%N)
ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))

if [[ "$HTTP_CODE" == "200" ]]; then
    ok "HTTP $HTTP_CODE — ${ELAPSED_MS}ms"
    echo ""
    python3 -c "
import json
with open('/tmp/vllm_test_models.json') as f:
    data = json.load(f)
models = data.get('data', [])
print(f'  Modelos disponibles ({len(models)}):')
for m in models:
    mid = m.get('id', m.get('name', 'unknown'))
    print(f'    • {mid}')
" 2>/dev/null || echo "  (respuesta: $(head -c 200 /tmp/vllm_test_models.json))"
else
    err "HTTP $HTTP_CODE — ${ELAPSED_MS}ms"
    cat /tmp/vllm_test_models.json 2>/dev/null || true
fi

# ─── Test 2: Chat solo texto ─────────────────────────────────
header "Test 2: Chat Completion (solo texto)"

TEXT_PROMPT="Explain the concept of neural networks in 2-3 sentences. Keep it simple."

START_TIME=$(date +%s%N)
HTTP_CODE=$(curl -s -o /tmp/vllm_test_text.json -w "%{http_code}" \
    "${SERVER}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "$(cat <<EOF
{
    "model": "${MODEL}",
    "messages": [
        {"role": "user", "content": "${TEXT_PROMPT}"}
    ],
    "max_tokens": ${MAX_TOKENS},
    "temperature": ${TEMPERATURE}
}
EOF
)" --max-time "$TIMEOUT")
END_TIME=$(date +%s%N)
ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))

if [[ "$HTTP_CODE" == "200" ]]; then
    ok "HTTP $HTTP_CODE — ${ELAPSED_MS}ms (tiempo total)"
    echo ""
    python3 -c "
import json, time

with open('/tmp/vllm_test_text.json') as f:
    data = json.load(f)

choice = data['choices'][0]
content = choice['message']['content']
role = choice['message']['role']

# Obtener uso de tokens
usage = data.get('usage', {})
prompt_tokens = usage.get('prompt_tokens', 0)
completion_tokens = usage.get('completion_tokens', 0)
total_tokens = usage.get('total_tokens', 0)
elapsed_ms = ${ELAPSED_MS}

# Calcular métricas
tokens_per_sec = (completion_tokens / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0

print(f'  Rol:        {role}')
print(f'  Tokens:     {prompt_tokens} prompt → {completion_tokens} completados ({total_tokens} total)')
print(f'  Latencia:   {elapsed_ms}ms')
print(f'  Throughput: {tokens_per_sec:.1f} tokens/s')
print(f'')
print(f'  Respuesta:')
for line in content.split('\n'):
    print(f'    {line}')
" 
else
    err "HTTP $HTTP_CODE — ${ELAPSED_MS}ms"
    cat /tmp/vllm_test_text.json 2>/dev/null | python3 -m json.tool 2>/dev/null || cat /tmp/vllm_test_text.json
fi

# ─── Test 3: Chat multimodal (texto + imagen) ────────────────
header "Test 3: Chat Completion (multimodal: texto + imagen)"

START_TIME=$(date +%s%N)
HTTP_CODE=$(python3 -c "
import requests, json, base64, sys, time

# Codificar imagen
with open('${IMAGE}', 'rb') as f:
    img_b64 = base64.b64encode(f.read()).decode()

# Payload
payload = {
    'model': '${MODEL}',
    'messages': [{
        'role': 'user',
        'content': [
            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}},
            {'type': 'text', 'text': '${PROMPT}'}
        ]
    }],
    'max_tokens': ${MAX_TOKENS},
    'temperature': ${TEMPERATURE}
}

# Enviar
resp = requests.post(
    '${SERVER}/v1/chat/completions',
    json=payload,
    timeout=${TIMEOUT}
)

# Guardar respuesta
with open('/tmp/vllm_test_multimodal.json', 'w') as f:
    json.dump(resp.json(), f, indent=2)

print(resp.status_code)
sys.stdout.flush()

if resp.status_code == 200:
    data = resp.json()
    choice = data['choices'][0]
    usage = data.get('usage', {})
    
    print(f'CONTENT:{choice[\"message\"][\"content\"]}')
    print(f'TOKENS:{usage.get(\"prompt_tokens\", 0)} prompt -> {usage.get(\"completion_tokens\", 0)} completion')
" 2>/dev/null || echo "failed")
END_TIME=$(date +%s%N)
ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))

# Parsear output del test multimodal
if [[ "$HTTP_CODE" == "200" ]]; then
    ok "HTTP 200 — ${ELAPSED_MS}ms"
    echo ""
    
    # Extraer contenido y tokens del output
    MULTIMODAL_CONTENT=$(python3 -c "
import json
with open('/tmp/vllm_test_multimodal.json') as f:
    data = json.load(f)
choice = data['choices'][0]
usage = data.get('usage', {})
prompt_t = usage.get('prompt_tokens', 0)
completion_t = usage.get('completion_tokens', 0)
total_t = usage.get('total_tokens', 0)
elapsed_ms = ${ELAPSED_MS}
tps = (completion_t / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0
print(f'  Tokens:     {prompt_t} prompt → {completion_t} completados ({total_t} total)')
print(f'  Latencia:   {elapsed_ms}ms')
print(f'  Throughput: {tps:.1f} tokens/s')
print(f'')
print(f'  Prompt:')
print(f'    {choice[\"message\"][\"content\"][:100]}...' if isinstance(choice['message']['content'], str) else '    (respuesta estructurada)')
if isinstance(choice['message']['content'], str):
    print(f'')
    print(f'  Respuesta completa:')
    for line in choice['message']['content'].split('\n'):
        print(f'    {line}')
" 2>/dev/null || warn "No se pudo parsear respuesta multimodal")
    
    echo "$MULTIMODAL_CONTENT"
else
    err "Falló la inferencia multimodal (${ELAPSED_MS}ms)"
    if [[ -f /tmp/vllm_test_multimodal.json ]]; then
        err "Respuesta:"
        python3 -m json.tool /tmp/vllm_test_multimodal.json 2>/dev/null | head -30
    fi
fi

# ─── Resumen de rendimiento ──────────────────────────────────
header "Resumen de Rendimiento"

echo ""
echo -e "  ${CYAN}Test${NC}                      ${CYAN}Estado${NC}    ${CYAN}Latencia${NC}"
echo "  ────────────────────────────────────────────"

# Test 1: Models endpoint
T1_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVER}/v1/models" --max-time 5 2>/dev/null || echo "000")
T1_STATUS=$( [[ "$T1_CODE" == "200" ]] && echo -e "${GREEN}✅ OK${NC}" || echo -e "${RED}❌ FAIL${NC}" )
printf "  %-28s %b    %s\n" "GET /v1/models" "$T1_STATUS" "${ELAPSED_MS}ms"

# Test 2: Text-only chat
T2_CODE=$(python3 -c "
import requests
try:
    r = requests.post('${SERVER}/v1/chat/completions', json={
        'model': '${MODEL}',
        'messages': [{'role': 'user', 'content': 'Hi'}],
        'max_tokens': 10
    }, timeout=10)
    print(r.status_code)
except: print('000')
" 2>/dev/null)
T2_STATUS=$( [[ "$T2_CODE" == "200" ]] && echo -e "${GREEN}✅ OK${NC}" || echo -e "${RED}❌ FAIL${NC}" )
printf "  %-28s %b\n" "Chat (solo texto)" "$T2_STATUS"

# Test 3: Multimodal chat
T3_CODE=$( [[ -f /tmp/vllm_test_multimodal.json ]] && python3 -c "
import json
with open('/tmp/vllm_test_multimodal.json') as f:
    d = json.load(f)
print('OK' if 'choices' in d else 'FAIL')
" 2>/dev/null || echo "FAIL" )
T3_STATUS=$( [[ "$T3_CODE" == "OK" ]] && echo -e "${GREEN}✅ OK${NC}" || echo -e "${RED}❌ FAIL${NC}" )
printf "  %-28s %b\n" "Chat (multimodal)" "$T3_STATUS"

echo ""
echo -e "  ${CYAN}Modelo:${NC} $MODEL"
echo -e "  ${CYAN}Servidor:${NC} $SERVER"
echo ""

# ─── Limpieza ────────────────────────────────────────────────
rm -f /tmp/vllm_test_models.json /tmp/vllm_test_text.json

# ─── Resultado final ─────────────────────────────────────────
if [[ "$T1_CODE" == "200" && "$T2_CODE" == "200" && "$T3_CODE" == "OK" ]]; then
    ok "✅ Todos los tests pasaron exitosamente."
    exit 0
else
    warn "⚠️  Algunos tests fallaron. Revisa los mensajes de error arriba."
    exit 1
fi
