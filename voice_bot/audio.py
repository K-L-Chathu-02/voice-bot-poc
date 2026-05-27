import pyaudio

INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK_SAMPLES = 320  # 20 ms at 16 kHz


class AudioIO:
    def __init__(self) -> None:
        self._pa = pyaudio.PyAudio()
        self.mic = self._pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SAMPLES,
        )
        self.speaker = self._pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
        )

    def read_chunk(self) -> bytes:
        return self.mic.read(CHUNK_SAMPLES, exception_on_overflow=False)

    def write(self, data: bytes) -> None:
        self.speaker.write(data)

    def close(self) -> None:
        try:
            self.mic.stop_stream()
            self.mic.close()
        except Exception:
            pass
        try:
            self.speaker.stop_stream()
            self.speaker.close()
        except Exception:
            pass
        self._pa.terminate()
