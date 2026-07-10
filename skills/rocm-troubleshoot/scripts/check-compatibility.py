#!/usr/bin/env python3
"""
check-compatibility.py — ROCm Component Compatibility Checker

Verifica la compatibilidad entre componentes del ecosistema ROCm:
  - ROCm version (drivers)
  - PyTorch version
  - vLLM version (si instalado)
  - Python version
  - GPU architecture
  - Docker (opcional)

Reporta qué componentes MATCH, qué NO match, y recomienda versiones correctas.

Usage:
    python3 check-compatibility.py          # Reporte legible
    python3 check-compatibility.py --json   # JSON output (for programmatic use)

Exit codes:
    0 — All components match / OK
    1 — Warnings (compatibilidad parcial)
    2 — Errors (componentes incompatibles)

Dependencies: Python 3.8+ stdlib; torch y vllm son opcionales.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

# ── Compatibility Tables ────────────────────────────────────────────────────

# ROCm major version → recommended PyTorch wheel
ROCM_TO_TORCH_WHEEL: Dict[str, str] = {
    "7": "rocm6.2",
    "6": "rocm6.2",
    "5": "rocm5.6",
}

# PyTorch wheel → recommended ROCm version (minimum)
TORCH_WHEEL_TO_ROCM: Dict[str, str] = {
    "rocm6.2": "6.2",
    "rocm6.1": "6.1",
    "rocm6.0": "6.0",
    "rocm5.6": "5.6",
    "rocm5.5": "5.5",
}

# Python version compatibility for vLLM ROCm
VLLM_ROCM_PYTHON = (3, 12)

# Recommended dtype by backend
DTYPE_RECOMMENDED: Dict[str, str] = {
    "rocm": "float16",
    "cuda": "bfloat16",
    "cpu": "float32",
}

# GPU architecture → friendly name
GFX_TO_NAME: Dict[str, str] = {
    "gfx900": "Vega 10 (MI25)",
    "gfx906": "Vega 20 (MI50/MI60)",
    "gfx908": "CDNA1 (MI100)",
    "gfx90a": "CDNA2 (MI250/MI250X)",
    "gfx940": "CDNA3 (MI300A)",
    "gfx941": "CDNA3 (MI300X early)",
    "gfx942": "CDNA3 (MI300X / MI325X)",
    "gfx950": "CDNA4 (MI350X)",
    "gfx1030": "RDNA2 (RX 6800/6900)",
    "gfx1100": "RDNA3 (RX 7900 XT/XTX)",
    "gfx1201": "RDNA4 (RX 9070 XT)",
}


def get_rocm_version() -> Tuple[Optional[str], Optional[str]]:
    """
    Detect installed ROCm version.

    Returns:
        (version_string, source) where source is "file", "dpkg", "rocminfo", or None.
    """
    # Method 1: version file
    version_file = "/opt/rocm/share/doc/rocm-version/version"
    if os.path.isfile(version_file):
        try:
            with open(version_file) as f:
                ver = f.read().strip()
            if ver:
                return ver, "file"
        except (IOError, OSError):
            pass

    # Method 2: dpkg
    try:
        result = subprocess.run(
            ["dpkg", "-l", "rocm-libs"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.split("\n"):
            if "rocm-libs" in line:
                parts = line.split()
                if len(parts) >= 3:
                    return parts[2], "dpkg"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Method 3: rocminfo
    try:
        result = subprocess.run(
            ["rocminfo"],
            capture_output=True, text=True, timeout=15,
        )
        for line in result.stdout.split("\n"):
            m = re.search(r'ROCk?\s+version:\s+([\d.]+)', line, re.IGNORECASE)
            if m:
                return m.group(1), "rocminfo"
            m = re.search(r'Driver\s+version:\s+([\d.]+)', line, re.IGNORECASE)
            if m:
                return m.group(1), "rocminfo"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None, None


def get_pytorch_info() -> Dict[str, Any]:
    """
    Detect PyTorch installation and ROCm/CUDA support.

    Returns:
        dict with keys: installed, version, hip, cuda, cuda_available, device_count, device_name
    """
    info: Dict[str, Any] = {
        "installed": False,
        "version": None,
        "hip": None,
        "cuda": None,
        "cuda_available": False,
        "device_count": 0,
        "device_name": None,
    }

    try:
        import torch  # type: ignore
        info["installed"] = True
        info["version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()

        hip_ver = getattr(torch.version, "hip", None)
        cuda_ver = getattr(torch.version, "cuda", None)
        info["hip"] = hip_ver
        info["cuda"] = cuda_ver

        if torch.cuda.is_available():
            info["device_count"] = torch.cuda.device_count()
            info["device_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    except Exception:
        pass

    return info


def get_vllm_info() -> Dict[str, Any]:
    """
    Detect vLLM installation.

    Returns:
        dict with keys: installed, version, is_rocm_wheel
    """
    info: Dict[str, Any] = {
        "installed": False,
        "version": None,
        "is_rocm_wheel": False,
        "is_cuda_wheel": False,
    }

    try:
        import vllm  # type: ignore
        info["installed"] = True
        info["version"] = getattr(vllm, "__version__", "unknown")
    except ImportError:
        # Check via pip
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=columns"],
                capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.split("\n"):
                if "vllm" in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        info["installed"] = True
                        info["version"] = parts[1]
                        # Detect if ROCm or CUDA wheel
                        wheel_info = subprocess.run(
                            [sys.executable, "-m", "pip", "show", "vllm"],
                            capture_output=True, text=True, timeout=10,
                        )
                        if "rocm" in wheel_info.stdout.lower():
                            info["is_rocm_wheel"] = True
                        if "cuda" in wheel_info.stdout.lower():
                            info["is_cuda_wheel"] = True
                    break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return info


def get_gpu_architecture() -> List[str]:
    """Detect GPU GFX architectures from rocminfo."""
    gfx_list: List[str] = []
    try:
        result = subprocess.run(
            ["rocminfo"],
            capture_output=True, text=True, timeout=15,
        )
        gfx_list = sorted(set(
            m.group(1)
            for line in result.stdout.split("\n")
            for m in [re.search(r'(gfx\d+)', line)]
            if m
        ))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return gfx_list


def get_python_version() -> Tuple[int, int, int]:
    """Get Python version as (major, minor, patch)."""
    return sys.version_info[:3]


def is_docker_available() -> bool:
    """Check if Docker is available."""
    return shutil.which("docker") is not None


def determine_backend(torch_info: Dict[str, Any], gfx_list: List[str]) -> str:
    """Determine the GPU backend."""
    if torch_info["installed"] and torch_info["hip"]:
        return "rocm"
    if torch_info["installed"] and torch_info["cuda"] and torch_info["cuda_available"]:
        return "cuda"
    if gfx_list:
        return "rocm"
    # Check nvidia-smi
    if shutil.which("nvidia-smi"):
        return "cuda"
    return "cpu"


def get_torch_wheel_from_version(version: Optional[str]) -> Optional[str]:
    """
    Extract the ROCm wheel name from PyTorch version string.
    Example: "2.4.0+rocm6.2" → "rocm6.2"
    """
    if not version:
        return None
    m = re.search(r'(rocm\d+\.\d+)', version)
    return m.group(1) if m else None


# ── Compatibility Checks ────────────────────────────────────────────────────

def check_rocm_torch_compatibility(
    rocm_ver: Optional[str],
    torch_info: Dict[str, Any],
) -> Tuple[str, str]:
    """
    Check compatibility between ROCm and PyTorch.

    Returns:
        (status, message): status = "ok" | "warning" | "error"
    """
    if not rocm_ver:
        return "warning", "ROCm version not detected — cannot verify compatibility"

    if not torch_info["installed"]:
        return "warning", "PyTorch not installed — cannot verify compatibility"

    # Get ROCm major version
    rocm_major = rocm_ver.split(".")[0] if "." in rocm_ver else rocm_ver

    # Get expected Torch wheel
    expected_wheel = None
    for key in sorted(ROCM_TO_TORCH_WHEEL.keys(), reverse=True):
        if rocm_major == key or rocm_ver.startswith(key):
            expected_wheel = ROCM_TO_TORCH_WHEEL[key]
            break

    # Get actual Torch wheel
    actual_wheel = get_torch_wheel_from_version(torch_info["version"])

    if not actual_wheel:
        # PyTorch is likely CUDA wheel or generic
        if torch_info["hip"]:
            return "warning", f"PyTorch has HIP ({torch_info['hip']}) but version {torch_info['version']} has no rocm tag"
        return "error", f"PyTorch {torch_info['version']} is NOT a ROCm wheel (CUDA: {torch_info['cuda']})"

    if expected_wheel:
        if actual_wheel == expected_wheel:
            return "ok", f"ROCm {rocm_ver} ↔ PyTorch {actual_wheel} — MATCH"
        else:
            return "warning", (
                f"ROCm {rocm_ver} → recommended wheel: {expected_wheel}, "
                f"but installed: {actual_wheel}"
            )

    return "ok", f"ROCm {rocm_ver} ↔ PyTorch {actual_wheel}"


def check_vllm_compatibility(
    vllm_info: Dict[str, Any],
    backend: str,
) -> Tuple[str, str]:
    """
    Check vLLM compatibility.

    Returns:
        (status, message)
    """
    if not vllm_info["installed"]:
        return "info", "vLLM not installed — skipping check"

    py_ver = get_python_version()

    if backend == "rocm":
        if py_ver[:2] != VLLM_ROCM_PYTHON:
            return "error", (
                f"vLLM ROCm requires Python {VLLM_ROCM_PYTHON[0]}.{VLLM_ROCM_PYTHON[1]}, "
                f"but running Python {py_ver[0]}.{py_ver[1]}.{py_ver[2]}"
            )
        if vllm_info["is_rocm_wheel"]:
            return "ok", f"vLLM {vllm_info['version']} ROCm wheel — OK"
        elif vllm_info["is_cuda_wheel"]:
            return "error", (
                f"vLLM {vllm_info['version']} is CUDA wheel — "
                f"ROCm requires: pip install vllm --extra-index-url https://wheels.vllm.ai/rocm/"
            )
        else:
            return "info", f"vLLM {vllm_info['version']} installed (wheel type unknown)"

    elif backend == "cuda":
        if vllm_info["is_cuda_wheel"]:
            return "ok", f"vLLM {vllm_info['version']} CUDA wheel — OK"
        else:
            return "info", f"vLLM {vllm_info['version']} installed"

    return "info", "vLLM installed (CPU mode)"


def check_python_version(backend: str) -> Tuple[str, str]:
    """Check Python version requirements."""
    py_ver = get_python_version()

    if backend == "rocm":
        # vLLM ROCm requires 3.12, but general ROCm works with 3.10+
        if py_ver[:2] == (3, 12):
            return "ok", f"Python {py_ver[0]}.{py_ver[1]}.{py_ver[2]} — OK (vLLM ROCm compatible)"
        elif py_ver[:2] >= (3, 10):
            return "warning", (
                f"Python {py_ver[0]}.{py_ver[1]}.{py_ver[2]} — "
                f"vLLM ROCm requires Python 3.12.x"
            )
        else:
            return "error", (
                f"Python {py_ver[0]}.{py_ver[1]}.{py_ver[2]} — "
                f"ROCm requires Python 3.10+"
            )

    return "ok", f"Python {py_ver[0]}.{py_ver[1]}.{py_ver[2]}"


def check_dtype_recommendation(backend: str) -> Tuple[str, str]:
    """Check dtype recommendation."""
    recommended = DTYPE_RECOMMENDED.get(backend, "float32")
    if backend == "rocm":
        return "info", (
            f"ROCm recommended dtype: {recommended} (NOT bfloat16 — "
            f"bfloat16 is not well supported on AMD)"
        )
    elif backend == "cuda":
        return "info", f"CUDA recommended dtype: {recommended}"
    return "info", f"CPU recommended dtype: {recommended}"


def build_report() -> Dict[str, Any]:
    """Build the full compatibility report."""
    report: Dict[str, Any] = {
        "status": "ok",
        "exit_code": 0,
        "backend": "cpu",
        "checks": [],
        "warnings": [],
        "errors": [],
        "components": {},
        "recommendations": [],
    }

    # ── Gather component info ────────────────────────────────────────
    rocm_ver, rocm_source = get_rocm_version()
    torch_info = get_pytorch_info()
    vllm_info = get_vllm_info()
    gfx_list = get_gpu_architecture()
    backend = determine_backend(torch_info, gfx_list)

    py_ver = get_python_version()
    docker_avail = is_docker_available()

    report["backend"] = backend
    report["components"] = {
        "rocm_version": rocm_ver,
        "rocm_source": rocm_source,
        "pytorch": torch_info,
        "vllm": vllm_info,
        "python": f"{py_ver[0]}.{py_ver[1]}.{py_ver[2]}",
        "gpu_architectures": gfx_list,
        "gpu_names": [GFX_TO_NAME.get(g, g) for g in gfx_list],
        "docker_available": docker_avail,
    }

    # ── 1. ROCm ↔ PyTorch ───────────────────────────────────────────
    status, msg = check_rocm_torch_compatibility(rocm_ver, torch_info)
    report["checks"].append({
        "check": "rocm_pytorch",
        "description": "ROCm ↔ PyTorch compatibility",
        "status": status,
        "message": msg,
    })
    if status == "error":
        report["errors"].append(f"rocm_pytorch: {msg}")
        report["status"] = "error"
        report["exit_code"] = 2
    elif status == "warning":
        report["warnings"].append(f"rocm_pytorch: {msg}")
        if report["status"] == "ok":
            report["status"] = "warning"
            report["exit_code"] = 1

    # ── 2. vLLM compatibility ────────────────────────────────────────
    status, msg = check_vllm_compatibility(vllm_info, backend)
    report["checks"].append({
        "check": "vllm",
        "description": "vLLM compatibility",
        "status": status,
        "message": msg,
    })
    if status == "error":
        report["errors"].append(f"vllm: {msg}")
        report["status"] = "error"
        report["exit_code"] = 2
    elif status == "warning":
        report["warnings"].append(f"vllm: {msg}")
        if report["status"] == "ok":
            report["status"] = "warning"
            report["exit_code"] = 1

    # ── 3. Python version ────────────────────────────────────────────
    status, msg = check_python_version(backend)
    report["checks"].append({
        "check": "python",
        "description": "Python version",
        "status": status,
        "message": msg,
    })
    if status == "error":
        report["errors"].append(f"python: {msg}")
        report["status"] = "error"
        report["exit_code"] = 2
    elif status == "warning":
        report["warnings"].append(f"python: {msg}")
        if report["status"] == "ok":
            report["status"] = "warning"
            report["exit_code"] = 1

    # ── 4. GPU architecture ──────────────────────────────────────────
    if gfx_list:
        gfx_names = [GFX_TO_NAME.get(g, g) for g in gfx_list]
        report["checks"].append({
            "check": "gpu_architecture",
            "description": "GPU architecture",
            "status": "ok",
            "message": f"GPU(s): {', '.join(f'{g} ({n})' for g, n in zip(gfx_list, gfx_names))}",
        })
    elif backend == "rocm":
        report["checks"].append({
            "check": "gpu_architecture",
            "description": "GPU architecture",
            "status": "warning",
            "message": "No GFX architecture detected via rocminfo",
        })
        report["warnings"].append("gpu_architecture: No GFX architecture detected")

    # ── 5. dtype recommendation ──────────────────────────────────────
    status, msg = check_dtype_recommendation(backend)
    report["checks"].append({
        "check": "dtype",
        "description": "Dtype recommendation",
        "status": status,
        "message": msg,
    })

    # ── 6. Docker ────────────────────────────────────────────────────
    report["checks"].append({
        "check": "docker",
        "description": "Docker availability",
        "status": "ok" if docker_avail else "info",
        "message": f"Docker {'available' if docker_avail else 'not available'}",
    })

    # ── Recommendations ──────────────────────────────────────────────
    recs: List[str] = []

    if backend == "rocm":
        recs.append(f"Use --dtype {DTYPE_RECOMMENDED['rocm']} for ML workloads")

    if torch_info["installed"] and not torch_info["hip"]:
        expected_wheel = None
        if rocm_ver:
            rocm_major = rocm_ver.split(".")[0]
            expected_wheel = ROCM_TO_TORCH_WHEEL.get(rocm_major)
        wheel_str = f"rocm{expected_wheel}" if expected_wheel else "rocm6.2"
        recs.append(
            f"Reinstall PyTorch ROCm: pip install torch --index-url "
            f"https://download.pytorch.org/whl/{wheel_str}"
        )

    if vllm_info["installed"] and backend == "rocm" and py_ver[:2] != (3, 12):
        recs.append(
            "Create Python 3.12 env for vLLM ROCm: uv venv --python 3.12"
        )

    if vllm_info["installed"] and backend == "rocm" and not vllm_info["is_rocm_wheel"]:
        recs.append(
            "Reinstall vLLM for ROCm: pip install vllm --extra-index-url "
            "https://wheels.vllm.ai/rocm/"
        )

    if gfx_list:
        first_gfx = gfx_list[0]
        if first_gfx == "gfx942":
            recs.append("MI300X detected — ensure ROCm 6.1+ is installed")
        elif first_gfx in ("gfx1100", "gfx1201"):
            recs.append(
                f"RDNA GPU detected — HSA_OVERRIDE_GFX_VERSION may be needed "
                f"for older ROCm versions"
            )

    report["recommendations"] = recs

    if not report["errors"] and not report["warnings"]:
        report["status"] = "ok"
        report["exit_code"] = 0

    return report


# ── Output Formatting ───────────────────────────────────────────────────────

def print_report(report: Dict[str, Any]) -> None:
    """Print human-readable compatibility report."""
    status_icon = {
        "ok": "✅",
        "warning": "⚠️",
        "error": "❌",
        "info": "ℹ️",
    }

    print("=" * 65)
    print("  AMD ROCm — Compatibility Check")
    print("=" * 65)

    backend = report["backend"].upper()
    print(f"  Backend detectado: {backend}")
    print()

    # Component versions
    comp = report["components"]
    print("─── Component Versions ───")
    print(f"  ROCm:  {comp['rocm_version'] or 'N/A'} ({comp['rocm_source'] or 'no detectado'})")
    if comp["pytorch"]["installed"]:
        pt = comp["pytorch"]
        print(f"  PyTorch: {pt['version']}")
        if pt["hip"]:
            print(f"  HIP:     {pt['hip']}")
        if pt["cuda"]:
            print(f"  CUDA:    {pt['cuda']}")
        print(f"  CUDA available: {pt['cuda_available']}")
        if pt["device_count"] > 0:
            print(f"  Device:  {pt['device_name']} ({pt['device_count']} GPU(s))")
    else:
        print(f"  PyTorch: no instalado")

    if comp["vllm"]["installed"]:
        vl = comp["vllm"]
        wheel_type = "ROCm" if vl["is_rocm_wheel"] else "CUDA" if vl["is_cuda_wheel"] else "generic"
        print(f"  vLLM:   {vl['version']} ({wheel_type} wheel)")
    else:
        print(f"  vLLM:   no instalado")

    print(f"  Python: {comp['python']}")
    if comp["gpu_architectures"]:
        for gfx, name in zip(comp["gpu_architectures"], comp["gpu_names"]):
            print(f"  GPU:    {gfx} ({name})")
    print(f"  Docker: {'✅' if comp['docker_available'] else '❌'}")

    print()

    # Checks
    print("─── Compatibility Checks ───")
    for check in report["checks"]:
        icon = status_icon.get(check["status"], "❓")
        print(f"  {icon} {check['check']}: {check['message']}")

    print()

    # Warnings
    if report["warnings"]:
        print("─── Warnings ───")
        for w in report["warnings"]:
            print(f"  ⚠️  {w}")
        print()

    # Errors
    if report["errors"]:
        print("─── Errors ───")
        for e in report["errors"]:
            print(f"  ❌ {e}")
        print()

    # Recommendations
    if report["recommendations"]:
        print("─── Recommendations ───")
        for r in report["recommendations"]:
            print(f"  💡 {r}")
        print()

    # Status
    status_map = {"ok": "✅ All components MATCH", "warning": "⚠️  Partial compatibility", "error": "❌ Incompatible components"}
    print("=" * 65)
    print(f"  {status_map.get(report['status'], 'Unknown')}")
    print("=" * 65)


# ── Entry Point ─────────────────────────────────────────────────────────────

def main() -> int:
    """Entry point. Returns exit code."""
    use_json = "--json" in sys.argv

    report = build_report()

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        print_report(report)

    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
