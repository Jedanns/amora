@echo off
echo ============================================
echo  Installation de AMORA
echo ============================================
echo.

set INSTALL_DIR=%LOCALAPPDATA%\AMORA
set PROJECT_DIR=%~dp0

echo Installation dans: %INSTALL_DIR%
echo.

:: Lancer l'installateur NSIS si pas deja installe
if not exist "%INSTALL_DIR%\AMORA.exe" (
    echo Lancement de l'installateur...
    start /wait "" "%PROJECT_DIR%frontend\src-tauri\target\release\bundle\nsis\AMORA_0.1.0_x64-setup.exe"
)

echo.
echo Copie de KoboldCPP...

:: Copier koboldcpp
if exist "%PROJECT_DIR%koboldcpp.exe" (
    copy /Y "%PROJECT_DIR%koboldcpp.exe" "%INSTALL_DIR%\" >nul
    echo   koboldcpp.exe OK
) else (
    echo   ERREUR: koboldcpp.exe non trouve dans le dossier du projet
)

:: Copier le dossier models
if exist "%PROJECT_DIR%models" (
    xcopy /E /I /Y "%PROJECT_DIR%models" "%INSTALL_DIR%\models" >nul
    echo   models/ OK
) else (
    echo   ERREUR: dossier models non trouve
)

echo.
echo Creation du raccourci bureau...

:: Creer raccourci via PowerShell
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\AMORA.lnk'); $s.TargetPath = '%INSTALL_DIR%\AMORA.exe'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'AMORA - AI RPG'; $s.Save()" 2>nul

if exist "%USERPROFILE%\Desktop\AMORA.lnk" (
    echo   Raccourci bureau cree
) else (
    echo   Impossible de creer le raccourci bureau
)

echo.
echo ============================================
echo  Installation terminee !
echo ============================================
echo.
echo Lance AMORA depuis le raccourci bureau
echo ou depuis: %INSTALL_DIR%\AMORA.exe
echo.
pause
