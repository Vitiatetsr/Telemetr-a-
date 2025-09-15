# Tesseract/GUI/Windows/FTPEmailConfigWindow.py

import json
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit,
    QPushButton, QTimeEdit, QCheckBox, QLabel, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import QTime
from Core.Network.FTPManager import FTPManager
from Core.System.ErrorHandler import ErrorHandler
from Core.System.StateManager import StateManager  # ✅ Nuevo import

class FTPEmailConfigWindow(QWidget):
    def __init__(self, file_scheduler, error_handler: ErrorHandler):
        super().__init__()
        self.file_scheduler = file_scheduler
        self.error_handler = error_handler
        self.setWindowTitle("Configuración FTP/Email")
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # FTP Configuration
        ftp_group = QGroupBox("Configuración FTP")
        ftp_layout = QFormLayout()
        
        self.ftp_host = QLineEdit()
        self.ftp_user = QLineEdit()
        self.ftp_pass = QLineEdit()
        self.ftp_pass.setEchoMode(QLineEdit.Password)
        self.ftp_remote_path = QLineEdit()
        
        ftp_layout.addRow("Servidor FTP:", self.ftp_host)
        ftp_layout.addRow("Usuario:", self.ftp_user)
        ftp_layout.addRow("Contraseña:", self.ftp_pass)
        ftp_layout.addRow("Ruta Remota:", self.ftp_remote_path)
        
        self.btn_test_ftp = QPushButton("Probar Conexión FTP")
        self.btn_test_ftp.clicked.connect(self.test_ftp_connection)
        ftp_layout.addRow(self.btn_test_ftp)
        
        ftp_group.setLayout(ftp_layout)
        main_layout.addWidget(ftp_group)

        # Email Configuration
        email_group = QGroupBox("Configuración Email")
        email_layout = QFormLayout()
        
        self.email_smtp = QLineEdit()
        self.email_port = QLineEdit()
        self.email_from = QLineEdit()
        self.email_to = QLineEdit()
        self.email_subject = QLineEdit()
        self.email_user = QLineEdit()
        self.email_pass = QLineEdit()
        self.email_pass.setEchoMode(QLineEdit.Password)
        
        email_layout.addRow("Servidor SMTP:", self.email_smtp)
        email_layout.addRow("Puerto:", self.email_port)
        email_layout.addRow("Remitente:", self.email_from)
        email_layout.addRow("Destinatarios (separados por coma):", self.email_to)
        email_layout.addRow("Asunto:", self.email_subject)
        email_layout.addRow("Usuario SMTP:", self.email_user)
        email_layout.addRow("Contraseña SMTP:", self.email_pass)
        
        self.btn_test_email = QPushButton("Probar Envío Email")
        self.btn_test_email.clicked.connect(self.test_email_sending)
        email_layout.addRow(self.btn_test_email)
        
        email_group.setLayout(email_layout)
        main_layout.addWidget(email_group)

        # Scheduling Configuration
        sched_group = QGroupBox("Programación de Envíos")
        sched_layout = QFormLayout()
        
        self.sched_time = QTimeEdit()
        self.sched_time.setDisplayFormat("HH:mm")
        self.sched_enabled = QCheckBox("Habilitar envío automático diario")
        
        sched_layout.addRow("Hora de envío:", self.sched_time)
        sched_layout.addRow(self.sched_enabled)
        
        sched_group.setLayout(sched_layout)
        main_layout.addWidget(sched_group)

        # Save Button
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Configuración")
        self.btn_save.clicked.connect(self.save_config)
        btn_layout.addWidget(self.btn_save)
        
        main_layout.addLayout(btn_layout)
        
        # Status Label
        self.status_label = QLabel()
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)

    def _clean_remote_path(self, path):
        """Convierte rutas con formato URL a ruta FTP válida"""
        if '://' in path:
            return '/' + path.split('://', 1)[1].split('/', 1)[1]
        elif '/' in path and '.' in path.split('/')[0]:
            return '/' + path.split('/', 1)[1]
        return path

    def load_config(self):
        """Carga la configuración actual desde archivos"""
        # Cargar configuración FTP
        try:
            if os.path.exists('Config/ftp_config.json'):
                with open('Config/ftp_config.json', 'r') as f:
                    ftp_config = json.load(f)
                    self.ftp_host.setText(ftp_config.get('host', ''))
                    self.ftp_user.setText(ftp_config.get('usuario', ''))
                    self.ftp_pass.setText(ftp_config.get('clave', ''))
                    self.ftp_remote_path.setText(ftp_config.get('ruta_remota', '/'))
        except Exception as e:
            self.error_handler.log_error("FTP_CONF_LOAD", f"Error cargando FTP: {e}")

        # Cargar configuración Email
        try:
            if os.path.exists('Config/email_config.json'):
                with open('Config/email_config.json', 'r') as f:
                    email_config = json.load(f)
                    self.email_smtp.setText(email_config.get('smtp_server', ''))
                    self.email_port.setText(str(email_config.get('smtp_port', 587)))
                    self.email_from.setText(email_config.get('from', ''))
                    self.email_to.setText(",".join(email_config.get('to', [])))
                    self.email_subject.setText(email_config.get('subject', ''))
                    self.email_user.setText(email_config.get('username', ''))
                    self.email_pass.setText(email_config.get('password', ''))
        except Exception as e:
            self.error_handler.log_error("EMAIL_CONF_LOAD", f"Error cargando Email: {e}")

        # Cargar configuración de programación
        self.sched_time.setTime(QTime(23, 59))  # Valor por defecto
        self.sched_enabled.setChecked(True)
        
        if hasattr(self.file_scheduler, 'config'):
            hora_envio = self.file_scheduler.config.get('hora_envio', '23:59')
            hora, minuto = map(int, hora_envio.split(':'))
            self.sched_time.setTime(QTime(hora, minuto))
            self.sched_enabled.setChecked(self.file_scheduler.config.get('enabled', True))

    def save_config(self):
        """Guardar configuración con sincronización en tiempo real"""
        try:
            # Crear directorio si no existe
            os.makedirs('Config', exist_ok=True)
            
            # SOLUCIÓN: Limpiar ruta remota
            clean_path = self._clean_remote_path(self.ftp_remote_path.text())
            
            # Guardar configuración FTP
            ftp_config = {
                "host": self.ftp_host.text(),
                "usuario": self.ftp_user.text(),
                "clave": self.ftp_pass.text(),
                "ruta_remota": clean_path  # Usar ruta limpia
            }
            with open('Config/ftp_config.json', 'w') as f:
                json.dump(ftp_config, f, indent=4)
            
            # Guardar configuración Email
            email_config = {
                "smtp_server": self.email_smtp.text(),
                "smtp_port": int(self.email_port.text()),
                "from": self.email_from.text(),
                "to": [t.strip() for t in self.email_to.text().split(',')],
                "subject": self.email_subject.text(),
                "username": self.email_user.text(),
                "password": self.email_pass.text()
            }
            with open('Config/email_config.json', 'w') as f:
                json.dump(email_config, f, indent=4)
            
            # Actualizar configuración de programación
            hora_config = self.sched_time.time().toString("HH:mm")
            self.file_scheduler.config['hora_envio'] = hora_config
            
            # SOLUCIÓN: Sincronizar ruta remota
            self.file_scheduler.config['ruta_remota'] = clean_path
            self.file_scheduler.transfer_service.config['ruta_remota'] = clean_path
            
            # Reiniciar scheduler si está habilitado
            if self.sched_enabled.isChecked():
                self.file_scheduler.detener()
                time.sleep(0.5)
                self.file_scheduler.iniciar()
            
            self.status_label.setText("✅ Configuración guardada exitosamente")
            # MARCAR CHECKPOINT AL GUARDAR
            StateManager.set_ready("ftp_email")
            QMessageBox.information(self, "Éxito", "Configuración guardada correctamente")
            
        except Exception as e:
            self.status_label.setText("❌ Error guardando configuración")
            self.error_handler.log_error("CONF_SAVE", f"Error guardando configuración: {e}")
            QMessageBox.critical(self, "Error", f"Error al guardar configuración: {str(e)}")

    def test_ftp_connection(self):
        """Prueba la conexión FTP con los parámetros actuales"""
        try:
            # Limpiar ruta para prueba
            clean_path = self._clean_remote_path(self.ftp_remote_path.text())
            
            ftp_config = {
                "host": self.ftp_host.text(),
                "usuario": self.ftp_user.text(),
                "clave": self.ftp_pass.text(),
                "ruta_remota": clean_path,
                "timeout": 10
            }
            
            ftp_manager = FTPManager(ftp_config, self.error_handler)
            if ftp_manager.verificar_conexion():
                QMessageBox.information(self, "Conexión FTP", "✅ Conexión FTP exitosa!")
            else:
                QMessageBox.warning(self, "Conexión FTP", "❌ Fallo en conexión FTP")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error probando FTP: {str(e)}")

    def test_email_sending(self):
        """Envía un email de prueba con los parámetros actuales"""
        try:
            # Crear mensaje de prueba
            msg = MIMEMultipart()
            msg['From'] = self.email_from.text()
            msg['To'] = self.email_to.text()
            msg['Subject'] = "Prueba de configuración - Tesseract"
            body = "Este es un correo de prueba para verificar la configuración SMTP."
            msg.attach(MIMEText(body, 'plain'))
            
            # Configurar conexión SMTP
            server = smtplib.SMTP(
                self.email_smtp.text(),
                int(self.email_port.text())
            )
            server.starttls()
            server.login(
                self.email_user.text(),
                self.email_pass.text()
            )
            
            # Enviar email
            server.sendmail(
                self.email_from.text(),
                [t.strip() for t in self.email_to.text().split(',')],
                msg.as_string()
            )
            server.quit()
            
            QMessageBox.information(self, "Prueba Email", "✅ Correo de prueba enviado exitosamente!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ Error enviando correo de prueba: {str(e)}")