"""Spoken confirmation of a triage result. Secondary model, output only.

Model split -- state it plainly:
  gemini-3.5-flash     triage, extraction, every executor  (the critical path)
  gemini-2.5-flash-tts spoken confirmation ONLY            (this module)

The TTS model performs no reasoning. It is handed one finished English sentence
that this module built in Python from counts that were already computed, and it
voices it. It never sees the audio, the transcript, or the task text, and it is
never on the path that decides anything.

One-way only: one request, one utterance, no session, no websocket, no turn
taking. Every failure degrades to text -- the caller gets None and the UI keeps
its existing text summary.
"""

import io
import struct
import time

from google.genai import types

from src.domain.logger import log_event
from src.domain.vertex import vertex_client

MODEL = "gemini-2.5-flash-tts"
VOICE = "Kore"
TIMEOUT_MS = 20_000

# The model returns raw little-endian 16-bit PCM (audio/L16;codec=pcm;rate=24000),
# which no browser will play from an <audio> element. A 44-byte RIFF header makes
# it a .wav, which every browser plays natively -- cheaper and more reliable than
# decoding PCM in JavaScript.
PCM_RATE = 24_000
PCM_CHANNELS = 1
PCM_BITS = 16

_client = None


def _tts_client():
    global _client
    if _client is None:
        _client = vertex_client(timeout_ms=TIMEOUT_MS)
    return _client


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def build_summary(
    total: int, pending: int, watching: int, auto_classes: list = None
) -> str:
    """The sentence to speak, built here in Python.

    Deliberately not model-generated: this is a confirmation of numbers already
    decided, and letting a model restate them invites it to get them wrong.
    """
    if not total:
        return "I did not find any tasks in that note."

    parts = [f"I found {_plural(total, 'task')}."]
    clauses = []
    if pending:
        clauses.append(
            f"{_plural(pending, 'task')} need your approval"
            if pending != 1
            else "one needs your approval"
        )
    if watching:
        clauses.append(
            f"{watching} are being watched" if watching != 1 else "one is being watched"
        )
    for cls in auto_classes or []:
        clauses.append(f"{cls.replace('_', ' ')} auto-approved")

    if clauses:
        parts.append(
            (
                ", ".join(clauses[:-1]) + f", and {clauses[-1]}"
                if len(clauses) > 1
                else clauses[0]
            ).capitalize()
            + "."
        )
    return " ".join(parts)


def _wav(pcm: bytes, rate: int = PCM_RATE) -> bytes:
    """Wrap raw PCM in a minimal RIFF/WAVE header."""
    byte_rate = rate * PCM_CHANNELS * PCM_BITS // 8
    block_align = PCM_CHANNELS * PCM_BITS // 8
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(pcm)))
    buf.write(b"WAVEfmt ")
    buf.write(
        struct.pack(
            "<IHHIIHH", 16, 1, PCM_CHANNELS, rate, byte_rate, block_align, PCM_BITS
        )
    )
    buf.write(b"data")
    buf.write(struct.pack("<I", len(pcm)))
    buf.write(pcm)
    return buf.getvalue()


def speak(text: str, correlation_id: str = "speak") -> bytes | None:
    """Voice `text`. Returns WAV bytes, or None on any failure.

    None is not an error condition for the caller -- it means "no audio this
    time", and the UI carries on with its text summary.
    """
    t0 = time.perf_counter()
    try:
        resp = _tts_client().models.generate_content(
            model=MODEL,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=VOICE
                        )
                    )
                ),
            ),
        )
        blob = resp.candidates[0].content.parts[0].inline_data
        pcm = blob.data or b""
        if not pcm:
            raise ValueError("no audio returned")

        rate = PCM_RATE
        for token in (blob.mime_type or "").split(";"):
            if token.strip().startswith("rate="):
                rate = int(token.split("=", 1)[1])

        wav = _wav(pcm, rate)
        log_event(
            correlation_id,
            "spoken confirmation",
            model=MODEL,
            ok=True,
            elapsed_seconds=round(time.perf_counter() - t0, 2),
            pcm_bytes=len(pcm),
            source_mime=blob.mime_type,
        )
        return wav
    except Exception as e:
        # Never raises. The spoken layer is decoration; triage, execution and
        # the ladder must be untouched by anything that happens here.
        log_event(
            correlation_id,
            "spoken confirmation",
            model=MODEL,
            ok=False,
            elapsed_seconds=round(time.perf_counter() - t0, 2),
            error=f"{type(e).__name__}: {e}"[:200],
        )
        return None
