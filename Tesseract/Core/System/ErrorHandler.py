# Tesseract/Core/System/ErrorHandler.py

import logging, time
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
        self._last_msg = None
        self._last_time = 0.0
        self._repeat_count = 0

    def _configurar_logger(self):
        logger = logging.getLogger("TelemetríaApp")
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 1) Archivo recoge todo
        file_handler = logging.FileHandler('errores.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            logger.addHandler(file_handler)

        # 2) Consola solo WARNING+
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            logger.addHandler(console_handler)

        return logger

    def log_error(self, codigo: str, contexto: str = ""):
        mensaje = f"KER-{codigo}: {self.KER_ERRORS.get(codigo,'Error desconocido')} | {contexto}"
        now = time.time()
        # Supresión de repeticiones en consola
        if mensaje == self._last_msg and (now - self._last_time) < 1.0:
            self._repeat_count += 1
            return
        # Emitir resumen de repeticiones acumuladas
        if self._repeat_count:
            resumen = f"{self._last_msg}  (repetido {self._repeat_count} veces)"
            self.logger.error(resumen)
            self._repeat_count = 0
        # Log error normal
        self.logger.error(mensaje)
        self._last_msg = mensaje
        self._last_time = now
        # Notificadores externos
        for canal in self.notificadores:
            if hasattr(canal, 'enviar_alerta'):
                canal.enviar_alerta(mensaje)

    def log_conexion(self, estado: bool, puerto: str):
        mensaje = f"Conexión {'exitosa' if estado else 'fallida'} en {puerto}"
        self.logger.info(mensaje)
        if not estado:
            self.log_error("005", f"Reconexión en progreso en {puerto}")

    def log_evento(self, contexto: str, codigo_personalizado: str = "100"):
        mensaje = f"KER-{codigo_personalizado}: {contexto}"
        self.logger.info(mensaje)
