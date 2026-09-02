@echo off
setlocal

for %%I in ("%~dp0..") do set "ALICE_PROJECT=%%~fI"
set "LLAMA_BIN=%ALICE_PROJECT%\tools\llama.cpp\bin3"
set "MODEL=%ALICE_PROJECT%\.alice-data\models\huggingface\empero-ai--Qwen3.8-2B-Distill-GGUF\Qwen3.8-2B-Q4_K_M.gguf"

if not exist "%LLAMA_BIN%\llama-server.exe" (
  echo llama.cpp is not installed at "%LLAMA_BIN%".
  exit /b 1
)

if not exist "%MODEL%" (
  echo The Q4 GGUF model was not found at "%MODEL%".
  exit /b 1
)

echo Starting llama.cpp in Alice balanced mode at http://127.0.0.1:8080
echo One active chat slot, 3K context, GPU flash attention, and 5-minute idle sleep.
"%LLAMA_BIN%\llama-server.exe" -m "%MODEL%" -ngl 99 -c 3072 -np 1 -t 6 -tb 8 -fa on -ctk q8_0 -ctv q8_0 --sleep-idle-seconds 300 --host 127.0.0.1 --port 8080
