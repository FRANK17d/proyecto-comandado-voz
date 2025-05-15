import os
import subprocess
import platform
import webbrowser
import datetime
import threading
import time
import json
import queue
import tempfile
import wave
import numpy as np
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QProgressBar, QSlider, QTextEdit, QLineEdit,
                            QFileDialog, QMessageBox, QFrame, QSplitter, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtGui import QFont, QColor, QTextCursor, QIcon, QPalette
import speech_recognition as sr

class AudioLevelThread(QThread):
    """Hilo para monitorear el nivel de audio del micrófono"""
    level_updated = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
    
    def run(self):
        try:
            # Simulación del nivel de audio
            self.running = True
            while self.running:
                # Simulamos un nivel fluctuante para el indicador
                level = np.random.random() * 0.5  # Valor entre 0 y 0.5
                self.level_updated.emit(level)
                time.sleep(0.1)  # Actualizar cada 100ms
        except Exception as e:
            print(f"Error en hilo de audio: {e}")
    
    def stop(self):
        self.running = False
        self.wait()

class SpeechRecognitionThread(QThread):
    """Hilo para reconocimiento de voz"""
    command_recognized = pyqtSignal(str)
    status_message = pyqtSignal(str)
    
    def __init__(self, energy_threshold=4000, parent=None):
        super().__init__(parent)
        self.running = False
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = True
    
    def set_energy_threshold(self, value):
        self.recognizer.energy_threshold = value
    
    def run(self):
        self.running = True
        while self.running:
            try:
                with sr.Microphone() as source:
                    self.status_message.emit("Escuchando...")
                    # Ajustar para ruido ambiente
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    
                    try:
                        # Escuchar audio
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        
                        # Reconocer
                        self.status_message.emit("Procesando...")
                        texto = self.recognizer.recognize_google(audio, language="es-ES")
                        self.command_recognized.emit(texto.lower())
                        
                    except sr.WaitTimeoutError:
                        pass
                    except sr.UnknownValueError:
                        self.status_message.emit("No se entendió el comando")
                    except sr.RequestError as e:
                        self.status_message.emit(f"Error de servicio: {e}")
            except Exception as e:
                self.status_message.emit(f"Error: {str(e)}")
                time.sleep(1)  # Esperar antes de reintentar
    
    def stop(self):
        self.running = False
        self.wait()

class ConsoleTextEdit(QTextEdit):
    """Widget personalizado para la consola con colores"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setReadOnly(True)
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
        # Definir colores para los tipos de mensajes
        colors = {
            "comando": "#61afef",
            "respuesta": "#98c379",
            "error": "#e06c75",
            "sistema": "#c678dd",
            "normal": "#abb2bf"
        }
        
        # Emojis para tipos
        emojis = {
            "comando": "🗣️",
            "respuesta": "🤖",
            "error": "❌",
            "sistema": "🖥️",
            "normal": ""
        }
        
        # Prefijos para tipos
        prefixes = {
            "comando": "Comando: ",
            "respuesta": "Respuesta: ",
            "error": "Error: ",
            "sistema": "",
            "normal": ""
        }
        
        self.setTextColor(QColor("#e5c07b"))
        if message_type in emojis and emojis[message_type]:
            self.append(f"{emojis[message_type]}")
            
        self.setTextColor(QColor(colors[message_type]))
        self.append(f"{prefixes[message_type]}{message}")
        
        # Desplazar hacia abajo para mostrar el mensaje recién agregado
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

class AsistenteVozQT(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Variables para configuración
        self.sistema_operativo = platform.system()
        self.escuchando = False
        self.prefijo_comando = "ejecutar"
        self.historial_comandos = []
        self.indice_historial = 0
        
        # Ruta predeterminada para creación de archivos y carpetas
        self.ruta_trabajo = os.path.expanduser("~")  # Carpeta del usuario por defecto
        self.cargar_configuracion()
        
        # Configurar la ventana principal
        self.setup_ui()
        self.setup_threads()
        
        # Mensaje de bienvenida
        self.agregar_mensaje("¡Bienvenido al Asistente de Voz Avanzado con PyQt5!", "sistema")
        self.agregar_mensaje(f"Ruta de trabajo actual: {self.ruta_trabajo}", "sistema")
        self.agregar_mensaje("Puedes usar comandos de voz o escribirlos en el campo de texto.", "sistema")
        
    def setup_ui(self):
        """Configura la interfaz de usuario con PyQt5"""
        self.setWindowTitle("Asistente de Voz Avanzado")
        self.setMinimumSize(1000, 700)
        
        # Widget central
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Barra superior
        self.top_bar = QFrame()
        self.top_bar.setFrameShape(QFrame.StyledPanel)
        self.top_bar.setMaximumHeight(60)
        self.top_bar.setStyleSheet("background-color: #3498db; border-radius: 5px;")
        
        self.top_layout = QHBoxLayout(self.top_bar)
        
        self.title_label = QLabel("Asistente de Voz Avanzado")
        self.title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        self.top_layout.addWidget(self.title_label)
        
        # Botón de tema oscuro/claro
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
        
        # Splitter principal (divide la pantalla horizontal)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.main_splitter)
        
        # Panel izquierdo (consola)
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        
        self.console_label = QLabel("Consola de Salida")
        self.console_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.left_layout.addWidget(self.console_label)
        
        # Consola de texto
        self.consola = ConsoleTextEdit()
        self.left_layout.addWidget(self.consola)
        
        # Entrada de comandos
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
        # Configurar navegación de historial
        self.command_input.installEventFilter(self)
        
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
        
        # Panel derecho (controles)
        self.right_panel = QWidget()
        self.right_panel.setMaximumWidth(350)
        self.right_panel.setMinimumWidth(250)
        self.right_layout = QVBoxLayout(self.right_panel)
        
        # Control de voz
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
        
        # Botón de micrófono
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
        
        # Control de sensibilidad
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
        
        # Ruta de trabajo
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
        
        # Mostrar ruta actual
        self.current_path_label = QLabel(self.ruta_trabajo)
        self.current_path_label.setWordWrap(True)
        self.current_path_label.setStyleSheet("padding: 5px; background-color: white; border-radius: 3px;")
        self.path_layout.addWidget(self.current_path_label)
        
        # Botones de ruta
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
        
        # Lista de comandos disponibles
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
        
        self.commands_list = QTextEdit()
        self.commands_list.setReadOnly(True)
        self.commands_list.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
        # Lista de comandos
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
        
        # Añadir paneles al splitter principal
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.right_panel)
        self.main_splitter.setSizes([650, 350])
        
        # Barra de estado
        self.status_bar = QLabel(f"Sistema: {platform.system()} {platform.release()} | Ruta: {self.ruta_trabajo}")
        self.status_bar.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 5px;
                border-top: 1px solid #bdc3c7;
            }
        """)
        self.main_layout.addWidget(self.status_bar)
        
        # Establecer el estilo inicial (claro por defecto)
        self.current_theme = "light"
        self.apply_theme()
    
    def setup_threads(self):
        """Configura hilos para reconocimiento de voz y nivel de audio"""
        # Hilo para nivel de audio
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
            # Tema oscuro
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
            # Tema claro
            self.setStyleSheet("")
            self.theme_button.setText("Tema Oscuro")
            self.current_path_label.setStyleSheet("padding: 5px; background-color: white; border-radius: 3px;")
            self.commands_list.setStyleSheet("background-color: white; border-radius: 3px;")
            self.status_bar.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-top: 1px solid #bdc3c7;")
            
            # Restaurar estilos específicos
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
            
            # Frames
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
        """Filtro de eventos para navegación de historial con teclas de flecha"""
        if source == self.command_input and event.type() == event.KeyPress:
            key = event.key()
            if key == Qt.Key_Up:
                self.navegar_historial_arriba()
                return True
            elif key == Qt.Key_Down:
                self.navegar_historial_abajo()
                return True
        return super().eventFilter(source, event)
    
    @pyqtSlot(float)
    def update_audio_level(self, level):
        """Actualiza el indicador de nivel de audio"""
        self.audio_level.setValue(int(level * 100))
    
    @pyqtSlot(str)
    def on_command_recognized(self, command):
        """Maneja un comando reconocido por voz"""
        self.agregar_mensaje(command, "comando")
        
        # Agregar al historial
        self.historial_comandos.append(command)
        self.indice_historial = len(self.historial_comandos)
        
        # Procesar el comando en un hilo separado
        threading.Thread(target=self.procesar_comando, args=(command,), daemon=True).start()
    
    @pyqtSlot(str)
    def on_status_message(self, message):
        """Maneja mensajes de estado del reconocedor de voz"""
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
            threading.Thread(target=self.procesar_comando, args=(comando.lower(),), daemon=True).start()
            
            # Limpiar el campo de entrada
            self.command_input.clear()
    
    def agregar_mensaje(self, mensaje, tipo="normal"):
        """Agrega un mensaje a la consola"""
        self.consola.append_message(mensaje, tipo)
    
    def ejecutar_comando_terminal(self, comando):
        """Ejecuta un comando en la terminal del sistema"""
        try:
            resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
            if resultado.returncode == 0:
                return f"Comando ejecutado correctamente:\n{resultado.stdout}"
            else:
                return f"Error al ejecutar comando:\n{resultado.stderr}"
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
            QTimer.singleShot(1000, self.close)
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
                
        # Eliminar archivo
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
                        
                        # Pedir confirmación
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
                            except Exception as e:
                                self.agregar_mensaje(f"Error al eliminar archivo: {str(e)}", "error")
                        else:
                            self.agregar_mensaje("Eliminación cancelada por el usuario", "sistema")
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
    
    def closeEvent(self, event):
        """Maneja el evento de cierre de ventana"""
        self.guardar_configuracion()
        
        # Detener hilos si están activos
        if hasattr(self, 'audio_thread') and self.audio_thread.isRunning():
            self.audio_thread.stop()
        
        if hasattr(self, 'speech_thread') and self.speech_thread.isRunning():
            self.speech_thread.stop()
        
        event.accept()

def main():
    # Evitar que el sistema operativo Windows DPI scaling distorsione la UI
    if platform.system() == 'Windows':
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
        
    app = QApplication(sys.argv)
    window = AsistenteVozQT()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()