# GUI/Windows/LoginWindow.py
from PyQt5.QtWidgets import QWidget, QLineEdit, QPushButton, QVBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal
from Core.System.ConfigManager import ConfigManager

class LoginWindow(QWidget):
    login_success = pyqtSignal(str)  # Señal con nombre de usuario

    def __init__(self, error_handler):
        super().__init__()
        self.error_handler = error_handler
        self.setWindowTitle("Login Tesseract")
        self.setFixedSize(300, 150)
        
        # Widgets
        self.txt_user = QLineEdit(placeholderText="Usuario")
        self.txt_pass = QLineEdit(placeholderText="Contraseña", echoMode=QLineEdit.Password)
        self.btn_login = QPushButton("Iniciar Sesión")
        self.lbl_status = QLabel()
        
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.txt_user)
        layout.addWidget(self.txt_pass)
        layout.addWidget(self.btn_login)
        layout.addWidget(self.lbl_status)
        self.setLayout(layout)
        
        # Conexiones
        self.btn_login.clicked.connect(self.authenticate)
        self.txt_pass.returnPressed.connect(self.authenticate)

    def authenticate(self):
        user = self.txt_user.text().strip()
        password = self.txt_pass.text()
        
        if ConfigManager.validar_credenciales(user, password):
            self.login_success.emit(user)
        else:
            self.lbl_status.setText("❌ Credenciales inválidas")
            self.error_handler.log_evento("LOGIN_FAIL", f"Intento fallido para usuario: {user}")