# Tesseract/GUI/Windows/MainWindow.py - VERSIÓN CORREGIDA POR DEEPSEEK

from PyQt5.QtWidgets import QMainWindow, QTabWidget, QAction, QApplication, QMessageBox, QStatusBar
from GUI.Windows.DashboardWindow import DashboardWindow
from GUI.Windows.ConfigWindow import ConfigWindow
from GUI.Windows.ReportsWindow import ReportsWindow
from GUI.Windows.ErrorConsoleWindow import ErrorConsoleWindow
from Core.Hardware.ModbusRTU_Manager import MedidorAguaBase
from Core.System.ErrorHandler import ErrorHandler
from GUI.Windows.FTPEmailConfigWindow import FTPEmailConfigWindow
from GUI.Windows.SettingsWindow import SettingsWindow  # Importación para añadir nueva ventana
from Core.System.StateManager import StateManager  # ✅ Nuevo import


class MainWindow(QMainWindow):
    def __init__(self, user, error_handler, sensor_profiles, file_scheduler, report_generator):
        super().__init__()
        self.user = user
        self.error_handler = error_handler
        self.sensor_profiles = sensor_profiles
        self.file_scheduler = file_scheduler
        self.report_generator = report_generator # ✅ Nuevo atributo
        self.setWindowTitle(f"Tesseract - {user}")
        self.setGeometry(100, 100, 800, 600)
        
        # Inicializar subsistemas
        self._init_subsystems()
        
        # Configurar interfaz
        self.tabs = QTabWidget()
        self.tabs.addTab(DashboardWindow(self.medidor, self.error_handler), "Dashboard")
        self.tabs.addTab(ConfigWindow(self.medidor, self.error_handler), "Configuración Hardware")
        self.tabs.addTab(ReportsWindow(self.medidor, self.error_handler), "Reportes")
        self.tabs.addTab(ErrorConsoleWindow(self.error_handler), "Errores")
        
        self.setCentralWidget(self.tabs)
        
        # CREAR MENÚ DE CONFIGURACIÓN (MODIFICADO)
        self.settings_menu = self.menuBar().addMenu("Configuración")
        
        # Configuración de hardware
        config_action = QAction("Configuración Hardware", self)
        config_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        # Abre la pestaña de ConfigWindow
        self.settings_menu.addAction(config_action)
        
        # Configuración del sistema (SettingsWindow)
        system_settings_action = QAction("Configuración Sistema", self)
        system_settings_action.triggered.connect(self.show_system_settings)
        self.settings_menu.addAction(system_settings_action)
        
        # Configuración FTP/Email
        ftp_action = QAction("Configuración FTP/Email", self)
        ftp_action.triggered.connect(self.show_ftp_email_config)
        self.settings_menu.addAction(ftp_action)
        self.setStatusBar(QStatusBar())   # ✅ Añadir barra de estado
        
    def show_warning(self, message):
        """Muestra una advertencia en la barra de estado"""
        self.statusBar().showMessage(f"⚠️ {message}", 5000)  # 5 segundos
        
    def show_system_settings(self):
        """Muestra la ventana de configuración del sistema"""
        self.settings_win = SettingsWindow()
        # Conectar la señal de actualización de configuracióon
        self.settings_win.config_updated.connect(self.handle_config_update)
        self.settings_win.show()
    
    def handle_config_update(self):
        """Actualiza el dashboard cuando cambia la configuración"""
        dashboard = self.tabs.widget(0)  # Primer tab = Dashboard
        if isinstance(dashboard, DashboardWindow):
            dashboard.refresh_unit_config()

    def show_ftp_email_config(self):
        """Muestra la ventana de configuración FTP/Email"""
        from Core.System.FileScheduler import FileScheduler
        from Core.System.ErrorHandler import ErrorHandler
        
        app = QApplication.instance()
        if hasattr(app, 'file_scheduler'):
            self.config_window = FTPEmailConfigWindow(
                file_scheduler=app.file_scheduler,
                error_handler=ErrorHandler()
            )
            self.config_window.show()

    def _init_subsystems(self):
        """Inicializa componentes de Core con configuración activa"""
        # Validación mejorada de perfiles 
        if not self.sensor_profiles:
            self.error_handler.log_error("HW-001", "No hay perfiles de sensor disponibles")
            return
        
        # Buscar perfil válido (no solo el primero)
        active_profile = None
        for profile in self.sensor_profiles:
            if profile.get("habilitado", True):
                active_profile = profile
                break
        if not active_profile:
            self.error_handler.log_error("HW-001", "No hay perfiles habilitados")
            return
        
        self.medidor = MedidorAguaBase(
            perfil_sensor=active_profile,
            error_handler=self.error_handler
        )
        
        # ✅ 1. Completar inyección de dependencias
        self.report_generator.medidor = self.medidor
        
        # ✅ 2. Marcar checkpoint
        StateManager.set_ready("meter_config")

        # Obtener estados de manera segura
        settings_ready = StateManager.is_ready("settings")
        ftp_email_ready = StateManager.is_ready("ftp_email")
        report_templates_ready = StateManager.is_ready("report_templates")

        # Verificar estados faltantes
        missing = []
        if not settings_ready:
            missing.append("Configuración General")
        if not ftp_email_ready:
            missing.append("Configuración FTP/Email")
        if not report_templates_ready:
            missing.append("Plantillas de Reportes")
    
        if missing:
            self.show_warning(f"Faltan configuraciones: {', '.join(missing)}")
        
        # ✅ 4. Iniciar servicios si el sistema está listo
        if StateManager.is_system_ready():
            self.start_system_services()
        
    def start_system_services(self):
        """Inicia servicios cuando todos los checkpoints están listos"""
        try:
            # Asegurar que el scheduler esté iniciado
            if not self.file_scheduler._scheduler or not self.file_scheduler._scheduler.running:
                self.file_scheduler.iniciar()
            
            # Iniciar monitoreo del dashboard
            dashboard = self.tabs.widget(0)
            if isinstance(dashboard, DashboardWindow):
                dashboard.setup_data_acquisition()
                
            self.show_warning("✅ Sistema operativo completo iniciado")
            
        except Exception as e:
            self.error_handler.log_error("MAIN_START", f"Error iniciando servicios: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo iniciar sistema: {str(e)}")