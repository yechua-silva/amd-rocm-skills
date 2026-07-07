#!/bin/bash
# =============================================================================
# gst-pipeline.sh — GStreamer Video Capture + Decode + Frame Extraction
# =============================================================================
# Multi-backend pipeline: AMD VCN (vaapi), NVIDIA NVDEC (nvdec), CPU (avdec).
# Supports RTSP streams, local files, and v4l2 cameras.
#
# Usage:
#   bash gst-pipeline.sh --source file   --input video.mp4 --output ./frames
#   bash gst-pipeline.sh --source rtsp   --input rtsp://... --output ./frames
#   bash gst-pipeline.sh --source camera --input /dev/video0 --output ./frames
#
# Options:
#   --source       Source type: file | rtsp | camera (default: auto)
#   --input        Input URI or path (required)
#   --output       Output directory for frames (required)
#   --interval     Interval in seconds between frames (default: 1.0)
#   --keyframes-only  Extract only keyframes (I-frames) instead of interval
#   --scene-change    Extract frames on scene change
#   --backend      Decode backend: auto | amd | nvidia | cpu (default: auto)
#   --width        Output frame width (default: 640)
#   --height       Output frame height (default: 480)
#   --format       Output image format: jpeg | png (default: jpeg)
#   --rtsp-transport  RTSP transport: tcp | udp | udp-mcast (default: tcp)
#   --rtsp-timeout    RTSP connection timeout in seconds (default: 10)
#   --help         Show this help
#
# Output:
#   - Frames saved as frame_0001.jpg (or .png) in output directory
#   - frames.txt file with list of all frame filenames and timestamps
# =============================================================================

set -euo pipefail

# ── Default Configuration ──────────────────────────────────────────────────
SOURCE="auto"
INPUT=""
OUTPUT=""
INTERVAL=1.0
KEYFRAMES_ONLY=false
SCENE_CHANGE=false
BACKEND="auto"
WIDTH=640
HEIGHT=480
FORMAT="jpeg"
RTSP_TRANSPORT="tcp"
RTSP_TIMEOUT=10
SHOW_HELP=false

# ── Parse Arguments ────────────────────────────────────────────────────────

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --source TYPE       Source type: file | rtsp | camera (default: auto)
  --input URI         Input URI or path (required)
  --output DIR        Output directory for frames (required)
  --interval SECS     Interval between frames in seconds (default: 1.0)
  --keyframes-only    Extract only keyframes (I-frames)
  --scene-change      Extract frames on scene change
  --backend BACKEND   Decode backend: auto | amd | nvidia | cpu (default: auto)
  --width PX          Output frame width (default: 640)
  --height PX         Output frame height (default: 480)
  --format FMT        Output format: jpeg | png (default: jpeg)
  --rtsp-transport    RTSP transport: tcp | udp | udp-mcast (default: tcp)
  --rtsp-timeout SECS RTSP timeout (default: 10)
  --help              Show this help

Examples:
  $(basename "$0") --source file --input video.mp4 --output ./frames --interval 2
  $(basename "$0") --source rtsp --input "rtsp://user:pass@192.168.1.100:554/stream1" --output ./frames
  $(basename "$0") --source camera --input /dev/video0 --output ./frames --width 1280 --height 720
  $(basename "$0") --source file --input video.mp4 --output ./frames --keyframes-only --backend amd
  $(basename "$0") --source file --input video.mp4 --output ./frames --scene-change
EOF
    exit 0
}

while [ $# -gt 0 ]; do
    case "$1" in
        --source)          SOURCE="$2";        shift 2 ;;
        --input)           INPUT="$2";          shift 2 ;;
        --output)          OUTPUT="$2";         shift 2 ;;
        --interval)        INTERVAL="$2";       shift 2 ;;
        --keyframes-only)  KEYFRAMES_ONLY=true;  shift ;;
        --scene-change)    SCENE_CHANGE=true;    shift ;;
        --backend)         BACKEND="$2";        shift 2 ;;
        --width)           WIDTH="$2";          shift 2 ;;
        --height)          HEIGHT="$2";         shift 2 ;;
        --format)          FORMAT="$2";         shift 2 ;;
        --rtsp-transport)  RTSP_TRANSPORT="$2"; shift 2 ;;
        --rtsp-timeout)    RTSP_TIMEOUT="$2";   shift 2 ;;
        --help)            SHOW_HELP=true;      shift ;;
        *) echo "❌ Unknown option: $1"; usage ;;
    esac
done

$SHOW_HELP && usage

# ── Validate Arguments ─────────────────────────────────────────────────────

if [ -z "$INPUT" ]; then
    echo "❌ --input is required"
    usage
fi

if [ -z "$OUTPUT" ]; then
    echo "❌ --output is required"
    usage
fi

# Validate source
case "$SOURCE" in
    file|rtsp|camera|auto) ;;
    *) echo "❌ Invalid source: $SOURCE (must be: file, rtsp, camera, auto)"; exit 1 ;;
esac

# Validate backend
case "$BACKEND" in
    auto|amd|nvidia|cpu) ;;
    *) echo "❌ Invalid backend: $BACKEND (must be: auto, amd, nvidia, cpu)"; exit 1 ;;
esac

# Validate format
case "$FORMAT" in
    jpeg|png) ;;
    *) echo "❌ Invalid format: $FORMAT (must be: jpeg, png)"; exit 1 ;;
esac

# Auto-detect source from input
if [ "$SOURCE" = "auto" ]; then
    if echo "$INPUT" | grep -qiE "^rtsp://|^rtsps://"; then
        SOURCE="rtsp"
    elif [ -f "$INPUT" ]; then
        SOURCE="file"
    elif [ -e "$INPUT" ] && [[ "$INPUT" =~ /dev/video ]]; then
        SOURCE="camera"
    else
        echo "❌ Cannot auto-detect source type. Use --source explicitly."
        exit 1
    fi
fi

# ── Detect Backend (if auto) ───────────────────────────────────────────────

detect_backend() {
    local detected="cpu"

    # Check AMD VAAPI
    if command -v gst-inspect-1.0 &>/dev/null; then
        if gst-inspect-1.0 vaapih264dec &>/dev/null 2>&1; then
            # Verify VAAPI driver is active
            if command -v vainfo &>/dev/null; then
                if vainfo &>/dev/null 2>&1; then
                    detected="amd"
                    echo "$detected"
                    return
                fi
            fi
        fi

        # Check NVIDIA NVDEC
        if gst-inspect-1.0 nvdec &>/dev/null 2>&1; then
            if command -v nvidia-smi &>/dev/null; then
                if nvidia-smi &>/dev/null 2>&1; then
                    detected="nvidia"
                    echo "$detected"
                    return
                fi
            fi
        fi
    fi

    echo "$detected"
}

if [ "$BACKEND" = "auto" ]; then
    BACKEND=$(detect_backend)
    echo "🔍 Auto-detected backend: ${BACKEND}"
fi

# ── Build Decode Pipeline ──────────────────────────────────────────────────

FRAME_FILTER="fpsinterval=${INTERVAL}"

if $KEYFRAMES_ONLY; then
    FRAME_FILTER="keyframe"
fi

if $SCENE_CHANGE; then
    FRAME_FILTER="scenechange"
fi

build_decode_pipeline() {
    local source_type="$1"
    local input_uri="$2"
    local backend="$3"
    local width="$4"
    local height="$5"
    local format="$6"
    local interval="$7"
    local keyframes="$8"
    local scene="$9"
    local transport="${10}"

    local src_pipeline=""
    local decode_pipeline=""
    local filter_pipeline=""
    local sink_pipeline=""

    # ── Source ──────────────────────────────────────────────────────────────
    case "$source_type" in
        file)
            src_pipeline="filesrc location=\"$(echo "$input_uri" | sed 's/"/\\"/g')\""
            # Add demuxer based on extension
            local ext
            ext=$(echo "$input_uri" | awk -F. '{print tolower($NF)}')
            case "$ext" in
                mp4|mov|m4v)   src_pipeline="$src_pipeline ! qtdemux" ;;
                avi)           src_pipeline="$src_pipeline ! avi" ;;
                mkv|webm)      src_pipeline="$src_pipeline ! matroskademux" ;;
                ts|m2ts)       src_pipeline="$src_pipeline ! tsdemux" ;;
                flv)           src_pipeline="$src_pipeline ! flvdemux" ;;
                *)             src_pipeline="$src_pipeline ! qtdemux" ;;  # best guess
            esac
            ;;

        rtsp)
            src_pipeline="rtspsrc location=\"$(echo "$input_uri" | sed 's/"/\\"/g')\" protocols=${transport} latency=2000 drop-on-latency=true timeout=0"
            ;;

        camera)
            src_pipeline="v4l2src device=${input_uri} io-mode=mmap"
            ;;
    esac

    # ── Decode ──────────────────────────────────────────────────────────────
    case "$backend" in
        amd)
            decode_pipeline="! h264parse ! vaapih264dec ! videoconvert ! videoscale ! video/x-raw,width=${width},height=${height} ! videoconvert"
            # Try H.265 if H.264 fails (pipeline handles via autoconversion)
            # For H.265 content, capsfilter will negotiate properly
            ;;

        nvidia)
            decode_pipeline="! h264parse ! nvdec ! videoconvert ! videoscale ! video/x-raw,width=${width},height=${height} ! videoconvert"
            ;;

        cpu)
            decode_pipeline="! h264parse ! avdec_h264 ! videoconvert ! videoscale ! video/x-raw,width=${width},height=${height} ! videoconvert"
            ;;
    esac

    # ── Filter (frame extraction strategy) ──────────────────────────────────
    if [ "$keyframes" = "true" ]; then
        filter_pipeline="! capsfilter caps=video/x-raw,framerate=0/1 !"
    elif [ "$scene" = "true" ]; then
        # GStreamer scenechange element (from gst-plugins-bad)
        filter_pipeline="! scenechange threshold=3000000 !"
    else
        # Interval-based: use videorate + capsfilter for interval
        local fps
        fps=$(echo "scale=6; 1 / $interval" | bc 2>/dev/null || echo "1.0")
        filter_pipeline="! videorate ! video/x-raw,framerate=${fps}/1 !"
    fi

    # ── Sink (save frames) ──────────────────────────────────────────────────
    local muxer=""
    local enc=""
    if [ "$format" = "jpeg" ]; then
        enc="jpegenc"
        muxer=""
    else
        enc="pngenc"
        muxer=""
    fi

    # Use multifilesink to save each frame to a numbered file
    sink_pipeline="! ${enc} ! multifilesink location=\"${OUTPUT}/frame_%05d.${format}\" index=1"

    # ── Full Pipeline ───────────────────────────────────────────────────────
    echo "${src_pipeline} ${decode_pipeline} ${filter_pipeline} ${sink_pipeline}"
}

build_hevc_decode_pipeline() {
    local source_type="$1"
    local input_uri="$2"
    local backend="$3"
    local width="$4"
    local height="$5"
    local format="$6"
    local interval="$7"
    local keyframes="$8"
    local scene="$9"
    local transport="${10}"

    local src_pipeline=""
    local decode_pipeline=""
    local filter_pipeline=""
    local sink_pipeline=""

    # Source (same as above but with correct demuxer)
    case "$source_type" in
        file)
            src_pipeline="filesrc location=\"$(echo "$input_uri" | sed 's/"/\\"/g')\" ! qtdemux"
            ;;
        rtsp)
            src_pipeline="rtspsrc location=\"$(echo "$input_uri" | sed 's/"/\\"/g')\" protocols=${transport} latency=2000 drop-on-latency=true timeout=0"
            ;;
        camera)
            src_pipeline="v4l2src device=${input_uri} io-mode=mmap"
            ;;
    esac

    # H.265 decode
    case "$backend" in
        amd)
            decode_pipeline="! h265parse ! vaapih265dec ! videoconvert ! videoscale ! video/x-raw,width=${width},height=${height} ! videoconvert"
            ;;
        nvidia)
            decode_pipeline="! h265parse ! nvdec ! videoconvert ! videoscale ! video/x-raw,width=${width},height=${height} ! videoconvert"
            ;;
        cpu)
            decode_pipeline="! h265parse ! avdec_h265 ! videoconvert ! videoscale ! video/x-raw,width=${width},height=${height} ! videoconvert"
            ;;
    esac

    # Filter
    if [ "$keyframes" = "true" ]; then
        filter_pipeline="! capsfilter caps=video/x-raw,framerate=0/1 !"
    elif [ "$scene" = "true" ]; then
        filter_pipeline="! scenechange threshold=3000000 !"
    else
        local fps
        fps=$(echo "scale=6; 1 / $interval" | bc 2>/dev/null || echo "1.0")
        filter_pipeline="! videorate ! video/x-raw,framerate=${fps}/1 !"
    fi

    # Sink
    local enc=""
    if [ "$format" = "jpeg" ]; then
        enc="jpegenc"
    else
        enc="pngenc"
    fi
    sink_pipeline="! ${enc} ! multifilesink location=\"${OUTPUT}/frame_%05d.${format}\" index=1"

    echo "${src_pipeline} ${decode_pipeline} ${filter_pipeline} ${sink_pipeline}"
}

# ── Create Output Directory ────────────────────────────────────────────────

mkdir -p "$OUTPUT"

# ── Run Pipeline ────────────────────────────────────────────────────────────

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Munin — GStreamer Video Pipeline                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Source:    ${SOURCE}"
echo "  Input:     ${INPUT}"
echo "  Output:    ${OUTPUT}"
echo "  Backend:   ${BACKEND}"
echo "  Size:      ${WIDTH}x${HEIGHT}"
echo "  Format:    ${FORMAT}"
echo "  Interval:  ${INTERVAL}s"
if $KEYFRAMES_ONLY; then echo "  Extract:   Keyframes only"; fi
if $SCENE_CHANGE; then echo "  Extract:   Scene change"; fi
echo ""

# Attempt H.264 pipeline first, then fallback to H.265
PIPELINE=$(build_decode_pipeline "$SOURCE" "$INPUT" "$BACKEND" "$WIDTH" "$HEIGHT" "$FORMAT" "$INTERVAL" "$KEYFRAMES_ONLY" "$SCENE_CHANGE" "$RTSP_TRANSPORT")

echo "🎬 Pipeline:"
echo "  gst-launch-1.0 ${PIPELINE}"
echo ""

# Run pipeline
echo "⏳ Processing (press Ctrl+C to stop)..."
if eval "gst-launch-1.0 ${PIPELINE} 2>&1"; then
    echo ""
    echo "✅ Pipeline completed successfully"
else
    local exit_code=$?
    echo ""
    echo "⚠️  H.264 pipeline failed (exit code: ${exit_code}) — trying H.265..."

    # Build and try H.265 pipeline
    PIPELINE_HEVC=$(build_hevc_decode_pipeline "$SOURCE" "$INPUT" "$BACKEND" "$WIDTH" "$HEIGHT" "$FORMAT" "$INTERVAL" "$KEYFRAMES_ONLY" "$SCENE_CHANGE" "$RTSP_TRANSPORT")

    echo "🎬 Fallback Pipeline (H.265):"
    echo "  gst-launch-1.0 ${PIPELINE_HEVC}"
    echo ""

    if eval "gst-launch-1.0 ${PIPELINE_HEVC} 2>&1"; then
        echo ""
        echo "✅ H.265 pipeline completed successfully"
    else
        echo ""
        echo "❌ Both H.264 and H.265 pipelines failed."
        echo ""
        echo "Troubleshooting tips:"
        echo "  1. Check if decoders are installed: gst-inspect-1.0 vaapih264dec"
        echo "  2. Try CPU backend: --backend cpu"
        echo "  3. Verify file exists and is not corrupted"
        echo "  4. Run detect-backend.sh to check acceleration: bash scripts/detect-backend.sh"
        exit 1
    fi
fi

# ── Generate Frame Index ──────────────────────────────────────────────────

echo ""
echo "📋 Generating frame index..."
FRAME_LIST="${OUTPUT}/frames.txt"
> "$FRAME_LIST"

# Sort frames numerically and write index
for f in $(ls "${OUTPUT}"/frame_*.${FORMAT} 2>/dev/null | sort); do
    frame_num=$(basename "$f" | sed 's/frame_0*//' | sed "s/\.${FORMAT}//")
    timestamp=$(echo "$frame_num * $INTERVAL" | bc 2>/dev/null || echo "0")
    echo "$(basename $f)  t=${timestamp}s" >> "$FRAME_LIST"
done

FRAME_COUNT=$(wc -l < "$FRAME_LIST" 2>/dev/null || echo 0)
echo "✅ Extracted ${FRAME_COUNT} frames to ${OUTPUT}/"
echo "   Frame index: ${FRAME_LIST}"

# ── Print Next Steps ──────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Next step: Run inference on extracted frames"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  python3 scripts/inference-pipeline.py \\"
echo "    --model yolov8x.pt \\"
echo "    --input-dir ${OUTPUT} \\"
echo "    --output results.json \\"
echo "    --batch-size 8"
echo ""
