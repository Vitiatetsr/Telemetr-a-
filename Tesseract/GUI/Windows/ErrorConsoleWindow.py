# GUI/Windows/ErrorConsoleWindow.py
import os
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QComboBox, QLabel, QHeaderView, QAbstractItemView, QLineEdit
)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QColor, QFont, QBrush
from Core.System.ErrorHandler import ErrorHandler

class ErrorConsoleWindow(QWidget):
    def __init__(self, error_handler):
        super().__init__()
        self.error_handler = error_handler
        self.log_file = "errores.log"
        self.last_modified = 0
        self.setup_ui()
        self.load_errors()
        
    def setup_ui(self):
        # Configuración principal
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # -- Barra de controles --
        control_layout = QHBoxLayout()
        
        # Filtro de nivel
        control_layout.addWidget(QLabel("Nivel:"))
        self.cmb_level = QComboBox()
        self.cmb_level.addItems(["TODOS", "INFO", "ADVERTENCIA", "ERROR", "CRÍTICO"])
        self.cmb_level.currentIndexChanged.connect(self.filter_errors)
        control_layout.addWidget(self.cmb_level)
        
        # Filtro de fecha
        control_layout.addWidget(QLabel("Fecha:"))
        self.txt_date = QLineEdit()
        self.txt_date.setPlaceholderText("YYYY-MM-DD")
        self.txt_date.setMaximumWidth(100)
        self.txt_date.textChanged.connect(self.filter_errors)
        control_layout.addWidget(self.txt_date)
        
        # Filtro de texto
        control_layout.addWidget(QLabel("Buscar:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Código o texto")
        self.txt_search.textChanged.connect(self.filter_errors)
        control_layout.addWidget(self.txt_search)
        
        # Botones de acción
        self.btn_clear = QPushButton("Limpiar Log")
        self.btn_clear.setStyleSheet("background-color: #E74C3C; color: white;")
        self.btn_clear.clicked.connect(self.clear_log)
        control_layout.addWidget(self.btn_clear)
        
        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.clicked.connect(self.load_errors)
        control_layout.addWidget(self.btn_refresh)
        
        control_layout.addStretch()
        main_layout.addLayout(control_layout)
        
        # -- Tabla de errores --
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Fecha/Hora", 
            "Nivel", 
            "Código", 
            "Descripción", 
            "Origen"
        ])
        
        # Configurar tabla
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        # Colores por nivel
        self.level_colors = {
            "INFO": QColor(52, 152, 219),
            "ADVERTENCIA": QColor(243, 156, 18),
            "ERROR": QColor(231, 76, 60),
            "CRÍTICO": QColor(155, 89, 182)
        }
        
        main_layout.addWidget(self.table)
        
        # -- Contador --
        self.lbl_count = QLabel("0 errores mostrados")
        self.lbl_count.setFont(QFont("Arial", 9))
        self.lbl_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        main_layout.addWidget(self.lbl_count)
        
        self.setLayout(main_layout)
        
        # Timer para actualización automática
        self.update_timer = QTimer()
        self.update_timer.setInterval(5000)  # 5 segundos
        self.update_timer.timeout.connect(self.check_log_changes)
        self.update_timer.start()

    def check_log_changes(self):
        """Verifica si el archivo de log ha cambiado"""
        if not os.path.exists(self.log_file):
            return
            
        current_modified = os.path.getmtime(self.log_file)
        if current_modified > self.last_modified:
            self.last_modified = current_modified
            self.load_errors()

    def load_errors(self):
        """Carga errores desde el archivo log con manejo de codificación"""
        if not os.path.exists(self.log_file):
            self.table.setRowCount(0)
            self.lbl_count.setText("Archivo de log no encontrado")
            return
            
        try:
            # INTENTAR DIFERENTES CODIFICACIONES
            for enconding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(self.log_file, "r", encoding=enconding) as f:
                        lines = f.readlines()
                    break  # Salir del loop si funciona
                except UnicodeDecodeError:
                    continue
            else:
                # Si todas fallan, usar utf-8 con manejo de errores
                with open(self.log_file, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readline()
            
            # Procesar líneas
            errors = []
            for line in lines:
                if not line.strip():
                    continue
                    
                # Parsear formato: [fecha] nivel: descripción
                parts = line.split("]", 1)
                if len(parts) < 2:
                    continue
                    
                timestamp = parts[0][1:].strip()
                rest = parts[1].split(":", 1)
                if len(rest) < 2:
                    continue
                    
                level = rest[0].strip()
                description = rest[1].strip()
                
                # Extraer código de error si existe
                code = ""
                if "KER-" in description:
                    code_start = description.find("KER-")
                    code_end = description.find(":", code_start)
                    if code_end != -1:
                        code = description[code_start+4:code_end]
                
                # Extraer origen (último componente antes de descripción)
                origin = ""
                if "-" in level:
                    origin = level.split("-")[-1].strip()
                    level = level.split("-")[0].strip()
                
                errors.append({
                    "timestamp": timestamp,
                    "level": level,
                    "code": code,
                    "description": description,
                    "origin": origin
                })
                
            # Almacenar todos los errores y aplicar filtros
            self.all_errors = errors
            self.filter_errors()
            
        except Exception as e:
            print(f"Error loading log: {e}")

    def filter_errors(self):
        """Aplica filtros seleccionados a los errores"""
        if not hasattr(self, 'all_errors'):
            return
            
        # Obtener criterios de filtrado
        level_filter = self.cmb_level.currentText()
        date_filter = self.txt_date.text().strip()
        text_filter = self.txt_search.text().strip().lower()
        
        # Filtrar errores
        filtered = []
        for error in self.all_errors:
            # Filtrar por nivel
            if level_filter != "TODOS" and level_filter != error["level"]:
                continue
                
            # Filtrar por fecha
            if date_filter and not error["timestamp"].startswith(date_filter):
                continue
                
            # Filtrar por texto
            if text_filter:
                text_match = (
                    text_filter in error["code"].lower() or
                    text_filter in error["description"].lower() or
                    text_filter in error["origin"].lower()
                )
                if not text_match:
                    continue
                    
            filtered.append(error)
            
        # Actualizar tabla
        self.table.setRowCount(len(filtered))
        
        for row, error in enumerate(filtered):
            # Fecha/Hora
            item_time = QTableWidgetItem(error["timestamp"])
            item_time.setData(Qt.UserRole, error["timestamp"])  # Para ordenamiento
            
            # Nivel con color
            item_level = QTableWidgetItem(error["level"])
            if error["level"] in self.level_colors:
                item_level.setForeground(QBrush(self.level_colors[error["level"]]))
                item_level.setFont(QFont("Arial", 9, QFont.Bold))
                
            # Código
            item_code = QTableWidgetItem(error["code"])
            
            # Descripción
            item_desc = QTableWidgetItem(error["description"])
            
            # Origen
            item_origin = QTableWidgetItem(error["origin"])
            
            # Añadir a tabla
            self.table.setItem(row, 0, item_time)
            self.table.setItem(row, 1, item_level)
            self.table.setItem(row, 2, item_code)
            self.table.setItem(row, 3, item_desc)
            self.table.setItem(row, 4, item_origin)
            
        # Ordenar por fecha más reciente primero
        self.table.sortItems(0, Qt.DescendingOrder)
        
        # Actualizar contador
        self.lbl_count.setText(f"{len(filtered)} de {len(self.all_errors)} errores mostrados")

    def clear_log(self):
        """Borra el contenido del archivo de log"""
        try:
            open(self.log_file, "w").close()
            self.last_modified = os.path.getmtime(self.log_file)
            self.load_errors()
            self.error_handler.log_evento("LOG limpiado manualmente")
        except Exception as e:
            print(f"Error clearing log: {e}")

    def closeEvent(self, event):
        self.update_timer.stop()
        super().closeEvent(event)