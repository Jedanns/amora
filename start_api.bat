@echo off
echo ============================================
echo    Mon RPG IA - Demarrage du serveur
echo ============================================
echo.
echo LLM: KoboldCPP sur http://localhost:5001
echo.
echo ** Ouvrez votre navigateur a cette adresse: **
echo.
echo    http://localhost:8000
echo.
echo ============================================
echo.
venv\Scripts\python.exe -m src.api.main
pause