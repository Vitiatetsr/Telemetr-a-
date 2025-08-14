# Tesseract/GUI/Windows/DashboardWindow.py 

import time
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel, QGroupBox)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QMutex, Qt, QMutexLocker
from PyQt5.QtGui import QFont, QColor
from Core.Hardware.ModbusRTU_Manager import MedidorAguaBase
from Core.System.ConfigManager import ConfigManager
from Core.DataProcessing.Services import UnitConverter
from Core.System import StateManager

class DataAcquisitionThread(QThread):
    new_data = pyqtSignal(dict)
    
    def __init__(self, medidor):
        super().__init__()
        self.medidor = medidor
        self._mutex = QMutex()
        self._running = True
        self._last_data = {}
        
    def run(self):
        while self._running:
            try:
                data = self.medidor.leer_registros()
                
                with QMutexLocker(self._mutex):
                    self._last_data = data
                
                if self.receivers(self.new_data) > 0:
                    self.new_data.emit(data)
                    
                time.sleep(1)  
                    
            except Exception as e:
                if self.medidor and hasattr(self.medidor, 'error_handler'):
                    self.medidor.error_handler.log_error("DASH_ACQ", f"Error adquisición: {e}")
                else:
                    logging.error(f"Error adquisición: {e}")
                time.sleep(1)
    
    def stop(self):
        self._running = False
        self.wait()
        
    def get_last_data(self):
        with QMutexLocker(self._mutex):
            return self._last_data.copy()

class DashboardWindow(QWidget):
    def __init__(self, medidor, error_handler):
        super().__init__()
        # Medidor puede ser None inicialmente
        self.medidor = medidor
        self.error_handler = error_handler
        self.unit_converter = UnitConverter()
        self.display_unit = "L/s"
        self.base_unit = "m³/h"
        self.convert_fn = lambda x: x
        
        # INICIALIZACIÓN TEMPRANA DE ATRIBUTOS CRÍTICOS
        self.last_update_time = time.time()
        self.last_data = {}
        
        # Widgets de estadísticas
        self.lbl_energizacion = QLabel("N/A") 
        self.lbl_errores = QLabel("N/A")
        self.lbl_cod_error = QLabel("N/A")
        
        # Configurar UI incluso si medidor es None
        self.setup_unit_conversion()
        self.setup_ui()
        self.setup_extra_ui()
        
    def setup_extra_ui(self):
        # Grupo: información Adicional
        extra_group = QGroupBox("Estadísticas del Sensor")
        extra_layout = QGridLayout()
        
        # Contador de encendidos
        extra_layout.addWidget(QLabel("Encendidos:"), 0, 0)
        self.lbl_energizacion.setFont(QFont("Arial", 12))
        self.lbl_energizacion.setToolTip("Número total de encendidos del sensor")
        extra_layout.addWidget(self.lbl_energizacion, 0, 1)
        
        # Errores activos
        extra_layout.addWidget(QLabel("Errores:"), 1, 0)
        self.lbl_errores.setFont(QFont("Arial", 12))
        self.lbl_errores.setToolTip("Errores activos en el detector")
        extra_layout.addWidget(self.lbl_errores, 1, 1)
        
        # Código de error
        extra_layout.addWidget(QLabel("Código Error:"), 2, 0)
        self.lbl_cod_error.setFont(QFont("Consolas", 10))
        self.lbl_cod_error.setToolTip("Código hexadecimal de error del sistema")
        extra_layout.addWidget(self.lbl_cod_error, 2, 1)
        
        extra_group.setLayout(extra_layout)
        self.layout().insertWidget(2, extra_group)

    def setup_unit_conversion(self):
        """Configura conversión de unidades eficiente"""
        try:
            # Manejar caso donde medidor o perfil no están disponibles
            if not self.medidor or "registros" not in self.medidor.perfil:
                self.base_unit = "m³/s"
                config = ConfigManager.cargar_config_general()
                self.display_unit = config.get("unidad_visualizacion", "L/s")
                self.convert_fn = lambda x: x
                return
                
            reg_config = self.medidor.perfil["registros"].get(
                "flujo_instantaneo", 
                {"unidad": "m³/s"}  # Valor por defecto
            )
            self.base_unit = reg_config.get("unidad", "m³/s")
        
            config = ConfigManager.cargar_config_general()
            self.display_unit = config.get("unidad_visualizacion", "L/s")
        
            if self.base_unit == self.display_unit:
                self.convert_fn = lambda x: x
            else:
                strategy = self.get_conversion_strategy(self.base_unit, self.display_unit)
                self.convert_fn = lambda x: strategy(x)
        except Exception as e:
            self.error_handler.log_error("DASH_UNIT", f"Error configuración unidades: {e}")
            self.convert_fn = lambda x: x

    def get_conversion_strategy(self, from_unit: str, to_unit: str):
        converter = UnitConverter()
        key = (from_unit, to_unit)
        if key in converter.CONVERSION_STRATEGIES:
            return converter.CONVERSION_STRATEGIES[key]
        
        reverse_key = (to_unit, from_unit)
        if reverse_key in converter.CONVERSION_STRATEGIES:
            reverse_fn = converter.CONVERSION_STRATEGIES[reverse_key]
            return lambda x: x / reverse_fn(1) if reverse_fn(1) != 0 else x
        
        self.error_handler.log_error("UNIT_CONV", f"Conversión no soportada: {from_unit}→{to_unit}")
        return lambda x: x

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        data_group = QGroupBox("Medición en Tiempo Real")
        data_layout = QGridLayout()
        
        data_layout.addWidget(QLabel("Flujo Instantáneo:"), 0, 0)
        data_layout.addWidget(QLabel("Flujo Acumulado:"), 1, 0)
        data_layout.addWidget(QLabel("Estado:"), 2, 0)
        data_layout.addWidget(QLabel("Última Actualización:"), 3, 0)
        
        self.lbl_instant = QLabel(f"0.00 {self.display_unit}")
        self.lbl_instant.setFont(QFont("Arial", 24, QFont.Bold))
        self.lbl_instant.setStyleSheet("color: #2E86C1;")
        data_layout.addWidget(self.lbl_instant, 0, 1)
        
        self.lbl_accumulated = QLabel("0.00 m³")
        self.lbl_accumulated.setFont(QFont("Arial", 24, QFont.Bold))
        self.lbl_accumulated.setStyleSheet("color: #27AE60;")
        data_layout.addWidget(self.lbl_accumulated, 1, 1)
        
        self.lbl_status = QLabel("INICIALIZANDO...")
        self.lbl_status.setFont(QFont("Arial", 14))
        data_layout.addWidget(self.lbl_status, 2, 1)
        
        self.lbl_timestamp = QLabel("--")
        self.lbl_timestamp.setFont(QFont("Arial", 10))
        data_layout.addWidget(self.lbl_timestamp, 3, 1)
        
        data_group.setLayout(data_layout)
        main_layout.addWidget(data_group)
        
        flags_group = QGroupBox("Estado del Sistema")
        flags_layout = QVBoxLayout()
        
        self.lbl_flags = QLabel("Sin alertas")
        self.lbl_flags.setFont(QFont("Arial", 10))
        self.lbl_flags.setStyleSheet("color: #7D3C98;")
        flags_layout.addWidget(self.lbl_flags)
        
        flags_group.setLayout(flags_layout)
        main_layout.addWidget(flags_group)

        main_layout.addStretch()
        self.setLayout(main_layout)
        
        self.ui_timer = QTimer()
        self.ui_timer.setInterval(500)
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start()

    def setup_data_acquisition(self):
        """Inicia monitoreo si el medidor está disponible"""
        if self.medidor is None:
            self.lbl_status.setText("MEDIDOR NO CONFIGURADO")
            self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
            return
        
        self.data_thread = DataAcquisitionThread(self.medidor)
        self.data_thread.new_data.connect(self.on_new_data)
        self.data_thread.start()
        
        # Opcional: reiniciar valores
        self.last_update_time = time.time()
        self.last_data = {}
        self.lbl_status.setText("CONECTANDO...")
        
    def on_new_data(self, data):
        self.last_data = data
        self.last_update_time = time.time()
        
    def refresh_unit_config(self):
        """Actualizar la configuración de unidades cuando cambia la configuración"""
        try:
            self.setup_unit_conversion()
            self.lbl_instant.setText(f"0.00 {self.display_unit}")
            if hasattr(self, 'last_data') and self.last_data:
                raw_flow = self.last_data.get('flujo_instantaneo', 0)
                display_flow = self.convert_fn(raw_flow)
                self.lbl_instant.setText(f"{display_flow:.2f} {self.display_unit}")
            logging.info("Configuración de unidades actualizada")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("DASH_REFRESH", f"Error actualizando unidades: {e}")
            else:
                logging.error(f"Error actualizando unidades: {e}")
        
    def update_ui(self):
        elapsed = time.time() - self.last_update_time
        
        # Mostrar advertencia si no hay datos
        if not hasattr(self, 'last_data') or not self.last_data:
            self.lbl_status.setText("ESPERANDO DATOS...")
            self.lbl_status.setStyleSheet("color: orange;")
            return
        
        # Mostrar advertencia pero CONTINUAR procesando datos
        if elapsed > 5.0:
            self.lbl_status.setText("¡FALLO DE COMUNICACIÓN!")
            self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
        
        else:
            self.lbl_status.setText("CONECTADO")
            self.lbl_status.setStyleSheet("color: #27AE60; font-weight: bold;")
            
        # Siempre procesar últimos datos disponibles (aunque sean antiguos)
        try:
            raw_flow = self.last_data.get('flujo_instantaneo', 0)
            display_flow = self.convert_fn(raw_flow)
            
            self.lbl_instant.setText(f"{display_flow:.2f} {self.display_unit}")
            self.lbl_accumulated.setText(f"{self.last_data.get('flujo_acumulado', 0):.2f} m³")
            
            # Manejo de dirección de flujo (1 = positivo, 2 = negativo)
            direccion = self.last_data.get('direccion_flujo', 0)
            if direccion == 1:
                self.lbl_status.setText("CONECTADO (→)")
            elif direccion == 2:
                self.lbl_status.setText("CONECTADO (←)")
        
            flags = self.last_data.get('flags', {})
            flags_text = []
            
            if flags.get('alerta_presion', False):
                flags_text.append("⚠️ Alta presión")
            if flags.get('alerta_temperatura', False):
                flags_text.append("⚠️ Alta temperatura")
            if flags.get('fallo_sensor', False):
                flags_text.append("❌ Fallo sensor")
                
            if flags_text:
                self.lbl_flags.setText(" | ".join(flags_text))
                self.lbl_flags.setStyleSheet("color: #E74C3C; font-weight: bold;")
            else:
                self.lbl_flags.setText("✅ Operación normal")
                self.lbl_flags.setStyleSheet("color: #27AE60;")
                
            if elapsed > 2.0:
                self.lbl_status.setText("Comunicación lenta")
                self.lbl_status.setStyleSheet("color: orange;")
            else:
                self.lbl_status.setText("CONECTADO")
                self.lbl_status.setStyleSheet("color: #27AE60; font-weight: bold;")
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("DASH_UPDATE", f"Error actualizando UI: {e}")
            else:
                logging.error(f"Error actualizando UI: {e}")
        
        try:
            # Manejo de opcionales con N/A
            energizacion = self.last_data.get('contador_energizacion', None)
            self.lbl_energizacion.setText(str(energizacion) if energizacion is not None else "N/A")
    
            if energizacion is not None and energizacion > 1000:
                self.lbl_energizacion.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.lbl_energizacion.setStyleSheet("")
    
            errores = self.last_data.get('errores_sensor', {})
            errores_text = []
            if errores.get('sensor_fault', False):
                errores_text.append("Sensor")
            if errores.get('over_range', False):
                errores_text.append("Rango")
            if errores.get('empty_pipe', False):
                errores_text.append("Tubería")
    
            self.lbl_errores.setText(", ".join(errores_text) if errores_text else "Ninguno" if errores else "N/A")
    
            if errores_text:
                self.lbl_errores.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.lbl_errores.setStyleSheet("")
    
            cod_error = self.last_data.get('codigo_error', None)
            self.lbl_cod_error.setText(f"{cod_error:04X}" if cod_error is not None else "N/A")
    
            if cod_error is not None and cod_error != 0:
                self.lbl_cod_error.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.lbl_cod_error.setStyleSheet("color: #7D3C98;")
        
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error("DASH_EXTRA_UI", f"Error actualizando UI extra: {e}")
            else:
                logging.error(f"Error actualizando UI extra: {e}")
        
    def closeEvent(self, event):
        if hasattr(self, 'data_thread'):
            self.data_thread.stop()
            self.data_thread.wait(2000)
        super().closeEvent(event)