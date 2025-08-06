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
from Core.DataProcessing.Services import RecordFormatter, ConfigProvider, BitmaskConverter

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
            
            if not usb_path:
                self.lbl_status.setText("❌ Ruta USB no configurada")
                return
            if not os.path.exists(usb_path):
                self.lbl_status.setText("❌ Ruta USB no existe")
                return

            # Crear archivo histórico en USB
            archivo_historico = os.path.join(usb_path, "historico_mediciones.txt")
            if not os.path.exists(archivo_historico):
                open(archivo_historico, 'w').close()

            # Programar tarea diaria
            self.programar_tarea_diaria(hora_programada, archivo_historico)
            
            # Generar reporte inmediato
            self.generar_reporte_diario(archivo_historico)
            self.lbl_status.setText("✅ Reporte diario programado")
            
        except Exception as e:
            self.lbl_status.setText(f"❌ Error: {str(e)}")
            self.error_handler.log_error("REP-INIT", str(e))

    def programar_tarea_diaria(self, hora: str, archivo_historico: str):
        schedule.clear()
        schedule.every().day.at(hora).do(
            self.generar_reporte_diario,
            archivo_historico=archivo_historico
        )
        
        if not self.scheduler_thread or not self.scheduler_thread.is_alive():
            self.scheduler_thread = threading.Thread(target=self.ejecutar_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()

    def ejecutar_scheduler(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def verificar_tareas_programadas(self):
        pass

    def generar_reporte_diario(self, archivo_historico=None):
        try:
            config = ConfigManager.cargar_config_general()
            tipo_reporte = config.get("report_type", "Medidor")
            
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
            
            # 1. Escribir en histórico (USB)
            if archivo_historico:
                with open(archivo_historico, 'a') as f:
                    f.write(contenido + "\n")
            
            # 2. Crear reporte pendiente
            os.makedirs("pendientes_usb", exist_ok=True)
            archivo_pendiente = os.path.join("pendientes_usb", f"reporte_{datetime.now().strftime('%Y%m%d')}.txt")
            with open(archivo_pendiente, 'w') as f:
                f.write(contenido)
                
        except Exception as e:
            self.error_handler.log_error("REP-GEN", f"Error generando reporte: {str(e)}")