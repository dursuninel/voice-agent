import os
import tempfile
import threading
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from dotenv import load_dotenv
from groq import Groq
from typing import Callable

load_dotenv()

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.005  # 0.008'den düşürdük
SILENCE_SECONDS = 1.8
CHUNK_SECONDS = 0.3
MAX_LISTEN_SECONDS = 30  # maksimum bekleme süresi


class VoiceListener:
    def __init__(self, on_text: Callable[[str], None]):
        self.on_text = on_text
        self._stop = False
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY bulunamadi.")
        self.client = Groq(api_key=api_key)
        print("Groq Whisper Large v3 hazir.")

    def stop(self):
        self._stop = True

    def listen_once(self):
        self._stop = False
        chunk_size = int(SAMPLE_RATE * CHUNK_SECONDS)
        silence_chunks_needed = int(SILENCE_SECONDS / CHUNK_SECONDS)
        max_chunks = int(MAX_LISTEN_SECONDS / CHUNK_SECONDS)

        frames = []
        silence_count = 0
        started_speaking = False
        total_chunks = 0

        print("Dinleniyor... (konusmaya baslayin)")

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
            while not self._stop:
                chunk, _ = stream.read(chunk_size)
                chunk_np = np.squeeze(chunk)
                rms = float(np.sqrt(np.mean(chunk_np ** 2)))
                total_chunks += 1

                if rms > SILENCE_THRESHOLD:
                    started_speaking = True
                    silence_count = 0
                    frames.append(chunk_np)
                elif started_speaking:
                    frames.append(chunk_np)
                    silence_count += 1
                    if silence_count >= silence_chunks_needed:
                        break
                
                if total_chunks >= max_chunks:
                    break

        if self._stop or not frames:
            return

        audio_np = np.concatenate(frames)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            wav.write(tmp_path, SAMPLE_RATE, (audio_np * 32767).astype(np.int16))

        try:
            with open(tmp_path, "rb") as f:
                transcription = self.client.audio.transcriptions.create(
                    file=("audio.wav", f.read()),
                    model="whisper-large-v3",
                    language="tr",
                    temperature=0.0,
                    response_format="text"
                )
            text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
            print(f"Algilanan: {text}")
            if text:
                self.on_text(text)
        except Exception as e:
            print(f"Transkripsiyon hatasi: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass