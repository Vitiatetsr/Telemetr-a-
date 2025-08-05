# Tesseract/Core/Network/FTPManager.py

import ftplib
import logging
import os
import time
import ssl
from typing import Optional
from Core.System.ErrorHandler import ErrorHandler
from .IFileTransfer import IFileTransfer

class FTPManager(IFileTransfer):
    def __init__(self, config: dict, error_handler: ErrorHandler):
        self.config = config
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        self.connection: Optional[ftplib.FTP_TLS] = None
        self.timeout = config.get("timeout", 30)
        self.port = config.get("puerto", 21)
        self.secure_mode = config.get("secure", True) # Valor por defecto True

    def _conectar(self) -> bool:
        try:
            if self.connection:
                try:
                    self.connection.quit()
                except:
                    pass
            
            # Intento con TLS si está habilitado
            if self.secure_mode:
                try:    
                    self.connection = ftplib.FTP_TLS(
                        timeout=self.timeout,
                        context=ssl.create_default_context()
                    )
                    self.connection.connect(
                        self.config["host"],
                        self.port
                    )
                    self.connection.login(
                        user=self.config["usuario"],
                        passwd=self.config["clave"]
                    )
                    # Intentan establecer protección de datos
                    try:
                        self.connection.prot_p()
                    except:
                        self.logger.warning("El servidor no soporta PROT P, continuando sin cifrado de datos")
                    return True
                except Exception as e:
                    self.logger.warning(f"Fallo TLS, intentando sin cifrado: {str(e)}")
                    
            # Conexión FTP estándar
            self.connection = ftplib.FTP(timeout=self.timeout)
            self.connection.connect(
                self.config["host"],
                self.port
            )
            self.connection.login(
                user=self.config["usuario"],
                passwd=self.config["clave"]
            )
            return True
        
        except ftplib.all_errors as e:
            self.error_handler.log_error("FTP-001", f"Conexión fallida: {e}")
            return False
        except Exception as e:
            self.error_handler.log_error("FTP-002", f"Error inesperado: {e}")
            return False


    def _cerrar_conexion(self):
        try:
            if self.connection:
                self.connection.quit()
        except:
            pass
        finally:
            self.connection = None

    def _crear_directorios_remotos(self, remote_dir: str):
        """Crea directorios remotos recursivamente"""
        try:
            # CORRECCIÓN: Manejo de rutas absolutas
            if remote_dir.startswith("/"):
                self.connection.cwd("/")
            
            directorios = [d for d in remote_dir.split('/') if d]
            path_actual = ""
        
            for dir in directorios:
                path_actual += f"/{dir}" if path_actual else dir
                try:
                    self.connection.cwd(path_actual)
                except:
                    try:
                        self.connection.mkd(path_actual)
                        self.connection.cwd(path_actual)
                    except ftplib.error_perm as e:
                        # Ignorar error "El directorio ya existe"
                        if "550" not in str(e):
                            raise
        except Exception as e:
            self.error_handler.log_error("FTP-003", f"Error creando directorios: {e}")

    def enviar_archivo(self, local_path: str, remote_path: str) -> bool:
        self.logger.info(f"Iniciando envío FTP: {local_path} -> {remote_path}")
        
        for intento in range(3):
            try:
                if not self._conectar():
                    self.logger.error("No se pudo establecer conexión FTP")
                    continue
                
                # Crear estructura de directorios
                remote_dir = os.path.dirname(remote_path)
                if remote_dir:
                    self._crear_directorios_remotos(remote_dir)
                
                # Enviar archivo
                with open(local_path, "rb") as file:
                    self.connection.storbinary(f"STOR {os.path.basename(remote_path)}", file)
                self.logger.info(f"Archivo enviado exitosamente: {local_path}")
                return True
            except (ftplib.error_temp, ConnectionResetError) as e:
                self.logger.warning(f"Reintento {intento+1}/3 por error temporal: {e}")
                time.sleep(2)
            except ftplib.error_perm as e:
                error_code = int(str(e).split()[0])
                # Código 534: Política no permite TLS
                if error_code == 534:
                    self.secure_mode = False
                    self.logger.warning("Desactivando TLS por política del servidor")
                    time.sleep(1)
                else:
                    self.error_handler.log_error("FTP-004", f"Error de permisos: {e}")
                    return False
            except Exception as e:
                self.error_handler.log_error("FTP-005", f"Error crítico: {e}")
                return False
            finally:
                self._cerrar_conexion()
        return False

    def verificar_conexion(self) -> bool:
        """Implementación de método de interfaz"""
        try:
            return self._conectar()
        finally:
            self._cerrar_conexion()