# Terminal Comandado por Voz - Crear Ejecutable

## Métodos para crear el ejecutable:

### Método 1: Usando el archivo .bat (Más fácil)
1. Ejecuta `crear_ejecutable.bat` haciendo doble clic
2. Espera a que termine el proceso
3. El ejecutable estará en la carpeta `dist/`

### Método 2: Usando comandos manuales

#### Opción A - Ejecutable simple:
```bash
C:/Users/LENOVO/AppData/Local/Programs/Python/Python312/python.exe -m PyInstaller --onefile --windowed voz.py
```

#### Opción B - Ejecutable con configuraciones avanzadas:
```bash
C:/Users/LENOVO/AppData/Local/Programs/Python/Python312/python.exe -m PyInstaller Terminal_Comandado_Voz.spec
```

#### Opción C - Comando completo con todas las opciones:
```bash
C:/Users/LENOVO/AppData/Local/Programs/Python/Python312/python.exe -m PyInstaller --onefile --windowed --name "Terminal_Comandado_Voz" --hidden-import=pyttsx3.drivers --hidden-import=pyttsx3.drivers.sapi5 --hidden-import=speech_recognition --hidden-import=PyQt5 --collect-all=pyttsx3 voz.py
```

## Opciones de PyInstaller explicadas:

- `--onefile`: Crea un solo archivo ejecutable
- `--windowed`: No muestra ventana de consola (solo la GUI)
- `--name`: Nombre del ejecutable
- `--icon`: Icono del ejecutable (opcional)
- `--hidden-import`: Importa módulos que PyInstaller podría no detectar automáticamente
- `--collect-all`: Incluye todos los archivos de un paquete

## Ubicación del ejecutable:
Después de la compilación, el ejecutable se encontrará en:
`dist/Terminal_Comandado_Voz.exe`

## Requisitos del sistema para ejecutar:
- Windows 7/8/10/11
- Micrófono conectado
- Conexión a internet (para reconocimiento de voz)
- Altavoces o auriculares (para síntesis de voz)

## Notas importantes:
1. El primer inicio puede ser lento mientras se cargan las librerías
2. Windows Defender podría marcar el ejecutable como sospechoso (falso positivo)
3. El tamaño del ejecutable será considerablemente grande (~100-200MB) debido a las dependencias
4. Se recomienda probar el ejecutable en el mismo sistema donde se compiló
