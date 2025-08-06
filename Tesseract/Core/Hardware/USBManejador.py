# Tesseract/Core/Hardware/USBManejador.py

import os
import logging
import shutil
import threading
import psutil  
from Core.System.ErrorHandler import ErrorHandler

class USBManejador:
    def __init__(self, error_handler: ErrorHandler, poll_interval: int = 5, pendientes_dir: str = "pendientes_usb"):
        self.error_handler = error_handler
        self._pendientes_dir = pendientes_dir
        self._poll_interval = poll_interval
        self._lock = threading.Lock()
        self._monitoring_thread = None
        self._running = False
        os.makedirs(self._pendientes_dir, exist_ok=True)

    def inicializar_monitoreo(self):
        """Inicia el monitoreo periódico de unidades USB"""
        self._running = True
        self._monitoring_thread = threading.Thread(
            target=self._monitor_usb_changes,
            args=(self._poll_interval,),
            daemon=True
        )
        self._monitoring_thread.start()

    def _monitor_usb_changes(self, interval):
        """Monitorea cambios en unidades USB cada intervalo especificado"""
        last_state = set()
        
        while self._running:
            current_state = self._get_usb_drives()
            new_drives = current_state - last_state
            
            if new_drives:
                for drive in new_drives:
                    self.error_handler.log_evento(f"USB detectado: {drive}")
                    self._copiar_pendientes(drive)
            
            last_state = current_state
            threading.Event().wait(interval)

    def _get_usb_drives(self):
        """Retorna conjunto de unidades USB actualmente montadas usando psutil"""
        drives = set()
        for partition in psutil.disk_partitions():
            if 'removable' in partition.opts or 'usb' in partition.device.lower():
                drives.add(partition.mountpoint)
        return drives

    def guardar_en_usb(self, contenido: str, nombre_base: str) -> bool:
        """Escribe contenido en USB (sobrescribe) o en pendientes"""
        with self._lock:
            try:
                usb_drive = self._get_first_usb_drive()
                if usb_drive:
                    ruta_completa = os.path.join(usb_drive, nombre_base)
                    # CORRECCIÓN: Usar modo 'w' para sobrescribir
                    with open(ruta_completa, 'w', encoding='utf-8') as f:
                        f.write(contenido)  # Sin añadir nueva línea
                    return os.path.exists(ruta_completa)
                else:
                    return False
            except Exception as e:
                self.error_handler.log_error("USB-015", f"Error USB: {e}")
                return False

    def _get_first_usb_drive(self):
        """Retorna la primera unidad USB detectada o None"""
        drives = self._get_usb_drives()
        return next(iter(drives), None) if drives else None

    def _copiar_pendientes(self, usb_drive: str):
        """Copia archivos pendientes al USB especificado"""
        with self._lock:
            if not os.path.exists(self._pendientes_dir):
                return

            for archivo in os.listdir(self._pendientes_dir):
                ruta_origen = os.path.join(self._pendientes_dir, archivo)
                ruta_destino = os.path.join(usb_drive, archivo)

                try:
                    if os.path.exists(ruta_destino):
                        with open(ruta_origen, 'r', encoding='utf-8') as f_origen:
                            contenido = f_origen.read()
                        with open(ruta_destino, 'a', encoding='utf-8') as f_destino:
                            f_destino.write("\n" + contenido)
                    else:
                        shutil.copy(ruta_origen, ruta_destino)
                    
                    os.remove(ruta_origen)
                except Exception as e:
                    self.error_handler.log_error("USB-016", f"Error copiando {archivo}: {e}")

    def detener_monitoreo(self):
        """Detiene el monitoreo de unidades USB"""
        self._running = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)