"""
Safe GPU / CPU accelerator resolution with user consent.

GPU is used only when hardware is available AND user consented (once / always).
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import asdict, dataclass
from functools import lru_cache

from utils.gpu_consent import get_request_consent, resolve_consent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AcceleratorProfile:
    mode_requested: str
    vendor: str
    gpu_name: str | None
    whisper_device: str
    whisper_compute: str
    whisper_backend: str
    embedding_device: str
    cuda_available: bool
    directml_available: bool
    cuda_device_name: str | None
    gpu_available: bool
    gpu_consent: str
    gpu_allowed: bool
    using_gpu: bool


def cuda_available_ctranslate2() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def cuda_available_torch() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


def directml_available() -> bool:
    try:
        import onnxruntime as ort

        if "DmlExecutionProvider" in ort.get_available_providers():
            return True
    except Exception:
        pass
    try:
        import torch_directml

        torch_directml.device()
        return True
    except Exception:
        return False


def detect_amd_gpu() -> tuple[bool, str | None]:
    override = os.getenv("AMD_GPU_NAME", "").strip()
    if override:
        return True, override

    force = os.getenv("AMD_GPU", "").lower() in ("1", "true", "yes")
    if force:
        return True, override or "AMD GPU (AMD_GPU=1)"

    if os.name == "nt":
        try:
            out = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                text=True,
                errors="ignore",
                timeout=8,
            )
            for line in out.splitlines():
                name = line.strip()
                if not name or name.upper() == "NAME":
                    continue
                upper = name.upper()
                if "AMD" in upper or "RADEON" in upper or "RX " in upper:
                    return True, name
        except Exception:
            pass

    return False, None


def resolve_cuda_device_name() -> str | None:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
    except Exception:
        pass
    if cuda_available_ctranslate2():
        return "NVIDIA CUDA (ctranslate2)"
    return None


def _normalize_mode(raw: str) -> str:
    value = (raw or "auto").strip().lower()
    if value in ("gpu", "cuda"):
        return "gpu"
    if value == "cpu":
        return "cpu"
    return "auto"


def _normalize_vendor(raw: str) -> str:
    value = (raw or "auto").strip().lower()
    if value in ("nvidia", "cuda"):
        return "nvidia"
    if value in ("amd", "rocm", "directml", "rx"):
        return "amd"
    if value == "cpu":
        return "cpu"
    return "auto"


def _hardware_gpu_available(
    vendor: str, cuda_whisper: bool, cuda_torch: bool, dml: bool, amd_detected: bool
) -> bool:
    if vendor == "amd":
        return amd_detected and dml
    if vendor == "nvidia":
        return cuda_whisper or cuda_torch
    return False


def _force_cpu_profile(
    profile: AcceleratorProfile, consent: str, allowed: bool
) -> AcceleratorProfile:
    return AcceleratorProfile(
        mode_requested=profile.mode_requested,
        vendor=profile.vendor if profile.gpu_available else "cpu",
        gpu_name=profile.gpu_name,
        whisper_device="cpu",
        whisper_compute="int8",
        whisper_backend="faster_whisper",
        embedding_device="cpu",
        cuda_available=profile.cuda_available,
        directml_available=profile.directml_available,
        cuda_device_name=profile.cuda_device_name,
        gpu_available=profile.gpu_available,
        gpu_consent=consent,
        gpu_allowed=allowed,
        using_gpu=False,
    )


@lru_cache
def _build_hardware_profile() -> AcceleratorProfile:
    mode = _normalize_mode(os.getenv("ACCELERATOR_MODE", "auto"))
    vendor_env = _normalize_vendor(
        os.getenv("GPU_VENDOR", os.getenv("ACCELERATOR_VENDOR", "auto"))
    )

    cuda_whisper = cuda_available_ctranslate2()
    cuda_torch = cuda_available_torch()
    dml = directml_available()
    amd_detected, amd_name = detect_amd_gpu()

    if vendor_env == "cpu":
        vendor = "cpu"
    elif vendor_env == "nvidia":
        vendor = "nvidia"
    elif vendor_env == "amd":
        vendor = "amd"
    elif cuda_whisper or cuda_torch:
        vendor = "nvidia"
    elif amd_detected:
        vendor = "amd"
    else:
        vendor = "cpu"

    whisper_device_env = os.getenv("WHISPER_DEVICE", "auto").strip().lower()
    embedding_env = os.getenv("EMBEDDING_DEVICE", "auto").strip().lower()
    whisper_backend_env = os.getenv("WHISPER_BACKEND", "auto").strip().lower()
    gpu_name = amd_name if vendor == "amd" else resolve_cuda_device_name()

    if vendor == "amd":
        use_dml = whisper_backend_env in ("auto", "onnx_directml", "directml") and dml
        whisper_backend = "onnx_directml" if use_dml else "faster_whisper"
        whisper_device = "directml" if use_dml else "cpu"
        whisper_compute = "float16" if use_dml else "int8"
        if embedding_env == "cpu":
            embedding_device = "cpu"
        elif mode == "cpu":
            embedding_device = "cpu"
        else:
            embedding_device = "directml" if dml else "cpu"
        using_gpu = dml and (
            whisper_backend == "onnx_directml" or embedding_device == "directml"
        )
        gpu_avail = _hardware_gpu_available(vendor, cuda_whisper, cuda_torch, dml, amd_detected)

        return AcceleratorProfile(
            mode_requested=mode,
            vendor="amd",
            gpu_name=gpu_name,
            whisper_device=whisper_device,
            whisper_compute=whisper_compute,
            whisper_backend=whisper_backend,
            embedding_device=embedding_device,
            cuda_available=False,
            directml_available=dml,
            cuda_device_name=None,
            gpu_available=gpu_avail,
            gpu_consent="unset",
            gpu_allowed=False,
            using_gpu=using_gpu,
        )

    if whisper_device_env == "cpu":
        whisper_device = "cpu"
    elif whisper_device_env in ("cuda", "gpu"):
        whisper_device = "cuda" if cuda_whisper else "cpu"
    elif mode == "cpu":
        whisper_device = "cpu"
    elif mode == "gpu":
        whisper_device = "cuda" if cuda_whisper else "cpu"
    else:
        whisper_device = "cuda" if cuda_whisper else "cpu"

    compute_env = os.getenv("WHISPER_COMPUTE", "auto").strip().lower()
    whisper_compute = (
        ("float16" if whisper_device == "cuda" else "int8")
        if compute_env in ("auto", "")
        else compute_env
    )
    if whisper_device == "cpu" and whisper_compute == "float16":
        whisper_compute = "int8"

    if embedding_env == "cpu" or mode == "cpu":
        embedding_device = "cpu"
    elif embedding_env in ("cuda", "gpu") or mode == "gpu":
        embedding_device = "cuda" if cuda_torch else "cpu"
    else:
        embedding_device = "cuda" if cuda_torch else "cpu"

    using_gpu = whisper_device == "cuda" or embedding_device == "cuda"
    gpu_avail = _hardware_gpu_available(vendor, cuda_whisper, cuda_torch, dml, amd_detected)

    return AcceleratorProfile(
        mode_requested=mode,
        vendor="nvidia" if (cuda_whisper or cuda_torch) else "cpu",
        gpu_name=gpu_name,
        whisper_device=whisper_device,
        whisper_compute=whisper_compute,
        whisper_backend="faster_whisper",
        embedding_device=embedding_device,
        cuda_available=cuda_whisper or cuda_torch,
        directml_available=False,
        cuda_device_name=resolve_cuda_device_name(),
        gpu_available=gpu_avail,
        gpu_consent="unset",
        gpu_allowed=False,
        using_gpu=using_gpu,
    )


def get_accelerator_profile() -> AcceleratorProfile:
    hw = _build_hardware_profile()
    consent = resolve_consent(get_request_consent())
    allowed = consent in ("once", "always")

    if not hw.gpu_available:
        return AcceleratorProfile(
            **{
                **asdict(hw),
                "gpu_consent": consent,
                "gpu_allowed": False,
                "using_gpu": False,
                "whisper_device": "cpu",
                "whisper_compute": "int8",
                "whisper_backend": "faster_whisper",
                "embedding_device": "cpu",
            }
        )

    if not allowed:
        return _force_cpu_profile(hw, consent, False)

    return AcceleratorProfile(
        **{
            **asdict(hw),
            "gpu_consent": consent,
            "gpu_allowed": True,
        }
    )


def get_embedding_model_kwargs() -> dict:
    profile = get_accelerator_profile()
    if profile.embedding_device == "directml":
        try:
            import torch_directml

            return {"model_kwargs": {"device": torch_directml.device()}}
        except Exception:
            return {"model_kwargs": {"device": "cpu"}}
    return {"model_kwargs": {"device": profile.embedding_device}}


def accelerator_status_dict() -> dict:
    return asdict(get_accelerator_profile())


def hardware_status_dict() -> dict:
    hw = _build_hardware_profile()
    cs = resolve_consent()
    return {
        "gpu_available": hw.gpu_available,
        "gpu_name": hw.gpu_name,
        "vendor": hw.vendor,
        "directml_available": hw.directml_available,
        "cuda_available": hw.cuda_available,
        "stored_consent": load_stored_consent_safe(),
        "resolved_consent": cs,
        "requires_prompt": hw.gpu_available and cs == "unset",
    }


def load_stored_consent_safe() -> str | None:
    from utils.gpu_consent import load_stored_consent

    return load_stored_consent()


def log_accelerator_profile() -> None:
    p = get_accelerator_profile()
    if not p.gpu_allowed and p.gpu_available:
        logger.info(
            "Accelerator: GPU available (%s) but consent=%s — using CPU until user allows",
            p.gpu_name or p.vendor,
            p.gpu_consent,
        )
    elif p.vendor == "amd" and p.using_gpu:
        logger.info(
            "Accelerator: AMD DirectML — %s, whisper=%s, embeddings=%s",
            p.gpu_name,
            p.whisper_backend,
            p.embedding_device,
        )
    elif p.using_gpu:
        logger.info(
            "Accelerator: NVIDIA GPU — whisper=%s (%s), embeddings=%s",
            p.whisper_device,
            p.whisper_compute,
            p.embedding_device,
        )
    else:
        logger.info(
            "Accelerator: CPU — whisper=%s (%s), embeddings=%s",
            p.whisper_device,
            p.whisper_compute,
            p.embedding_device,
        )
