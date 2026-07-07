#!/bin/bash
# =============================================================================
# detect-backend.sh — Video Acceleration Backend Detection
# =============================================================================
# Detects available video acceleration hardware on the system:
#   - AMD VCN (VAAPI via vainfo / gstvaapiinfo / gst-inspect)
#   - NVIDIA NVDEC (nvidia-smi + nv-codec-headers + gst-inspect)
#   - CPU fallback (software decode via avdec_*)
#
# Usage:
#   bash detect-backend.sh           # Human-readable report
#   bash detect-backend.sh --json    # JSON output for programmatic use
#   bash detect-backend.sh --quiet   # Exit code only
#
# Exit codes:
#   0 = Hardware decode available (AMD VCN or NVIDIA NVDEC)
#   1 = CPU only (software decode)
#   2 = Error during detection
# =============================================================================

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
MODE="${1:-normal}"
EXIT_CODE=0

# ── State ────────────────────────────────────────────────────────────────────
BACKEND="cpu"
BACKEND_SCORE=0
DECODE_ELEMENTS=""
ENCODE_ELEMENTS=""
VAAPI_DRIVER=""
VAAPI_VERSION=""
NVIDIA_DRIVER=""
NVIDIA_GPUS=0
DEVICES=""
SUPPORTED_CODECS=""
ERRORS=""

# ── Output Helpers ──────────────────────────────────────────────────────────

log_info()    { [ "$MODE" != "--json" ] && echo -e "  $1"; }
log_ok()      { [ "$MODE" != "--json" ] && echo -e "  ✅ $1"; }
log_warn()    { [ "$MODE" != "--json" ] && echo -e "  ⚠️  $1"; }
log_error()   { [ "$MODE" != "--json" ] && echo -e "  ❌ $1"; }
log_header()  { [ "$MODE" != "--json" ] && echo -e "\n─── $1 ───"; }

json_escape() {
    echo "$1" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null || echo "\"$1\""
}

# ── Detection Functions ─────────────────────────────────────────────────────

detect_vaapi() {
    """Detect AMD VAAPI/VCN capabilities via vainfo and gstvaapiinfo."""
    local vaapi_found=false

    # Check vainfo
    if command -v vainfo &>/dev/null; then
        local vainfo_out
        vainfo_out=$(vainfo 2>&1 || true)
        if echo "$vainfo_out" | grep -qiE "Driver version|VAProfile|renderD|Gallium|Mesa|amdgpu|radeonsi"; then
            vaapi_found=true
            VAAPI_DRIVER=$(echo "$vainfo_out" | grep -i "Driver version" | head -1 | sed 's/.*Driver version: //' | xargs || echo "unknown")
            VAAPI_VERSION=$(echo "$vainfo_out" | grep -i "libva" | head -1 | sed 's/.*libva //' | xargs || echo "")
            log_ok "VAAPI available — Driver: ${VAAPI_DRIVER:-unknown}"

            # Extract supported profiles/codecs
            local codecs
            codecs=$(echo "$vainfo_out" | grep -i "VAProfile" | sed 's/.*VAProfile//' | sed 's/ .*//' | sort -u | tr '\n' ' ' || true)
            SUPPORTED_CODECS="$codecs"
            log_info "  VAAPI profiles: $(echo "$codecs" | tr '\n' ' ')"
        else
            log_warn "vainfo found but no VAAPI driver active"
            log_info "  Output: $(echo "$vainfo_out" | head -3 | tr '\n' ' ')"
        fi
    else
        log_info "vainfo not found (install with: sudo apt install vainfo)"
    fi

    # Check gstvaapiinfo (more detailed)
    if command -v gstvaapiinfo &>/dev/null; then
        local gstva_out
        gstva_out=$(gstvaapiinfo 2>&1 || true)
        if echo "$gstva_out" | grep -qiE "Decoder|Encoder|VCN|UVD"; then
            vaapi_found=true
            log_ok "gstvaapiinfo: VAAPI acceleration details available"
        fi
    fi

    # Check via gst-inspect for VAAPI elements
    if command -v gst-inspect-1.0 &>/dev/null; then
        local vaapi_elements
        vaapi_elements=$(gst-inspect-1.0 2>/dev/null | grep -i "vaapi" | awk '{print $2}' | tr '\n' ' ' || true)
        if [ -n "$vaapi_elements" ]; then
            vaapi_found=true
            DECODE_ELEMENTS=$(echo "$vaapi_elements" | tr ' ' '\n' | grep -i "dec$\|decode" | tr '\n' ' ' || true)
            ENCODE_ELEMENTS=$(echo "$vaapi_elements" | tr ' ' '\n' | grep -i "enc$\|encode" | tr '\n' ' ' || true)
            log_info "  VAAPI GStreamer elements: ${vaapi_elements}"
        fi
    fi

    # Check /dev/dri for render nodes
    if [ -d /dev/dri ]; then
        local render_nodes
        render_nodes=$(ls /dev/dri/render* 2>/dev/null | tr '\n' ' ' || true)
        if [ -n "$render_nodes" ]; then
            DEVICES="$render_nodes"
        fi
    fi

    echo "$vaapi_found"
}

detect_nvidia() {
    """Detect NVIDIA NVDEC/NVENC capabilities via nvidia-smi and gst-inspect."""
    local nvidia_found=false

    # Check nvidia-smi
    if command -v nvidia-smi &>/dev/null; then
        local nv_out
        nv_out=$(nvidia-smi --query-gpu=name,driver_version,index --format=csv,noheader 2>/dev/null || true)
        if [ -n "$nv_out" ]; then
            NVIDIA_GPUS=$(echo "$nv_out" | grep -c . || echo 0)
            NVIDIA_DRIVER=$(echo "$nv_out" | head -1 | cut -d',' -f2 | xargs || echo "unknown")
            local nv_names
            nv_names=$(echo "$nv_out" | cut -d',' -f1 | xargs | tr '\n' ';' || true)
            log_ok "NVIDIA GPU(s) detected: ${NVIDIA_GPUS} — ${nv_names}"
            nvidia_found=true
        fi
    fi

    # Check nvidia-smi dmon for encoder/decoder utilization
    if command -v nvidia-smi &>/dev/null; then
        local enc_dec_support
        enc_dec_support=$(nvidia-smi -q 2>/dev/null | grep -i "Encoder\|Decoder" || true)
        if [ -n "$enc_dec_support" ]; then
            log_info "  NVIDIA encoder/decoder capabilities found"
        fi
    fi

    # Check gst-inspect for NVDEC/NVENC elements
    if command -v gst-inspect-1.0 &>/dev/null; then
        local nvdec_exists
        nvdec_exists=$(gst-inspect-1.0 nvdec 2>/dev/null && echo "yes" || echo "no")
        local nvenc_exists
        nvenc_exists=$(gst-inspect-1.0 nvenc 2>/dev/null && echo "yes" || echo "no")
        local nvcodec_exists
        nvcodec_exists=$(gst-inspect-1.0 nvcodec 2>/dev/null && echo "yes" || echo "no")

        if [ "$nvdec_exists" = "yes" ]; then
            nvidia_found=true
            DECODE_ELEMENTS="$DECODE_ELEMENTS nvdec"
            log_ok "GStreamer NVDEC element available"
        fi
        if [ "$nvenc_exists" = "yes" ]; then
            ENCODE_ELEMENTS="$ENCODE_ELEMENTS nvenc"
            log_ok "GStreamer NVENC element available"
        fi
        if [ "$nvcodec_exists" = "yes" ]; then
            nvidia_found=true
            log_ok "GStreamer NVCODEC element available"
        fi
    fi

    echo "$nvidia_found"
}

detect_cpu() {
    """Detect CPU software decode capabilities via gst-inspect."""
    local cpu_found=false

    if command -v gst-inspect-1.0 &>/dev/null; then
        local av_decoders
        av_decoders=$(gst-inspect-1.0 2>/dev/null | grep "avdec_" | awk '{print $2}' | tr '\n' ' ' || true)
        if [ -n "$av_decoders" ]; then
            cpu_found=true
            DECODE_ELEMENTS="$DECODE_ELEENTS $av_decoders"
            log_info "  Software decoders (avdec): $(echo "$av_decoders" | wc -w) available"
            SUPPORTED_CODECS="$SUPPORTED_CODECS avdec"
        fi

        local software_enc
        software_enc=$(gst-inspect-1.0 2>/dev/null | grep -E "x264|x265|avenc_" | awk '{print $2}' | tr '\n' ' ' || true)
        if [ -n "$software_enc" ]; then
            ENCODE_ELEMENTS="$ENCODE_ELEMENTS $software_enc"
        fi
    fi

    # Check number of CPU cores
    local cpu_cores
    cpu_cores=$(nproc 2>/dev/null || echo "unknown")
    log_info "  CPU cores: ${cpu_cores}"

    echo "$cpu_found"
}

# ── Scoring ─────────────────────────────────────────────────────────────────

calculate_score() {
    """Calculate backend score: 100 = optimal HW decode, 50 = CPU, 0 = none."""
    local backend_type="$1"

    case "$backend_type" in
        amd)
            BACKEND_SCORE=100
            # Deduct for missing VAAPI elements
            if [ -z "$DECODE_ELEMENTS" ]; then
                BACKEND_SCORE=$((BACKEND_SCORE - 30))
            fi
            ;;
        nvidia)
            BACKEND_SCORE=100
            if [ -z "$DECODE_ELEMENTS" ]; then
                BACKEND_SCORE=$((BACKEND_SCORE - 30))
            fi
            ;;
        cpu)
            BACKEND_SCORE=50
            ;;
        *)
            BACKEND_SCORE=0
            ;;
    esac
}

# ── Main ────────────────────────────────────────────────────────────────────

main() {
    [ "$MODE" != "--json" ] && [ "$MODE" != "--quiet" ] && echo "
╔══════════════════════════════════════════════════════════╗
║   Munin — Video Acceleration Backend Detection          ║
║   AMD VCN / NVIDIA NVDEC / CPU Software Decode          ║
╚══════════════════════════════════════════════════════════╝
"

    # ── Step 1: GStreamer Base Check ────────────────────────────────────────
    log_header "GStreamer"
    if command -v gst-inspect-1.0 &>/dev/null; then
        local gst_ver
        gst_ver=$(gst-inspect-1.0 --version 2>&1 | head -1 | sed 's/.*version //' || true)
        log_ok "GStreamer ${gst_ver:-found}"
    else
        log_error "gst-inspect-1.0 not found. Install GStreamer: sudo apt install gstreamer1.0-tools"
        ERRORS="gst-inspect-1.0 not found"
    fi

    # ── Step 2: AMD VAAPI / VCN Detection ──────────────────────────────────
    log_header "AMD VCN (VAAPI)"
    local amd_found
    amd_found=$(detect_vaapi)

    if [ "$amd_found" = "true" ]; then
        log_ok "AMD VCN hardware acceleration detected"
    else
        log_info "No AMD VCN detected"
    fi

    # ── Step 3: NVIDIA NVDEC Detection ────────────────────────────────────
    log_header "NVIDIA NVDEC"
    local nvidia_found
    nvidia_found=$(detect_nvidia)

    if [ "$nvidia_found" = "true" ]; then
        log_ok "NVIDIA NVDEC hardware acceleration detected"
    else
        log_info "No NVIDIA NVDEC detected"
    fi

    # ── Step 4: CPU Software Decode ────────────────────────────────────────
    log_header "CPU Software Decode"
    local cpu_found
    cpu_found=$(detect_cpu)

    # ── Determine Best Backend ─────────────────────────────────────────────
    if [ "$amd_found" = "true" ]; then
        BACKEND="amd"
        calculate_score "amd"
    elif [ "$nvidia_found" = "true" ]; then
        BACKEND="nvidia"
        calculate_score "nvidia"
    elif [ "$cpu_found" = "true" ]; then
        BACKEND="cpu"
        calculate_score "cpu"
    else
        log_warn "No decode backend detected at all"
        BACKEND="none"
        BACKEND_SCORE=0
        EXIT_CODE=2
    fi

    # ── Summary ────────────────────────────────────────────────────────────
    log_header "Summary"
    local backend_label=""
    case "$BACKEND" in
        amd)     backend_label="AMD VCN (VAAPI)" ;;
        nvidia)  backend_label="NVIDIA NVDEC" ;;
        cpu)     backend_label="CPU (Software)" ;;
        none)    backend_label="None" ;;
    esac

    if [ "$BACKEND" = "amd" ] || [ "$BACKEND" = "nvidia" ]; then
        log_ok "🎯 Backend: ${backend_label} (score: ${BACKEND_SCORE}) — Hardware accelerated"
        EXIT_CODE=0
    elif [ "$BACKEND" = "cpu" ]; then
        log_warn "🎯 Backend: ${backend_label} (score: ${BACKEND_SCORE}) — Software decode only"
        EXIT_CODE=1
    else
        log_error "No decode backend available"
        EXIT_CODE=2
    fi

    # ── JSON Output ────────────────────────────────────────────────────────
    if [ "$MODE" = "--json" ]; then
        cat <<JSONEOF
{
  "backend": $(json_escape "$BACKEND"),
  "backend_label": $(json_escape "$backend_label"),
  "score": $BACKEND_SCORE,
  "vaapi": {
    "available": $(json_escape "$amd_found"),
    "driver": $(json_escape "$VAAPI_DRIVER"),
    "version": $(json_escape "$VAAPI_VERSION"),
    "devices": $(json_escape "$DEVICES")
  },
  "nvidia": {
    "available": $(json_escape "$nvidia_found"),
    "gpu_count": $NVIDIA_GPUS,
    "driver": $(json_escape "$NVIDIA_DRIVER")
  },
  "cpu": {
    "available": $(json_escape "$cpu_found"),
    "cores": $(nproc 2>/dev/null || echo 0)
  },
  "decode_elements": $(json_escape "$DECODE_ELEMENTS"),
  "encode_elements": $(json_escape "$ENCODE_ELEMENTS"),
  "supported_codecs": $(json_escape "$SUPPORTED_CODECS"),
  "exit_code": $EXIT_CODE
}
JSONEOF
    fi

    [ "$MODE" != "--json" ] && [ "$MODE" != "--quiet" ] && echo ""
    exit $EXIT_CODE
}

main
