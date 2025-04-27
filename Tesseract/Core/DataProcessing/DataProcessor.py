from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from typing import Tuple

class DataProcessor:
    UNIT_CONVERSION = {
        'metric_volume': {
            'ml': 0.001, 'l': 1.0, 'm³': 1000.0, 
            'dal': 10.0, 'hl': 100.0, 'cm³': 0.001, 
            'dm³': 1.0, 'Ml': 1000000.0
        },
        'imperial_volume': {
            'Gal': 3.78541, 'IGL': 4.54609, 'ft³': 28.3168,
            'bbl': 158.987, 'BBL': 119.24, 'kf³': 28316.8,
            'Aft': 1233.48, 'in3': 0.0163871, 'hf3': 2831.68,
            'KGL': 3785.41, 'IKG': 4546.09, 'ttG': 37854.1,
            'MGL': 3785410.0, 'IMG': 4546090.0
        },
        'metric_weight': {'g': 0.001, 'kg': 1.0, 't': 1000.0},
        'imperial_weight': {'oz': 0.0283495, 'lb': 0.453592, 'ton': 907.185}
    }

    @staticmethod
    def decode_32bit_float(registers) -> float:
        if not registers or len(registers) != 2:
            raise ValueError("Registros Modbus inválidos para float de 32 bits")
            
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers,
            byteorder=Endian.BIG,
            wordorder=Endian.BIG
        )
        return decoder.decode_32bit_float()

    @staticmethod
    def decode_32bit_uint(registers) -> int:
        if not registers or len(registers) != 2:
            raise ValueError("Registros Modbus inválidos para entero de 32 bits")
            
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers,
            byteorder=Endian.BIG,
            wordorder=Endian.BIG
        )
        return decoder.decode_32bit_uint()

    @classmethod
    def obtener_unidad_y_decimales(cls, registro_unidad: int) -> Tuple[str, str, int]:
        if registro_unidad > 0xFFFF:
            raise ValueError("Registro de unidad excede 16 bits")

        sistema = 'imperial' if (registro_unidad >> 15) & 0x1 else 'metric'
        tipo = 'weight' if (registro_unidad >> 14) & 0x1 else 'volume'
        indice_unidad = (registro_unidad >> 8) & 0x3F
        decimales = (registro_unidad >> 2) & 0x7

        if sistema == 'metric' and tipo == 'volume' and indice_unidad > 7:
            raise ValueError(f"Índice {indice_unidad} no válido para unidades métricas de volumen")

        return sistema, tipo, decimales

    @classmethod
    def aplicar_unidades(cls, valor: float, registro_unidad: int, preferencia_usuario: str = None) -> float:
        sistema, tipo, decimales = cls.obtener_unidad_y_decimales(registro_unidad)
        clave = f"{sistema}_{tipo}"
        unidad = preferencia_usuario or cls._obtener_unidad_default(sistema, tipo)

        if unidad not in cls.UNIT_CONVERSION[clave]:
            raise ValueError(f"Unidad '{unidad}' no existe para {clave}")

        factor = cls.UNIT_CONVERSION[clave][unidad]
        return round(valor * factor, decimales)

    @classmethod
    def _obtener_unidad_default(cls, sistema: str, tipo: str) -> str:
        defaults = {
            'metric_volume': 'l',
            'imperial_volume': 'Gal',
            'metric_weight': 'kg',
            'imperial_weight': 'lb'
        }
        return defaults.get(f"{sistema}_{tipo}", '')