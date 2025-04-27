# Core/System/ErrorHandler.py
import logging
from datetime import datetime
from typing import List

class ErrorHandler:
    KER_ERRORS = {
        "001": "Falta conexión a internet",
        "002": "Fallo en conexión FTP",
        "005": "Error en puerto COM",
        "007": "Error de comunicación con medidor",
        "010": "Fallo general del sistema",
        "011": "Error en envío de SMS"
    }

    def __init__(self, notificadores: List[object] = []):
        self.notificadores = notificadores
        self.logger = self._configurar_logger()

    def _configurar_logger(self):
        logger = logging.getLogger("TelemetríaApp")
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler = logging.FileHandler('errores.log')
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        return logger

    def log_error(self, codigo: str, contexto: str = ""):
        mensaje = f"KER-{codigo}: {self.KER_ERRORS.get(codigo, 'Error desconocido')} | {contexto}"
        self.logger.error(mensaje)
        for canal in self.notificadores:
            if hasattr(canal, 'enviar_alerta'):
                canal.enviar_alerta(mensaje)

    def log_conexion(self, estado: bool, puerto: str):
        mensaje = f"Conexión {'exitosa' if estado else 'fallida'} en {puerto}"
        self.logger.info(mensaje)
        if not estado:
            self.log_error("005", f"Reconexión en progreso en {puerto}")

    # ========== NUEVO MÉTODO (NO AFECTA CÓDIGO EXISTENTE) ==========
    def log_evento(self, contexto: str, codigo_personalizado: str = "100"):
        mensaje = f"KER-{codigo_personalizado}: {contexto}"
        self.logger.info(mensaje)