# Importación de bibliotecas necesarias
import os                   # Para operaciones del sistema de archivos
import subprocess           # Para ejecutar comandos del sistema
import platform             # Para obtener información del sistema operativo
import webbrowser           # Para abrir navegadores web
import datetime             # Para manejar fechas y horas
import time                 # Para funciones relacionadas con tiempo
import json                 # Para leer/guardar configuraciones
import sys                  # Para acceder a variables del sistema

# Importación de componentes PyQt5 para la interfaz gráfica
from PyQt5.QtWidgets import (
    QApplication,           # Aplicación principal
    QMainWindow,            # Ventana principal
    QWidget,                # Widget básico
    QVBoxLayout, QHBoxLayout, # Disposiciones verticales y horizontales
    QPushButton,            # Botones
    QLabel,                 # Etiquetas de texto
    QProgressBar,           # Barras de progreso
    QSlider,                # Controles deslizantes
    QTextEdit,              # Áreas de texto
    QLineEdit,              # Campos de entrada de una línea
    QFileDialog,            # Diálogos para seleccionar archivos
    QMessageBox,            # Ventanas de mensaje
    QFrame,                 # Marcos para agrupar elementos
    QSplitter               # Divisor que permite redimensionar paneles
)

# Importación de componentes PyQt5 para señales, temporizadores y hilos
from PyQt5.QtCore import (
    Qt,                     # Constantes de Qt
    QTimer,                 # Temporizador
    pyqtSignal, pyqtSlot,   # Mecanismos para comunicación entre componentes
    QThread                 # Clase para crear hilos
)

# Importación de componentes PyQt5 para manejo gráfico
from PyQt5.QtGui import (
    QFont,                  # Fuentes
    QColor,                 # Colores
    QTextCursor             # Cursor para manipular texto
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
        self.running = False  # Bandera para controlar si el hilo está ejecutándose
        
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
                    self.level_updated.emit(level)       # Emitir el nivel para actualizar la interfaz
                    time.sleep(0.1)                      # Esperar 100ms antes de actualizar de nuevo
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
                    time.sleep(0.1) 
    
    def stop(self):
        """Detiene el hilo de reconocimiento de voz"""
        self.running = False
        self.wait(1000)  # Esperar hasta 1 segundo para terminar


# Clase personalizada para mostrar mensajes en la consola con colores
class ConsoleTextEdit(QTextEdit):
    """Widget personalizado para la consola con colores"""
    def __init__(self, parent_window, parent=None): # Añadido parent_window
        super().__init__(parent)
        self.parent_window = parent_window # Guardar referencia a la ventana principal
        self.setup_ui()
        
        self.buffer = []              
        self.max_buffer = 200         
        self.buffer_timer = QTimer() 
        self.buffer_timer.timeout.connect(self.flush_buffer)
        self.buffer_timer.start(100)  
            
    def setup_ui(self):
        """Configura la apariencia de la consola"""
        self.setReadOnly(True) 
        self.setFont(QFont("Consolas", 10))
        # El estilo principal se aplicará desde AsistenteVozQT.apply_theme
        # Este es un fallback o estilo base muy simple.
        self.setStyleSheet("background-color: black; color: white;")

    def append_message(self, message, message_type="normal"):
        """Añade un mensaje al buffer para mostrarlo en la consola"""
        self.buffer.append((message, message_type))
        if len(self.buffer) >= 10: 
            self.flush_buffer()
    
    def flush_buffer(self):
        """Procesa todos los mensajes pendientes en el buffer"""
        if not self.buffer:
            return
            
        self.setUpdatesEnabled(False)
        
        is_black_and_white_theme = (hasattr(self.parent_window, 'current_theme') and 
                                    self.parent_window.current_theme == "black_and_white")

        # Colores base (para tema claro o si no es B&W)
        text_color = "#abb2bf" # Default for light theme console
        prompt_color = "#61afef"
        command_text_color = "#98c379"
        respuesta_color = "#98c379"
        error_color = "#e06c75"
        sistema_color = "#c678dd"
        timestamp_color = "#5c6370" # Un gris para el timestamp en tema claro
        
        if is_black_and_white_theme:
            # Todo el texto es blanco en el tema negro y blanco
            text_color = "#FFFFFF"
            prompt_color = "#FFFFFF"
            command_text_color = "#FFFFFF"
            respuesta_color = "#FFFFFF"
            error_color = "#FFFFFF"
            sistema_color = "#FFFFFF"
            timestamp_color = "#FFFFFF" # Timestamp también blanco

        colors = {
            "prompt": prompt_color,
            "comando_text": command_text_color,
            "respuesta": respuesta_color,
            "error": error_color,
            "sistema": sistema_color,
            "normal": text_color, 
            "timestamp": timestamp_color
        }
        
        # Emojis (se mantienen)
        emojis = {
            "comando": "🗣️", "respuesta": "✔️", "error": "❌", "sistema": "⚙️", "normal": ""
        }
        
        prompt_text = "PS>" # Se mantiene el prompt visualmente
        
        for message, message_type in self.buffer:
            current_timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
            self.setTextColor(QColor(colors["timestamp"]))
            self.insertPlainText(current_timestamp)

            emoji = emojis.get(message_type, "")
            if emoji:
                # Los emojis no tienen color de texto, usan el de la fuente
                self.insertPlainText(f"{emoji} ") 

            if message_type == "comando":
                self.setTextColor(QColor(colors["prompt"]))
                self.insertPlainText(f"{prompt_text} ")
                self.setTextColor(QColor(colors["comando_text"]))
                self.append(message) 
            else:
                prefix_map = {
                    "respuesta": "Respuesta: " if not is_black_and_white_theme else "", # Sin prefijo textual en B&W
                    "error": "Error: " if not is_black_and_white_theme else "",
                    "sistema": "Sistema: " if not is_black_and_white_theme else "",
                    "normal": ""
                }
                prefix = prefix_map.get(message_type, "")
                
                self.setTextColor(QColor(colors.get(message_type, colors["normal"])))
                if prefix: # Solo añadir prefijo si no es tema B&W (para mantener limpieza)
                    self.insertPlainText(prefix)
                self.append(message) 
        
        self.buffer.clear()
        
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        
        if self.document().blockCount() > self.max_buffer:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.Start)
            blocks_to_remove = self.document().blockCount() - self.max_buffer
            if blocks_to_remove > 0:
                 cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, blocks_to_remove)
                 cursor.removeSelectedText()
        
        self.setUpdatesEnabled(True)


# Clase principal que implementa la ventana del asistente de voz
class AsistenteVozQT(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.sistema_operativo = platform.system() 
        self.escuchando = False                    
        self.prefijo_comando = "ejecutar"          
        self.historial_comandos = []               
        self.indice_historial = 0                  
        
        self.ruta_trabajo = os.path.expanduser("~") 
        self.cargar_configuracion()                 
        
        self.setup_ui()
        self.setup_threads()
        
        self.agregar_mensaje("¡Bienvenido al Asistente de Voz!", "sistema")
        self.agregar_mensaje(f"Ruta de trabajo actual: {self.ruta_trabajo}", "sistema")
        self.agregar_mensaje("Escribe un comando o usa la voz.", "sistema")
            
    def setup_ui(self):
        """Configura todos los elementos de la interfaz gráfica"""
        self.setWindowTitle("Asistente de Voz")
        self.setMinimumSize(1000, 700)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.top_bar = QFrame()
        self.top_bar.setObjectName("top_bar") 
        self.top_bar.setMaximumHeight(60)
        
        self.top_layout = QHBoxLayout(self.top_bar)
        
        self.title_label = QLabel("Asistente de Voz")
        self.title_label.setObjectName("title_label")
        self.top_layout.addWidget(self.title_label)
        
        self.theme_button = QPushButton("Tema Claro") 
        self.theme_button.clicked.connect(self.toggle_theme)
        self.top_layout.addWidget(self.theme_button)
        
        self.main_layout.addWidget(self.top_bar)
        
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.main_splitter)
        
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        
        self.console_label = QLabel("Consola de Salida")
        self.console_label.setObjectName("console_label_id")
        self.left_layout.addWidget(self.console_label)
        
        self.consola = ConsoleTextEdit(parent_window=self) # Pasar referencia
        self.left_layout.addWidget(self.consola)
        
        self.command_input_layout = QHBoxLayout()
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Escribe un comando aquí...")
        self.command_input.returnPressed.connect(self.ejecutar_comando_escrito)
        self.command_input.installEventFilter(self)
        
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.ejecutar_comando_escrito)
        
        self.command_input_layout.addWidget(self.command_input)
        self.command_input_layout.addWidget(self.send_button)
        
        self.left_layout.addLayout(self.command_input_layout)
        
        self.right_panel = QWidget()
        self.right_panel.setMaximumWidth(350)
        self.right_panel.setMinimumWidth(250)
        self.right_layout = QVBoxLayout(self.right_panel)
        
        self.voice_control_frame = QFrame()
        self.voice_layout = QVBoxLayout(self.voice_control_frame)
        
        self.voice_label = QLabel("Control de Voz")
        self.voice_label.setObjectName("voice_label_id")
        self.voice_layout.addWidget(self.voice_label)
        
        self.mic_button = QPushButton("Iniciar Escucha")
        self.mic_button.setMinimumHeight(50)
        self.mic_button.clicked.connect(self.toggle_escucha)
        self.voice_layout.addWidget(self.mic_button)
        
        self.audio_level_label = QLabel("Nivel de Audio:")
        self.voice_layout.addWidget(self.audio_level_label)
        
        self.audio_level = QProgressBar()
        self.audio_level.setRange(0, 100)
        self.audio_level.setValue(0)
        self.voice_layout.addWidget(self.audio_level)
        
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
        
        self.path_frame = QFrame()
        self.path_layout = QVBoxLayout(self.path_frame)
        
        self.path_label = QLabel("Ruta de Trabajo")
        self.path_label.setObjectName("path_label_id")
        self.path_layout.addWidget(self.path_label)
        
        self.current_path_label = QLabel(self.ruta_trabajo)
        self.current_path_label.setWordWrap(True)
        self.path_layout.addWidget(self.current_path_label)
        
        self.path_buttons_layout = QHBoxLayout()
        
        self.change_path_button = QPushButton("Cambiar Ruta")
        self.change_path_button.clicked.connect(self.cambiar_ruta_dialogo)
        
        self.use_current_path_button = QPushButton("Usar Actual")
        self.use_current_path_button.clicked.connect(self.usar_ruta_actual)
        
        self.path_buttons_layout.addWidget(self.change_path_button)
        self.path_buttons_layout.addWidget(self.use_current_path_button)
        
        self.path_layout.addLayout(self.path_buttons_layout)
        self.right_layout.addWidget(self.path_frame)
        
        self.commands_frame = QFrame()
        self.commands_layout = QVBoxLayout(self.commands_frame)
        
        self.commands_label = QLabel("Comandos Disponibles")
        self.commands_label.setObjectName("commands_label_id")
        self.commands_layout.addWidget(self.commands_label)
        
        self.commands_list = QTextEdit()
        self.commands_list.setReadOnly(True)
        
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
        
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.right_panel)
        self.main_splitter.setSizes([650, 350]) 
        
        self.status_bar = QLabel(f"Sistema: {platform.system()} {platform.release()} | Ruta: {self.ruta_trabajo}")
        self.main_layout.addWidget(self.status_bar)
        
        # Cargar tema guardado o default a "black_and_white"
        self.current_theme = getattr(self, 'current_theme', "black_and_white")
        self.apply_theme()
        self.update_mic_button_style() 
    
    def setup_threads(self):
        """Configura los hilos para reconocimiento de voz y nivel de audio"""
        self.audio_thread = AudioLevelThread()
        self.audio_thread.level_updated.connect(self.update_audio_level)
        
        self.speech_thread = SpeechRecognitionThread()
        self.speech_thread.command_recognized.connect(self.on_command_recognized)
        self.speech_thread.status_message.connect(self.on_status_message)
    
    def toggle_theme(self):
        """Cambia entre tema claro y negro/blanco"""
        if self.current_theme == "light":
            self.current_theme = "black_and_white"
        else:
            self.current_theme = "light"
        self.apply_theme()
    
    def apply_theme(self):
        """Aplica el tema actual a toda la aplicación"""
        if self.current_theme == "black_and_white":
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: black; 
                    color: white; 
                    font-family: Consolas, Courier, monospace;
                }
                QFrame#top_bar { 
                    background-color: black; 
                    border-bottom: 1px solid #333333; /* Borde sutil para la barra superior */
                    border-radius: 0px;
                }
                QLabel#title_label { 
                    color: white; 
                    font-size: 14pt; 
                    font-weight: bold;
                    padding: 5px;
                }
                QPushButton {
                    background-color: black;
                    color: white;
                    border: 1px solid white; 
                    border-radius: 3px;
                    padding: 8px;
                    font-size: 9pt;
                }
                QPushButton:hover {
                    background-color: #181818; /* Un negro un poco más claro al pasar el mouse */
                    border: 1px solid #CCCCCC; 
                }
                QLineEdit {
                    background-color: black;
                    color: white;
                    border: 1px solid white; 
                    border-radius: 3px;
                    padding: 5px;
                    font-size: 10pt;
                }
                QTextEdit { 
                    background-color: black;
                    color: white;
                    border: 1px solid #333333; /* Borde sutil para áreas de texto */
                    border-radius: 0px; /* Sin bordes redondeados para un look más de terminal */
                    font-size: 10pt;
                }
                QProgressBar {
                    border: 1px solid white;
                    border-radius: 3px;
                    background-color: black;
                    text-align: center;
                    color: white;
                }
                QProgressBar::chunk {
                    background-color: white; 
                    border-radius: 2px;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #333333; height: 8px; background: black;
                    margin: 2px 0; border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: white; border: 1px solid white;
                    width: 18px; margin: -2px 0; border-radius: 9px;
                }
                QLabel { 
                    color: white;
                    font-size: 9pt;
                }
                QLabel#console_label_id, QLabel#voice_label_id, QLabel#path_label_id, QLabel#commands_label_id {
                     font-weight: bold; font-size: 11pt; color: white;
                }
                QFrame { /* Estilo para paneles laterales y otros frames */
                    background-color: black; 
                    border-radius: 0px; 
                    padding: 5px;
                    border: 1px solid #333333; /* Borde sutil */
                }
                QSplitter::handle {
                    background-color: #333333; /* Manija del splitter */
                }
                QSplitter::handle:hover {
                    background-color: #555555;
                }
            """)
            # Asegurar que la consola principal también siga el tema
            self.consola.setStyleSheet("background-color: black; color: white; font-family: Consolas, Courier, monospace; font-size: 10pt; border: none;")
            self.commands_list.setStyleSheet("background-color: black; color: white; border: 1px solid #333333; font-family: Consolas, Courier, monospace; padding:5px;")
            self.current_path_label.setStyleSheet("padding: 5px; background-color: black; border: 1px solid #333333; color: white;")
            self.status_bar.setStyleSheet("background-color: black; color: white; padding: 5px; border-top: 1px solid #333333;")
            self.theme_button.setText("Tema Claro")

        else: # Light Theme (Original)
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #F0F0F0; color: #333333;
                    font-family: Segoe UI, Arial, sans-serif;
                }
                QFrame#top_bar {
                    background-color: #3498db; border-radius: 5px; border: none;
                }
                QLabel#title_label {
                    color: white; font-size: 18px; font-weight: bold;
                }
                QPushButton {
                    background-color: #E0E0E0; color: #333333;
                    border: 1px solid #C0C0C0; border-radius: 3px;
                    padding: 8px; font-size: 9pt;
                }
                QPushButton:hover {
                    background-color: #D0D0D0; border: 1px solid #B0B0B0;
                }
                QLineEdit {
                    background-color: #FFFFFF; color: #333333;
                    border: 1px solid #C0C0C0; border-radius: 3px;
                    padding: 5px; font-size: 10pt;
                }
                QTextEdit { 
                    background-color: #FFFFFF; color: #333333;
                    border: 1px solid #C0C0C0; border-radius: 3px;
                }
                QProgressBar {
                    border: 1px solid #bdc3c7; border-radius: 3px;
                    background-color: #f0f0f0; text-align: center; color: #333333;
                }
                QProgressBar::chunk { background-color: #3498db; border-radius: 2px; }
                QSlider::groove:horizontal {
                    border: 1px solid #cccccc; height: 8px; background: #e0e0e0;
                    margin: 2px 0; border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #3498db; border: 1px solid #cccccc;
                    width: 18px; margin: -2px 0; border-radius: 9px;
                }
                QLabel { color: #333333; font-size: 9pt; }
                QLabel#console_label_id, QLabel#voice_label_id, QLabel#path_label_id, QLabel#commands_label_id {
                     font-weight: bold; font-size: 12pt; color: #2c3e50; 
                }
                QFrame { 
                    background-color: #F8F8F8; border-radius: 5px;
                    padding: 5px; border: 1px solid #E0E0E0;
                }
                QSplitter::handle { background-color: #D0D0D0; }
                QSplitter::handle:hover { background-color: #C0C0C0; }
            """)
            self.consola.setStyleSheet("""
                QTextEdit {
                    background-color: #282c34; color: #abb2bf; /* Estilo original de consola para tema claro */
                    font-family: Consolas, Courier, monospace; font-size: 10pt;
                    border-radius: 5px; padding: 5px; border: 1px solid #202328;
                }
            """)
            self.commands_list.setStyleSheet("background-color: #FFFFFF; color: #333333; border-radius: 3px; border: 1px solid #C0C0C0; padding: 5px;")
            self.current_path_label.setStyleSheet("padding: 5px; background-color: #FFFFFF; border: 1px solid #C0C0C0; border-radius: 3px; color: #333333;")
            self.status_bar.setStyleSheet("background-color: #E0E0E0; color: #333333; padding: 5px; border-top: 1px solid #C0C0C0;")
            self.theme_button.setText("Tema Negro/Blanco")
            # Restaurar estilos específicos de botones para tema claro
            self.send_button.setStyleSheet("""
                QPushButton { background-color: #2ecc71; color: white; border-radius: 5px; padding: 5px 15px;}
                QPushButton:hover { background-color: #27ae60; }
            """)
            self.change_path_button.setStyleSheet("""
                 QPushButton { background-color: #3498db; color: white; border-radius: 5px; padding: 5px;}
                 QPushButton:hover { background-color: #2980b9; }
            """)
            self.use_current_path_button.setStyleSheet("""
                 QPushButton { background-color: #3498db; color: white; border-radius: 5px; padding: 5px;}
                 QPushButton:hover { background-color: #2980b9; }
            """)
        self.update_mic_button_style()
        self.consola.flush_buffer() # Refrescar colores de la consola

    def update_mic_button_style(self):
        """Actualiza el estilo del botón del micrófono según el estado de escucha y el tema."""
        if self.current_theme == "black_and_white":
            border_color = "#555555" if not self.escuchando else "#FFFFFF" # Borde más brillante si está escuchando
            self.mic_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: black; 
                    color: white; 
                    border-radius: 3px; 
                    padding: 10px; 
                    font-size: 9pt;
                    border: 1px solid {border_color}; 
                }} 
                QPushButton:hover {{ background-color: #181818; border: 1px solid white; }}
            """)
        else: # Light theme
            if self.escuchando:
                self.mic_button.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c; color: white; border-radius: 5px; padding: 10px; font-size: 14px;
                    } QPushButton:hover { background-color: #c0392b; }
                """)
            else:
                self.mic_button.setStyleSheet("""
                    QPushButton {
                        background-color: #2ecc71; color: white; border-radius: 5px; padding: 10px; font-size: 14px;
                    } QPushButton:hover { background-color: #27ae60; }
                """)
    
    def eventFilter(self, source, event):
        """Captura eventos de teclado para navegación en historial"""
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
        """Actualiza el indicador visual de nivel de audio"""
        self.audio_level.setValue(int(level * 100))
    
    @pyqtSlot(str)
    def on_command_recognized(self, command):
        """Maneja un comando reconocido por voz"""
        self.agregar_mensaje(command, "comando")
        
        self.historial_comandos.append(command)
        self.indice_historial = len(self.historial_comandos)
        
        if hasattr(self, 'speech_thread'):
            self.speech_thread.pause()
            
        QTimer.singleShot(0, lambda cmd=command: self.procesar_comando_seguro(cmd))
    
    def procesar_comando_seguro(self, comando):
        """Procesa el comando de forma segura y reanuda reconocimiento al terminar"""
        try:
            self.procesar_comando(comando)
        except Exception as e:
            self.agregar_mensaje(f"Error al procesar comando: {str(e)}", "error")
        finally:
            if hasattr(self, 'speech_thread') and self.speech_thread.isRunning(): 
                self.speech_thread.resume()
    
    @pyqtSlot(str)
    def on_status_message(self, message):
        """Actualiza la barra de estado con mensajes del reconocedor"""
        base_status = f"Sistema: {platform.system()} {platform.release()} | Ruta: {self.ruta_trabajo}"
        self.status_bar.setText(f"{base_status} | Estado: {message}")
    
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
                    # Cargar tema guardado, default a "black_and_white"
                    self.current_theme = config.get('theme', 'black_and_white') 
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
            self.current_theme = "black_and_white" # Default en caso de error

    def guardar_configuracion(self):
        """Guarda la configuración actual"""
        config_path = os.path.join(os.path.expanduser("~"), ".asistente_voz_qt_config.json")
        try:
            config = {
                'ruta_trabajo': self.ruta_trabajo,
                'theme': self.current_theme 
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
        self.update_mic_button_style() 
    
    def iniciar_escucha(self):
        """Inicia la escucha de voz"""
        self.escuchando = True
        self.mic_button.setText("Detener Escucha")
        self.agregar_mensaje("Escucha iniciada. Di un comando...", "sistema")
        
        if not self.audio_thread.isRunning():
            self.audio_thread.start()
        if not self.speech_thread.isRunning():
            self.speech_thread.start()
    
    def detener_escucha(self):
        """Detiene la escucha de voz"""
        self.escuchando = False
        self.mic_button.setText("Iniciar Escucha")
        self.agregar_mensaje("Escucha detenida", "sistema")
        self.audio_level.setValue(0)
        
        if self.audio_thread.isRunning():
            self.audio_thread.stop()
        if self.speech_thread.isRunning():
            self.speech_thread.stop()
    
    def cambiar_ruta_dialogo(self):
        """Abre un diálogo para seleccionar la nueva ruta de trabajo"""
        nueva_ruta = QFileDialog.getExistingDirectory(self, "Seleccionar Ruta de Trabajo", self.ruta_trabajo)
        if nueva_ruta: 
            self.cambiar_ruta_trabajo(nueva_ruta)
    
    def usar_ruta_actual(self):
        """Establece el directorio actual como ruta de trabajo"""
        self.cambiar_ruta_trabajo(os.getcwd())
    
    def cambiar_ruta_trabajo(self, nueva_ruta):
        """Cambia la ruta de trabajo para la creación de archivos y carpetas"""
        try:
            if os.path.exists(nueva_ruta) and os.path.isdir(nueva_ruta):
                self.ruta_trabajo = nueva_ruta
                self.current_path_label.setText(self.ruta_trabajo)
                self.on_status_message(self.status_bar.text().split("| Estado:")[-1].strip()) 
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
            self.historial_comandos.append(comando)
            self.indice_historial = len(self.historial_comandos)
            
            self.agregar_mensaje(comando, "comando")
            self.procesar_comando_seguro(comando.lower())
            self.command_input.clear()
    
    def agregar_mensaje(self, mensaje, tipo="normal"):
        """Agrega un mensaje a la consola"""
        self.consola.append_message(mensaje, tipo)
    
    def ejecutar_comando_terminal(self, comando_str):
        """Ejecuta un comando en la terminal del sistema y devuelve (mensaje, tipo_mensaje)"""
        try:
            proceso = subprocess.Popen(
                comando_str, 
                shell=True, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.ruta_trabajo, 
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            try:
                stdout, stderr = proceso.communicate(timeout=15) 
                
                if proceso.returncode == 0:
                    if len(stdout) > 5000: 
                        stdout = stdout[:5000] + "\n...(resultado truncado)..."
                    return f"Resultado:\n{stdout}", "normal" 
                else:
                    if len(stderr) > 2000:
                        stderr = stderr[:2000] + "\n...(error truncado)..."
                    return f"Error (código {proceso.returncode}):\n{stderr}", "error"
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.communicate() 
                return "Error: Comando cancelado (timeout > 15s).", "error"
                
        except PermissionError:
            return "Error: Permisos insuficientes.", "error"
        except FileNotFoundError:
            return f"Error: Comando '{comando_str.split()[0]}' no encontrado.", "error"
        except Exception as e:
            return f"Excepción al ejecutar: {str(e)}", "error"

    def procesar_comando(self, texto):
        """Procesa el comando de voz y ejecuta la acción correspondiente"""
        # Salir de la aplicación
        if "salir" in texto or "terminar" in texto or "adiós" in texto or "adios" in texto:
            self.agregar_mensaje("Cerrando asistente...", "sistema")
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
                    else:
                        self.agregar_mensaje("No se especificó una ruta válida.", "error")
                    return
            self.agregar_mensaje("No se especificó una ruta válida.", "error")
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
                            ruta_completa = os.path.join(self.ruta_trabajo, nombre_carpeta)
                            os.makedirs(ruta_completa, exist_ok=True)
                            self.agregar_mensaje(f"Carpeta creada: {ruta_completa}", "respuesta")
                        except Exception as e:
                            self.agregar_mensaje(f"Error al crear carpeta: {str(e)}", "error")
                    else:
                        self.agregar_mensaje("No se especificó nombre para la carpeta.", "error")
                    return
        
        # Ejecutar comando directo de terminal
        elif texto.startswith(self.prefijo_comando):
            comando_terminal_str = texto[len(self.prefijo_comando):].strip()
            self.agregar_mensaje(f"Ejecutando: {comando_terminal_str}", "sistema")
            resultado, tipo_resultado = self.ejecutar_comando_terminal(comando_terminal_str)
            self.agregar_mensaje(resultado, tipo_resultado)
            return
        
        # Listar archivos y directorios
        elif "listar" in texto or "mostrar archivos" in texto or "mostrar directorio" in texto:
            comando_ls = "dir" if self.sistema_operativo == "Windows" else "ls -la"
            resultado, tipo_resultado = self.ejecutar_comando_terminal(comando_ls)
            self.agregar_mensaje(resultado, tipo_resultado)
            return
        
        # Cambiar de directorio
        elif "cambiar directorio" in texto or "ir a directorio" in texto:
            partes = texto.split(" a ")
            if len(partes) > 1:
                directorio_str = partes[1].strip()
                directorio_destino = os.path.join(os.getcwd(), directorio_str) if not os.path.isabs(directorio_str) else directorio_str
                try:
                    os.chdir(directorio_destino) 
                    self.ruta_trabajo = os.getcwd() 
                    self.current_path_label.setText(self.ruta_trabajo)
                    self.on_status_message(self.status_bar.text().split("| Estado:")[-1].strip())
                    self.agregar_mensaje(f"Directorio cambiado a: {os.getcwd()}", "respuesta")
                except FileNotFoundError:
                    self.agregar_mensaje(f"Directorio '{directorio_destino}' no encontrado.", "error")
                except Exception as e:
                    self.agregar_mensaje(f"Error al cambiar directorio: {str(e)}", "error")
            else:
                self.agregar_mensaje("No se especificó un directorio.", "error")
            return
        
        # Mostrar directorio actual
        elif "directorio actual" in texto or "dónde estoy" in texto:
            self.agregar_mensaje(f"Directorio CWD: {os.getcwd()}", "respuesta")
            self.agregar_mensaje(f"Ruta de trabajo: {self.ruta_trabajo}", "respuesta")
            return
            
        # Apagar sistema
        elif "apagar sistema" in texto or "apagar computadora" in texto:
            QTimer.singleShot(0, lambda: self.confirmar_apagado(texto))
            return
                
        # Cancelar apagado
        elif "cancelar apagado" in texto:
            comando_cancelar = "shutdown /a" if self.sistema_operativo == "Windows" else "shutdown -c"
            resultado, tipo_resultado = self.ejecutar_comando_terminal(comando_cancelar)
            if tipo_resultado != "error":
                 self.agregar_mensaje("Cancelación de apagado solicitada.", "respuesta")
            else:
                 self.agregar_mensaje(f"No se pudo cancelar apagado: {resultado}", "error")
            return
            
        # Crear archivo
        elif "crear archivo" in texto:
            partes = texto.split("crear archivo")
            if len(partes) > 1:
                nombre_archivo = partes[1].strip()
                if nombre_archivo:
                    try:
                        ruta_completa = os.path.join(self.ruta_trabajo, nombre_archivo)
                        with open(ruta_completa, 'w') as f: pass
                        self.agregar_mensaje(f"Archivo creado: {ruta_completa}", "respuesta")
                    except Exception as e:
                        self.agregar_mensaje(f"Error al crear archivo: {str(e)}", "error")
                else:
                    self.agregar_mensaje("No se especificó nombre de archivo.", "error")
            else:
                self.agregar_mensaje("No se especificó nombre de archivo.", "error")
            return
                
        # Eliminar archivo
        elif "eliminar archivo" in texto or "borrar archivo" in texto:
            for palabra_clave_del in ["eliminar archivo", "borrar archivo"]:
                if palabra_clave_del in texto:
                    partes = texto.split(palabra_clave_del)
                    if len(partes) > 1:
                        nombre_archivo_del = partes[1].strip()
                        if nombre_archivo_del:
                            ruta_completa_del = os.path.join(self.ruta_trabajo, nombre_archivo_del) if not os.path.isabs(nombre_archivo_del) else nombre_archivo_del
                            if not os.path.exists(ruta_completa_del):
                                self.agregar_mensaje(f"Error: Archivo {ruta_completa_del} no existe.", "error")
                                return
                            QTimer.singleShot(0, lambda rc=ruta_completa_del: self.confirmar_eliminacion(rc))
                            return
            self.agregar_mensaje("No se especificó archivo a eliminar.", "error")
            return
            
        # Mostrar información del sistema
        elif "información del sistema" in texto or "info sistema" in texto:
            info = f"OS: {platform.system()} {platform.release()}\nVer: {platform.version()}\nArch: {platform.machine()}\nProc: {platform.processor()}\nHost: {platform.node()}"
            self.agregar_mensaje(info, "respuesta")
            return
            
        # Mostrar hora actual
        elif "hora" in texto or "qué hora es" in texto:
            self.agregar_mensaje(f"Son las {datetime.datetime.now().strftime('%H:%M:%S')}", "respuesta")
            return
            
        # Mostrar fecha actual
        elif "fecha" in texto or "qué día es" in texto or "qué fecha es" in texto:
            self.agregar_mensaje(f"Hoy es {datetime.datetime.now().strftime('%d/%m/%Y')}", "respuesta")
            return
            
        # Abrir navegador web
        elif "abrir navegador" in texto or "abrir web" in texto:
            try:
                webbrowser.open("https://www.google.com")
                self.agregar_mensaje("Abriendo navegador...", "respuesta")
            except Exception as e:
                self.agregar_mensaje(f"No se pudo abrir navegador: {e}", "error")
            return
            
        # Buscar en Google
        elif "buscar" in texto:
            busqueda = texto.replace("buscar", "").strip()
            if busqueda:
                try:
                    url = f"https://www.google.com/search?q={busqueda.replace(' ', '+')}"
                    webbrowser.open(url)
                    self.agregar_mensaje(f"Buscando '{busqueda}'...", "respuesta")
                except Exception as e:
                    self.agregar_mensaje(f"No se pudo buscar: {e}", "error")
            else:
                self.agregar_mensaje("No se especificó qué buscar.", "error")
            return
                
        # Mostrar procesos en ejecución
        elif "mostrar procesos" in texto or "procesos en ejecución" in texto:
            comando_proc = "tasklist" if self.sistema_operativo == "Windows" else "ps aux"
            resultado, tipo_resultado = self.ejecutar_comando_terminal(comando_proc)
            self.agregar_mensaje(resultado, tipo_resultado)
            return
                
        # Mostrar uso de memoria
        elif "uso de memoria" in texto or "memoria" in texto:
            comando_mem = "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value" if self.sistema_operativo == "Windows" else "free -h"
            resultado, tipo_resultado = self.ejecutar_comando_terminal(comando_mem)
            self.agregar_mensaje(resultado, tipo_resultado)
            return
                
        # Mostrar uso de disco
        elif "uso de disco" in texto or "espacio en disco" in texto:
            comando_disk = "wmic logicaldisk get caption,freespace,size /format:table" if self.sistema_operativo == "Windows" else "df -h"
            resultado, tipo_resultado = self.ejecutar_comando_terminal(comando_disk)
            self.agregar_mensaje(resultado, tipo_resultado)
            return
                
        # Mostrar conexiones de red
        elif "conexiones de red" in texto or "mostrar conexiones" in texto:
            comando_net = "netstat -an" if self.sistema_operativo == "Windows" else "netstat -tulnp"
            resultado, tipo_resultado = self.ejecutar_comando_terminal(comando_net)
            self.agregar_mensaje(resultado, tipo_resultado)
            return
        
        else:
            self.agregar_mensaje(f"Comando no reconocido: '{texto}'.", "error")
            return
            
    def confirmar_eliminacion(self, ruta_completa):
        """Muestra diálogo de confirmación para eliminar un archivo"""
        confirmacion = QMessageBox.question(
            self, "Confirmar Eliminación", 
            f"¿Seguro que deseas eliminar {ruta_completa}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirmacion == QMessageBox.Yes:
            try:
                os.remove(ruta_completa)
                self.agregar_mensaje(f"Archivo eliminado: {ruta_completa}", "respuesta")
            except Exception as e:
                self.agregar_mensaje(f"Error al eliminar: {str(e)}", "error")
        else:
            self.agregar_mensaje("Eliminación cancelada.", "sistema")
            
    def confirmar_apagado(self, texto):
        """Muestra diálogo de confirmación para apagar el sistema"""
        confirmacion = QMessageBox.question(
            self, "Confirmar Apagado", 
            "¿Seguro que deseas apagar el sistema?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirmacion == QMessageBox.Yes:
            comando_apagar = "shutdown /s /t 60" if self.sistema_operativo == "Windows" else "shutdown -h +1"
            resultado, tipo_resultado = self.ejecutar_comando_terminal(comando_apagar)
            if tipo_resultado != "error":
                msg = "Apagando sistema en 60s (Win) o 1m (Lin/Mac)."
                self.agregar_mensaje(f"{msg} Cancela con 'cancelar apagado'", "respuesta")
            else:
                self.agregar_mensaje(f"Error al programar apagado: {resultado}", "error")
        else:
            self.agregar_mensaje("Apagado cancelado.", "sistema")
    
    def closeEvent(self, event):
        """Maneja el evento de cierre de ventana"""
        self.guardar_configuracion()
        
        try:
            if hasattr(self, 'audio_thread') and self.audio_thread.isRunning():
                self.audio_thread.stop()
                if not self.audio_thread.wait(500): self.audio_thread.terminate() 
        except Exception as e: print(f"Error al detener audio_thread: {e}")
            
        try:
            if hasattr(self, 'speech_thread') and self.speech_thread.isRunning():
                self.speech_thread.stop()
                if not self.speech_thread.wait(500): self.speech_thread.terminate() 
        except Exception as e: print(f"Error al detener speech_thread: {e}")
        
        if hasattr(self, 'consola') and hasattr(self.consola, 'buffer_timer'):
            self.consola.buffer_timer.stop()
        
        event.accept()

# Función principal para iniciar la aplicación
def main():
    if platform.system() == 'Windows':
        try:
            from ctypes import windll
            try: windll.shcore.SetProcessDpiAwareness(1)
            except AttributeError: windll.user32.SetProcessDPIAware()
        except Exception as e: print(f"Advertencia DPI: {e}")
    
    app = QApplication(sys.argv)
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        import traceback
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"Error no capturado:\n{error_msg}")
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error Crítico")
        msg_box.setText(f"Error:\n{exc_type.__name__}: {exc_value}")
        msg_box.setDetailedText(error_msg)
        msg_box.exec_()
        
    sys.excepthook = handle_exception
    
    try:
        window = AsistenteVozQT()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        import traceback
        error_msg_init = f"Error al iniciar: {str(e)}\n\n{traceback.format_exc()}"
        print(error_msg_init)
        msg_box = QMessageBox(); msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error de Inicialización"); msg_box.setText(f"Error al iniciar: {str(e)}")
        msg_box.setDetailedText(traceback.format_exc()); msg_box.exec_()
        sys.exit(1)

# Punto de entrada de la aplicación
if __name__ == "__main__":
    main()
