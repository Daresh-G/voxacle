"""Audio decoding via FFmpeg (spec §7: FFMPEG).

INPUT:   arbitrary uploaded audio bytes (WAV/MP3/M4A/FLAC/OGG/WEBM...)
TRANSFORM: ffmpeg decode -> 16 kHz mono s16le raw PCM
MATH:    none (format conversion only)
OUTPUT:  float32 numpy waveform at 16 kHz mono + original bytes preserved
ERRORS:  UnsupportedFormatError / AudioDecodeError -> truthful failure states

The ORIGINAL file bytes are never modified; decoding produces an ANALYSIS COPY
(spec §21-§22). Original bytes are stored separately according to policy.
"""
from __future__ import annotations

import io
import subprocess

import numpy as np
import soundfile as sf

from backend import config

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".mp4", ".aif", ".aiff", ".amr", ".3gp"}


def ffmpeg_available() -> bool:
    """Truthful component check for /api/health (spec §51)."""
    try:
        p = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
        return p.returncode == 0
    except Exception:  # noqa: BLE001
        # ffmpeg missing is fine for WAV/FLAC/OGG via soundfile; degraded, not fatal
        try:
            import soundfile as sf_  # noqa: N813
            return sf_.__version__ is not None
        except Exception:  # noqa: BLE001
            return False


class AudioDecodeError(Exception):
    code = "AUDIO_DECODE_ERROR"


class UnsupportedFormatError(Exception):
    code = "UNSUPPORTED_FORMAT"


def decode_to_16k_mono(data: bytes, original_name: str | None = None) -> dict:
    """Decode arbitrary audio bytes into the internal standard representation.

    Returns dict with waveform (float32 [-1,1]), sample_rate=16000, source info.
    Raises UnsupportedFormatError / AudioDecodeError on failure (never fakes).
    """
    if not data or len(data) < 64:
        raise AudioDecodeError("File is empty or too small to be valid audio.")

    ext = ("." + (original_name or "").rsplit(".", 1)[-1].lower()) if (original_name and "." in original_name) else ""
    if ext and ext not in SUPPORTED_EXTENSIONS:
        # Still allow decode attempt for extensionless uploads, but reject known-bad
        raise UnsupportedFormatError(f"File extension '{ext}' is not a supported audio type.")

    # Fast path: try soundfile for WAV/FLAC/OGG (lossless, no subprocess)
    try:
        wf, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
        mono = wf.mean(axis=1).astype(np.float32)
        if sr <= 0 or mono.size == 0:
            raise AudioDecodeError("Decoded audio is empty.")
        from backend.audio.standardizer import standardize
        std = standardize(mono, sr)
        std["source_sample_rate"] = sr
        std["source_channels"] = wf.shape[1]
        return std
    except (AudioDecodeError, UnsupportedFormatError):
        raise
    except Exception:  # noqa: BLE001 — fall through to ffmpeg for compressed formats
        pass

    # FFmpeg path: decode to 16 kHz mono f32 raw
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", "pipe:0",
        "-ac", str(config.TARGET_CHANNELS),
        "-ar", str(config.TARGET_SAMPLE_RATE),
        "-f", "f32le", "-acodec", "pcm_f32le",
        "pipe:1",
    ]
    try:
        proc = subprocess.run(cmd, input=data, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired as e:
        raise AudioDecodeError("Audio decoding timed out.") from e
    if proc.returncode != 0 or len(proc.stdout) < 64:
        msg = proc.stderr.decode(errors="replace").strip()[-300:]
        raise AudioDecodeError(f"FFmpeg could not decode this audio. {msg}")

    mono = np.frombuffer(proc.stdout, dtype=np.float32).copy()
    if mono.size == 0:
        raise AudioDecodeError("Decoded audio contains no samples.")
    return {
        "waveform": mono,
        "sample_rate": config.TARGET_SAMPLE_RATE,
        "channels": 1,
        "source_sample_rate": None,
        "source_channels": None,
        "decoded_by": "ffmpeg",
    }
