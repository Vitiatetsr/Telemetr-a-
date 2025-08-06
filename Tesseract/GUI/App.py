# Tesseract/GUI/App.py

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from GUI.Windows.LoginWindow import LoginWindow
from Core.System.ConfigManager import ConfigManager
from Core.System.ErrorHandler import ErrorHandler
from Core.System.StateManager import StateManager

class TesseractApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.error_handler = ErrorHandler()
        self.config_manager = ConfigManager()
        
        self.init_state_manager()
        self.init_usb_storage()
        self.init_scheduler()
        
        try:
            self.sensor_profiles = ConfigManager.obtener_perfiles_sensores()
        except Exception as e:
            self.error_handler.log_error("APP_INIT", f"Error cargando perfiles: {e}")
            sys.exit(1)
        
        self.login_window = LoginWindow(self.error_handler)
        self.login_window.login_success.connect(self.on_login_success)
        self.login_window.show()
    
    def init_state_manager(self):
        StateManager.reset_all()
        logging.info("StateManager inicializado")
    
    def init_usb_storage(self):
        try:
            config = ConfigManager.cargar_config_general()
            usb_path = config.get("storage_path", "D:\\TesseractData")
            os.makedirs(usb_path, exist_ok=True)
        except Exception as e:
            self.error_handler.log_error("APP_INIT_USB", f"Error inicializando almacenamiento USB: {e}")

    def init_scheduler(self):
        from Core.Network.FTPManager import FTPManager
        from Core.System.FileScheduler import FileScheduler
        
        ftp_config = ConfigManager.cargar_config_ftp()
        ftp_manager = FTPManager(ftp_config, self.error_handler)
        
        sched_config = {
            "hora_envio": "23:59",
            "directorio_pendientes": "pendientes_usb",
            "retencion_dias": 30,
            "enable": True
        }
        
        def get_plantilla(nombre_archivo):
            return {"nombre_remoto": nombre_archivo}
        
        self.file_scheduler = FileScheduler(
            transfer_service=ftp_manager,
            config=sched_config,
            get_plantilla_fn=get_plantilla,
            error_handler=self.error_handler
        )
        
        logging.info("FileScheduler configurado")

    def on_login_success(self, user):
        from GUI.Windows.MainWindow import MainWindow
        
        self.main_window = MainWindow(
            user=user,
            error_handler=self.error_handler,
            sensor_profiles=self.sensor_profiles,
            file_scheduler=self.file_scheduler
        )
        
        if StateManager.is_system_ready():
            self.start_system_services()
        else:
            logging.warning("Sistema no iniciado: Configuración incompleta")
            QMessageBox.warning(
                self.main_window,
                "Configuración Incompleta",
                "Complete la configuración en 'Settings' y 'FTP/Email' para iniciar monitoreo"
            )
        
        self.main_window.show()
        self.login_window.close()
    
    def start_system_services(self):
        try:
            if self.file_scheduler.config.get("enabled", True):
                self.file_scheduler.iniciar()
                logging.info("FileScheduler iniciado")
            
            self.main_window.dashboard.start_monitoring()
            logging.info("Monitoreo iniciado")
            
        except Exception as e:
            self.error_handler.log_error("APP_START", f"Error iniciando servicios: {e}")

if __name__ == "__main__":
    app = TesseractApp(sys.argv)
    sys.exit(app.exec_())