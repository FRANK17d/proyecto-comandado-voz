@echo off
echo Creando ejecutable del Terminal comandado por voz...
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0"

REM Crear el ejecutable con PyInstaller
C:/Users/LENOVO/AppData/Local/Programs/Python/Python312/python.exe -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "Terminal_Comandado_Voz" ^
    --icon=icono.ico ^
    --add-data "README;." ^
    --hidden-import=pyttsx3.drivers ^
    --hidden-import=pyttsx3.drivers.sapi5 ^
    --hidden-import=speech_recognition ^
    --hidden-import=PyQt5 ^
    --hidden-import=PyQt5.QtCore ^
    --hidden-import=PyQt5.QtWidgets ^
    --hidden-import=PyQt5.QtGui ^
    --collect-all=pyttsx3 ^
    voz.py

echo.
echo ¡Ejecutable creado exitosamente!
echo El archivo se encuentra en la carpeta 'dist'
echo.
pause
