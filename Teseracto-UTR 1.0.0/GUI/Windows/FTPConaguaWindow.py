# TESERACTO-UTR/GUI/Windows/FTPConaguaWindow.py

import os
import re
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QComboBox, QPushButton, QMessageBox, QTextEdit, QGroupBox)
from PyQt5.QtCore import Qt
from Core.System.ConfigManager import ConfigManager
from Core.System.StateManager import StateManager
from Core.DataProcessing.Services import RecordFormatter, ConfigProvider, BitmaskConverter, FileNameGenerator
from Core.Network.FTPManager import FTPManager

class FTPConaguaWindow(QWidget):
    def __init__(self, error_handler):
        super().__init__()
        self.error_handler = error_handler
        self.setWindowTitle("FTP CONAGUA")
        self.setGeometry(100, 100, 600, 700)
        self.current_content = None
        self.current_filename = None
        self.setup_ui()
        self.load_ftp_config()
        self.apply_dark_theme()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Grupo para configuración FTP
        ftp_group = QGroupBox("Configuración FTP")
        ftp_layout = QVBoxLayout()

        # Campos FTP
        self.ftp_host = QLineEdit()
        self.ftp_port = QLineEdit("21")
        self.ftp_user = QLineEdit()
        self.ftp_password = QLineEdit()
        self.ftp_password.setEchoMode(QLineEdit.Password)
        self.ftp_remote_path = QLineEdit()

        ftp_layout.addWidget(QLabel("Servidor FTP:"))
        ftp_layout.addWidget(self.ftp_host)
        ftp_layout.addWidget(QLabel("Puerto:"))
        ftp_layout.addWidget(self.ftp_port)
        ftp_layout.addWidget(QLabel("Usuario:"))
        ftp_layout.addWidget(self.ftp_user)
        ftp_layout.addWidget(QLabel("Contraseña:"))
        ftp_layout.addWidget(self.ftp_password)
        ftp_layout.addWidget(QLabel("Ruta remota (opcional):"))
        ftp_layout.addWidget(self.ftp_remote_path)

        ftp_group.setLayout(ftp_layout)
        layout.addWidget(ftp_group)

        # Grupo para reporte CONAGUA
        report_group = QGroupBox("Reporte CONAGUA")
        report_layout = QVBoxLayout()

        # Tipo de reporte
        report_layout.addWidget(QLabel("Tipo de reporte:"))
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems(["Medidor", "SistemaMedicion"])
        report_layout.addWidget(self.report_type_combo)

        # Clave CONAGUA
        report_layout.addWidget(QLabel("Clave CONAGUA:"))
        self.clave_conagua = QLineEdit()
        self.clave_conagua.setMaxLength(5)
        self.clave_conagua.setPlaceholderText("Ejemplo: AB123")
        report_layout.addWidget(self.clave_conagua)

        # Botones de generación
        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Generar reporte Conagua")
        self.generate_btn.clicked.connect(self.generate_report)
        self.clear_btn = QPushButton("Borrar reporte")
        self.clear_btn.clicked.connect(self.clear_report)
        self.clear_btn.setEnabled(False)
        btn_layout.addWidget(self.generate_btn)
        btn_layout.addWidget(self.clear_btn)
        report_layout.addLayout(btn_layout)

        # Mostrar nombre de archivo
        report_layout.addWidget(QLabel("Nombre de archivo:"))
        self.filename_label = QLabel("")
        self.filename_label.setWordWrap(True)
        report_layout.addWidget(self.filename_label)

        # Mostrar contenido
        report_layout.addWidget(QLabel("Contenido del reporte:"))
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        report_layout.addWidget(self.content_text)

        report_group.setLayout(report_layout)
        layout.addWidget(report_group)

        # Botón de enviar
        self.send_btn = QPushButton("Enviar a servidor")
        self.send_btn.clicked.connect(self.send_report)
        self.send_btn.setEnabled(False)
        layout.addWidget(self.send_btn)

        self.setLayout(layout)

    def apply_dark_theme(self):
        dark_theme = """
            QWidget {
                background-color: #2b2b2b;
                color: #cccccc;
                font-family: Segoe UI;
            }
            QLabel {
                color: #cccccc;
                padding: 2px;
            }
            QComboBox, QLineEdit, QTextEdit {
                background-color: #3b3b3b;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
            QComboBox:hover, QLineEdit:hover, QTextEdit:hover {
                border: 1px solid #777777;
            }
            QPushButton {
                background-color: #5a5a5a;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #666666;
                border: 1px solid #777777;
            }
            QPushButton:pressed {
                background-color: #777777;
            }
            QPushButton:disabled {
                background-color: #3b3b3b;
                color: #777777;
            }
            QGroupBox {
                color: #cccccc;
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #cccccc;
            }
        """
        self.setStyleSheet(dark_theme)

    def load_ftp_config(self):
        """Cargar configuración FTP existente si está disponible"""
        try:
            config = ConfigManager.cargar_config_ftp()
            self.ftp_host.setText(config.get("host", ""))
            self.ftp_port.setText(str(config.get("port", "21")))
            self.ftp_user.setText(config.get("usuario", ""))
            self.ftp_password.setText(config.get("clave", ""))
            self.ftp_remote_path.setText(config.get("ruta_remota", ""))
        except:
            pass

    def validate_clave(self, clave):
        """Validar formato de clave CONAGUA: 2 letras + 3 números"""
        if len(clave) != 5:
            return False
        if not clave[:2].isalpha():
            return False
        if not clave[2:].isdigit():
            return False
        return True

    def generate_report(self):
        """Generar el reporte CONAGUA con la última lectura del medidor"""
        # Validar clave CONAGUA
        clave = self.clave_conagua.text().strip()
        if not self.validate_clave(clave):
            QMessageBox.warning(self, "Clave inválida", 
                            "La clave CONAGUA debe tener exactamente 2 letras seguidas de 3 números.")
            return

        # Obtener el medidor desde StateManager (igual que en Dashboard)
        medidor = StateManager.get_state('medidor')
        if not medidor:
            QMessageBox.warning(self, "Error", "No hay medidor configurado o conectado.")
            return

        # Leer los datos del medidor (igual que en Dashboard)
        try:
            datos = medidor.leer_registros()
        except Exception as e:
            QMessageBox.warning(self, "Error", 
                            f"No se pudieron leer los datos del medidor: {str(e)}")
            return

        perfil = medidor.perfil
        # Obtener código KER del ErrorHandler
        ker_code = self.error_handler.get_ker_code()

        # Obtener el tipo de reporte
        tipo_reporte = self.report_type_combo.currentText()

        # Generar el contenido del reporte base
        config_provider = ConfigProvider(ConfigManager())
        bitmask_converter = BitmaskConverter()
        formatter = RecordFormatter(config_provider, bitmask_converter)
        
        try:
            contenido = formatter.format(tipo_reporte, datos, perfil, ker_code)
        except Exception as e:
            QMessageBox.warning(self, "Error", 
                            f"Error al formatear el reporte: {str(e)}")
            return

        # Agregar la clave CONAGUA al final del contenido
        contenido_con_clave = contenido + f"|{clave}"

        # Generar el nombre del archivo con fecha
        name_gen = FileNameGenerator(config_provider)
        filename = name_gen.generate_daily_name(tipo_reporte)

        # Mostrar en la interfaz
        self.filename_label.setText(filename)
        self.content_text.setPlainText(contenido_con_clave)

        # Habilitar botones
        self.clear_btn.setEnabled(True)
        self.send_btn.setEnabled(True)

        # Guardar para envío
        self.current_content = contenido_con_clave
        self.current_filename = filename

        QMessageBox.information(self, "Éxito", "Reporte generado correctamente.")

    def clear_report(self):
        """Limpiar el reporte generado"""
        self.filename_label.setText("")
        self.content_text.setPlainText("")
        self.current_content = None
        self.current_filename = None
        self.clear_btn.setEnabled(False)
        self.send_btn.setEnabled(False)

    def send_report(self):
        """Enviar el reporte al servidor FTP"""
        if not self.current_content or not self.current_filename:
            QMessageBox.warning(self, "Error", "No hay reporte generado para enviar.")
            return

        # Validar campos FTP
        host = self.ftp_host.text().strip()
        port = self.ftp_port.text().strip()
        user = self.ftp_user.text().strip()
        password = self.ftp_password.text().strip()
        remote_path = self.ftp_remote_path.text().strip()

        if not host or not user or not password:
            QMessageBox.warning(self, "Error", 
                            "Complete los campos obligatorios del FTP (servidor, usuario y contraseña).")
            return

        # Crear archivo temporal
        temp_path = os.path.join(os.getcwd(), self.current_filename)
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(self.current_content)
        except Exception as e:
            QMessageBox.warning(self, "Error", 
                            f"No se pudo crear el archivo temporal: {str(e)}")
            return

        # Enviar via FTP
        try:
            # Crear configuración para FTPManager
            ftp_config = {
                "host": host,
                "usuario": user,
                "clave": password,
                "port": int(port) if port else 21,
                "ruta_remota": remote_path
            }
            ftp_manager = FTPManager(ftp_config, self.error_handler)
            remote_filename = os.path.join(remote_path, self.current_filename) if remote_path else self.current_filename
            success = ftp_manager.enviar_archivo(temp_path, remote_filename)
            if success:
                QMessageBox.information(self, "Éxito", "Reporte enviado correctamente al servidor FTP.")
            else:
                QMessageBox.warning(self, "Error", "No se pudo enviar el reporte. Verifique la conexión.")
        except Exception as e:
            QMessageBox.warning(self, "Error", 
                            f"Error al enviar el reporte: {str(e)}")
        finally:
            # Eliminar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass