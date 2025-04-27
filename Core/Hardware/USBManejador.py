import os
import logging
import shutil
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from Core.System.ErrorHandler import ErrorHandler

class USBEHandler(FileSystemEventHandler):
    def on_created(self, event):
        if 'usb' in event.src_path.lower() or 'removable' in event.src_path.lower():
            USBManejador._copiar_pendientes()

class USBManejador:
    _observer = None
    _pendientes_dir = "pendientes_usb"
    
    @staticmethod
    def inicializar_monitoreo():
        USBManejador._observer = Observer()
        USBManejador._observer.schedule(USBEHandler(), path='D:\\', recursive=False)
        USBManejador._observer.start()
        os.makedirs(USBManejador._pendientes_dir, exist_ok=True)

    @staticmethod
    def guardar_en_usb(contenido: str, nombre_base: str) -> bool:
        try:
            ruta_usb = USBManejador.detectar_usb()
            fecha_actual = datetime.now().strftime("%Y%m%d")
            nombre_archivo = f"{fecha_actual}_{nombre_base}.txt"
            
            if ruta_usb:
                ruta_completa = os.path.join(ruta_usb, nombre_archivo)
                with open(ruta_completa, 'a', encoding='utf-8') as f:
                    f.write(contenido + "\n")
                logging.info(f"Append exitoso en USB: {nombre_archivo}")
                return True
            else:
                ruta_local = os.path.join(USBManejador._pendientes_dir, nombre_archivo)
                with open(ruta_local, 'a', encoding='utf-8') as f:
                    f.write(contenido + "\n")
                logging.warning(f"Guardado local: {ruta_local}")
                return False
        except Exception as e:
            ErrorHandler().log_error("015", f"Error USB: {str(e)}")
            return False

    @staticmethod
    def _copiar_pendientes():
        ruta_usb = USBManejador.detectar_usb()
        if not ruta_usb:
            return

        for archivo in os.listdir(USBManejador._pendientes_dir):
            ruta_origen = os.path.join(USBManejador._pendientes_dir, archivo)
            ruta_destino = os.path.join(ruta_usb, archivo)
            
            try:
                if os.path.exists(ruta_destino):
                    with open(ruta_origen, 'r', encoding='utf-8') as f_origen:
                        contenido = f_origen.read()
                    with open(ruta_destino, 'a', encoding='utf-8') as f_destino:
                        f_destino.write(contenido)
                else:
                    shutil.copy(ruta_origen, ruta_destino)
                os.remove(ruta_origen)
                logging.info(f"Copiado pendiente: {archivo}")
            except Exception as e:
                ErrorHandler().log_error("015", f"Error copiando {archivo}: {str(e)}")

    @staticmethod
    def detectar_usb() -> str:
        for letra in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            ruta = f"{letra}:\\"
            if os.path.exists(ruta) and os.path.ismount(ruta):
                return ruta
        return None

    @staticmethod
    def detener_monitoreo():
        if USBManejador._observer:
            USBManejador._observer.stop()
            USBManejador._observer.join()