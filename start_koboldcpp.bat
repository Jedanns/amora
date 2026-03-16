@echo off
echo Demarrage de KoboldCPP avec Qwen 3 8B...
echo.
echo Model: models/Qwen_Qwen3-8B-Q4_K_M.gguf
echo Port: 5001
echo Contexte: 4096 tokens
echo GPU Layers: 99 (tout le modele en VRAM)
echo Threads: 8
echo.
koboldcpp.exe --model models\Qwen_Qwen3-8B-Q4_K_M.gguf --contextsize 4096 --port 5001 --gpulayers 99 --flashattention --threads 8
pause
