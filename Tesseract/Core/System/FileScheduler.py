# Tesseract/Core/System/FileScheduler.py

import os
import time
import threading
import logging
import json
import smtplib
import queue
from datetime import datetime, timedelta
from typing import Callable, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor, as_completed
from Core.Network.IFileTransfer import IFileTransfer
from Core.System.ErrorHandler import ErrorHandler
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

class FileScheduler:
    MAX_QUEUE_SIZE = 100
    EMAIL_WORKERS = 3
    
    def __init__(
        self,
        transfer_service: IFileTransfer,
        config: Dict[str, Any],
        get_plantilla_fn: Callable[[str], Dict[str, Any]],
        error_handler: ErrorHandler
    ):
        self.transfer_service = transfer_service
        self.config = config
        self.get_plantilla = get_plantilla_fn
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        
        self._scheduler = None
        self._lock = threading.Lock()
        
        self.email_config = self._cargar_config_email()
        
        self._email_queue = queue.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._email_workers = []
        self._stop_event = threading.Event()
        self._init_email_workers()

    def _cargar_config_email(self) -> Dict[str, Any]:
        try:
            config_path = 'Config/email_config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.error_handler.log_error("EMAIL_CONF", f"Error cargando configuración email: {e}")
            return None

    def _init_email_workers(self):
        for i in range(self.EMAIL_WORKERS):
            worker = threading.Thread(
                target=self._email_worker_task,
                name=f"EmailWorker-{i}",
                daemon=True
            )
            worker.start()
            self._email_workers.append(worker)

    def _email_worker_task(self):
        server = None
        while not self._stop_event.is_set():
            file_path = None
            try:
                file_path = self._email_queue.get(timeout=5.0)
                
                if server is None:
                    server = self._crear_smtp_server()
                
                if server:
                    self._enviar_email(server, file_path)
                    
            except queue.Empty:
                continue
            except Exception as e:
                self.error_handler.log_error("EMAIL_WORKER", f"Error en worker: {e}")
                server = None
            finally:
                if file_path is not None:
                    self._email_queue.task_done()

        if server:
            try:
                server.quit()
            except:
                pass

    def _crear_smtp_server(self) -> smtplib.SMTP:
        if not self.email_config:
            return None
            
        for _ in range(3):
            try:
                server = smtplib.SMTP(
                    self.email_config['smtp_server'],
                    self.email_config['smtp_port'],
                    timeout=15
                )
                server.starttls()
                server.login(
                    self.email_config['username'],
                    self.email_config['password']
                )
                self.logger.info("Conexión SMTP establecida")
                return server
            except Exception as e:
                self.error_handler.log_error("SMTP_CONN", f"Error conexión SMTP: {e}")
                time.sleep(2)
        return None

    def _enviar_email(self, server: smtplib.SMTP, file_path: str):
        if not os.path.exists(file_path):
            self.logger.warning(f"Archivo no encontrado: {file_path}")
            return
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from']
            msg['To'] = ", ".join(self.email_config['to'])
            msg['Subject'] = self.email_config['subject']
            
            with open(file_path, "rb") as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(file_path)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(part)
            
            server.sendmail(
                self.email_config['from'],
                self.email_config['to'],
                msg.as_string()
            )
            self.logger.info(f"Email enviado: {filename}")
            
            
            
        except smtplib.SMTPServerDisconnected:
            self.logger.warning("Reconectando SMTP...")
            raise
        except Exception as e:
            self.error_handler.log_error("EMAIL_SEND", f"Error enviando email: {e}")

    def _eliminar_archivo_seguro(self, ruta_local):
        try:
            if os.path.exists(ruta_local):
                os.remove(ruta_local)
                self.logger.info(f"Archivo eliminado: {os.path.basename(ruta_local)}")
        except Exception as e:
            self.error_handler.log_error("FILE_DELETE", f"Error eliminando archivo: {e}")

    def _validate_time_format(self, hora_envio: str) -> tuple[int, int]:
        try:
            hora, minuto = map(int, hora_envio.split(":"))
            if not (0 <= hora <= 23 and 0 <= minuto <= 59):
                raise ValueError("Hora o minuto fuera de rango")
            return hora, minuto
        except ValueError as e:
            self.error_handler.log_error("SCHED_CONF", f"Formato de hora_envio inválido: {e}")
            return 23, 59

    def iniciar(self):
        try:
            if self._scheduler is None or self._scheduler.state == 0:
                self._scheduler = BackgroundScheduler(
                    daemon=True,
                    executors={'default': {'type': 'threadpool', 'max_workers': 4}},
                    job_defaults={'misfire_grace_time': 3600}
                )
            
            hora_envio = self.config.get("hora_envio", "23:59")
            hora, minuto = self._validate_time_format(hora_envio)
            
            self._scheduler.remove_all_jobs()
            
            self._scheduler.add_job(
                self._enviar_archivos_pendientes,
                "cron",
                hour=hora,
                minute=minuto
            )
            self._scheduler.add_job(
                self._verificar_pendientes,
                "interval",
                minutes=15
            )
            
            if self._scheduler.state == 0:
                self._scheduler.start()
                self.logger.info("Scheduler iniciado correctamente")
            else:
                self.logger.info("Scheduler ya está en ejecución")
            
        except Exception as e:
            self.error_handler.log_error("SCHED_INIT", f"Error iniciando scheduler: {e}")

    def _procesar_archivo_individual(self, ruta_local):
        archivo = os.path.basename(ruta_local)
        try:
            plantilla = self.get_plantilla(archivo)
            # ¡CORRECCIÓN! Ruta remota segura (sin slash final)
            ruta_base = self.config.get("ruta_remota", "/default_conagua").rstrip('/')
            nombre_remoto = plantilla.get("nombre_remoto", archivo)
            ruta_remota = os.path.join(ruta_base, nombre_remoto)

            ftp_exitoso = False
            if "/default_conagua" in ruta_remota:
                self.error_handler.log_error("CONFIG_ERROR", f"Falta 'ruta_remota' para {archivo}")
            else:
                ftp_exitoso = self.transfer_service.enviar_archivo(ruta_local, ruta_remota)
                if ftp_exitoso:
                    self.logger.info(f"FTP exitoso: {archivo}")
                else:
                    self.logger.warning(f"Fallo FTP: {archivo}")

            # ¡IMPORTANTE! Eliminación condicional segura
            if ftp_exitoso:
                if self.email_config:
                    try:
                        self._email_queue.put(ruta_local, block=False)
                    except queue.Full:
                        self.error_handler.log_error("EMAIL_QUEUE", f"Cola llena, omitiendo {archivo}")
                else:
                    # Eliminar solo si no hay email configurado
                    self._eliminar_archivo_seguro(ruta_local)
            else:
                self.logger.warning(f"Archivo retenido por fallo FTP: {archivo}")
                
        except Exception as e:
            self.error_handler.log_error("SCHED_SEND", f"Error procesando {archivo}: {e}")
            
    def _enviar_archivos_pendientes(self):
        with self._lock:
            directorio = self.config.get("directorio_pendientes", "pendientes_usb")
            archivos = [f for f in os.listdir(directorio) if f.endswith(".txt")]
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {}
                for archivo in archivos:
                    ruta_local = os.path.join(directorio, archivo)
                    future = executor.submit(self._procesar_archivo_individual, ruta_local)
                    futures[future] = archivo
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        archivo = futures[future]
                        self.error_handler.log_error("SCHED_PARALLEL", f"Error en paralelo: {archivo} - {e}")

    def _verificar_pendientes(self):
        with self._lock:
            directorio = self.config.get("directorio_pendientes", "pendientes_usb")
            max_dias = max(self.config.get("retencion_dias", 7), 180)
            
            for archivo in os.listdir(directorio):
                ruta = os.path.join(directorio, archivo)
                if os.path.isfile(ruta):
                    tiempo_creacion = datetime.fromtimestamp(os.path.getctime(ruta))
                    if (datetime.now() - tiempo_creacion) > timedelta(days=max_dias):
                        try:
                            os.remove(ruta)
                            self.logger.warning(f"Archivo antiguo eliminado: {archivo}")
                        except Exception as e:
                            self.error_handler.log_error("SCHED_CLEAN", f"Error eliminando {archivo}: {e}")

    def detener(self):
        try:
            if self._scheduler and self._scheduler.running:
                self._scheduler.shutdown(wait=True)
                self.logger.info("Scheduler principal detenido")
        except Exception as e:
            self.error_handler.log_error("SCHED_TOP", f"Error detenido scheduler: {e}")
        
        self._stop_event.set()
        self._email_queue.join()
        
        for worker in self._email_workers:
            worker.join(timeout=3.0)
        
        self._stop_event.clear()
        self._email_workers = []
        self._init_email_workers()
            
        self.logger.info("Todos los componentes fueron detenidos correctamente")