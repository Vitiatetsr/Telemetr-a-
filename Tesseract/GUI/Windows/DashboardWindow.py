# Tesseract/GUI/Windows/DashboardWindow.py

import logging
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QPalette, QFont
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
        
        # Estado inicial
        self.unidad_medidor = "m³/h"  # Valor por defecto hasta lectura
        self.unidad_visual = self.config_manager.cargar_config_general().get("unidad_visualizacion", "m³/h")
        self.unidad_volumen = "m³"    # Unidad base para volumen (no configurable)
        
        # Inicializar UI
        self.setup_ui()
        
        # Configurar temporizadores
        self.setup_timers()
        
        # Cargar configuración inicial
        self.actualizar_unidades()

    def setup_ui(self):
        """Configura todos los elementos de la interfaz de usuario"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(50, 50, 50, 50)
        
        # Panel de título
        title_layout = QHBoxLayout()
        self.title_label = QLabel("DASHBOARD DE MONITOREO")
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        title_layout.addWidget(self.title_label)
        
        # Estado del sistema
        self.system_status = QLabel("✅ Sistema operativo")
        self.system_status.setStyleSheet("color: green; font-weight: bold;")
        title_layout.addStretch()
        title_layout.addWidget(self.system_status)
        
        main_layout.addLayout(title_layout)
        
        # Separador
        separator = QLabel()
        separator.setStyleSheet("background-color: #CCCCCC; height: 2px;")
        main_layout.addWidget(separator)
        
        # Panel de datos principales - CORRECCIÓN COMPLETA DEL LAYOUT
        data_group = QGroupBox("Datos de Medición")
        data_layout = QGridLayout()
        data_layout.setSpacing(15)
        
        # FLUJO INSTANTÁNEO (columna 0)
        flow_label = QLabel("FLUJO INSTANTÁNEO:")  # Texto corregido
        flow_label.setStyleSheet("font-weight: bold;")
        data_layout.addWidget(flow_label, 0, 0)
        
        flow_container = QWidget()
        flow_h_layout = QHBoxLayout(flow_container)
        flow_h_layout.setContentsMargins(0, 0, 0, 0)
        flow_h_layout.setSpacing(5)
        
        self.flow_value = QLabel("--")
        self.flow_value.setStyleSheet("font-size: 50pt; color: #0066CC;")
        self.flow_value.setMinimumWidth(120)  # Ancho mínimo para valores
        self.flow_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.flow_unit = QLabel("m³/h")
        self.flow_unit.setStyleSheet("font-size: 40pt; color: #0066CC;")
        
        flow_h_layout.addWidget(self.flow_value)
        flow_h_layout.addWidget(self.flow_unit)
        flow_h_layout.addStretch()
        
        data_layout.addWidget(flow_container, 1, 0)
        
        # VOLUMEN ACUMULADO (columna 1)
        volume_label = QLabel("VOLUMEN ACUMULADO:")
        volume_label.setStyleSheet("font-weight: bold;")
        data_layout.addWidget(volume_label, 0, 1)
        
        volume_container = QWidget()
        volume_h_layout = QHBoxLayout(volume_container)
        volume_h_layout.setContentsMargins(0, 0, 0, 0)
        volume_h_layout.setSpacing(5)
        
        self.volume_value = QLabel("--")
        self.volume_value.setStyleSheet("font-size: 50pt; color: #009900;")
        self.volume_value.setMinimumWidth(120)  # Ancho mínimo para valores
        self.volume_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.volume_unit = QLabel("m³")
        self.volume_unit.setStyleSheet("font-size: 40pt; color: #009900;")
        
        volume_h_layout.addWidget(self.volume_value)
        volume_h_layout.addWidget(self.volume_unit)
        volume_h_layout.addStretch()
        
        data_layout.addWidget(volume_container, 1, 1)
        
        # DIRECCIÓN DE FLUJO (columna 0, span 2 columnas)
        direction_label = QLabel("DIRECCIÓN DE FLUJO:")  # Texto corregido
        direction_label.setStyleSheet("font-weight: bold;")
        data_layout.addWidget(direction_label, 2, 0, 1, 2)  # Span de 2 columnas
        
        self.direction_value = QLabel("--")
        self.direction_value.setStyleSheet("font-size: 50pt;")
        data_layout.addWidget(self.direction_value, 3, 0, 1, 2)  # Span de 2 columnas
        
        data_group.setLayout(data_layout)
        main_layout.addWidget(data_group)
        
        # Panel de información del sistema
        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)
        
        # Sección Estadísticas del Sensor
        sensor_stats_group = QGroupBox("Estadísticas del Sensor")
        sensor_stats_layout = QGridLayout()
        
        # Contador de encendidos
        sensor_stats_layout.addWidget(QLabel("Encendidos:"), 0, 0)
        self.lbl_energizacion = QLabel("N/A")
        self.lbl_energizacion.setFont(QFont("Arial", 20))
        sensor_stats_layout.addWidget(self.lbl_energizacion, 0, 1)
        
        # Errores activos
        sensor_stats_layout.addWidget(QLabel("Errores:"), 1, 0)
        self.lbl_errores = QLabel("N/A")
        self.lbl_errores.setFont(QFont("Arial", 20))
        sensor_stats_layout.addWidget(self.lbl_errores, 1, 1)
        
        # Código de error
        sensor_stats_layout.addWidget(QLabel("Código Error:"), 2, 0)
        self.lbl_cod_error = QLabel("N/A")
        self.lbl_cod_error.setFont(QFont("Consolas", 20))
        sensor_stats_layout.addWidget(self.lbl_cod_error, 2, 1)
        
        sensor_stats_group.setLayout(sensor_stats_layout)
        main_layout.addWidget(sensor_stats_group)
        
        # Panel inferior con unidades y conexión
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)
        
        # Unidades
        unit_box = QGroupBox("Configuración de Unidades")  # Texto corregido
        unit_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        unit_layout = QVBoxLayout(unit_box)
        
        self.medidor_unit_label = QLabel("Medidor: Cargando...")
        self.visual_unit_label = QLabel("Visualización: Cargando...")
        
        unit_layout.addWidget(self.medidor_unit_label)
        unit_layout.addWidget(self.visual_unit_label)
        bottom_layout.addWidget(unit_box)
        
        # Estado de conexión
        status_box = QGroupBox("Estado de Conexión")  # Texto corregido
        status_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        status_layout = QVBoxLayout(status_box)
        
        self.connection_status = QLabel("Desconectado")
        self.connection_status.setStyleSheet("color: #FF0000; font-weight: bold;")
        
        self.last_update = QLabel("Última actualización: --:--:--")  # Texto corregido
        
        status_layout.addWidget(self.connection_status)
        status_layout.addWidget(self.last_update)
        bottom_layout.addWidget(status_box)
        
        main_layout.addLayout(bottom_layout)
        
        self.setLayout(main_layout)

    def setup_timers(self):
        """Configura los temporizadores para actualización automática"""
        # Temporizador para datos rápidos (1 segundo)
        self.data_timer = QTimer(self)
        self.data_timer.timeout.connect(self.actualizar_datos)
        self.data_timer.start(1000)  # 1 segundo
        
        # Temporizador para actualización de unidades (60 segundos)
        self.unit_timer = QTimer(self)
        self.unit_timer.timeout.connect(self.actualizar_unidades)
        self.unit_timer.start(60000)  # 60 segundos
        
        # Temporizador para estado de conexión (5 segundos)
        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.verificar_conexion)
        self.connection_timer.start(5000)  # 5 segundos

    def verificar_conexion(self):
        """Actualiza el estado de conexión en la UI"""
        try:
            if self.medidor and hasattr(self.medidor, 'client') and self.medidor.client.connected:
                self.connection_status.setText("Conectado")
                self.connection_status.setStyleSheet("color: #009900; font-weight: bold;")
            else:
                self.connection_status.setText("Desconectado")
                self.connection_status.setStyleSheet("color: #FF0000; font-weight: bold;")
        except Exception as e:
            self.error_handler.log_error("DASH_CONN", f"Error verificando conexión: {str(e)}")

    def actualizar_unidades(self):
        """Actualiza la información de unidades desde el medidor y configuración"""
        try:
            # Obtener unidad del medidor (si está disponible)
            if self.medidor and hasattr(self.medidor, 'obtener_unidad_flujo'):
                self.unidad_medidor = self.medidor.obtener_unidad_flujo()
            
            # Obtener unidad de visualización desde configuración
            config = self.config_manager.cargar_config_general()
            self.unidad_visual = config.get("unidad_visualizacion", "m³/h")
            
            # Actualizar UI
            self.medidor_unit_label.setText(f"Medidor: {self.unidad_medidor}")
            self.visual_unit_label.setText(f"Visualización: {self.unidad_visual}")
            self.flow_unit.setText(self.unidad_visual)
            
        except Exception as e:
            self.error_handler.log_error("DASH_UNIT", f"Error actualizando unidades: {str(e)}")
            # Fallback a valores por defecto
            self.unidad_medidor = "m³/h"
            self.unidad_visual = "m³/h"

    def actualizar_datos(self):
        """Lee datos del medidor y actualiza la interfaz"""
        try:
            # Registrar hora de actualización
            from datetime import datetime
            self.last_update.setText(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
            
            # Verificar conexión
            if not self.medidor or not hasattr(self.medidor, 'leer_registros'):
                self.system_status.setText("⚠️ Medidor no configurado")
                self.system_status.setStyleSheet("color: #FF9900; font-weight: bold;")
                return
                
            # Leer datos del medidor - CLAVES DIRECTAS, NO USAR output_mapping
            datos = self.medidor.leer_registros()
            
            # Procesar flujo instantáneo
            flujo_valor = datos.get("flujo_instantaneo", 0.0)
            
            # Convertir a unidad de visualización
            flujo_convertido = self.unit_converter.convert(
                flujo_valor,
                self.unidad_medidor,
                self.unidad_visual
            )
            
            # Procesar volumen acumulado
            volumen_valor = datos.get("flujo_acumulado", 0.0)
            
            # Procesar dirección de flujo
            direccion_valor = datos.get("direccion_flujo", 0)
            
            # Actualizar UI
            self.flow_value.setText(f"{flujo_convertido:.3f}")
            self.volume_value.setText(f"{volumen_valor:.2f}")
            
            # Dirección de flujo
            if direccion_valor == 1:
                self.direction_value.setText("➡️ POSITIVA")
                self.direction_value.setStyleSheet("color: #0066CC; font-size: 18pt;")
            elif direccion_valor == 2:
                self.direction_value.setText("⬅️ NEGATIVA")
                self.direction_value.setStyleSheet("color: #FF6600; font-size: 18pt;")
            else:
                self.direction_value.setText("⏹️ DETENIDO")
                self.direction_value.setStyleSheet("color: #999999; font-size: 18pt;")
            
            # Actualizar estado del sistema
            self.system_status.setText("✅ Sistema operativo")
            self.system_status.setStyleSheet("color: #009900; font-weight: bold;")
            
            # Actualizar estadísticas del sensor
            try:
                # Contador de encendidos
                energizacion = datos.get('contador_energizacion', None)
                self.lbl_energizacion.setText(str(energizacion) if energizacion is not None else "N/A")
                
                # Errores activos
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
                
                # Código de error
                cod_error = datos.get('codigo_error', None)
                self.lbl_cod_error.setText(f"{cod_error:04X}" if cod_error is not None else "N/A")
                
            except Exception as e:
                self.error_handler.log_error("DASH_STATS", f"Error actualizando estadísticas: {str(e)}")
                
        except Exception as e:
            self.error_handler.log_error("DASH_DATA", f"Error actualizando datos: {str(e)}")
            self.system_status.setText("⚠️ Error en lectura")
            self.system_status.setStyleSheet("color: #FF0000; font-weight: bold;")
            self.flow_value.setText("--")
            self.volume_value.setText("--")
            self.direction_value.setText("--")

    def refresh_unit_config(self):
        """Actualiza la configuración de unidades (llamado desde MainWindow)"""
        try:
            # Obtener nueva unidad de visualización
            config = self.config_manager.cargar_config_general()
            self.unidad_visual = config.get("unidad_visualizacion", "m³/h")
            
            # Actualizar UI
            self.visual_unit_label.setText(f"Visualización: {self.unidad_visual}")
            self.flow_unit.setText(self.unidad_visual)
            
            # Forzar actualización de datos
            self.actualizar_datos()
            
        except Exception as e:
            self.error_handler.log_error("DASH_REFRESH", f"Error refrescando unidades: {str(e)}")

    def closeEvent(self, event):
        """Detiene los temporizadores al cerrar la ventana"""
        self.data_timer.stop()
        self.unit_timer.stop()
        self.connection_timer.stop()
        event.accept()