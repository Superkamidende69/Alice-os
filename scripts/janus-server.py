"""Local, text-only OpenAI-compatible Janus service. No remote model code."""
import argparse
import base64
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--model-dir", required=True)
parser.add_argument("--port", type=int, default=8082)
args = parser.parse_args()
model_dir = Path(args.model_dir).resolve()
print("Initializing Janus", flush=True)
import torch
from transformers import JanusForConditionalGeneration, JanusProcessor

if not torch.cuda.is_available() or torch.cuda.mem_get_info()[0] < 5 * 1024**3:
    raise SystemExit("Janus needs CUDA and at least 5 GiB free GPU memory.")
processor = JanusProcessor.from_pretrained(model_dir, local_files_only=True)
model = JanusForConditionalGeneration.from_pretrained(
    model_dir, dtype=torch.bfloat16, device_map="cuda", local_files_only=True,
).eval()
gate = threading.Lock()
model_id = "Janus-Pro-1B"

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, value):
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/v1/models":
            self.reply(200, {"object": "list", "data": [{"id": model_id, "object": "model"}]})
        elif self.path == "/health":
            self.reply(200, {"service": "alice-janus", "model_dir": str(model_dir), "image_generation": True})
        else:
            self.reply(404, {"error": "Not found"})

    def do_POST(self):
        if self.headers.get("Origin"):
            self.reply(403, {"error": "Browser requests are not accepted by this local runtime"})
            return
        if self.path not in {"/v1/chat/completions", "/v1/images/generations"}:
            self.reply(404, {"error": "Not found"})
            return
        if not gate.acquire(blocking=False):
            self.reply(429, {"error": "Janus is busy; retry after the current reply"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024 * 1024:
                self.reply(413, {"error": "Request too large"})
                return
            body = json.loads(self.rfile.read(length))
            if self.path == "/v1/images/generations":
                prompt = body.get("prompt")
                if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 2000:
                    self.reply(400, {"error": "Enter an image description of 1–2000 characters"})
                    return
                messages = [{"role": "user", "content": [{"type": "text", "text": prompt.strip()}]}]
                formatted = processor.apply_chat_template(messages, add_generation_prompt=True)
                inputs = processor(text=formatted, generation_mode="image", return_tensors="pt").to(model.device)
                with torch.inference_mode():
                    tokens = model.generate(**inputs, generation_mode="image", do_sample=True,
                        num_return_sequences=1, use_cache=True)
                    pixels = model.decode_image_tokens(tokens)
                    pictures = processor.postprocess(list(pixels.float()), return_tensors="PIL.Image.Image")
                buffer = io.BytesIO()
                pictures["pixel_values"][0].save(buffer, format="PNG")
                self.reply(200, {"data": [{"b64_json": base64.b64encode(buffer.getvalue()).decode()}]})
                return
            if body.get("tools"):
                self.reply(400, {"error": "tools are not supported by Janus; use chat mode"})
                return
            if body.get("model") != model_id:
                self.reply(400, {"error": "Unknown model"})
                return
            messages = body.get("messages", [])
            if not messages or any(m.get("role") not in {"system", "user", "assistant"}
                                   or not isinstance(m.get("content"), str) for m in messages):
                self.reply(400, {"error": "This Janus endpoint supports text messages only"})
                return
            converted = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in messages]
            inputs = processor.apply_chat_template(converted, add_generation_prompt=True,
                generation_mode="text", tokenize=True, return_dict=True, return_tensors="pt").to(model.device)
            if inputs["input_ids"].shape[1] > 4096:
                self.reply(400, {"error": "Janus chat context exceeds 4096 tokens; start a new conversation"})
                return
            with torch.inference_mode():
                output = model.generate(**inputs, max_new_tokens=256, generation_mode="text", do_sample=False)
            text = processor.decode(output[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            if body.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                chunk = {"choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]}
                self.wfile.write(("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode())
            else:
                self.reply(200, {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            self.reply(500, {"error": str(error)})
        finally:
            gate.release()

server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
print("Janus ready on 127.0.0.1:" + str(args.port), flush=True)
server.serve_forever()
