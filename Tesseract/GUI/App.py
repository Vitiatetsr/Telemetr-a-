# Tesseract/GUI/App.py - VERSIÓN PRODUCCIÓN ACTUALIZADA

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox

# Añadir directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from GUI.Windows.LoginWindow import LoginWindow
from Core.System.ConfigManager import ConfigManager
from Core.System.ErrorHandler import ErrorHandler
from Core.System.StateManager import StateManager  # ✅ Nuevo: Gestor de estados


class TesseractApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.error_handler = ErrorHandler()
        self.config_manager = ConfigManager()
        
        # Inicializar StateManager primero
        self.init_state_manager()
        self.init_usb_storage()
        self.init_scheduler()
        
        try:
            # Cargar perfiles de sensores
            self.sensor_profiles = ConfigManager.obtener_perfiles_sensores()
        except Exception as e:
            self.error_handler.log_error("APP_INIT", f"Error cargando perfiles: {e}")
            sys.exit(1)
        
        # Iniciar con ventana de login
        self.login_window = LoginWindow(self.error_handler)
        self.login_window.login_success.connect(self.on_login_success)
        self.login_window.show()
    
    def init_state_manager(self):
        """Inicializa el gestor de estados del sistema"""
        # SOLUCIÓN: Usar método reset_all()  en lugar de set_ready () con 2 args
        StateManager.reset_all()
        logging.info("StateManager inicializado")
    
    def init_usb_storage(self):
        """Asegura que exista directorio USB por defecto"""
        try:
            config = ConfigManager.cargar_config_general()
            usb_path = config.get("storage_path", "D:\\TesseractData")
            
            # Crear directorio si no existe
            os.makedirs(usb_path, exist_ok=True)
        except Exception as e:
            self.error_handler.log_error("APP_INIT_USB", f"Error inicializando almacenamiento USB: {e}")

    def init_scheduler(self):
        """Inicializa el programador de archivos con generación anticipada"""
        from Core.Network.FTPManager import FTPManager
        from Core.System.FileScheduler import FileScheduler
        
        # Cargar configuración FTP
        ftp_config = ConfigManager.cargar_config_ftp()
        ftp_manager = FTPManager(ftp_config, self.error_handler)
        
        # Configuración base del scheduler
        sched_config = {
            "hora_envio": "23:59",
            "directorio_pendientes": "pendientes_usb",
            "retencion_dias": 30,
            "enable": True
        }
        


    def on_login_success(self, user):
        from GUI.Windows.MainWindow import MainWindow
        
        # CORRECCIÓN: Pasar sensor_profiles a MainWindow
        self.main_window = MainWindow(
            user=user,
            error_handler=self.error_handler,
            sensor_profiles=self.sensor_profiles
        )
        
        # Iniciar servicios solo si sistema está listo
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
        """Inicia todos los servicios centrales cuando el sistema está listo"""
        try:
            
            # 2. Iniciar monitoreo en dashboard
            self.main_window.dashboard.start_monitoring()
            logging.info("Monitoreo iniciado")
            
        except Exception as e:
            self.error_handler.log_error("APP_START", f"Error iniciando servicios: {e}")

if __name__ == "__main__":
    app = TesseractApp(sys.argv)
    sys.exit(app.exec_())