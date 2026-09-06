@echo off
setlocal

for %%I in ("%~dp0..") do set "ALICE_PROJECT=%%~fI"
set "LLAMA_BIN=%ALICE_PROJECT%\tools\llama.cpp\bin3"
set "MODEL="
for /f "delims=" %%F in ('dir /b /s /a:-d /o:-d "%ALICE_PROJECT%\.alice-data\models\localai\*.gguf" 2^>nul') do if not defined MODEL set "MODEL=%%F"
if not defined MODEL set "MODEL=%ALICE_PROJECT%\.alice-data\models\huggingface\empero-ai--Qwen3.8-2B-Distill-GGUF\Qwen3.8-2B-Q4_K_M.gguf"

if not exist "%LLAMA_BIN%\llama-server.exe" (
  echo llama.cpp is not installed at "%LLAMA_BIN%".
  exit /b 1
)

if not exist "%MODEL%" (
  echo No Alice-managed GGUF model was found at "%MODEL%".
  exit /b 1
)

echo Starting llama.cpp with "%MODEL%" at http://127.0.0.1:8081
echo One active chat slot, 3K context, GPU flash attention, and 5-minute idle sleep.
"%LLAMA_BIN%\llama-server.exe" -m "%MODEL%" -ngl 99 -c 3072 -np 1 -t 6 -tb 8 -fa on -ctk q8_0 -ctv q8_0 --sleep-idle-seconds 300 --host 127.0.0.1 --port 8081
