# -*- coding: utf-8 -*-
"""받아쓰기(faster-whisper) 공용 부품 — 단어 시각 포함. GPU 있으면 GPU.
(뤼미에르 에디트의 stages/asr.py 에서 옮김 — 2026-10-09 젠 분리 정리)"""
import os


def cuda_dlls():
    """pip 로 깐 nvidia-cublas-cu12 의 DLL 폴더를 검색 경로에 넣는다(ctranslate2 GPU 받아쓰기용)."""
    try:
        import nvidia.cublas
        for base in nvidia.cublas.__path__:
            b = os.path.join(base, "bin")
            if os.path.isdir(b) and b not in os.environ.get("PATH", ""):
                os.environ["PATH"] = b + os.pathsep + os.environ.get("PATH", "")
                if hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(b)
    except ImportError:
        pass


def load_model(cfg):
    cuda_dlls()
    from faster_whisper import WhisperModel
    dev = cfg.get("장치", "auto")
    if dev == "auto":
        try:
            import ctranslate2
            dev = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            dev = "cpu"
    try:
        return WhisperModel(cfg["모델"], device=dev, compute_type="float16" if dev == "cuda" else "int8"), dev
    except Exception:
        return WhisperModel(cfg["모델"], device="cpu", compute_type="int8"), "cpu"


def transcribe(model, wav, lang="ko", on_seg=None, prompt=None):
    segments, info = model.transcribe(wav, language=lang, word_timestamps=True, vad_filter=True,
                                      vad_parameters={"min_silence_duration_ms": 500}, condition_on_previous_text=False,
                                      initial_prompt=prompt)
    out = []
    for seg in segments:
        words = [{"s": round(w.start, 3), "e": round(w.end, 3), "w": w.word} for w in (seg.words or [])]
        out.append({"start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text, "words": words})
        if on_seg:
            on_seg(out[-1], info.duration)
    return out

