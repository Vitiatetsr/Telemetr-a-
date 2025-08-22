# Tesseract/Core/Network/AlertManager.py

import logging
from abc import ABC, abstractmethod
from Core.System.ErrorHandler import ErrorHandler
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText

class AlertChannel(ABC):
    """Interfaz para canales de alerta"""
    @abstractmethod
    def send(self, message: str, destination: str) -> bool:
        pass

class SMSChannel(AlertChannel):
    def __init__(self, config: dict, error_handler: ErrorHandler):
        self.config = config
        self.error_handler = error_handler
        try:
            self.client = Client(config["account_sid"], config["auth_token"])
        except Exception as e:
            self.error_handler.log_error("SMS-INIT", f"Error inicializando cliente SMS: {e}")
            self.client = None

    def send(self, message: str, destination: str) -> bool:
        if self.client is None:
            return False
        try:
            self.client.messages.create(
                body=message,
                from_=self.config["numero_twilio"],
                to=destination
            )
            logging.info(f"SMS enviado a {destination}")
            return True
        except Exception as e:
            logging.error(f"Error enviando SMS: {e}")
            self.error_handler.log_error("SMS-SEND", f"Error enviando SMS: {e}")
            return False

class EmailChannel(AlertChannel):
    def __init__(self, config: dict, error_handler: ErrorHandler):
        self.config = config
        self.error_handler = error_handler

    def send(self, message: str, destination: str) -> bool:
        try:
            msg = MIMEText(message)
            msg['Subject'] = self.config.get("subject", "Alerta de Telemetría")
            msg['From'] = self.config["email_from"]
            msg['To'] = destination

            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["email_user"], self.config["email_password"])
                server.sendmail(self.config["email_from"], destination, msg.as_string())
            logging.info(f"Email enviado a {destination}")
            return True
        except Exception as e:
            logging.error(f"Error enviando email: {e}")
            self.error_handler.log_error("EMAIL-SEND", f"Error enviando email: {e}")
            return False

class AlertManager:
    def __init__(self, config: dict, error_handler: ErrorHandler):
        self.config = config
        self.error_handler = error_handler
        self.channel = self._create_channel()

    def _create_channel(self) -> AlertChannel:
        if self.config.get("use_sms", False):
            return SMSChannel(self.config, self.error_handler)
        else:
            return EmailChannel(self.config, self.error_handler)

    def enviar_alerta(self, mensaje: str, destino: str):
        try:
            success = self.channel.send(f"ALERTA: {mensaje}", destino)
            if not success:
                self.error_handler.log_error("ALERT-001", "Fallo en envío de alerta")
            return success
        except Exception as e:
            self.error_handler.log_error("ALERT-002", f"Error crítico: {e}")
            return False

    def enviar_archivo_como_sms(self, archivo_path: str, destino: str):
        """Envía el contenido de un archivo como SMS"""
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido = f.read().strip()
            
            # Limitar el contenido si es muy largo para SMS (1600 caracteres máximo)
            if len(contenido) > 1600:
                contenido = contenido[:1596] + "..."
            
            # Enviar como SMS
            success = self.channel.send(contenido, destino)
            if not success:
                self.error_handler.log_error("SMS-FILE", f"Fallo enviando archivo por SMS: {archivo_path}")
            return success
        except Exception as e:
            self.error_handler.log_error("SMS-FILE-READ", f"Error leyendo archivo para SMS: {e}")
            return False