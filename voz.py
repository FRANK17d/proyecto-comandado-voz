# Importación de bibliotecas necesarias
import os                      # Para operaciones del sistema de archivos
import subprocess              # Para ejecutar comandos del sistema
import platform                # Para obtener información del sistema operativo
import webbrowser              # Para abrir navegadores web
import datetime                # Para manejar fechas y horas
import time                    # Para funciones relacionadas con tiempo
import json                    # Para leer/guardar configuraciones
import sys                     # Para acceder a variables del sistema

# Importación de componentes PyQt5 para la interfaz gráfica
from PyQt5.QtWidgets import (
    QApplication,              # Aplicación principal
    QMainWindow,               # Ventana principal
    QWidget,                   # Widget básico
    QVBoxLayout, QHBoxLayout,  # Disposiciones verticales y horizontales
    QPushButton,               # Botones
    QLabel,                    # Etiquetas de texto
    QProgressBar,              # Barras de progreso
    QSlider,                   # Controles deslizantes
    QTextEdit,                 # Áreas de texto
    QLineEdit,                 # Campos de entrada de una línea
    QFileDialog,               # Diálogos para seleccionar archivos
    QMessageBox,               # Ventanas de mensaje
    QFrame,                    # Marcos para agrupar elementos
    QSplitter                 # Divisor que permite redimensionar paneles                # Áreas con desplazamiento
)

# Importación de componentes PyQt5 para señales, temporizadores y hilos
from PyQt5.QtCore import (
    Qt,                        # Constantes de Qt
    QTimer,                    # Temporizador
    pyqtSignal, pyqtSlot,      # Mecanismos para comunicación entre componentes
    QThread                    # Clase para crear hilos
)

# Importación de componentes PyQt5 para manejo gráfico
from PyQt5.QtGui import (
    QFont,                     # Fuentes
    QColor,                    # Colores
    QTextCursor               # Cursor para manipular texto                   # Paletas de colores
)

# Biblioteca para reconocimiento de voz
import speech_recognition as sr


# Clase que maneja la simulación del nivel de audio en un hilo separado
class AudioLevelThread(QThread):
    """Hilo para monitorear el nivel de audio del micrófono"""
    # Señal que se emite cuando cambia el nivel de audio
    level_updated = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False   # Bandera para controlar si el hilo está ejecutándose
        
        # Intentar usar numpy para mejor rendimiento o usar biblioteca estándar si no está disponible
        try:
            import numpy as np
            self.np = np
            self.has_numpy = True
        except ImportError:
            self.has_numpy = False
    
    def run(self):
        """Método que se ejecuta cuando se inicia el hilo"""
        try:
            # Generar valores aleatorios para simular nivel de audio
            self.running = True
            
            if self.has_numpy:
                # Usar numpy para generar valores aleatorios más eficientemente
                while self.running:
                    level = self.np.random.random() * 0.5  # Valor entre 0 y 0.5
                    self.level_updated.emit(level)         # Emitir el nivel para actualizar la interfaz
                    time.sleep(0.1)                        # Esperar 100ms antes de actualizar de nuevo
            else:
                # Alternativa usando la biblioteca estándar si numpy no está disponible
                import random
                while self.running:
                    level = random.random() * 0.5
                    self.level_updated.emit(level)
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"Error en hilo de audio: {e}")
    
    def stop(self):
        """Detiene la ejecución del hilo"""
        self.running = False
        self.wait(200)  # Espera hasta 200ms para que el hilo termine


# Clase que maneja el reconocimiento de voz en un hilo separado
class SpeechRecognitionThread(QThread):
    """Hilo para reconocimiento de voz"""
    # Señales para comunicar resultados y estado
    command_recognized = pyqtSignal(str)  # Se emite cuando se reconoce un comando
    status_message = pyqtSignal(str)      # Se emite para mostrar mensajes de estado
    
    def __init__(self, energy_threshold=4000, parent=None):
        super().__init__(parent)
        self.running = False
        
        # Configurar reconocedor de voz
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold  # Sensibilidad del micrófono
        self.recognizer.dynamic_energy_threshold = True      # Ajuste automático de sensibilidad
        self.pause_processing = False                        # Bandera para pausar procesamiento
        
        # Intentar cargar la lista de micrófonos para mejorar rendimiento
        self.microphone_list = None
        try:
            self.microphone_list = sr.Microphone.list_microphone_names()
        except:
            pass
    
    def set_energy_threshold(self, value):
        """Actualiza el umbral de energía (sensibilidad) del reconocedor"""
        self.recognizer.energy_threshold = value
    
    def pause(self):
        """Pausa temporalmente el procesamiento de comandos"""
        self.pause_processing = True
    
    def resume(self):
        """Reanuda el procesamiento de comandos"""
        self.pause_processing = False
    
    def run(self):
        """Método principal que ejecuta el reconocimiento de voz"""
        self.running = True
        error_count = 0  # Contador para seguimiento de errores consecutivos
        
        while self.running:
            # Si está pausado, esperar un momento y continuar
            if self.pause_processing:
                time.sleep(0.2)
                continue
                
            try:
                # Iniciar micrófono y escuchar
                with sr.Microphone() as source:
                    self.status_message.emit("Escuchando...")
                    
                    # Ajustar para ruido ambiente (solo ocasionalmente para mejorar rendimiento)
                    if error_count == 0 or error_count % 5 == 0:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    
                    try:
                        # Escuchar audio con límite de tiempo
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        
                        # Verificar si se debe pausar el procesamiento
                        if self.pause_processing:
                            continue
                            
                        # Reconocer el texto del audio
                        self.status_message.emit("Procesando...")
                        texto = self.recognizer.recognize_google(audio, language="es-ES")
                        
                        # Verificar nuevamente antes de emitir el comando
                        if not self.pause_processing:
                            self.command_recognized.emit(texto.lower())
                            
                        error_count = 0  # Reiniciar contador de errores tras éxito
                        
                    except sr.WaitTimeoutError:
                        # Timeout normal, no es un error
                        pass
                    except sr.UnknownValueError:
                        # No se pudo entender lo que se dijo
                        self.status_message.emit("No se entendió el comando")
                        error_count += 1
                    except sr.RequestError as e:
                        # Error de conexión al servicio de reconocimiento
                        self.status_message.emit(f"Error de servicio: {e}")
                        error_count += 1
                        time.sleep(1)  # Esperar un poco más si hay error de red
            except Exception as e:
                # Manejo de otros errores
                self.status_message.emit(f"Error: {str(e)}")
                error_count += 1
                
                # Aumentar tiempo de espera si hay muchos errores seguidos
                if error_count > 3:
                    time.sleep(2)
                else:
                    time.sleep(1)
    
    def stop(self):
        """Detiene el hilo de reconocimiento de voz"""
        self.running = False
        self.wait(1000)  # Esperar hasta 1 segundo para terminar


# Clase personalizada para mostrar mensajes en la consola con colores
class ConsoleTextEdit(QTextEdit):
    """Widget personalizado para la consola con colores"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        # Usar buffer para acumular mensajes y procesarlos en lote (mejora rendimiento)
        self.buffer = []               # Lista de mensajes pendientes
        self.max_buffer = 100          # Cantidad máxima de mensajes a mantener
        self.buffer_timer = QTimer()   # Temporizador para procesar mensajes
        self.buffer_timer.timeout.connect(self.flush_buffer)
        self.buffer_timer.start(100)   # Actualizar cada 100ms
        
    def setup_ui(self):
        """Configura la apariencia de la consola"""
        self.setReadOnly(True)  # Hacer que el texto no sea editable
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #282c34;
                color: #abb2bf;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
    def append_message(self, message, message_type="normal"):
        """Añade un mensaje al buffer para mostrarlo en la consola"""
        # En lugar de procesar inmediatamente, añadir al buffer
        self.buffer.append((message, message_type))
        
        # Si el buffer es demasiado grande, forzar procesamiento
        if len(self.buffer) >= 10:
            self.flush_buffer()
    
    def flush_buffer(self):
        """Procesa todos los mensajes pendientes en el buffer"""
        if not self.buffer:
            return  # Si no hay mensajes, no hacer nada
            
        # Desactivar actualizaciones visuales durante el procesamiento (mejora rendimiento)
        self.setUpdatesEnabled(False)
        
        # Definir colores para los diferentes tipos de mensajes
        colors = {
            "comando": "#61afef",    # Azul
            "respuesta": "#98c379",  # Verde
            "error": "#e06c75",      # Rojo
            "sistema": "#c678dd",    # Púrpura
            "normal": "#abb2bf"      # Gris claro
        }
        
        # Emojis para cada tipo de mensaje
        emojis = {
            "comando": "🗣️",
            "respuesta": "🤖",
            "error": "❌",
            "sistema": "🖥️",
            "normal": ""
        }
        
        # Prefijos de texto para cada tipo de mensaje
        prefixes = {
            "comando": "Comando: ",
            "respuesta": "Respuesta: ",
            "error": "Error: ",
            "sistema": "",
            "normal": ""
        }
        
        # Procesar todos los mensajes en lote
        for message, message_type in self.buffer:
            # Mostrar emoji con color amarillo
            self.setTextColor(QColor("#e5c07b"))
            if message_type in emojis and emojis[message_type]:
                self.append(f"{emojis[message_type]}")
                
            # Mostrar mensaje con el color correspondiente
            self.setTextColor(QColor(colors[message_type]))
            self.append(f"{prefixes[message_type]}{message}")
        
        # Limpiar buffer después de procesarlo
        self.buffer.clear()
        
        # Desplazar hacia abajo para mostrar el mensaje más reciente
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        
        # Limitar historial para evitar consumo excesivo de memoria
        if self.document().blockCount() > self.max_buffer:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 
                               self.document().blockCount() - self.max_buffer)
            cursor.removeSelectedText()
        
        # Reactivar actualizaciones visuales
        self.setUpdatesEnabled(True)


# Clase principal que implementa la ventana del asistente de voz
class AsistenteVozQT(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Variables de configuración general
        self.sistema_operativo = platform.system()  # Detectar sistema operativo
        self.escuchando = False                     # Estado del reconocimiento de voz
        self.prefijo_comando = "ejecutar"           # Prefijo para comandos de terminal
        self.historial_comandos = []                # Historial de comandos utilizados
        self.indice_historial = 0                   # Índice actual en el historial
        
        # Ruta predeterminada para trabajar con archivos
        self.ruta_trabajo = os.path.expanduser("~")  # Carpeta del usuario por defecto
        self.cargar_configuracion()                  # Cargar configuración guardada
        
        # Configurar la interfaz gráfica
        self.setup_ui()
        self.setup_threads()
        
        # Mostrar mensajes de bienvenida
        self.agregar_mensaje("¡Bienvenido al Asistente de Voz Avanzado con PyQt5!", "sistema")
        self.agregar_mensaje(f"Ruta de trabajo actual: {self.ruta_trabajo}", "sistema")
        self.agregar_mensaje("Puedes usar comandos de voz o escribirlos en el campo de texto.", "sistema")
        
    def setup_ui(self):
        """Configura todos los elementos de la interfaz gráfica"""
        # Configurar ventana principal
        self.setWindowTitle("Asistente de Voz Avanzado")
        self.setMinimumSize(1000, 700)
        
        # Widget central que contendrá todos los elementos
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal vertical
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Barra superior con título y botón de tema
        self.top_bar = QFrame()
        self.top_bar.setFrameShape(QFrame.StyledPanel)
        self.top_bar.setMaximumHeight(60)
        self.top_bar.setStyleSheet("background-color: #3498db; border-radius: 5px;")
        
        self.top_layout = QHBoxLayout(self.top_bar)
        
        # Título de la aplicación
        self.title_label = QLabel("Asistente de Voz Avanzado")
        self.title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        self.top_layout.addWidget(self.title_label)
        
        # Botón para cambiar entre tema claro y oscuro
        self.theme_button = QPushButton("Cambiar Tema")
        self.theme_button.setStyleSheet("""
            QPushButton {
                background-color: #2980b9; 
                color: white; 
                border-radius: 5px; 
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """)
        self.theme_button.clicked.connect(self.toggle_theme)
        self.top_layout.addWidget(self.theme_button)
        
        self.main_layout.addWidget(self.top_bar)
        
        # Divisor principal que permite ajustar tamaño de paneles
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.main_splitter)
        
        # Panel izquierdo - Consola de salida y entrada de comandos
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        
        self.console_label = QLabel("Consola de Salida")
        self.console_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.left_layout.addWidget(self.console_label)
        
        # Consola donde se muestran los mensajes
        self.consola = ConsoleTextEdit()
        self.left_layout.addWidget(self.consola)
        
        # Área para ingresar comandos manualmente
        self.command_input_layout = QHBoxLayout()
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Escribe un comando aquí...")
        self.command_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #3498db;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
        """)
        self.command_input.returnPressed.connect(self.ejecutar_comando_escrito)
        # Configurar navegación con teclas arriba/abajo para acceder al historial
        self.command_input.installEventFilter(self)
        
        # Botón para enviar comando escrito
        self.send_button = QPushButton("Enviar")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.send_button.clicked.connect(self.ejecutar_comando_escrito)
        
        self.command_input_layout.addWidget(self.command_input)
        self.command_input_layout.addWidget(self.send_button)
        
        self.left_layout.addLayout(self.command_input_layout)
        
        # Panel derecho - Controles y opciones
        self.right_panel = QWidget()
        self.right_panel.setMaximumWidth(350)
        self.right_panel.setMinimumWidth(250)
        self.right_layout = QVBoxLayout(self.right_panel)
        
        # Marco para controles de voz
        self.voice_control_frame = QFrame()
        self.voice_control_frame.setFrameShape(QFrame.StyledPanel)
        self.voice_control_frame.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        self.voice_layout = QVBoxLayout(self.voice_control_frame)
        
        self.voice_label = QLabel("Control de Voz")
        self.voice_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.voice_layout.addWidget(self.voice_label)
        
        # Botón para iniciar/detener reconocimiento de voz
        self.mic_button = QPushButton("Iniciar Escucha")
        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.mic_button.setMinimumHeight(50)
        self.mic_button.clicked.connect(self.toggle_escucha)
        self.voice_layout.addWidget(self.mic_button)
        
        # Indicador de nivel de audio
        self.audio_level_label = QLabel("Nivel de Audio:")
        self.voice_layout.addWidget(self.audio_level_label)
        
        self.audio_level = QProgressBar()
        self.audio_level.setRange(0, 100)
        self.audio_level.setValue(0)
        self.audio_level.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: #f0f0f0;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 5px;
            }
        """)
        self.voice_layout.addWidget(self.audio_level)
        
        # Control deslizante para ajustar sensibilidad del micrófono
        self.sensitivity_label = QLabel("Sensibilidad: 4000")
        self.voice_layout.addWidget(self.sensitivity_label)
        
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(1000, 8000)
        self.sensitivity_slider.setValue(4000)
        self.sensitivity_slider.setTickPosition(QSlider.TicksBelow)
        self.sensitivity_slider.setTickInterval(1000)
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity)
        self.voice_layout.addWidget(self.sensitivity_slider)
        
        self.right_layout.addWidget(self.voice_control_frame)
        
        # Marco para configuración de ruta de trabajo
        self.path_frame = QFrame()
        self.path_frame.setFrameShape(QFrame.StyledPanel)
        self.path_frame.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        self.path_layout = QVBoxLayout(self.path_frame)
        
        self.path_label = QLabel("Ruta de Trabajo")
        self.path_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.path_layout.addWidget(self.path_label)
        
        # Mostrar ruta actual donde se crean/modifican archivos
        self.current_path_label = QLabel(self.ruta_trabajo)
        self.current_path_label.setWordWrap(True)
        self.current_path_label.setStyleSheet("padding: 5px; background-color: white; border-radius: 3px;")
        self.path_layout.addWidget(self.current_path_label)
        
        # Botones para cambiar la ruta de trabajo
        self.path_buttons_layout = QHBoxLayout()
        
        self.change_path_button = QPushButton("Cambiar Ruta")
        self.change_path_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.change_path_button.clicked.connect(self.cambiar_ruta_dialogo)
        
        self.use_current_path_button = QPushButton("Usar Actual")
        self.use_current_path_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.use_current_path_button.clicked.connect(self.usar_ruta_actual)
        
        self.path_buttons_layout.addWidget(self.change_path_button)
        self.path_buttons_layout.addWidget(self.use_current_path_button)
        
        self.path_layout.addLayout(self.path_buttons_layout)
        
        self.right_layout.addWidget(self.path_frame)
        
        # Marco para mostrar lista de comandos disponibles
        self.commands_frame = QFrame()
        self.commands_frame.setFrameShape(QFrame.StyledPanel)
        self.commands_frame.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        self.commands_layout = QVBoxLayout(self.commands_frame)
        
        self.commands_label = QLabel("Comandos Disponibles")
        self.commands_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.commands_layout.addWidget(self.commands_label)
        
        # Área de texto con lista de comandos disponibles
        self.commands_list = QTextEdit()
        self.commands_list.setReadOnly(True)
        self.commands_list.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
        # Lista de comandos que se pueden usar
        comandos_texto = """• "ejecutar [comando]" - Ejecuta comando de terminal
• "listar" o "mostrar archivos" - Lista directorios
• "directorio actual" - Muestra ruta actual
• "cambiar directorio a [ruta]" - Cambia de directorio
• "establecer ruta a [ruta]" - Cambia ruta de trabajo
• "usar ruta predeterminada" - Usa carpeta de usuario
• "crear carpeta [nombre]" - Crea una carpeta
• "crear archivo [nombre]" - Crea un archivo
• "eliminar archivo [nombre]" - Borra un archivo
• "información del sistema" - Muestra datos del sistema
• "hora" o "qué hora es" - Muestra la hora actual
• "fecha" o "qué día es" - Muestra la fecha actual
• "abrir navegador" - Abre navegador predeterminado
• "buscar [término]" - Busca en Google
• "mostrar procesos" - Lista procesos en ejecución
• "uso de memoria" - Muestra uso de memoria RAM
• "uso de disco" - Muestra espacio en disco
• "conexiones de red" - Muestra conexiones activas
• "salir" o "terminar" - Cierra la aplicación"""
        
        self.commands_list.setText(comandos_texto)
        self.commands_layout.addWidget(self.commands_list)
        
        self.right_layout.addWidget(self.commands_frame)
        
        # Añadir los paneles al divisor principal
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.right_panel)
        self.main_splitter.setSizes([650, 350])  # Tamaño inicial de los paneles
        
        # Barra de estado en la parte inferior
        self.status_bar = QLabel(f"Sistema: {platform.system()} {platform.release()} | Ruta: {self.ruta_trabajo}")
        self.status_bar.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 5px;
                border-top: 1px solid #bdc3c7;
            }
        """)
        self.main_layout.addWidget(self.status_bar)
        
        # Establecer tema inicial (claro por defecto)
        self.current_theme = "light"
        self.apply_theme()
    
    def setup_threads(self):
        """Configura los hilos para reconocimiento de voz y nivel de audio"""
        # Hilo para mostrar nivel de audio
        self.audio_thread = AudioLevelThread()
        self.audio_thread.level_updated.connect(self.update_audio_level)
        
        # Hilo para reconocimiento de voz
        self.speech_thread = SpeechRecognitionThread()
        self.speech_thread.command_recognized.connect(self.on_command_recognized)
        self.speech_thread.status_message.connect(self.on_status_message)
    
    def toggle_theme(self):
        """Cambia entre tema claro y oscuro"""
        if self.current_theme == "light":
            self.current_theme = "dark"
        else:
            self.current_theme = "light"
        self.apply_theme()
    
    def apply_theme(self):
        """Aplica el tema actual a toda la aplicación"""
        if self.current_theme == "dark":
            # Configuración para tema oscuro
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                }
                QFrame {
                    background-color: #34495e;
                    color: #ecf0f1;
                    border-radius: 5px;
                }
                QLineEdit {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    border: 1px solid #3498db;
                    border-radius: 5px;
                    padding: 5px;
                }
                QTextEdit {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    border-radius: 3px;
                }
                QLabel {
                    color: #ecf0f1;
                }
            """)
            self.theme_button.setText("Tema Claro")
            self.current_path_label.setStyleSheet("padding: 5px; background-color: #2c3e50; border: 1px solid #3498db; border-radius: 3px;")
            self.commands_list.setStyleSheet("background-color: #2c3e50; color: #ecf0f1; border-radius: 3px;")
            self.status_bar.setStyleSheet("background-color: #34495e; padding: 5px; border-top: 1px solid #2c3e50;")
        else:
            # Configuración para tema claro
            self.setStyleSheet("")
            self.theme_button.setText("Tema Oscuro")
            self.current_path_label.setStyleSheet("padding: 5px; background-color: white; border-radius: 3px;")
            self.commands_list.setStyleSheet("background-color: white; border-radius: 3px;")
            self.status_bar.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-top: 1px solid #bdc3c7;")
            
            # Restaurar estilos específicos para componentes
            self.top_bar.setStyleSheet("background-color: #3498db; border-radius: 5px;")
            self.title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
            self.theme_button.setStyleSheet("""
                QPushButton {
                    background-color: #2980b9; 
                    color: white; 
                    border-radius: 5px; 
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #3498db;
                }
            """)
            
            # Restaurar estilos de marcos
            frames = [self.voice_control_frame, self.path_frame, self.commands_frame]
            for frame in frames:
                frame.setStyleSheet("""
                    QFrame {
                        background-color: #f0f0f0;
                        border-radius: 5px;
                        padding: 5px;
                    }
                """)
    
    def eventFilter(self, source, event):
        """Captura eventos de teclado para navegación en historial"""
        if source == self.command_input and event.type() == event.KeyPress:
            key = event.key()
            if key == Qt.Key_Up:
                # Flecha arriba: comando anterior del historial
                self.navegar_historial_arriba()
                return True
            elif key == Qt.Key_Down:
                # Flecha abajo: comando siguiente del historial
                self.navegar_historial_abajo()
                return True
        return super().eventFilter(source, event)
    
    @pyqtSlot(float)
    def update_audio_level(self, level):
        """Actualiza el indicador visual de nivel de audio"""
        self.audio_level.setValue(int(level * 100))
    
    @pyqtSlot(str)
    def on_command_recognized(self, command):
        """Maneja un comando reconocido por voz"""
        self.agregar_mensaje(command, "comando")
        
        # Agregar al historial
        self.historial_comandos.append(command)
        self.indice_historial = len(self.historial_comandos)
        
        # Pausar temporalmente el reconocimiento durante procesamiento
        if hasattr(self, 'speech_thread'):
            self.speech_thread.pause()
            
        # Procesar el comando en el hilo principal para evitar bloqueos
        QTimer.singleShot(0, lambda cmd=command: self.procesar_comando_seguro(cmd))
    
    def procesar_comando_seguro(self, comando):
        """Procesa el comando de forma segura y reanuda reconocimiento al terminar"""
        try:
            self.procesar_comando(comando)
        except Exception as e:
            self.agregar_mensaje(f"Error al procesar comando: {str(e)}", "error")
        finally:
            # Reanudar reconocimiento de voz siempre, incluso si hay errores
            if hasattr(self, 'speech_thread'):
                self.speech_thread.resume()
    
    @pyqtSlot(str)
    def on_status_message(self, message):
        """Actualiza la barra de estado con mensajes del reconocedor"""
        self.status_bar.setText(message)
    
    def navegar_historial_arriba(self):
        """Navega hacia arriba en el historial de comandos"""
        if self.historial_comandos and self.indice_historial > 0:
            self.indice_historial -= 1
            self.command_input.setText(self.historial_comandos[self.indice_historial])
    
    def navegar_historial_abajo(self):
        """Navega hacia abajo en el historial de comandos"""
        if self.historial_comandos and self.indice_historial < len(self.historial_comandos) - 1:
            self.indice_historial += 1
            self.command_input.setText(self.historial_comandos[self.indice_historial])
        elif self.indice_historial == len(self.historial_comandos) - 1:
            # Si estamos al final del historial, limpiar el campo
            self.indice_historial = len(self.historial_comandos)
            self.command_input.clear()
    
    def cargar_configuracion(self):
        """Carga la configuración guardada si existe"""
        config_path = os.path.join(os.path.expanduser("~"), ".asistente_voz_qt_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if 'ruta_trabajo' in config and os.path.exists(config['ruta_trabajo']):
                        self.ruta_trabajo = config['ruta_trabajo']
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
    
    def guardar_configuracion(self):
        """Guarda la configuración actual"""
        config_path = os.path.join(os.path.expanduser("~"), ".asistente_voz_qt_config.json")
        try:
            config = {
                'ruta_trabajo': self.ruta_trabajo
            }
            with open(config_path, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error al guardar configuración: {e}")
    
    def update_sensitivity(self, value):
        """Actualiza el valor de sensibilidad del micrófono"""
        self.sensitivity_label.setText(f"Sensibilidad: {value}")
        if hasattr(self, 'speech_thread'):
            self.speech_thread.set_energy_threshold(value)
    
    def toggle_escucha(self):
        """Activa o desactiva la escucha por voz"""
        if self.escuchando:
            self.detener_escucha()
        else:
            self.iniciar_escucha()
    
    def iniciar_escucha(self):
        """Inicia la escucha de voz"""
        self.escuchando = True
        # Cambiar apariencia del botón a rojo para indicar que está activo
        self.mic_button.setText("Detener Escucha")
        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.agregar_mensaje("Escucha iniciada. Di un comando...", "sistema")
        
        # Iniciar hilos
        self.audio_thread.start()
        self.speech_thread.start()
    
    def detener_escucha(self):
        """Detiene la escucha de voz"""
        self.escuchando = False
        # Cambiar apariencia del botón a verde para indicar que está inactivo
        self.mic_button.setText("Iniciar Escucha")
        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.agregar_mensaje("Escucha detenida", "sistema")
        self.audio_level.setValue(0)
        
        # Detener hilos
        self.audio_thread.stop()
        self.speech_thread.stop()
    
    def cambiar_ruta_dialogo(self):
        """Abre un diálogo para seleccionar la nueva ruta de trabajo"""
        nueva_ruta = QFileDialog.getExistingDirectory(self, "Seleccionar Ruta de Trabajo", self.ruta_trabajo)
        if nueva_ruta:  # Si el usuario no canceló el diálogo
            self.cambiar_ruta_trabajo(nueva_ruta)
    
    def usar_ruta_actual(self):
        """Establece el directorio actual como ruta de trabajo"""
        self.cambiar_ruta_trabajo(os.getcwd())
    
    def cambiar_ruta_trabajo(self, nueva_ruta):
        """Cambia la ruta de trabajo para la creación de archivos y carpetas"""
        try:
            # Verificar si la ruta existe y es accesible
            if os.path.exists(nueva_ruta) and os.path.isdir(nueva_ruta):
                self.ruta_trabajo = nueva_ruta
                self.current_path_label.setText(self.ruta_trabajo)
                self.status_bar.setText(f"Sistema: {platform.system()} {platform.release()} | Ruta: {self.ruta_trabajo}")
                self.agregar_mensaje(f"Ruta de trabajo cambiada a: {self.ruta_trabajo}", "sistema")
                self.guardar_configuracion()
            else:
                self.agregar_mensaje(f"Error: La ruta '{nueva_ruta}' no existe o no es accesible", "error")
        except Exception as e:
            self.agregar_mensaje(f"Error al cambiar la ruta: {str(e)}", "error")
    
    def ejecutar_comando_escrito(self):
        """Ejecuta un comando escrito en la entrada de texto"""
        comando = self.command_input.text().strip()
        if comando:
            # Agregar al historial
            self.historial_comandos.append(comando)
            self.indice_historial = len(self.historial_comandos)
            
            # Mostrar el comando
            self.agregar_mensaje(comando, "comando")
            
            # Procesar el comando
            self.procesar_comando_seguro(comando.lower())
            
            # Limpiar el campo de entrada
            self.command_input.clear()
    
    def agregar_mensaje(self, mensaje, tipo="normal"):
        """Agrega un mensaje a la consola"""
        self.consola.append_message(mensaje, tipo)
    
    def ejecutar_comando_terminal(self, comando):
        """Ejecuta un comando en la terminal del sistema"""
        try:
            # Limitar el tiempo de ejecución para evitar bloqueos
            if self.sistema_operativo == "Windows":
                # En Windows usamos un enfoque diferente
                with subprocess.Popen(
                    comando, 
                    shell=True, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW  # Evitar ventanas emergentes
                ) as proceso:
                    try:
                        # Ejecutar con límite de tiempo
                        stdout, stderr = proceso.communicate(timeout=10)
                        if proceso.returncode == 0:
                            # Limitar la longitud del resultado para evitar desbordamiento
                            if len(stdout) > 5000:
                                stdout = stdout[:5000] + "\n...(resultado truncado)..."
                            return f"Comando ejecutado correctamente:\n{stdout}"
                        else:
                            return f"Error al ejecutar comando:\n{stderr}"
                    except subprocess.TimeoutExpired:
                        # Si tarda demasiado, matar el proceso
                        proceso.kill()
                        return "Error: El comando tardó demasiado en ejecutarse y fue cancelado."
            else:
                # Linux/Mac - método alternativo
                resultado = subprocess.run(
                    comando, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    timeout=10  # 10 segundos de timeout
                )
                
                if resultado.returncode == 0:
                    # Limitar la longitud del resultado
                    if len(resultado.stdout) > 5000:
                        stdout = resultado.stdout[:5000] + "\n...(resultado truncado)..."
                    else:
                        stdout = resultado.stdout
                    return f"Comando ejecutado correctamente:\n{stdout}"
                else:
                    return f"Error al ejecutar comando:\n{resultado.stderr}"
                    
        except subprocess.TimeoutExpired:
            return "Error: El comando tardó demasiado en ejecutarse y fue cancelado."
        except PermissionError:
            return "Error: No tienes permisos para ejecutar este comando."
        except Exception as e:
            return f"Excepción al ejecutar comando: {str(e)}"
    
    def procesar_comando(self, texto):
        """Procesa el comando de voz y ejecuta la acción correspondiente"""
        # Salir de la aplicación
        if "salir" in texto or "terminar" in texto or "adiós" in texto or "adios" in texto:
            self.agregar_mensaje("Cerrando asistente por voz...", "sistema")
            if self.escuchando:
                self.detener_escucha()
            self.guardar_configuracion()
            QTimer.singleShot(1000, self.close)  # Cerrar aplicación después de 1 segundo
            return
        
        # Establecer ruta de trabajo
        elif any(frase in texto for frase in ["establecer ruta a", "cambiar ruta a", "cambiar ruta de trabajo a"]):
            palabras_clave = ["establecer ruta a", "cambiar ruta a", "cambiar ruta de trabajo a"]
            for palabra in palabras_clave:
                if palabra in texto:
                    nueva_ruta = texto.split(palabra)[1].strip()
                    if nueva_ruta:
                        self.cambiar_ruta_trabajo(nueva_ruta)
                    return
            self.agregar_mensaje("No se especificó una ruta válida", "error")
            return
            
        # Usar ruta predeterminada (carpeta del usuario)
        elif "usar ruta predeterminada" in texto or "ruta por defecto" in texto:
            ruta_predeterminada = os.path.expanduser("~")
            self.cambiar_ruta_trabajo(ruta_predeterminada)
            return
        
        # Crear carpeta
        elif "crear carpeta" in texto or "nueva carpeta" in texto:
            palabras_clave = ["crear carpeta", "nueva carpeta"]
            for palabra in palabras_clave:
                if palabra in texto:
                    nombre_carpeta = texto.split(palabra)[1].strip()
                    if nombre_carpeta:
                        try:
                            # Crear la carpeta en la ruta de trabajo
                            ruta_completa = os.path.join(self.ruta_trabajo, nombre_carpeta)
                            os.makedirs(ruta_completa, exist_ok=True)
                            self.agregar_mensaje(f"Carpeta creada: {ruta_completa}", "respuesta")
                        except Exception as e:
                            self.agregar_mensaje(f"Error al crear carpeta: {str(e)}", "error")
                    else:
                        self.agregar_mensaje("No se especificó un nombre para la carpeta", "error")
                    return
        
        # Ejecutar comando directo de terminal
        elif texto.startswith(self.prefijo_comando):
            # Extrae el comando después de "ejecutar"
            comando_terminal = texto[len(self.prefijo_comando):].strip()
            self.agregar_mensaje(f"Ejecutando en terminal: {comando_terminal}", "sistema")
            resultado = self.ejecutar_comando_terminal(comando_terminal)
            self.agregar_mensaje(resultado, "respuesta")
            return
        
        # Listar archivos y directorios
        elif "listar" in texto or "mostrar archivos" in texto or "mostrar directorio" in texto:
            # Listar archivos en la ruta de trabajo
            if self.sistema_operativo == "Windows":
                resultado = self.ejecutar_comando_terminal(f"dir \"{self.ruta_trabajo}\"")
            else:  # Linux/Mac
                resultado = self.ejecutar_comando_terminal(f"ls -la \"{self.ruta_trabajo}\"")
            self.agregar_mensaje(resultado, "respuesta")
            return
        
        # Cambiar de directorio
        elif "cambiar directorio" in texto or "ir a directorio" in texto:
            partes = texto.split(" a ")
            if len(partes) > 1:
                directorio = partes[1].strip()
                # Si la ruta es relativa, hacerla relativa a la ruta de trabajo
                if not os.path.isabs(directorio):
                    directorio = os.path.join(self.ruta_trabajo, directorio)
                try:
                    os.chdir(directorio)
                    self.agregar_mensaje(f"Cambiado al directorio: {os.getcwd()}", "respuesta")
                except:
                    self.agregar_mensaje(f"No se pudo cambiar al directorio: {directorio}", "error")
            else:
                self.agregar_mensaje("No se especificó un directorio", "error")
            return
        
        # Mostrar directorio actual
        elif "directorio actual" in texto or "dónde estoy" in texto:
            self.agregar_mensaje(f"Directorio actual: {os.getcwd()}", "respuesta")
            self.agregar_mensaje(f"Ruta de trabajo: {self.ruta_trabajo}", "respuesta")
            return
            
        # Apagar sistema
        elif "apagar sistema" in texto or "apagar computadora" in texto:
            # Usar QTimer para ejecutar el diálogo en el hilo principal
            QTimer.singleShot(0, lambda: self.confirmar_apagado(texto))
            return
                
        # Cancelar apagado
        elif "cancelar apagado" in texto:
            if self.sistema_operativo == "Windows":
                os.system("shutdown /a")
            else:  # Linux/Mac
                os.system("shutdown -c")
            self.agregar_mensaje("Apagado cancelado", "respuesta")
            return
            
        # Crear archivo
        elif "crear archivo" in texto:
            partes = texto.split("crear archivo")
            if len(partes) > 1:
                nombre_archivo = partes[1].strip()
                try:
                    # Crear el archivo en la ruta de trabajo
                    ruta_completa = os.path.join(self.ruta_trabajo, nombre_archivo)
                    with open(ruta_completa, 'w') as f:
                        pass
                    self.agregar_mensaje(f"Archivo creado: {ruta_completa}", "respuesta")
                except Exception as e:
                    self.agregar_mensaje(f"Error al crear archivo: {str(e)}", "error")
            else:
                self.agregar_mensaje("No se especificó un nombre de archivo", "error")
            return
                
        # Eliminar archivo - CORREGIDO
        elif "eliminar archivo" in texto or "borrar archivo" in texto:
            for palabra in ["eliminar archivo", "borrar archivo"]:
                if palabra in texto:
                    partes = texto.split(palabra)
                    if len(partes) > 1:
                        nombre_archivo = partes[1].strip()
                        
                        # Si la ruta es relativa, hacerla relativa a la ruta de trabajo
                        if not os.path.isabs(nombre_archivo):
                            ruta_completa = os.path.join(self.ruta_trabajo, nombre_archivo)
                        else:
                            ruta_completa = nombre_archivo
                        
                        # Verificar si el archivo existe antes de intentar eliminarlo
                        if not os.path.exists(ruta_completa):
                            self.agregar_mensaje(f"Error: El archivo {ruta_completa} no existe", "error")
                            return
                        
                        # Usar QTimer para ejecutar el diálogo en el hilo principal
                        QTimer.singleShot(0, lambda rc=ruta_completa: self.confirmar_eliminacion(rc))
                        return
            
            self.agregar_mensaje("No se especificó un nombre de archivo", "error")
            return
            
        # Mostrar información del sistema
        elif "información del sistema" in texto or "información sistema" in texto:
            info = f"Sistema operativo: {platform.system()} {platform.release()}\n"
            info += f"Versión: {platform.version()}\n"
            info += f"Arquitectura: {platform.machine()}\n"
            info += f"Procesador: {platform.processor()}\n"
            info += f"Nombre de equipo: {platform.node()}"
            self.agregar_mensaje(info, "respuesta")
            return
            
        # Mostrar hora actual
        elif "hora" in texto or "qué hora es" in texto:
            hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
            self.agregar_mensaje(f"Son las {hora_actual}", "respuesta")
            return
            
        # Mostrar fecha actual
        elif "fecha" in texto or "qué día es" in texto or "qué fecha es" in texto:
            fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
            self.agregar_mensaje(f"Hoy es {fecha_actual}", "respuesta")
            return
            
        # Abrir navegador web
        elif "abrir navegador" in texto or "abrir web" in texto:
            webbrowser.open("https://www.google.com")
            self.agregar_mensaje("Abriendo navegador web", "respuesta")
            return
            
        # Buscar en Google
        elif "buscar" in texto:
            busqueda = texto.replace("buscar", "").strip()
            if busqueda:
                url = f"https://www.google.com/search?q={busqueda}"
                webbrowser.open(url)
                self.agregar_mensaje(f"Buscando '{busqueda}' en Google", "respuesta")
            else:
                self.agregar_mensaje("No se especificó qué buscar", "error")
            return
                
        # Mostrar procesos en ejecución
        elif "mostrar procesos" in texto or "procesos en ejecución" in texto:
            if self.sistema_operativo == "Windows":
                resultado = self.ejecutar_comando_terminal("tasklist")
            else:  # Linux/Mac
                resultado = self.ejecutar_comando_terminal("ps aux")
            self.agregar_mensaje(resultado, "respuesta")
            return
                
        # Mostrar uso de memoria
        elif "uso de memoria" in texto or "memoria" in texto:
            if self.sistema_operativo == "Windows":
                resultado = self.ejecutar_comando_terminal("wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value")
            else:  # Linux/Mac
                resultado = self.ejecutar_comando_terminal("free -h")
            self.agregar_mensaje(resultado, "respuesta")
            return
                
        # Mostrar uso de disco
        elif "uso de disco" in texto or "espacio en disco" in texto:
            if self.sistema_operativo == "Windows":
                resultado = self.ejecutar_comando_terminal("wmic logicaldisk get caption,description,providername,size,freespace")
            else:  # Linux/Mac
                resultado = self.ejecutar_comando_terminal("df -h")
            self.agregar_mensaje(resultado, "respuesta")
            return
                
        # Mostrar conexiones de red
        elif "conexiones de red" in texto or "mostrar conexiones" in texto:
            if self.sistema_operativo == "Windows":
                resultado = self.ejecutar_comando_terminal("netstat -an")
            else:  # Linux/Mac
                resultado = self.ejecutar_comando_terminal("netstat -tuln")
            self.agregar_mensaje(resultado, "respuesta")
            return
        
        # Comando no reconocido
        else:
            self.agregar_mensaje(f"No reconozco el comando: '{texto}'. Prueba de nuevo.", "error")
            return
            
    def confirmar_eliminacion(self, ruta_completa):
        """Muestra diálogo de confirmación para eliminar un archivo"""
        # Este método se ejecuta en el hilo principal
        confirmacion = QMessageBox.question(
            self,
            "Confirmar Eliminación", 
            f"¿Estás seguro de que deseas eliminar el archivo {ruta_completa}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirmacion == QMessageBox.Yes:
            try:
                os.remove(ruta_completa)
                self.agregar_mensaje(f"Archivo eliminado: {ruta_completa}", "respuesta")
            except PermissionError:
                self.agregar_mensaje(f"Error: No tienes permisos para eliminar {ruta_completa}", "error")
            except Exception as e:
                self.agregar_mensaje(f"Error al eliminar archivo: {str(e)}", "error")
        else:
            self.agregar_mensaje("Eliminación cancelada por el usuario", "sistema")
            
    def confirmar_apagado(self, texto):
        """Muestra diálogo de confirmación para apagar el sistema"""
        # Este método se ejecuta en el hilo principal
        confirmacion = QMessageBox.question(
            self, 
            "Confirmar Apagado", 
            "¿Estás seguro de que deseas apagar el sistema?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirmacion == QMessageBox.Yes:
            if self.sistema_operativo == "Windows":
                os.system("shutdown /s /t 60")
                self.agregar_mensaje("Apagando el sistema en 60 segundos. Para cancelar di 'cancelar apagado'", "respuesta")
            else:  # Linux/Mac
                os.system("shutdown -h +1")
                self.agregar_mensaje("Apagando el sistema en 1 minuto", "respuesta")
        else:
            self.agregar_mensaje("Apagado cancelado por el usuario", "sistema")
    
    def closeEvent(self, event):
        """Maneja el evento de cierre de ventana"""
        # Guardar configuración
        self.guardar_configuracion()
        
        # Detener hilos si están activos (con mejor manejo de errores)
        try:
            if hasattr(self, 'audio_thread') and self.audio_thread.isRunning():
                self.audio_thread.stop()
                if not self.audio_thread.wait(1000):  # Esperar máximo 1 segundo
                    self.audio_thread.terminate()  # Forzar terminación si no responde
        except Exception as e:
            print(f"Error al detener hilo de audio: {e}")
            
        try:
            if hasattr(self, 'speech_thread') and self.speech_thread.isRunning():
                self.speech_thread.stop()
                if not self.speech_thread.wait(1000):  # Esperar máximo 1 segundo
                    self.speech_thread.terminate()  # Forzar terminación si no responde
        except Exception as e:
            print(f"Error al detener hilo de reconocimiento: {e}")
        
        # Asegurarse de detener el timer de la consola
        if hasattr(self, 'consola') and hasattr(self.consola, 'buffer_timer'):
            self.consola.buffer_timer.stop()
        
        # Aceptar el evento
        event.accept()


# Función principal para iniciar la aplicación
def main():
    # Evitar que el sistema operativo Windows DPI scaling distorsione la UI
    if platform.system() == 'Windows':
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception as e:
            print(f"Advertencia: No se pudo configurar DPI: {e}")
    
    # Crear aplicación con manejo de excepciones
    app = QApplication(sys.argv)
    
    # Función para manejar excepciones no capturadas
    def handle_exception(exc_type, exc_value, exc_traceback):
        import traceback
        error_msg = f"Error no capturado: {exc_type.__name__}: {exc_value}"
        print(error_msg)
        print("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        
        # Mostrar diálogo de error
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error en la aplicación")
        msg_box.setText("Ha ocurrido un error en la aplicación.")
        msg_box.setDetailedText("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        msg_box.exec_()
        
    # Configurar manejador de excepciones
    sys.excepthook = handle_exception
    
    try:
        # Iniciar la ventana principal
        window = AsistenteVozQT()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        # Capturar cualquier error durante la inicialización
        error_msg = f"Error al iniciar la aplicación: {str(e)}"
        print(error_msg)
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error de inicialización")
        msg_box.setText(error_msg)
        msg_box.exec_()
        sys.exit(1)


# Punto de entrada de la aplicación
if __name__ == "__main__":
    main()