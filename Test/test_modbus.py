import time 
from Core.Hardware.ModbusUtils import obtener_puertos_com
from Core.System.ConfigManager import ConfigManager
from Core.Hardware.ModbusRTU_Manager import ModbusRTUManager
from Core.System.ErrorHandler import ErrorHandler


def test_modbus_connection(retries=3, delay=2):
    """
    Prube la conexión al medidor RS485 usando la configuracion del sensor y reintentos automaticos.
    """
    error_handler = ErrorHandler()
    try:
        sensor_cfg = ConfigManager.cargar_config_sensor()["sensores"][0]
    except Exception as e:
        error_handler.log_error("CFG", f"Error al cargar configuración del sensor: {str(e)}")
        return False
    
    sensor = ModbusRTUManager(
        port=sensor_cfg["Puerto_serie"],
        baudrate=sensor_cfg["baudrate"],
        slave_id=sensor_cfg["slave_id"],
        parity=sensor_cfg.get("parity", "N")
    )
    
    
    for intento in range(1, retries + 1):
        print(f"Intento {intento} de conexión al medidor...")
        if sensor.connect(intentos=1):
            print("Conexión exitosa.")
            sensor.close()
            return True
        else:
            print("Conexión fallida.")
            time.sleep(delay)
            
    print("No se pudo establecer conexión tras varios intentos.")
    return False

if __name__ == "__main__":
    #Mostrar puertos COM detectados
    com_ports = obtener_puertos_com()
    print("Puertos COM disponibles:", com_ports)
    
    #Ejecutar la prueba de conexión 
    if test_modbus_connection(retries=3, delay=2):
        print("La conexión Modbus se estableció correctamente.")
    else:
        print("La conexión Modbus no pudo ser establecida.")