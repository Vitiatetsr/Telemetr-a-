# Tesseract/Core/Hardware/ModbusUtils.py

import serial.tools.list_ports
import re
import logging

def obtener_puertos_com(only_modbus=False, modbus_patterns=None):
    """
    Retorna lista de puertos COM disponibles, con opción de filtrar
    dispositivos Modbus usando expresiones regulares avanzadas.

    Args:
        only_modbus (bool): Si True, filtra puertos que probablemente sean Modbus.
        modbus_patterns (list[str]): Lista de patrones regex para filtrar puertos.

    Returns:
        List[str]: Lista de nombres de puertos COM.
    """
    try:
        ports = serial.tools.list_ports.comports()
    except Exception as e:
        logging.error(f"Error al listar puertos COM: {e}")
        return []

    if only_modbus:
        patterns = modbus_patterns or [
            r'USB.*Serial', r'COM\d+', r'FTDI', r'Prolific', r'CH340', r'CP210', r'Arduino'
        ]
        return [
            port.device for port in ports
            if any(re.search(pattern, port.description, re.IGNORECASE) for pattern in patterns)
        ]
    return [port.device for port in ports]