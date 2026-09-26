# LocalAlice deployment

This Compose deployment runs LocalAI and the optional FreeToken runtime on one
NVIDIA CUDA 13 host. It keeps model files, configurations, chats and generated
images outside the repository under `H:/LocalAI`.

Before starting it, copy `external_backends.json` and
`freetoken-model-template.yaml` into `H:/LocalAI/configuration/`, then run:

```powershell
docker compose up -d
```

FreeToken serves models selected through a LocalAI YAML configuration whose
backend is `freetoken`. The model must be a LocalAI-downloaded Hugging Face
safetensors directory or FreeToken FTW checkpoint; GGUF files continue to use
llama.cpp.
