# Tesseract/GUI/Windows/ReportsWindow.py 

import os
import json
import schedule
import threading
import time
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel
from PyQt5.QtCore import QTimer
from Core.System.ConfigManager import ConfigManager
from Core.System.StateManager import StateManager
from Core.System.ErrorHandler import ErrorHandler
from Core.DataProcessing.Services import RecordFormatter, ConfigProvider, BitmaskConverter, FileNameGenerator

class ReportsWindow(QWidget):
    def __init__(self, medidor, error_handler: ErrorHandler):
        super().__init__()
        self.medidor = medidor
        self.error_handler = error_handler
        
        # Widgets
        self.combo_formato = QComboBox()
        self.combo_formato.addItems(["Medidor", "SistemaMedicion"])
        self.btn_generar = QPushButton("Generar TXT")
        self.lbl_status = QLabel("Seleccione formato y pulse Generar")
        
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Formato de Reporte:"))
        layout.addWidget(self.combo_formato)
        layout.addWidget(self.btn_generar)
        layout.addWidget(self.lbl_status)
        self.setLayout(layout)
        
        # Conexiones
        self.btn_generar.clicked.connect(self.iniciar_proceso_reportes)
        
        # Timer para scheduler
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.verificar_tareas_programadas)
        self.timer.start(60000)
        self.scheduler_thread = None

    def iniciar_proceso_reportes(self):
        try:
            config = ConfigManager.cargar_config_general()
            usb_path = config.get("storage_path", "")
            hora_programada = config.get("hora_reporte", "23:00")
            
            # Guardar tipo de reporte seleccionado
            tipo_reporte = self.combo_formato.currentText()
            config["report_type"] = tipo_reporte
            ConfigManager.guardar_config_general(config)
            
            # Validación básica de USB
            if not usb_path:
                self.lbl_status.setText("❌ Ruta USB no configurada")
                return
            if not os.path.exists(usb_path):
                self.lbl_status.setText("❌ Ruta USB no existe")
                return

            # Programar tarea diaria (SIN pasar archivos histórico)
            self.programar_tarea_diaria(hora_programada)
            
            # Generar reporte inmediato
            self.generar_reporte_diario()
            self.lbl_status.setText("✅ Reporte diario programado")
            
        except Exception as e:
            self.lbl_status.setText(f"❌ Error: {str(e)}")
            self.error_handler.log_error("REP-INIT", str(e))

    def programar_tarea_diaria(self, hora: str):
        schedule.clear()
        schedule.every().day.at(hora).do(self.generar_reporte_diario)

    def generar_reporte_diario(self):
        try:
            config = ConfigManager.cargar_config_general()
            tipo_reporte = config.get("report_type", "Medidor")
            usb_path = config.get("storage_path", "")
            
            # Validacíón crítica de USB
            if not usb_path or not os.path.exists(usb_path):
                raise ValueError("Ruta USB no configurada o inválida")
            
            # Obtener medidor desde StateManager
            medidor = StateManager.get_state('medidor')
            if not medidor:
                raise ValueError("Medidor no configurado")
            
            # Obtener datos del medidor
            datos = medidor.leer_registros()
            perfil = medidor.perfil
            
            # Generar contenido con formato
            config_provider = ConfigProvider(ConfigManager())
            bitmask_converter = BitmaskConverter()
            formatter = RecordFormatter(config_provider, bitmask_converter)
            contenido = formatter.format(tipo_reporte, datos, perfil)
            
            name_gen = FileNameGenerator(config_provider)
            
            # 1. Archivo historico (USB) - SIN FECHA
            nombre_historico = name_gen.generate_historic_name(tipo_reporte)
            ruta_historico = os.path.join(usb_path, nombre_historico)
            
            with open(ruta_historico, 'a') as f:
                f.write(contenido + "\n")
            
            # 2. Crear archivo diario (pendientes_usb) - CON FECHA
            nombre_diario = name_gen.generate_daily_name(tipo_reporte)
            ruta_diario = os.path.join("pendientes_usb", nombre_diario)
            
            os.makedirs("pendientes_usb", exist_ok=True)
            with open(ruta_diario, 'w') as f:
                f.write(contenido)
                
        except Exception as e:
            self.error_handler.log_error("REP-GEN", f"Error generando reporte: {str(e)}")
    
    def verificar_tareas_programadas(self):
        """Ejecuta las tareas programadas pendientes."""
        schedule.run_pending()