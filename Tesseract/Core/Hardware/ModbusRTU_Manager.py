# Tesseract/Core/Hardware/ModbusRTU_Manager.py -

import logging
import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Union, Optional
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from Core.System.ErrorHandler import ErrorHandler

RegisterValue = Union[float, int, Dict[str, bool]]

class IMedidorAgua(ABC):
    """Interfaz para todos los tipos de medidores de agua"""
    @abstractmethod
    def leer_registros(self) -> Dict[str, RegisterValue]:
        pass

    @abstractmethod
    def conectar(self) -> bool:
        pass

    @abstractmethod
    def desconectar(self):
        pass

class ModbusDecoderStrategy(ABC):
    """Estrategia para decodificación de registros"""
    @abstractmethod
    def decodificar(self, registers: list, reg_config: Dict[str, Any], perfil: Dict[str, Any]) -> RegisterValue:
        pass

class Float32Decoder(ModbusDecoderStrategy):
    def decodificar(self, registers, reg_config, perfil) -> float:
        byteord = Endian.BIG if perfil.get("endianness") == "big" else Endian.LITTLE
        wordord = Endian.BIG if perfil.get("word_order") == "big" else Endian.LITTLE
        dec = BinaryPayloadDecoder.fromRegisters(registers, byteorder=byteord, wordorder=wordord)
        return dec.decode_32bit_float() * reg_config.get("escala", 1.0)

class Int16Decoder(ModbusDecoderStrategy):
    def decodificar(self, registers, reg_config, perfil) -> int:
        if reg_config.get("no_escalar", False):
            return registers[0]
        return registers[0] * reg_config.get("escala", 1)

class UInt32Decoder(ModbusDecoderStrategy):
    def decodificar(self, registers, reg_config, perfil) -> int:
        byteord = Endian.BIG if perfil.get("endianness") == "big" else Endian.LITTLE
        wordord = Endian.BIG if perfil.get("word_order") == "big" else Endian.LITTLE
        dec = BinaryPayloadDecoder.fromRegisters(registers, byteorder=byteord, wordorder=wordord)
        return dec.decode_32bit_uint() * reg_config.get("escala", 1)

class BitmaskDecoder(ModbusDecoderStrategy):
    def decodificar(self, registers, reg_config, perfil) -> Dict[str, bool]:
        value = registers[0]
        return {desc: bool(value & (1 << int(bit))) for bit, desc in reg_config.get("bit_map", {}).items()}

class ErrorDecoder(ModbusDecoderStrategy):
    """Decodificador para registros de error"""
    def decodificar(self, registers, reg_config, perfil) -> Dict[str, bool]:
        error_code = registers[0]
        return {
            "sensor_fault": bool(error_code & 0x01),
            "over_range": bool(error_code & 0x02),
            "empty_pipe": bool(error_code & 0x04),
        }

class DecoderFactory:
    _decoders = {
        "float32": Float32Decoder(),
        "int16": Int16Decoder(),
        "uint32": UInt32Decoder(),
        "bitmask": BitmaskDecoder(),
        "error": ErrorDecoder()
    }
    
    @classmethod
    def register_decoder(cls, data_type: str, decoder: ModbusDecoderStrategy):
        cls._decoders[data_type] = decoder
        
    @classmethod
    def get_decoder(cls, data_type: str) -> Optional[ModbusDecoderStrategy]:
        return cls._decoders.get(data_type)

class MedidorAguaBase(IMedidorAgua):
    """Implementación base para medidores de agua"""
    DECODER_FACTORY = DecoderFactory
    
    def __init__(self, perfil_sensor: Dict[str, Any], error_handler: ErrorHandler):
        self.perfil = perfil_sensor
        self.error_handler = error_handler
        self.logger = logging.getLogger(f"{__name__}.{type(self).__name__}")
        self.client = None
        self._connection_lock = threading.RLock()  # 🚀 Solución para errores de lock
        self._init_client()

    def _init_client(self):
        """Inicializa o reinicializa el cliente Modbus"""
        with self._connection_lock:
            if self.client is None or not self.client.connected:
                self.client = ModbusSerialClient(
                    port=self.perfil["puerto_serie"],
                    baudrate=self.perfil["baudrate"],
                    parity=self._map_parity(self.perfil.get("parity", "N")),
                    stopbits=self.perfil.get("stopbits", 1),
                    bytesize=self.perfil.get("bytesize", 8),
                    timeout=self.perfil.get("timeout", 1.5)
                )

    def _map_parity(self, parity_char: str) -> str:
        mapping = {'N': 'N', 'E': 'E', 'O': 'O'}
        return mapping.get(parity_char.upper(), 'N')

    def conectar(self) -> bool:
        with self._connection_lock:
            if self.client.connected:
                return True
            try:
                return self.client.connect()
            except FileNotFoundError as e:
                self.error_handler.log_error("005", f"Puerto no disponible: {e}")
            except ModbusException as e:
                self.error_handler.log_error("020", f"Error Modbus: {e}")
            except Exception as e:
                self.error_handler.log_error("010", f"Error conexión: {type(e).__name__}: {e}")
            return False

    def desconectar(self):
        with self._connection_lock:
            if self.client and self.client.connected:
                try:
                    self.client.close()
                except Exception as e:
                    self.error_handler.log_error("015", f"Error desconexión: {e}")

    def leer_registros(self) -> Dict[str, RegisterValue]:
        """Lee registros con protección de lock reentrante"""
        with self._connection_lock:    # ✅ Permite llamadas anidadas
            if not self.client.connected and not self.conectar():
                return {}
                
            resultados = {}
            for reg_name in self.perfil["registros"]:
                try:
                    resultados[reg_name] = self._leer_registro(reg_name)
                except ModbusException as e:
                    self.error_handler.log_error("021", f"Error registro {reg_name}: {e}")
                    resultados[reg_name] = None
                except Exception as e:
                    self.error_handler.log_error("022", f"Error decodificación {reg_name}: {e}")
                    resultados[reg_name] = None
            return resultados

    def _leer_registro(self, reg_name: str) -> RegisterValue:
        """Lee un registro individual con reintentos"""
        reg_config = self.perfil["registros"].get(reg_name)
        if not reg_config:
            raise ValueError(f"Registro {reg_name} no configurado")
        
        # USAR SIEMPRE CONFIGURACIÓN DEL PERFIL (NO HARDCODEADO)
        funcion = reg_config.get("funcion", self.perfil.get("funcion_default", 3))
        
        # Flags sin escalar
        if reg_name == "direccion_flujo":
            reg_config["no_escalar"] = True
            
        decoder = self.DECODER_FACTORY.get_decoder(reg_config["data_type"])
        
        if not decoder:
            raise ValueError(f"Tipo dato no soportado: {reg_config['data_type']}")

        for intento in range(3):
            try:
                if funcion == 3:
                    response = self.client.read_holding_registers(
                        reg_config["address"], 
                        reg_config["count"],
                        slave=self.perfil["slave_id"]
                    )
                elif funcion == 4:
                    response = self.client.read_input_registers(
                        reg_config["address"], 
                        reg_config["count"],
                        slave=self.perfil["slave_id"]
                    )
                else:
                    raise ModbusException(f"Función {funcion} no soportada")

                if response.isError():
                    raise ModbusException(f"Error en respuesta: {response}")
                    
                return decoder.decodificar(response.registers, reg_config, self.perfil)
                
            except ModbusException as e:
                # ¡CORRECCIÓN! Backoff exponencial industrial
                wait_time = 0.5 * (2 ** intento)  # 0.5s, 1s, 2s
                time.sleep(wait_time)
                if intento < 2:  # Reintentar si no es el último intento
                    self.conectar()
                else:
                    raise