import time
import threading
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from Core.System.ConfigManager import ConfigManager
from Core.Hardware.ModbusRTU_Manager import ModbusRTUManager
from Core.DataProcessing.DataProcessor import DataProcessor
from Core.DataProcessing.DataFormatter import DataFormatter
from Core.Network.FTPManager import FTPManager
from Core.Network.SMSManager import SMSManager
from Core.Network.InternetManager import InternetManager
from Core.Hardware.USBManejador import USBManejador
from Core.System.ErrorHandler import ErrorHandler

class FileScheduler:
    def __init__(self):
        self.error_handler = ErrorHandler()
        self._cargar_configuracion()
        self._inicializar_base_datos()
        self._inicializar_programador()
        
    def _cargar_configuracion(self):
        try:
            self.config = ConfigManager.cargar_config_general()
            self.sensor_cfg = ConfigManager.cargar_config_sensor()["sensores"][0]
            self.ftp_cfg = ConfigManager.cargar_config_ftp()
            self.sms_cfg = ConfigManager.cargar_config_sms()
        except Exception as e:
            self.error_handler.log_error("010", f"Error cargando config: {str(e)}")
            raise

    def _inicializar_base_datos(self):
        self.conn = sqlite3.connect('pendientes.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS cola_pendientes
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             contenido TEXT NOT NULL,
                             intentos INTEGER DEFAULT 0,
                             proximo_intento DATETIME)''')
        self.conn.commit()

    def _inicializar_programador(self):
        self.sched = BackgroundScheduler(daemon=True)
        hora_programada = self.config.get("hora_programada", "00:01")
        
        hour, minute = map(int, hora_programada.split(":"))
        # Envío diario
        self.sched.add_job(self._generar_txt1, 'cron', hour=hour, minute=minute)
        # Exportación USB diaria
        self.sched.add_job(self._generar_txt2, 'cron', hour=hour, minute=minute)
        # Procesar pendientes cada hora
        self.sched.add_job(self._procesar_cola_pendientes, 'interval', hours=1)
        
        self.sched.start()

    def _obtener_datos_sensor(self):
        """
        Lee múltiples registros del sensor según manual MV110-210:
         - Porcentaje de flujo (regs 2-3)
         - Flujo instantáneo (regs 4-5)
         - Velocidad (regs 6-7)
         - Flujo acumulado (regs 8-9)
         - Totalizador T+ y decimales (regs 8-9, reg 10)
         - Totalizador P+ y decimales (regs 11-12, reg 13)
         - Flags de proceso (reg 20)
         - Temperatura CPU (reg 28)
         - Batería (reg 27)
        Devuelve un dict con todos los valores decodificados.
        """
        try:
            cfg = self.sensor_cfg
            sensor = ModbusRTUManager(
                port=cfg["puerto_serie"],
                baudrate=cfg["baudrate"],
                slave_id=cfg["slave_id"],
                parity=cfg.get("parity", "N")
            )
            if not sensor.connect():
                raise ConnectionError("KER-007: Fallo de conexión al sensor")
            
            # Leer registros
            regs_pct = sensor.read_registers(2, 2)    # % flujo
            regs_inst = sensor.read_registers(4, 2)   # flujo instantáneo
            regs_spd = sensor.read_registers(6, 2)    # velocidad
            regs_acu = sensor.read_registers(8, 2)    # flujo acumulado
            
            # Totalizador T+
            regs_T = sensor.read_registers(8, 2)      # mismos regs que flujo acumulado
            dec_T = sensor.read_registers(10, 1)[0] & 0xFF  # LSB = decimales
            
            # Totalizador P+
            regs_P = sensor.read_registers(11, 2)
            dec_P = sensor.read_registers(13, 1)[0] & 0xFF
            
            # Flags de proceso (MSB/LSB)
            reg_flags = sensor.read_registers(20, 1)
            flags = reg_flags[0] if reg_flags else 0
            
            # Temperatura CPU
            reg_temp = sensor.read_registers(28, 1)
            temp = reg_temp[0] / 10.0 if reg_temp else 0.0
            
            # Batería
            reg_batt = sensor.read_registers(27, 1)
            batt = reg_batt[0] if reg_batt else 0
            
            sensor.close()
            
            return {
                "porcentaje_flujo": DataProcessor.decode_32bit_float(regs_pct),
                "flujo_instantaneo": DataProcessor.decode_32bit_float(regs_inst),
                "velocidad": DataProcessor.decode_32bit_float(regs_spd),
                "flujo_acumulado": DataProcessor.decode_32bit_float(regs_acu),
                "totalizador_T": DataProcessor.decode_32bit_uint(regs_T),
                "decimales_T": dec_T,
                "totalizador_P": DataProcessor.decode_32bit_uint(regs_P),
                "decimales_P": dec_P,
                "flags": flags,
                "temperatura": temp,
                "bateria": batt
            }
        except Exception as e:
            self.error_handler.log_error("010", f"Error sensor: {str(e)}")
            return None

    def _generar_txt1(self):
        datos = self._obtener_datos_sensor()
        if not datos:
            return
        
        # Antes de enviar, asegurarnos de tener internet
        if not InternetManager.wait_for_connection():
            # Añadir a cola y salir
            contenido = DataFormatter.formatear_registro("Medidor", datos)
            self._agregar_a_cola_pendientes(contenido)
            return
        
        contenido = DataFormatter.formatear_registro("Medidor", datos)
        exito_ftp = FTPManager(self.ftp_cfg["host"], self.ftp_cfg["usuario"]).enviar_alerta(contenido)
        exito_sms = SMSManager(**self.sms_cfg).enviar_alerta(contenido, self.sms_cfg["numero_destino"])
        
        if not (exito_ftp and exito_sms):
            self._agregar_a_cola_pendientes(contenido)

    def _generar_txt2(self):
        datos = self._obtener_datos_sensor()
        if not datos:
            return
        
        nombre_archivo = DataFormatter.generar_nombre_archivo("SistemaMedicion")
        USBManejador.guardar_en_usb(DataFormatter.formatear_registro("SistemaMedicion", datos),
                                    nombre_archivo)

    def _agregar_a_cola_pendientes(self, contenido: str):
        self.cursor.execute('''INSERT INTO cola_pendientes 
                            (contenido, intentos, proximo_intento)
                            VALUES (?, ?, ?)''',
                            (contenido, 0, datetime.now() + timedelta(minutes=30)))
        self.conn.commit()

    def _procesar_cola_pendientes(self):
        # Procesa envíos pendientes, reintentando con backoff exponencial
        self.cursor.execute('''SELECT id, contenido, intentos 
                            FROM cola_pendientes 
                            WHERE proximo_intento <= ?''', (datetime.now(),))
        pendientes = self.cursor.fetchall()
        
        for id_, contenido, intentos in pendientes:
            if not InternetManager.wait_for_connection():
                continue
            
            exito_ftp = FTPManager(self.ftp_cfg["host"], self.ftp_cfg["usuario"]).enviar_alerta(contenido)
            exito_sms = SMSManager(**self.sms_cfg).enviar_alerta(contenido, self.sms_cfg["numero_destino"])
            
            if exito_ftp and exito_sms:
                self.cursor.execute("DELETE FROM cola_pendientes WHERE id = ?", (id_,))
            else:
                nuevo_intento = datetime.now() + timedelta(hours=2 ** intentos)
                self.cursor.execute('''UPDATE cola_pendientes 
                                    SET intentos = ?, 
                                        proximo_intento = ?
                                    WHERE id = ?''',
                                    (intentos + 1, nuevo_intento, id_))
            self.conn.commit()

    def detener(self):
        self.sched.shutdown()
        self.conn.close()

    def iniciar(self):
        pass

if __name__ == "__main__":
    fs = FileScheduler()
    try:
        # Mantener el scheduler vivo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        fs.detener()
