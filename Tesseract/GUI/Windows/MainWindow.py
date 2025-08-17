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
        
        # 1. PRIMERO: Construir la interfaz UI
        self.setup_ui()
        
        # 2. SEGUNDO: Inicializar subsistemas (CON self.tabs YA CREADO)
        self._init_subsystems()
        
    def setup_ui(self):
        """Configura todos los componentes de UI primero"""
        # Crear el widget de pestañas
        self.tabs = QTabWidget()
        
        # Crear ventanas con placeholders (medidor=None)
        self.dashboard_window = DashboardWindow(None, self.error_handler)
        self.config_window = ConfigWindow(None, self.error_handler)
        
        # Añadir pestañas
        self.tabs.addTab(self.dashboard_window, "Dashboard")
        self.tabs.addTab(self.config_window, "Configuración Hardware")
        self.tabs.addTab(ReportsWindow(None, self.error_handler), "Reportes")
        self.tabs.addTab(ErrorConsoleWindow(self.error_handler), "Errores")
        
        self.setCentralWidget(self.tabs)
        
        # Crear menú
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
        # Actualizar conversión de unidades en el dashboard
        if hasattr(self, 'dashboard_window'):
            self.dashboard_window.refresh_unit_config()

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
        
        # Encontrar el perfil activo
        active_profile = None
        for profile in self.sensor_profiles:
            if profile.get("habilitado", True):
                active_profile = profile
                break
        if not active_profile:
            self.error_handler.log_error("HW-001", "No hay perfiles habilitados")
            return
        
        # Crear el medidor con el perfil activo
        self.medidor = MedidorAguaBase(
            perfil_sensor=active_profile,
            error_handler=self.error_handler
        )
        
        StateManager.set_state('medidor', self.medidor)
        
        # Establecer estados esenciales como completados (omitir comprobaciones por ahora)
        StateManager.set_ready('settings')
        StateManager.set_ready('ftp_email')
        StateManager.set_ready('report_templates')
        StateManager.set_ready('meter_config')
        
        # Actualizar ventanas con el medidor real
        self.dashboard_window.medidor = self.medidor
        self.config_window.medidor = self.medidor
        
        if hasattr(self.dashboard_window, 'setup_timers'):
            self.dashboard_window.setup_timers()  # ✅ Nuevo método
        
        # Cargar configuración inicial en la ventana de configuración
        if hasattr(self.config_window, 'load_initial_config'):
            self.config_window.load_initial_config()
        
        # Mostrar estado
        self.show_warning("✅ Sistema operativo iniciado")
            