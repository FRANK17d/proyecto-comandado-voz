#!/usr/bin/env python3
"""
Script para crear ejecutable del Terminal Comandado por Voz
"""

import os
import sys
import subprocess

def crear_ejecutable():
    """Crea el ejecutable usando PyInstaller"""
    
    # Comando de PyInstaller
    comando = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed", 
        "--name", "Terminal_Comandado_Voz",
        "--distpath", "./dist",
        "--workpath", "./build",
        "--specpath", ".",
        "--noconfirm",
        "voz.py"
    ]
    
    print("Creando ejecutable...")
    print("Comando:", " ".join(comando))
    print()
    
    try:
        # Ejecutar PyInstaller
        resultado = subprocess.run(comando, capture_output=True, text=True)
        
        print("STDOUT:")
        print(resultado.stdout)
        print("\nSTDERR:")
        print(resultado.stderr)
        print(f"\nCódigo de retorno: {resultado.returncode}")
        
        if resultado.returncode == 0:
            print("\n¡Ejecutable creado exitosamente!")
            print("Ubicación: ./dist/Terminal_Comandado_Voz.exe")
        else:
            print("\nError al crear el ejecutable")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print(f"Directorio de trabajo: {os.getcwd()}")
    print(f"Python ejecutable: {sys.executable}")
    print()
    
    crear_ejecutable()
