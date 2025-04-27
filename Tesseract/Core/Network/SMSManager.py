import logging
from twilio.rest import Client
from Core.System.ErrorHandler import ErrorHandler

class SMSManager:
    def __init__(self, account_sid: str, auth_token: str, numero_twilio: str):
        self.client = Client(account_sid, auth_token)
        self.numero_twilio = numero_twilio
        self.error_handler = ErrorHandler()

    def enviar_alerta(self, mensaje: str, numero_destino: str):
        try:
            self.client.messages.create(
                body=f"ALERTA: {mensaje}",
                from_=self.numero_twilio,
                to=numero_destino
            )
            logging.info(f"SMS enviado a {numero_destino}")
        except Exception as e:
            self.error_handler.log_error("011", f"Error enviando SMS: {str(e)}")