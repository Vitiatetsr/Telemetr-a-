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
    def __init__(self, config: dict):
        self.config = config
        self.client = Client(config["account_sid"], config["auth_token"])

    def send(self, message: str, destination: str) -> bool:
        try:
            self.client.messages.create(
                body=message,
                from_=self.config["from_number"],
                to=destination
            )
            logging.info(f"SMS enviado a {destination}")
            return True
        except Exception as e:
            logging.error(f"Error enviando SMS: {e}")
            return False

class EmailChannel(AlertChannel):
    def __init__(self, config: dict):
        self.config = config

    def send(self, message: str, destination: str) -> bool:
        try:
            msg = MIMEText(message)
            msg['Subject'] = "Alerta de Telemetría"
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
            return False

class AlertManager:
    def __init__(self, config: dict, error_handler: ErrorHandler):
        self.config = config
        self.error_handler = error_handler
        self.channel = self._create_channel()

    def _create_channel(self) -> AlertChannel:
        if self.config.get("use_sms"):
            return SMSChannel(self.config)
        return EmailChannel(self.config)

    def enviar_alerta(self, mensaje: str, destino: str):
        try:
            success = self.channel.send(f"ALERTA: {mensaje}", destino)
            if not success:
                self.error_handler.log_error("ALERT-001", "Fallo en envío de alerta")
        except Exception as e:
            self.error_handler.log_error("ALERT-002", f"Error crítico: {e}")