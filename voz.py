import speech_recognition as sr
import os
import subprocess
import platform
import webbrowser
import datetime
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, ttk
import queue

class AsistenteVozGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Asistente de Voz")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Variables para configuración
        self.sistema_operativo = platform.system()
        self.escuchando = False
        self.cola_mensajes = queue.Queue()
        self.prefijo_comando = "ejecutar"
        
        # Configuración del reconocedor de voz
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 4000
        
        # Crear y configurar la interfaz
        self.crear_interfaz()
        
        # Iniciar el hilo para actualizar la interfaz
        self.actualizar_interfaz()
    
    def crear_interfaz(self):
        """Crea todos los elementos de la interfaz gráfica"""
        # Usar un estilo moderno
        style = ttk.Style()
        if self.sistema_operativo == "Windows":
            style.theme_use("vista")
        else:
            style.theme_use("clam")
        
        # Marco principal con dos paneles
        panel_principal = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        panel_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Panel izquierdo - Consola de salida
        frame_consola = ttk.LabelFrame(panel_principal, text="Consola de Salida")
        panel_principal.add(frame_consola, weight=3)
        
        # Panel derecho - Controles y Comandos
        frame_controles = ttk.LabelFrame(panel_principal, text="Controles")
        panel_principal.add(frame_controles, weight=1)
        
        # Configurar área de texto para consola
        self.consola = scrolledtext.ScrolledText(frame_consola, wrap=tk.WORD, bg="#282c34", fg="#abb2bf", font=("Consolas", 10))
        self.consola.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.consola.config(state=tk.DISABLED)
        
        # Configurar controles
        frame_botones = ttk.Frame(frame_controles)
        frame_botones.pack(fill=tk.X, padx=5, pady=10)
        
        # Botón para iniciar/detener escucha
        self.btn_escuchar = ttk.Button(
            frame_botones, 
            text="🎤 Iniciar Escucha", 
            command=self.toggle_escucha
        )
        self.btn_escuchar.pack(fill=tk.X, pady=5)
        
        # Indicador de estado
        self.lbl_estado = ttk.Label(
            frame_botones, 
            text="Estado: Inactivo", 
            background="#e74c3c", 
            foreground="white",
            anchor=tk.CENTER
        )
        self.lbl_estado.pack(fill=tk.X, pady=5)
        
        # Configuración de sensibilidad
        frame_sensibilidad = ttk.LabelFrame(frame_controles, text="Sensibilidad del micrófono")
        frame_sensibilidad.pack(fill=tk.X, pady=10, padx=5)
        
        self.sensibilidad = tk.DoubleVar(value=4000)
        escala_sensibilidad = ttk.Scale(
            frame_sensibilidad, 
            from_=1000, 
            to=8000, 
            orient=tk.HORIZONTAL,
            variable=self.sensibilidad,
            command=self.actualizar_sensibilidad
        )
        escala_sensibilidad.pack(fill=tk.X, pady=5, padx=5)
        
        self.lbl_valor_sensibilidad = ttk.Label(
            frame_sensibilidad, 
            text="4000", 
            anchor=tk.CENTER
        )
        self.lbl_valor_sensibilidad.pack(pady=5)
        
        # Lista de comandos disponibles
        frame_comandos = ttk.LabelFrame(frame_controles, text="Comandos Disponibles")
        frame_comandos.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        comandos_lista = [
            "🔊 'ejecutar [comando]' - Ejecuta comando de terminal",
            "📂 'listar' o 'mostrar archivos' - Lista directorios",
            "📁 'directorio actual' - Muestra ruta actual",
            "🔄 'cambiar directorio a [ruta]' - Cambia de directorio",
            "📝 'crear archivo [nombre]' - Crea un archivo",
            "❌ 'eliminar archivo [nombre]' - Borra un archivo",
            "💻 'información del sistema' - Muestra datos del sistema",
            "🕒 'hora' o 'qué hora es' - Muestra la hora actual",
            "📅 'fecha' o 'qué día es' - Muestra la fecha actual",
            "🌐 'abrir navegador' - Abre navegador predeterminado",
            "🔍 'buscar [término]' - Busca en Google",
            "📊 'mostrar procesos' - Lista procesos en ejecución",
            "💾 'uso de memoria' - Muestra uso de memoria RAM",
            "💿 'uso de disco' - Muestra espacio en disco",
            "🔌 'conexiones de red' - Muestra conexiones activas",
            "🔚 'salir' o 'terminar' - Cierra la aplicación"
        ]
        
        lista_comandos = ttk.Treeview(frame_comandos, show="tree")
        lista_comandos.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        for i, comando in enumerate(comandos_lista):
            lista_comandos.insert("", i, text=comando)
        
        # Barra de estado
        self.barra_estado = ttk.Label(
            self.root, 
            text=f"Sistema: {platform.system()} {platform.release()} | Asistente de Voz v1.0", 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.barra_estado.pack(side=tk.BOTTOM, fill=tk.X)
        
    def toggle_escucha(self):
        """Activa o desactiva la escucha por voz"""
        if self.escuchando:
            self.escuchando = False
            self.btn_escuchar.config(text="🎤 Iniciar Escucha")
            self.lbl_estado.config(text="Estado: Inactivo", background="#e74c3c")
            self.agregar_mensaje("Sistema: Escucha detenida", "sistema")
        else:
            self.escuchando = True
            self.btn_escuchar.config(text="⏹️ Detener Escucha")
            self.lbl_estado.config(text="Estado: Escuchando...", background="#2ecc71")
            self.agregar_mensaje("Sistema: Escucha iniciada. Di un comando...", "sistema")
            
            # Iniciar escucha en un hilo separado
            threading.Thread(target=self.escuchar_en_bucle, daemon=True).start()
    
    def actualizar_sensibilidad(self, *args):
        """Actualiza el valor de sensibilidad del micrófono"""
        valor = int(self.sensibilidad.get())
        self.lbl_valor_sensibilidad.config(text=str(valor))
        self.recognizer.energy_threshold = valor
    
    def agregar_mensaje(self, mensaje, tipo="normal"):
        """Agrega un mensaje a la cola para ser mostrado en la consola"""
        # Los tipos pueden ser: normal, comando, respuesta, error, sistema
        self.cola_mensajes.put((mensaje, tipo))
    
    def actualizar_interfaz(self):
        """Actualiza la interfaz con los mensajes en cola"""
        try:
            while not self.cola_mensajes.empty():
                mensaje, tipo = self.cola_mensajes.get_nowait()
                
                self.consola.config(state=tk.NORMAL)
                
                # Configurar colores según el tipo de mensaje
                if tipo == "comando":
                    self.consola.insert(tk.END, "🗣️ ", "emoji")
                    self.consola.insert(tk.END, f"Comando: {mensaje}\n", "comando")
                elif tipo == "respuesta":
                    self.consola.insert(tk.END, "🤖 ", "emoji")
                    self.consola.insert(tk.END, f"Respuesta: {mensaje}\n", "respuesta")
                elif tipo == "error":
                    self.consola.insert(tk.END, "❌ ", "emoji")
                    self.consola.insert(tk.END, f"Error: {mensaje}\n", "error")
                elif tipo == "sistema":
                    self.consola.insert(tk.END, "🖥️ ", "emoji")
                    self.consola.insert(tk.END, f"{mensaje}\n", "sistema")
                else:
                    self.consola.insert(tk.END, f"{mensaje}\n")
                
                # Configurar etiquetas de colores
                self.consola.tag_config("comando", foreground="#61afef")
                self.consola.tag_config("respuesta", foreground="#98c379")
                self.consola.tag_config("error", foreground="#e06c75")
                self.consola.tag_config("sistema", foreground="#c678dd")
                self.consola.tag_config("emoji", foreground="#e5c07b")
                
                self.consola.config(state=tk.DISABLED)
                self.consola.see(tk.END)
        except Exception as e:
            print(f"Error al actualizar interfaz: {e}")
        
        # Programar la próxima actualización
        self.root.after(100, self.actualizar_interfaz)
    
    def escuchar_en_bucle(self):
        """Función para escuchar comandos de voz en un bucle"""
        while self.escuchando:
            comando = self.escuchar_comando()
            if comando:
                # Procesar el comando en un hilo separado
                threading.Thread(target=self.procesar_comando, args=(comando,), daemon=True).start()
    
    def escuchar_comando(self):
        """Escucha un comando de voz y lo devuelve como texto"""
        try:
            with sr.Microphone() as source:
                self.agregar_mensaje("Escuchando...", "sistema")
                self.barra_estado.config(text="Escuchando...")
                
                # Ajustar para el ruido ambiente
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                try:
                    # Escuchar audio
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    
                    # Reconocer el comando
                    self.agregar_mensaje("Procesando comando...", "sistema")
                    self.barra_estado.config(text="Procesando...")
                    
                    texto = self.recognizer.recognize_google(audio, language="es-ES")
                    self.agregar_mensaje(texto, "comando")
                    
                    self.barra_estado.config(text=f"Sistema: {platform.system()} {platform.release()} | Asistente de Voz v1.0")
                    return texto.lower()
                    
                except sr.WaitTimeoutError:
                    self.barra_estado.config(text=f"Sistema: {platform.system()} {platform.release()} | Asistente de Voz v1.0")
                    return ""
                    
        except sr.UnknownValueError:
            self.agregar_mensaje("No se pudo entender el comando", "error")
            self.barra_estado.config(text=f"Sistema: {platform.system()} {platform.release()} | Asistente de Voz v1.0")
            return ""
            
        except sr.RequestError as e:
            self.agregar_mensaje(f"Error de servicio: {e}", "error")
            self.barra_estado.config(text=f"Sistema: {platform.system()} {platform.release()} | Asistente de Voz v1.0")
            return ""
            
        except Exception as e:
            self.agregar_mensaje(f"Error: {str(e)}", "error")
            self.barra_estado.config(text=f"Sistema: {platform.system()} {platform.release()} | Asistente de Voz v1.0")
            return ""
    
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
            self.escuchando = False
            self.btn_escuchar.config(text="🎤 Iniciar Escucha")
            self.lbl_estado.config(text="Estado: Inactivo", background="#e74c3c")
            self.root.after(1000, self.root.destroy)
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
            if self.sistema_operativo == "Windows":
                resultado = self.ejecutar_comando_terminal("dir")
            else:  # Linux/Mac
                resultado = self.ejecutar_comando_terminal("ls -la")
            self.agregar_mensaje(resultado, "respuesta")
            return
        
        # Cambiar de directorio
        elif "cambiar directorio" in texto or "ir a directorio" in texto:
            partes = texto.split(" a ")
            if len(partes) > 1:
                directorio = partes[1].strip()
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
            return
            
        # Apagar sistema
        elif "apagar sistema" in texto or "apagar computadora" in texto:
            if self.sistema_operativo == "Windows":
                os.system("shutdown /s /t 60")
                self.agregar_mensaje("Apagando el sistema en 60 segundos. Para cancelar di 'cancelar apagado'", "respuesta")
            else:  # Linux/Mac
                os.system("shutdown -h +1")
                self.agregar_mensaje("Apagando el sistema en 1 minuto", "respuesta")
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
                    with open(nombre_archivo, 'w') as f:
                        pass
                    self.agregar_mensaje(f"Archivo creado: {nombre_archivo}", "respuesta")
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
                        try:
                            os.remove(nombre_archivo)
                            self.agregar_mensaje(f"Archivo eliminado: {nombre_archivo}", "respuesta")
                        except Exception as e:
                            self.agregar_mensaje(f"Error al eliminar archivo: {str(e)}", "error")
                    return
            self.agregar_mensaje("No se especificó un nombre de archivo", "error")
            return
            
        # Mostrar información del sistema
        elif "información del sistema" in texto or "información sistema" in texto:
            info = f"Sistema operativo: {platform.system()} {platform.release()}\n"
            info += f"Versión: {platform.version()}\n"
            info += f"Arquitectura: {platform.machine()}\n"
            info += f"Procesador: {platform.processor()}"
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

# Función principal para iniciar la aplicación
def main():
    root = tk.Tk()
    app = AsistenteVozGUI(root)
    
    # Mensaje de bienvenida
    app.agregar_mensaje("¡Bienvenido al Asistente de Voz para Escritorio!", "sistema")
    app.agregar_mensaje("Presiona el botón 'Iniciar Escucha' para comenzar a usar comandos de voz.", "sistema")
    
    root.mainloop()

if __name__ == "__main__":
    main()