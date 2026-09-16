"""Offline Janus text-generation check using the dedicated .venv-janus."""
from pathlib import Path
import time

print("Initializing PyTorch and Transformers…", flush=True)
import torch
from transformers import JanusForConditionalGeneration, JanusProcessor

model_dir = Path(__file__).resolve().parents[1] / ".alice-data/models/huggingface/deepseek-community--Janus-Pro-1B"
if not torch.cuda.is_available():
    raise SystemExit("CUDA unavailable; no automatic CPU fallback for this test.")
free, total = torch.cuda.mem_get_info()
if free < 5 * 1024**3:
    raise SystemExit("Less than 5 GiB GPU memory free. Close a GPU workload and retry; no processes were stopped.")
print(f"GPU: {torch.cuda.get_device_name(0)}; free {free / 1024**3:.2f} GiB", flush=True)
started = time.monotonic()
processor = JanusProcessor.from_pretrained(model_dir, local_files_only=True)
model = JanusForConditionalGeneration.from_pretrained(
    model_dir, dtype=torch.bfloat16, device_map="cuda", local_files_only=True,
).eval()
messages = [{"role": "user", "content": [{"type": "text", "text": "Say hello in one short sentence."}]}]
inputs = processor.apply_chat_template(
    messages, add_generation_prompt=True, generation_mode="text", tokenize=True,
    return_dict=True, return_tensors="pt",
).to(model.device)
with torch.inference_mode():
    output = model.generate(**inputs, max_new_tokens=32, generation_mode="text", do_sample=False)
print(processor.decode(output[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True), flush=True)
print(f"Peak GPU allocation: {torch.cuda.max_memory_allocated() / 1024**3:.2f} GiB", flush=True)
print(f"Load + response: {time.monotonic() - started:.1f}s", flush=True)
