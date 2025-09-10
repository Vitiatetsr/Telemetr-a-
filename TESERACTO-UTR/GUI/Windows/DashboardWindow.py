# TESERACTO-UTR/GUI/Windows/DashboardWindow.py

import logging
import os
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QPalette, QFont, QPixmap
from Core.DataProcessing.Services import UnitConverter
from Core.System.ConfigManager import ConfigManager
from Core.System.ErrorHandler import ErrorHandler
from Core.System.StateManager import StateManager

class DashboardWindow(QWidget):
    def __init__(self, medidor, error_handler: ErrorHandler):
        super().__init__()
        self.medidor = medidor
        self.error_handler = error_handler
        self.config_manager = ConfigManager()
        self.unit_converter = UnitConverter()
        
        self.unidad_medidor = "m³/h"
        self.unidad_visual = self.config_manager.cargar_config_general().get("unidad_visualizacion", "m³/h")
        self.unidad_volumen = "m³"
        
        self.logo_image = self.load_logo_image()
        
        self.apply_dark_theme()
        self.setup_ui()
        self.setup_timers()
        self.actualizar_unidades()

    def load_logo_image(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            image_path = os.path.join(project_root, 'images', 'LOGO2.jpeg')
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                return pixmap.scaled(320, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                self.error_handler.log_error(
                    "DASH_LOGO", 
                    f"Imagen de logo no encontrada: {image_path}"
                )
                return None
        except Exception as e:
            self.error_handler.log_error("DASH_LOGO", f"Error cargando logo: {str(e)}")
            return None

    def apply_dark_theme(self):
        dark_theme = """
            QWidget { background-color: #2b2b2b; color: #ffffff; border: none; font-size: 12pt; }
            QGroupBox { color: #ffffff; border: 1px solid #555; border-radius: 5px; margin-top: 10px; padding-top: 10px; font-weight: bold; font-size: 12pt; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; color: #ffffff; font-size: 12pt; }
            QLabel { color: #ffffff; background-color: transparent; font-size: 12pt; }
            .flow-value { font-size: 50pt; color: #4fc3f7; }
            .flow-unit { font-size: 30pt; color: #4fc3f7; }
            .volume-value { font-size: 50pt; color: #81c784; }
            .volume-unit { font-size: 30pt; color: #81c784; }
            .velocity-value { font-size: 50pt; color: #e1bee7; }
            .velocity-unit { font-size: 30pt; color: #e1bee7; }
            .positive-flow { color: #4fc3f7; font-size: 22pt; }
            .negative-flow { color: #ff9800; font-size: 22pt; }
            .stopped-flow { color: #bdbdbd; font-size: 22pt; }
            .connected-status { color: #81c784; font-weight: bold; font-size: 12pt; }
            .disconnected-status { color: #ff5252; font-weight: bold; font-size: 12pt; }
            .system-ok { color: #81c784; font-weight: bold; font-size: 12pt; }
            .system-warning { color: #ffb74d; font-weight: bold; font-size: 12pt; }
            .system-error { color: #ff5252; font-weight: bold; font-size: 12pt; }
            .sensor-value { font-size: 22pt; font-family: Arial; }
            .error-code { font-size: 22pt; font-family: Consolas; }
            .status-label { font-size: 12pt; }
            .logo-label { background-color: transparent; border: none; padding: 5px; }
        """
        self.setStyleSheet(dark_theme)

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        title_main_layout = QVBoxLayout()
        title_main_layout.setSpacing(5)
        
        title_top_layout = QHBoxLayout()
        
        title_container = QVBoxLayout()
        self.title_label = QLabel("TESERACTO UTR")
        self.title_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: #ffffff;")
        title_container.addWidget(self.title_label)
        
        self.system_status = QLabel("✅ Sistema operativo")
        self.system_status.setProperty("class", "system-ok")
        title_container.addWidget(self.system_status)
        
        title_top_layout.addLayout(title_container)
        title_top_layout.addStretch()
        
        if self.logo_image:
            logo_label = QLabel()
            logo_label.setPixmap(self.logo_image)
            logo_label.setProperty("class", "logo-label")
            logo_label.setAlignment(Qt.AlignRight)
            title_top_layout.addWidget(logo_label)
        
        title_main_layout.addLayout(title_top_layout)
        main_layout.addLayout(title_main_layout)
        
        separator = QLabel()
        separator.setStyleSheet("background-color: #555; height: 2px;")
        main_layout.addWidget(separator)
        
        data_group = QGroupBox("Datos de Medición")
        data_layout = QGridLayout()
        data_layout.setSpacing(15)
        
        # --- COLUMNA 0: FLUJO INSTANTÁNEO ---
        flow_label = QLabel("FLUJO INSTANTÁNEO:")
        flow_label.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 14pt;")
        data_layout.addWidget(flow_label, 0, 0)
        
        flow_container = QWidget()
        flow_h_layout = QHBoxLayout(flow_container)
        flow_h_layout.setContentsMargins(0, 0, 0, 0)
        flow_h_layout.setSpacing(5)
        
        self.flow_value = QLabel("--")
        self.flow_value.setProperty("class", "flow-value")
        self.flow_value.setMinimumWidth(120)
        self.flow_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.flow_unit = QLabel("m³/h")
        self.flow_unit.setProperty("class", "flow-unit")
        
        flow_h_layout.addWidget(self.flow_value)
        flow_h_layout.addWidget(self.flow_unit)
        flow_h_layout.addStretch()
        
        data_layout.addWidget(flow_container, 1, 0)
        
        # --- COLUMNA 1: VOLUMEN ACUMULADO ---
        volume_label = QLabel("VOLUMEN ACUMULADO:")
        volume_label.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 14pt;")
        data_layout.addWidget(volume_label, 0, 1)
        
        volume_container = QWidget()
        volume_h_layout = QHBoxLayout(volume_container)
        volume_h_layout.setContentsMargins(0, 0, 0, 0)
        volume_h_layout.setSpacing(5)
        
        self.volume_value = QLabel("--")
        self.volume_value.setProperty("class", "volume-value")
        self.volume_value.setMinimumWidth(120)
        self.volume_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.volume_unit = QLabel("m³")
        self.volume_unit.setProperty("class", "volume-unit")
        
        volume_h_layout.addWidget(self.volume_value)
        volume_h_layout.addWidget(self.volume_unit)
        volume_h_layout.addStretch()
        
        data_layout.addWidget(volume_container, 1, 1)
        
        # --- COLUMNA 2: VELOCIDAD DE FLUJO (AJUSTADO) ---
        velocity_label = QLabel("VELOCIDAD DE FLUJO:")
        velocity_label.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 14pt;")
        data_layout.addWidget(velocity_label, 0, 2) # << MODIFICADO >> Fila 0, Columna 2

        velocity_container = QWidget()
        velocity_h_layout = QHBoxLayout(velocity_container)
        velocity_h_layout.setContentsMargins(0, 0, 0, 0)
        velocity_h_layout.setSpacing(5)

        self.velocity_value = QLabel("--")
        self.velocity_value.setProperty("class", "velocity-value")
        self.velocity_value.setMinimumWidth(120)
        self.velocity_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.velocity_unit = QLabel("m/s")
        self.velocity_unit.setProperty("class", "velocity-unit")

        velocity_h_layout.addWidget(self.velocity_value)
        velocity_h_layout.addWidget(self.velocity_unit)
        velocity_h_layout.addStretch()

        data_layout.addWidget(velocity_container, 1, 2) # << MODIFICADO >> Fila 1, Columna 2
        
        # --- DIRECCIÓN DE FLUJO (DEBAJO, ABARCANDO 3 COLUMNAS) ---
        direction_label = QLabel("DIRECCIÓN DE FLUJO:")
        direction_label.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 14pt;")
        data_layout.addWidget(direction_label, 2, 0, 1, 3) # << MODIFICADO >> Fila 2, abarca 3 columnas
        
        self.direction_value = QLabel("--")
        self.direction_value.setProperty("class", "stopped-flow")
        data_layout.addWidget(self.direction_value, 3, 0, 1, 3) # << MODIFICADO >> Fila 3, abarca 3 columnas
        
        data_group.setLayout(data_layout)
        main_layout.addWidget(data_group)
        
        # ... (El resto del archivo setup_ui y la clase permanecen exactamente iguales) ...

        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)
        
        sensor_stats_group = QGroupBox("Estadísticas del Sensor")
        sensor_stats_layout = QGridLayout()
        
        sensor_label_energizacion = QLabel("Encendidos:")
        sensor_label_energizacion.setStyleSheet("font-weight: bold;")
        sensor_stats_layout.addWidget(sensor_label_energizacion, 0, 0)
        
        self.lbl_energizacion = QLabel("N/A")
        self.lbl_energizacion.setProperty("class", "sensor-value")
        sensor_stats_layout.addWidget(self.lbl_energizacion, 0, 1)
        
        sensor_label_errores = QLabel("Errores:")
        sensor_label_errores.setStyleSheet("font-weight: bold;")
        sensor_stats_layout.addWidget(sensor_label_errores, 1, 0)
        
        self.lbl_errores = QLabel("N/A")
        self.lbl_errores.setProperty("class", "sensor-value")
        sensor_stats_layout.addWidget(self.lbl_errores, 1, 1)
        
        sensor_label_cod_error = QLabel("Código Error:")
        sensor_label_cod_error.setStyleSheet("font-weight: bold;")
        sensor_stats_layout.addWidget(sensor_label_cod_error, 2, 0)
        
        self.lbl_cod_error = QLabel("N/A")
        self.lbl_cod_error.setProperty("class", "error-code")
        sensor_stats_layout.addWidget(self.lbl_cod_error, 2, 1)
        
        sensor_stats_group.setLayout(sensor_stats_layout)
        main_layout.addWidget(sensor_stats_group)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)
        
        unit_box = QGroupBox("Configuración de Unidades")
        unit_layout = QVBoxLayout(unit_box)
        
        self.medidor_unit_label = QLabel("Medidor: Cargando...")
        self.visual_unit_label = QLabel("Visualización: Cargando...")
        
        unit_layout.addWidget(self.medidor_unit_label)
        unit_layout.addWidget(self.visual_unit_label)
        bottom_layout.addWidget(unit_box)
        
        status_box = QGroupBox("Estado de Conexión")
        status_layout = QVBoxLayout(status_box)
        
        self.connection_status = QLabel("Desconectado")
        self.connection_status.setProperty("class", "disconnected-status")
        
        from datetime import datetime
        self.startup_datetime = datetime.now()
        self.startup_label = QLabel(f"Inicio: {self.startup_datetime.strftime('%d/%m/%Y %H:%M:%S')}")
        self.startup_label.setProperty("class", "status-label")
        
        self.last_update = QLabel("Última actualización: --:--:--")
        self.last_update.setProperty("class", "status-label")
        
        status_layout.addWidget(self.connection_status)
        status_layout.addWidget(self.startup_label)
        status_layout.addWidget(self.last_update)
        bottom_layout.addWidget(status_box)
        
        main_layout.addLayout(bottom_layout)
        
        self.setLayout(main_layout)

    def setup_timers(self):
        self.data_timer = QTimer(self)
        self.data_timer.timeout.connect(self.actualizar_datos)
        self.data_timer.start(1000)
        
        self.unit_timer = QTimer(self)
        self.unit_timer.timeout.connect(self.actualizar_unidades)
        self.unit_timer.start(60000)
        
        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.verificar_conexion)
        self.connection_timer.start(5000)

    def verificar_conexion(self):
        try:
            if self.medidor and hasattr(self.medidor, 'client') and self.medidor.client.connected:
                self.connection_status.setText("Conectado")
                self.connection_status.setProperty("class", "connected-status")
            else:
                self.connection_status.setText("Desconectado")
                self.connection_status.setProperty("class", "disconnected-status")
                
            self.style().unpolish(self.connection_status)
            self.style().polish(self.connection_status)
                
        except Exception as e:
            self.error_handler.log_error("DASH_CONN", f"Error verificando conexión: {str(e)}")

    def actualizar_unidades(self):
        try:
            if self.medidor and hasattr(self.medidor, 'obtener_unidad_flujo'):
                self.unidad_medidor = self.medidor.obtener_unidad_flujo()
            
            config = self.config_manager.cargar_config_general()
            self.unidad_visual = config.get("unidad_visualizacion", "m³/h")
            
            self.medidor_unit_label.setText(f"Medidor: {self.unidad_medidor}")
            self.visual_unit_label.setText(f"Visualización: {self.unidad_visual}")
            self.flow_unit.setText(self.unidad_visual)
            
        except Exception as e:
            self.error_handler.log_error("DASH_UNIT", f"Error actualizando unidades: {str(e)}")
            self.unidad_medidor = "m³/h"
            self.unidad_visual = "m³/h"

    def actualizar_datos(self):
        try:
            from datetime import datetime
            current_time = datetime.now()
            self.last_update.setText(f"Última actualización: {current_time.strftime('%d/%m/%Y %H:%M:%S')}")
            
            if not self.medidor or not hasattr(self.medidor, 'leer_registros'):
                self.system_status.setText("⚠️ Medidor no configurado")
                self.system_status.setProperty("class", "system-warning")
                self.style().unpolish(self.system_status)
                self.style().polish(self.system_status)
                return
                
            datos = self.medidor.leer_registros()
            
            flujo_valor = datos.get("flujo_instantaneo", 0.0)
            
            flujo_convertido = self.unit_converter.convert(
                flujo_valor,
                self.unidad_medidor,
                self.unidad_visual
            )
            
            volumen_valor = datos.get("flujo_acumulado", 0.0)
            velocidad_valor = datos.get("velocidad_flujo", 0.0)
            direccion_valor = datos.get("direccion_flujo", 0)
            
            self.flow_value.setText(f"{flujo_convertido:.3f}")
            self.volume_value.setText(f"{volumen_valor:.2f}")
            self.velocity_value.setText(f"{velocidad_valor:.3f}")
            
            if direccion_valor == 1:
                self.direction_value.setText("➡️ POSITIVA")
                self.direction_value.setProperty("class", "positive-flow")
            elif direccion_valor == 2:
                self.direction_value.setText("⬅️ NEGATIVA")
                self.direction_value.setProperty("class", "negative-flow")
            else:
                self.direction_value.setText("⏹️ DETENIDO")
                self.direction_value.setProperty("class", "stopped-flow")
                
            self.style().unpolish(self.direction_value)
            self.style().polish(self.direction_value)
            
            self.system_status.setText("✅ Sistema operativo")
            self.system_status.setProperty("class", "system-ok")
            self.style().unpolish(self.system_status)
            self.style().polish(self.system_status)
            
            try:
                energizacion = datos.get('contador_energizacion', None)
                self.lbl_energizacion.setText(str(energizacion) if energizacion is not None else "N/A")
                
                errores = datos.get('errores_sensor', {})
                errores_text = []
                if isinstance(errores, dict):
                    if errores.get('sensor_fault', False):
                        errores_text.append("Sensor")
                    if errores.get('over_range', False):
                        errores_text.append("Rango")
                    if errores.get('empty_pipe', False):
                        errores_text.append("Tubería")
                self.lbl_errores.setText(", ".join(errores_text) if errores_text else "Ninguno")
                
                cod_error = datos.get('codigo_error', None)
                self.lbl_cod_error.setText(f"{cod_error:04X}" if cod_error is not None else "N/A")
            
            except Exception as e:
                self.error_handler.log_error("DASH_STATS", f"Error actualizando estadísticas: {str(e)}")
                
        except Exception as e:
            self.error_handler.log_error("DASH_DATA", f"Error actualizando datos: {str(e)}")
            self.system_status.setText("⚠️ Error en lectura")
            self.system_status.setProperty("class", "system-error")
            self.style().unpolish(self.system_status)
            self.style().polish(self.system_status)
            self.flow_value.setText("--")
            self.volume_value.setText("--")
            self.velocity_value.setText("--")
            self.direction_value.setText("--")

    def refresh_unit_config(self):
        try:
            config = self.config_manager.cargar_config_general()
            self.unidad_visual = config.get("unidad_visualizacion", "m³/h")
            
            self.visual_unit_label.setText(f"Visualización: {self.unidad_visual}")
            self.flow_unit.setText(self.unidad_visual)
            
            self.actualizar_datos()
            
        except Exception as e:
            self.error_handler.log_error("DASH_REFRESH", f"Error refrescando unidades: {str(e)}")

    def closeEvent(self, event):
        self.data_timer.stop()
        self.unit_timer.stop()
        self.connection_timer.stop()
        event.accept()