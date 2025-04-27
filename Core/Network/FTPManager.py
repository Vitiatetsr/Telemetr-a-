import ftplib
import logging
import os
from datetime import datetime
from cryptography.fernet import Fernet
from Core.System.ErrorHandler import ErrorHandler
from Core.System.ConfigManager import ConfigManager

class FTPManager:
    def __init__(self, host: str, usuario: str):
        self.host = host
        self.usuario = usuario
        self.error_handler = ErrorHandler()
        self._clave_fernet = self._obtener_clave_fernet()
        self._clave = self._descifrar_contraseña()

    def _obtener_clave_fernet(self) -> bytes:
        clave_env = os.getenv("FERNET_KEY")
        if clave_env:
            return clave_env.encode()
            
        ftp_config = ConfigManager.cargar_config_ftp()
        return ftp_config["clave_fernet"].encode()

    def _descifrar_contraseña(self) -> str:
        ftp_config = ConfigManager.cargar_config_ftp()
        clave_cifrada = ftp_config["clave_cifrada"].encode()
        return Fernet(self._clave_fernet).decrypt(clave_cifrada).decode()

    def enviar_alerta(self, mensaje: str):
        try:
            with ftplib.FTP_TLS(self.host, timeout=10) as ftp:
                ftp.login(user=self.usuario, passwd=self._clave)
                ftp.prot_p()
                nombre_archivo = f"alerta_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
                ftp.storbinary(f'STOR {nombre_archivo}', mensaje.encode())
                logging.info(f"Archivo {nombre_archivo} enviado por FTP")
                return True
        except ftplib.all_errors as e:
            self.error_handler.log_error("002", f"Error FTP: {str(e)}")
            return False