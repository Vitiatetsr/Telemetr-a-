# Tesseract/GUI/Windows/ConfigWindow.py
# Tesseract/GUI/Windows/ConfigWindow.py

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, 
    QLineEdit, QPushButton, QFormLayout, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator
from Core.Hardware import ModbusUtils
from Core.System.ConfigManager import ConfigManager
from Core.System import ErrorHandler

class ConfigWindow(QWidget):
    def __init__(self, medidor, error_handler):
        super().__init__()
        self.medidor = medidor
        self.error_handler = error_handler
        self.current_profile = {}
        self.setup_ui()
        self.load_initial_config()
        
    def setup_ui(self):
        # Configuración principal
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Área desplazable para muchos parámetros
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        
        # -- Sección: Conexión Serial --
        serial_group = QGroupBox("Configuración Modbus RTU")
        serial_layout = QFormLayout()
        
        # Puerto COM
        self.cmb_ports = QComboBox()
        self.cmb_ports.setMinimumWidth(150)
        serial_layout.addRow("Puerto COM:", self.cmb_ports)
        
        # Baudrate
        self.cmb_baudrate = QComboBox()
        self.cmb_baudrate.addItems(["9600", "19200", "38400", "57600", "115200"])
        serial_layout.addRow("Baudrate:", self.cmb_baudrate)
        
        # Paridad
        self.cmb_parity = QComboBox()
        self.cmb_parity.addItems(["Ninguna", "Par", "Impar"])
        serial_layout.addRow("Paridad:", self.cmb_parity)
        
        # Bits de parada
        self.cmb_stopbits = QComboBox()
        self.cmb_stopbits.addItems(["1", "1.5", "2"])
        serial_layout.addRow("Bits de parada:", self.cmb_stopbits)
        
        # ID Esclavo (¡Rango Modbus válido!)
        self.txt_slave_id = QLineEdit("1")
        self.txt_slave_id.setValidator(QIntValidator(1, 247))  # CORRECCIÓN CRÍTICA
        serial_layout.addRow("ID Esclavo:", self.txt_slave_id)
        
        # Botón detección puertos
        self.btn_refresh_ports = QPushButton("Detectar Puertos")
        self.btn_refresh_ports.clicked.connect(self.refresh_com_ports)
        serial_layout.addRow(self.btn_refresh_ports)
        
        serial_group.setLayout(serial_layout)
        content_layout.addWidget(serial_group)
        
        # -- Sección: Perfil de Sensor --
        sensor_group = QGroupBox("Perfil de Medidor")
        sensor_layout = QVBoxLayout()
        
        # Selector de perfiles
        self.cmb_profiles = QComboBox()
        self.cmb_profiles.currentIndexChanged.connect(self.load_profile)
        sensor_layout.addWidget(QLabel("Perfil Predefinido:"))
        sensor_layout.addWidget(self.cmb_profiles)
        
        # Campos editables
        self.profile_form = QFormLayout()
        self.profile_form.addRow("Modelo:", QLineEdit())
        self.profile_form.addRow("Fabricante:", QLineEdit())
        sensor_layout.addLayout(self.profile_form)
        
        # Campos para endianness y word order
        endian_layout = QHBoxLayout()
        self.cmb_endianness = QComboBox()
        self.cmb_endianness.addItems(["Big", "Little"])
        endian_layout.addWidget(QLabel("Endianness:"))
        endian_layout.addWidget(self.cmb_endianness)
        
        self.cmb_word_order = QComboBox()
        self.cmb_word_order.addItems(["Big", "Little"])
        endian_layout.addWidget(QLabel("Word Order:"))
        endian_layout.addWidget(self.cmb_word_order)
        serial_layout.addRow(endian_layout)
        
        # Campos para escalas
        self.txt_esc_instant = QLineEdit("0.001")
        self.txt_esc_instant.setValidator(QDoubleValidator(0.00001, 10000.1, 5))
        serial_layout.addRow("Escala Flujo Inst:", self.txt_esc_instant)
        
        self.txt_esc_accum = QLineEdit("1.0")
        self.txt_esc_accum.setValidator(QDoubleValidator(0.00001, 10000.0, 5))
        serial_layout.addRow("Escala Flujo Acum:", self.txt_esc_accum)
        
        # Registros
        reg_group = QGroupBox("Asignación de Registros")
        reg_layout = QFormLayout()
        
        self.reg_instant = QLineEdit("40001")
        self.reg_instant.setValidator(QIntValidator(0, 65535))
        reg_layout.addRow("Flujo Instantáneo:", self.reg_instant)
        
        self.reg_accumulated = QLineEdit("40003")
        self.reg_accumulated.setValidator(QIntValidator(0, 65535))
        reg_layout.addRow("Flujo Acumulado:", self.reg_accumulated)
        
        self.reg_dir = QLineEdit("40010")
        self.reg_dir.setValidator(QIntValidator(0, 65535))
        reg_layout.addRow("Dirección de Flujo:", self.reg_dir)
        
        self.reg_energizacion = QLineEdit("245")
        reg_layout.addRow("Energización:", self.reg_energizacion)
        
        self.reg_errores_sensor = QLineEdit("246")
        reg_layout.addRow("Errores Sensor:", self.reg_errores_sensor)
        
        self.reg_codigo_error = QLineEdit("257")
        reg_layout.addRow("Código Error:", self.reg_codigo_error)
        
        reg_group.setLayout(reg_layout)
        sensor_layout.addWidget(reg_group)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Perfil")
        self.btn_save.clicked.connect(self.save_profile)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_apply = QPushButton("Aplicar Configuración")
        self.btn_apply.clicked.connect(self.apply_config)
        btn_layout.addWidget(self.btn_apply)
        
        sensor_layout.addLayout(btn_layout)
        sensor_group.setLayout(sensor_layout)
        content_layout.addWidget(sensor_group)
        
        # Sección: Config Guardada
        self.lbl_status = QLabel("Configuración no guardada")
        self.lbl_status.setFont(QFont("Arial", 10, QFont.Bold))
        self.lbl_status.setStyleSheet("color: #E74C3C;")
        content_layout.addWidget(self.lbl_status)
        
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
        
        # Timer para actualización periódica
        self.update_timer = QTimer()
        self.update_timer.setInterval(5000)
        self.update_timer.timeout.connect(self.refresh_com_ports)
        self.update_timer.start()

    class ConnectionWorker(QThread):
        finished = pyqtSignal(bool, str)
        
        def __init__(self, medidor, profile, parent=None):
            super().__init__(parent)
            self.medidor = medidor
            self.profile = profile
        
        def run(self):
            try:
                # SOLUCIÓN: Usar el lock nativo de Python, no Qt
                with self.medidor._connection_lock:
                    # Desconectar y reiniciar conexión
                    self.medidor.desconectar()
                    self.medidor.perfil = self.profile
                    self.medidor._init_client()
                    
                    # Conexión con timeout controlado
                    success = self.medidor.conectar()
                    message = "✅ Configuración aplicada" if success else "❌ Conexión fallida"
                    self.finished.emit(success, message)
            except Exception as e:
                self.finished.emit(False, f"❌ Error crítico: {str(e)}")


    def load_initial_config(self):
        """Carga inicial diferida para mejor rendimiento"""
        QTimer.singleShot(100, self.load_profiles)
        self.refresh_com_ports()
        if self.medidor.perfil:
            self.current_profile = self.medidor.perfil
            self.show_profile(self.current_profile)

    def load_profiles(self):
        """Carga perfiles disponibles sin bloquear UI"""
        self.cmb_profiles.clear()
        try:
            profiles = ConfigManager.obtener_perfiles_predefinidos()
            self.cmb_profiles.addItem("-- Nuevo Perfil --", None)
            for profile in profiles:
                self.cmb_profiles.addItem(profile["nombre"], profile)
        except Exception as e:
            self.error_handler.log_error("CONFIG_LOAD", f"Error cargando perfiles: {e}")

    def refresh_com_ports(self):
        """Actualiza lista de puertos COM disponibles"""
        current = self.cmb_ports.currentText()
        self.cmb_ports.clear()
        try:
            ports = ModbusUtils.obtener_puertos_com(only_modbus=True)
            self.cmb_ports.addItems(ports)
            if current in ports:
                self.cmb_ports.setCurrentText(current)
            elif ports:
                self.cmb_ports.setCurrentIndex(0)
        except Exception as e:
            self.error_handler.log_error("PORT_REFRESH", f"Error detectando puertos: {e}")

    def load_profile(self, index):
        """Carga perfil seleccionado en formulario"""
        profile = self.cmb_profiles.itemData(index)
        if not profile:
            self.clear_form()
            return
        self.show_profile(profile)
        self.current_profile = profile

    def show_profile(self, profile):
        """Muestra perfil en UI"""
        # Conexión
        self.cmb_ports.setCurrentText(profile.get("puerto_serie", ""))
        self.cmb_baudrate.setCurrentText(str(profile.get("baudrate", 9600)))
        self.cmb_parity.setCurrentText(self.map_parity(profile.get("parity", "N")))
        self.cmb_stopbits.setCurrentText(str(profile.get("stopbits", 1)))
        self.txt_slave_id.setText(str(profile.get("slave_id", 1)))
        
        # Parámetros críticos
        if "endianness" in profile:
            self.cmb_endianness.setCurrentText(profile["endianness"].capitalize())
        if "word_order" in profile:
            self.cmb_word_order.setCurrentText(profile["word_order"].capitalize())
            
        # Información general
        for i in range(self.profile_form.rowCount()):
            widget = self.profile_form.itemAt(i, QFormLayout.FieldRole).widget()
            if isinstance(widget, QLineEdit):
                if i == 0:
                    widget.setText(profile.get("modelo", ""))
                elif i == 1:
                    widget.setText(profile.get("fabricante", ""))
        
        # Registros
        registros = profile.get("registros", {})
        self.reg_instant.setText(str(registros.get("flujo_instantaneo", {}).get("address", 237)))
        self.reg_accumulated.setText(str(registros.get("flujo_acumulado", {}).get("address", 207)))
        self.reg_dir.setText(str(registros.get("direccion_flujo", {}).get("address", 301)))
        self.reg_energizacion.setText(str(registros.get("contador_energizacion", {}).get("address", 245)))
        self.reg_errores_sensor.setText(str(registros.get("errores_sensor", {}).get("address", 246)))
        self.reg_codigo_error.setText(str(registros.get("codigo_error", {}).get("address", 257)))
        
        # Escalas
        self.txt_esc_instant.setText(str(registros.get("flujo_instantaneo", {}).get("escala", 0.001)))
        self.txt_esc_accum.setText(str(registros.get("flujo_acumulado", {}).get("escala", 1.0)))
        
        self.lbl_status.setText("Perfil cargado")
        self.lbl_status.setStyleSheet("color: #27AE60;")

    def map_parity(self, parity_char):
        mapping = {"N": "Ninguna", "E": "Par", "O": "Impar"}
        return mapping.get(parity_char.upper(), "Ninguna")

    def unmap_parity(self, text):
        mapping = {"Ninguna": "N", "Par": "E", "Impar": "O"}
        return mapping.get(text, "N")

    def clear_form(self):
        """Limpia formulario para nuevo perfil"""
        self.cmb_ports.setCurrentIndex(0)
        self.cmb_baudrate.setCurrentIndex(0)
        self.cmb_parity.setCurrentIndex(0)
        self.cmb_stopbits.setCurrentIndex(0)
        self.txt_slave_id.setText("1")
        
        for i in range(self.profile_form.rowCount()):
            widget = self.profile_form.itemAt(i, QFormLayout.FieldRole).widget()
            if isinstance(widget, QLineEdit):
                widget.clear()
        
        self.reg_instant.setText("40001")
        self.reg_accumulated.setText("40003")
        self.reg_dir.setText("40010")
        self.reg_energizacion.setText("245")
        self.reg_errores_sensor.setText("246")
        self.reg_codigo_error.setText("257")
        
        self.current_profile = {}
        self.lbl_status.setText("Listo para nuevo perfil")
        self.lbl_status.setStyleSheet("color: #3498DB;")

    def save_profile(self):
        """Guarda perfil actual en configuración con validación mejorada"""
        try:
            # Validar campos obligatorios
            modelo = self.profile_form.itemAt(0, QFormLayout.FieldRole).widget().text()
            if not modelo.strip():
                raise ValueError("El modelo no puede estar vacío")
                
            # Validar campos numéricos
            campos_numericos = {
                "Flujo Instantáneo": self.reg_instant,
                "Flujo Acumulado": self.reg_accumulated,
                "Dirección de Flujo": self.reg_dir,
                "Energización": self.reg_energizacion,
                "Errores Sensor": self.reg_errores_sensor,
                "Código Error": self.reg_codigo_error,
                "ID Esclavo": self.txt_slave_id
            }
            
            for nombre, campo in campos_numericos.items():
                if not campo.text().strip():
                    raise ValueError(f"El campo '{nombre}' no puede estar vacío")
                try:
                    int(campo.text())
                except ValueError:
                    raise ValueError(f"Valor inválido en '{nombre}': debe ser un número entero")
            
            # Validar escalas
            try:
                float(self.txt_esc_instant.text())
                float(self.txt_esc_accum.text())
            except ValueError:
                raise ValueError("Las escalas deben ser valores numéricos")
            
            # Recolectar datos y guardar
            profile = self.collect_form_data()
            ConfigManager.guardar_perfil_sensor(profile, es_nuevo=True)
            self.load_profiles()
            
            self.lbl_status.setText("✅ Perfil guardado exitosamente")
            self.lbl_status.setStyleSheet("color: #27AE60;")
            
        except Exception as e:
            self.error_handler.log_error("CONFIG_SAVE", f"Error guardando perfil: {e}")
            self.lbl_status.setText(f"❌ Error: {str(e)}")
            self.lbl_status.setStyleSheet("color: #E74C3C;")
            
            # Mostrar mensaje de error al usuario
            QMessageBox.critical(
                self,
                "Error al guardar",
                f"No se pudo guardar el perfil:\n\n{str(e)}",
                QMessageBox.Ok
            )

    def apply_config(self):
        """Aplica configuración con validación extendida"""
        try:
            # Validar campos obligatorios
            if not self.cmb_ports.currentText():
                raise ValueError("Seleccione un puerto COM")
                
            # Validar campos numéricos
            campos_numericos = {
                "ID Esclavo": self.txt_slave_id,
                "Flujo Instantáneo": self.reg_instant,
                "Flujo Acumulado": self.reg_accumulated,
                "Dirección de Flujo": self.reg_dir,
                "Energización": self.reg_energizacion,
                "Errores Sensor": self.reg_errores_sensor,
                "Código Error": self.reg_codigo_error
            }
            
            for nombre, campo in campos_numericos.items():
                if not campo.text().strip():
                    raise ValueError(f"El campo '{nombre}' no puede estar vacío")
                try:
                    valor = int(campo.text())
                    if not (0 <= valor <= 65535):
                        raise ValueError(f"Valor inválido en '{nombre}': debe estar entre 0-65535")
                except ValueError:
                    raise ValueError(f"Valor inválido en '{nombre}': debe ser un número entero")
            
            # Validar escalas
            try:
                float(self.txt_esc_instant.text())
                float(self.txt_esc_accum.text())
            except ValueError:
                raise ValueError("Las escalas deben ser valores numéricos")
            
            # Recolectar datos
            profile = self.collect_form_data()
            
            # Deshabilitar UI durante operación
            self.setEnabled(False)
            self.lbl_status.setText("Aplicando configuración...")
            self.lbl_status.setStyleSheet("color: #3498DB;")
            
            # Crear y configurar worker
            self.worker = self.ConnectionWorker(self.medidor, profile)
            self.worker.finished.connect(self.handle_connection_result)
            self.worker.start()
            
        except Exception as e:
            self.handle_connection_error(e)

    def handle_connection_result(self, success, message):
        """Maneja resultado de la conexión en segundo plano"""
        self.setEnabled(True)
        self.lbl_status.setText(message)
        self.lbl_status.setStyleSheet("color: #27AE60;" if success else "color: #E74C3C;")
        
        if success:
            QTimer.singleShot(500, self.force_initial_read)

    def handle_connection_error(self, error):
        """Maneja errores durante la conexión"""
        self.setEnabled(True)
        self.error_handler.log_error("CONFIG_APPLY", f"Error crítico: {error}")
        self.lbl_status.setText(f"❌ Error: {str(error)}")
        self.lbl_status.setStyleSheet("color: #E74C3C;")
        
        # Mostrar mensaje de error detallado
        QMessageBox.critical(
            self,
            "Error de Conexión",
            f"No se pudo aplicar la configuración:\n\n{str(error)}\n\n"
            "Verifique los parámetros de conexión e intente nuevamente.",
            QMessageBox.Ok
        )

    def collect_form_data(self):
        """Recopila datos del formulario con validación incorporada"""
        # Validar que todos los campos numéricos tengan valores
        campos = [
            self.reg_instant, self.reg_accumulated, self.reg_dir,
            self.reg_energizacion, self.reg_errores_sensor, self.reg_codigo_error
        ]
        
        for campo in campos:
            if not campo.text().isdigit():
                raise ValueError("Todos los campos de registros deben contener números")
        
        # Construir perfil
        profile = {
            "puerto_serie": self.cmb_ports.currentText(),
            "baudrate": int(self.cmb_baudrate.currentText()),
            "parity": self.unmap_parity(self.cmb_parity.currentText()),
            "stopbits": float(self.cmb_stopbits.currentText()),
            "bytesize": 8,
            "timeout": 1.5,
            "slave_id": int(self.txt_slave_id.text()),
            "endianness": self.cmb_endianness.currentText().lower(),
            "word_order": self.cmb_word_order.currentText().lower(),
            "funcion_default": 3,
            "modelo": self.profile_form.itemAt(0, QFormLayout.FieldRole).widget().text(),
            "fabricante": self.profile_form.itemAt(1, QFormLayout.FieldRole).widget().text(),
            "registros": {
                "flujo_instantaneo": {
                    "address": int(self.reg_instant.text()),
                    "count": 2,
                    "data_type": "float32",
                    "escala": float(self.txt_esc_instant.text()),
                    "unidad": "m³/s"
                },
                "flujo_acumulado": {
                    "address": int(self.reg_accumulated.text()),
                    "count": 2,
                    "data_type": "float32",
                    "escala": float(self.txt_esc_accum.text()),
                    "unidad": "m³"
                },
                "direccion_flujo": {
                    "address": int(self.reg_dir.text()),
                    "count": 1,
                    "data_type": "int16",
                    "funcion": 3
                },
                "contador_energizacion": {
                    "address": int(self.reg_energizacion.text()),
                    "count": 1,
                    "data_type": "int16"
                },
                "errores_sensor": {
                    "address": int(self.reg_errores_sensor.text()),
                    "count": 1,
                    "data_type": "error"
                },
                "codigo_error": {
                    "address": int(self.reg_codigo_error.text()),
                    "count": 1,
                    "data_type": "int16"
                }
            },
            "output_mapping": {
                "flujo_instantaneo": "flujo_instantaneo",
                "flujo_acumulado": "flujo_acumulado",
                "direccion_flujo": "direccion_flujo"
            }
        }
        
        return profile
    
    def force_initial_read(self):
        """Fuerza lectura inicial para verificar conexión"""
        try:
            if self.medidor.leer_registros():
                self.lbl_status.setText("✅ Lectura inicial exitosa")
        except Exception as e:
            self.lbl_status.setText(f"⚠️ Error en lectura: {str(e)}")
            self.lbl_status.setStyleSheet("color: #E67E22;")

    def closeEvent(self, event):
        self.update_timer.stop()
        super().closeEvent(event)