from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian 
import logging
import time 



class ModbusRTUManager:
    def __init__(self, port: str, baudrate: int, slave_id: int, parity: str = "N"):
        if parity not in ['N', 'E', 'O']:
            raise ValueError("Paridad invalida. Valores permitidos: N, E, O")
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity=parity,
            stopbits=1,
            bytesize=8,
            timeout=2
        )
        self.slave_id = slave_id
        self.logger = logging.getLogger(__name__)
    
    
    def connect(self, intentos=3) -> bool:
        """
        Intenta conectar utilizando hasta 'intentos' reintentos.
        Retorna True si la conexión fue exitosa.
        """
        for i in range(intentos):
            try:
                if not self.client.connected:
                    self.client.connect()
                if self.client.connected:
                    return True
            except ModbusException as e:
                self.logger.error(f"Intento {i+1} fallido: {str(e)}")
                time.sleep(2)
        return False
    
    
    def test_connection(self, retries=3, delay=2) -> bool:
        """
        Realiza una prueba de conexión con reintentos.
        Devuelve True si en alguno de los intentos la conexión es exitosa.
        """
        for attempt in range(1, retries + 1):
            self.logger.info(f"Test connection attempt {attempt}")
            if self.connect(intentos=1):
                self.close()
                return True 
            time.sleep(delay)
        return False
    
    
    def read_registers(self, address: int, count: int, intentos=3):
        for i in range(intentos):
            if not self.client.connected and not self.connect():
                self.logger.error("KER-007: No se pudo reconectar al sensor")
                return None
            try:
                response = self.client.read_input_registers(address, count, slave=self.slave_id)
                if response.isError() or not response.registers:
                    raise ModbusException(f"Respuesta inválida: {response}")
                
                #Ejemplo: Si se tratan registros para flujo (float) o totalizadores (uint), decidifica
                if address in [0x0004, 0x0008]:
                    return self._decode_32bit_float(response.registers)
                elif address in [0x0008, 0x0011]:
                    return self._decode_32bit_uint(response.registers)
                else:
                    return response.registers
            except ModbusException as e:
                self.logger.error(f"KER-007 (Intento {i+1}): {str(e)}")
                time.sleep(2)
        return None
    
    
    def _decode_31bit_float(self, registers):
        decoder = BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
        return decoder.decode_32bit_float()
    
    
    def _decode_32bit_uint(self, registers):
        decoder = BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
        return decoder.decode_32bit_uint()
    
    
    def close(self):
        if self.client.connected:
            self.client.close()