# Tesseract/GUI/Windows/MainWindow.py

from PyQt5.QtWidgets import QMainWindow, QTabWidget, QAction, QApplication, QMessageBox, QStatusBar
from GUI.Windows.DashboardWindow import DashboardWindow
from GUI.Windows.ConfigWindow import ConfigWindow
from GUI.Windows.ReportsWindow import ReportsWindow
from GUI.Windows.ErrorConsoleWindow import ErrorConsoleWindow
from Core.Hardware.ModbusRTU_Manager import MedidorAguaBase
from Core.System.ErrorHandler import ErrorHandler
from GUI.Windows.FTPEmailConfigWindow import FTPEmailConfigWindow
from GUI.Windows.SettingsWindow import SettingsWindow
from Core.System.StateManager import StateManager

class MainWindow(QMainWindow):
    def __init__(self, user, error_handler, sensor_profiles, file_scheduler):
        super().__init__()
        self.user = user
        self.error_handler = error_handler
        self.sensor_profiles = sensor_profiles
        self.file_scheduler = file_scheduler
        self.setWindowTitle(f"Tesseract - {user}")
        self.setGeometry(100, 100, 800, 600)
        
        self._init_subsystems()
        
        self.tabs = QTabWidget()
        self.tabs.addTab(DashboardWindow(self.medidor, self.error_handler), "Dashboard")
        self.tabs.addTab(ConfigWindow(self.medidor, self.error_handler), "Configuración Hardware")
        self.tabs.addTab(ReportsWindow(self.medidor, self.error_handler), "Reportes")
        self.tabs.addTab(ErrorConsoleWindow(self.error_handler), "Errores")
        
        self.setCentralWidget(self.tabs)
        
        self.settings_menu = self.menuBar().addMenu("Configuración")
        
        config_action = QAction("Configuración Hardware", self)
        config_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        self.settings_menu.addAction(config_action)
        
        system_settings_action = QAction("Configuración Sistema", self)
        system_settings_action.triggered.connect(self.show_system_settings)
        self.settings_menu.addAction(system_settings_action)
        
        ftp_action = QAction("Configuración FTP/Email", self)
        ftp_action.triggered.connect(self.show_ftp_email_config)
        self.settings_menu.addAction(ftp_action)
        self.setStatusBar(QStatusBar())
        
    def show_warning(self, message):
        self.statusBar().showMessage(f"⚠️ {message}", 5000)
        
    def show_system_settings(self):
        self.settings_win = SettingsWindow()
        self.settings_win.config_updated.connect(self.handle_config_update)
        self.settings_win.show()
    
    def handle_config_update(self):
        dashboard = self.tabs.widget(0)
        if isinstance(dashboard, DashboardWindow):
            dashboard.refresh_unit_config()

    def show_ftp_email_config(self):
        from Core.System.ErrorHandler import ErrorHandler
        
        app = QApplication.instance()
        if hasattr(app, 'file_scheduler'):
            self.config_window = FTPEmailConfigWindow(
                file_scheduler=app.file_scheduler,
                error_handler=ErrorHandler()
            )
            self.config_window.show()

    def _init_subsystems(self):
        if not self.sensor_profiles:
            self.error_handler.log_error("HW-001", "No hay perfiles de sensor disponibles")
            return
        
        active_profile = None
        for profile in self.sensor_profiles:
            if profile.get("habilitado", True):
                active_profile = profile
                break
        
        # ¡VALIDACIÓN CRÍTICA! Perfil debe tener registros
        if not active_profile or not active_profile.get("registros"):
            self.error_handler.log_error("HW-001", "Perfil de sensor inválido")
            QMessageBox.critical(
                self, 
                "Error de Configuración", 
                "No se encontró un perfil de sensor válido. Configure un perfil en Configuración Hardware."
            )
            return
        
        self.medidor = MedidorAguaBase(
            perfil_sensor=active_profile,
            error_handler=self.error_handler
        )
        
        StateManager.set_state('medidor', self.medidor)
        StateManager.set_ready("meter_config")
        
        missing = []
        if not StateManager.is_ready("settings"):
            missing.append("Configuración General")
        if not StateManager.is_ready("ftp_email"):
            missing.append("Configuración FTP/Email")
        if not StateManager.is_ready("report_templates"):
            missing.append("Plantillas de Reportes")
            
        if missing:
            self.show_warning(f"Faltan configuraciones: {', '.join(missing)}")
            
        if StateManager.is_system_ready():
            self.start_system_services()
        
    def start_system_services(self):
        try:
            if not self.file_scheduler._scheduler or not self.file_scheduler._scheduler.running:
                self.file_scheduler.iniciar()
            
            dashboard = self.tabs.widget(0)
            if isinstance(dashboard, DashboardWindow):
                dashboard.setup_data_acquisition()
                
            self.show_warning("✅ Sistema operativo completo iniciado")
            
        except Exception as e:
            self.error_handler.log_error("MAIN_START", f"Error iniciando servicios: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo iniciar sistema: {str(e)}")