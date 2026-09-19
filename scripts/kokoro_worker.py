"""Private stdin/stdout worker: model stays resident; no listening network port."""
import contextlib
import json
import os
import sys
from pathlib import Path

from voice_speech import text_for_speech


def main():
    root = Path(sys.argv[1])
    protocol = sys.stdout
    with contextlib.redirect_stdout(sys.stderr):
        import numpy as np
        import onnxruntime as ort
        import soundfile as sf
        from kokoro_onnx import Kokoro

        options = ort.SessionOptions()
        options.intra_op_num_threads = max(1, min(4, (os.cpu_count() or 2) // 2))
        session = ort.InferenceSession(str(root / "kokoro-v1.0.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
        model = Kokoro.from_session(session, str(root / "voices-v1.0.bin"))
    for line in sys.stdin:
        try:
            payload = json.loads(line)
            with contextlib.redirect_stdout(sys.stderr):
                text = text_for_speech(payload["text"])
                if not text:
                    raise ValueError("No speakable text")
                samples, rate = model.create(text, voice=payload["voice"], speed=payload["speed"], lang="en-us")
                # Leave a small quiet tail for a clean streamed-clip transition.
                samples = np.concatenate([samples, np.zeros(int(rate * .08), dtype=np.float32)])
                sf.write(payload["output"], samples, rate, subtype="PCM_16")
            result = {"ok": True}
        except Exception as error:
            result = {"ok": False, "error": str(error)}
        protocol.write(json.dumps(result) + "\n")
        protocol.flush()


if __name__ == "__main__":
    main()
