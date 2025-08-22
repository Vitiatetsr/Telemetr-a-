# Tesseract/GUI/Windows/SMSConfigWindow.py

import json
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit,
    QPushButton, QCheckBox, QLabel, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt
from Core.System.ErrorHandler import ErrorHandler
from Core.Network.AlertManager import AlertManager

class SMSConfigWindow(QWidget):
    def __init__(self, error_handler: ErrorHandler):
        super().__init__()
        self.error_handler = error_handler
        self.setWindowTitle("Configuración SMS")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # SMS Configuration
        sms_group = QGroupBox("Configuración SMS Twilio")
        sms_layout = QFormLayout()
        
        self.sms_enabled = QCheckBox("Habilitar envío de SMS")
        self.sms_enabled.setChecked(True)
        
        self.account_sid = QLineEdit()
        self.account_sid.setPlaceholderText("Ej: ACa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6")
        
        self.auth_token = QLineEdit()
        self.auth_token.setEchoMode(QLineEdit.Password)
        self.auth_token.setPlaceholderText("Tu token de autenticación Twilio")
        
        self.twilio_number = QLineEdit()
        self.twilio_number.setPlaceholderText("Ej: +1234567890")
        
        self.destination_number = QLineEdit()
        self.destination_number.setPlaceholderText("Ej: +521234567890")
        
        sms_layout.addRow(self.sms_enabled)
        sms_layout.addRow("Account SID:", self.account_sid)
        sms_layout.addRow("Auth Token:", self.auth_token)
        sms_layout.addRow("Número Twilio:", self.twilio_number)
        sms_layout.addRow("Número Destino:", self.destination_number)
        
        self.btn_test_sms = QPushButton("Probar Envío SMS")
        self.btn_test_sms.clicked.connect(self.test_sms_sending)
        sms_layout.addRow(self.btn_test_sms)
        
        sms_group.setLayout(sms_layout)
        main_layout.addWidget(sms_group)

        # Save Button
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Configuración")
        self.btn_save.clicked.connect(self.save_config)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.close)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)
        
        # Status Label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)

    def load_config(self):
        """Carga la configuración SMS actual desde el archivo"""
        try:
            config_path = 'Config/sms_config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    sms_config = json.load(f)
                    
                    self.sms_enabled.setChecked(sms_config.get('use_sms', True))
                    self.account_sid.setText(sms_config.get('account_sid', ''))
                    self.auth_token.setText(sms_config.get('auth_token', ''))
                    self.twilio_number.setText(sms_config.get('numero_twilio', ''))
                    self.destination_number.setText(sms_config.get('numero_destino', ''))
                    
        except Exception as e:
            self.error_handler.log_error("SMS_CONF_LOAD", f"Error cargando configuración SMS: {e}")
            self.status_label.setText("❌ Error cargando configuración")

    def save_config(self):
        """Guarda la configuración SMS en el archivo"""
        try:
            # Validar campos obligatorios si SMS está habilitado
            if self.sms_enabled.isChecked():
                if not all([self.account_sid.text().strip(), 
                           self.auth_token.text().strip(),
                           self.twilio_number.text().strip(),
                           self.destination_number.text().strip()]):
                    QMessageBox.warning(self, "Campos incompletos", 
                                      "Todos los campos son obligatorios cuando SMS está habilitado.")
                    return
            
            # Crear directorio si no existe
            os.makedirs('Config', exist_ok=True)
            
            # Guardar configuración SMS
            sms_config = {
                "use_sms": self.sms_enabled.isChecked(),
                "account_sid": self.account_sid.text().strip(),
                "auth_token": self.auth_token.text().strip(),
                "numero_twilio": self.twilio_number.text().strip(),
                "numero_destino": self.destination_number.text().strip()
            }
            
            with open('Config/sms_config.json', 'w') as f:
                json.dump(sms_config, f, indent=4)
            
            self.status_label.setText("✅ Configuración SMS guardada exitosamente")
            QMessageBox.information(self, "Éxito", "Configuración SMS guardada correctamente")
            
        except Exception as e:
            self.status_label.setText("❌ Error guardando configuración SMS")
            self.error_handler.log_error("SMS_CONF_SAVE", f"Error guardando configuración SMS: {e}")
            QMessageBox.critical(self, "Error", f"Error al guardar configuración SMS: {str(e)}")

    def test_sms_sending(self):
        """Envía un SMS de prueba con la configuración actual"""
        try:
            # Validar campos
            if not all([self.account_sid.text().strip(), 
                       self.auth_token.text().strip(),
                       self.twilio_number.text().strip(),
                       self.destination_number.text().strip()]):
                QMessageBox.warning(self, "Campos incompletos", 
                                  "Complete todos los campos para probar el envío de SMS.")
                return
            
            # Crear configuración temporal para prueba
            test_config = {
                "use_sms": True,
                "account_sid": self.account_sid.text().strip(),
                "auth_token": self.auth_token.text().strip(),
                "numero_twilio": self.twilio_number.text().strip(),
                "numero_destino": self.destination_number.text().strip()
            }
            
            # Crear AlertManager y enviar prueba
            alert_manager = AlertManager(test_config, self.error_handler)
            success = alert_manager.enviar_alerta(
                "Este es un mensaje de prueba del sistema Tesseract", 
                self.destination_number.text().strip()
            )
            
            if success:
                QMessageBox.information(self, "Prueba SMS", "✅ SMS de prueba enviado exitosamente!")
            else:
                QMessageBox.warning(self, "Prueba SMS", "❌ Fallo en envío de SMS. Verifique la configuración.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ Error enviando SMS de prueba: {str(e)}")