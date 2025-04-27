import serial.tools.list_ports

def obtener_puertos_com():
    """
    Retorna una lista de dispositivos COM disponibles usando pyserial.
    """
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]
