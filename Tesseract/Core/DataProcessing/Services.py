# Tesseract/Core/DataProcessing/Services.py - VERSIÓN PRODUCCIÓN

import logging
import os
import shutil
from datetime import datetime
from typing import Dict
from .Interfaces import IConfigProvider, IBitmaskConverter, IUnitConverter, IRecordFormatter, IFileNameGenerator

class ConfigProvider(IConfigProvider):
    def __init__(self, config_manager):
        self.config_manager = config_manager
    
    def get_config(self) -> dict:
        return self.config_manager.cargar_config_general()

class BitmaskConverter(IBitmaskConverter):
    def to_integer(self, bitmask_dict: Dict[str, bool]) -> int:
        value = 0
        for bit_str, flag_value in bitmask_dict.items():
            try:
                if flag_value:
                    bit = int(bit_str)
                    value |= (1 << bit)
            except ValueError:
                logging.warning(f"Bit inválido omitido: {bit_str}")
        return value

class UnitConverter(IUnitConverter):
    # Estrategias como propiedad de CLASE
    CONVERSION_STRATEGIES = {
    # Temperatura
    ('°C', '°F'): lambda v: (v * 9/5) + 32,
    ('°F', '°C'): lambda v: (v - 32) * 5/9,
    
    # Volumen
    ('ml', 'l'): lambda v: v * 0.001,
    ('ml', 'm³'): lambda v: v * 0.000001,
    ('l', 'm³'): lambda v: v * 0.001,
    ('gal', 'l'): lambda v: v * 3.78541,
    
    # Flujo (NUEVAS CONVERSIONES)
    ('m³/s', 'L/s'): lambda v: v * 1000,
    ('m³/s', 'gal/min'): lambda v: v * 15850.3,
    ('m³/s', 'm³/h'): lambda v: v * 3600,
    ('m³/h', 'L/s'): lambda v: v * 0.2778,
    ('gal/min', 'L/s'): lambda v: v * 0.0630902,
    ('m³/h', 'gal/min'): lambda v: v * 4.40287
}

    
    def convert(self, value: float, from_unit: str, to_unit: str) -> float:
        if from_unit == to_unit:
            return value
            
        strategy_key = (from_unit, to_unit)
        if strategy_key in self.CONVERSION_STRATEGIES:
            return self.CONVERSION_STRATEGIES[strategy_key](value)
            
        # Búsqueda de estrategia inversa
        reverse_key = (to_unit, from_unit)
        if reverse_key in self.CONVERSION_STRATEGIES:
            reverse_fn = self.CONVERSION_STRATEGIES[reverse_key]
            return value / reverse_fn(1) if reverse_fn(1) != 0 else value
            
        raise ValueError(f"Conversión no soportada: {from_unit}→{to_unit}")

class FileNameGenerator(IFileNameGenerator):
    def __init__(self, config_provider: IConfigProvider):
        self.config_provider = config_provider

    def generate(self, tipo_registro: str, fecha_en_nombre: bool = True) -> str:
        try:
            config = self.config_provider.get_config()
            fecha = datetime.now().strftime("%Y%m%d")
            base = f"{config['RFC']}_{config['NSM']}" if tipo_registro == "Medidor" else f"{config['RFC']}_QA"
            return f"{base}_{fecha}.txt" if fecha_en_nombre else f"{base}.txt"
        except Exception as e:
            logging.error(f"Error generando nombre: {e}")
            return f"EMG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

class RecordFormatter(IRecordFormatter):
    def __init__(self, config_provider: IConfigProvider, bitmask_converter: IBitmaskConverter):
        self.config_provider = config_provider
        self.bitmask_converter = bitmask_converter

    def format(self, tipo_registro: str, datos_sensor: dict, perfil_sensor: dict) -> str:
        try:
            config = self.config_provider.get_config()
            now = datetime.now()
            fecha = now.strftime("%Y%m%d")
            hora = now.strftime("%H%M%S")
            mapa = perfil_sensor.get("output_mapping", {})
            
            # CORRECCIÓN: Usar claves de mapeo
            flujo_inst = datos_sensor.get(mapa.get("flujo_instantaneo", "Q"), 0.0)
            flujo_acum = datos_sensor.get(mapa.get("flujo_acumulado", "Vol"), 0.0)
            flags_raw = datos_sensor.get(mapa.get("flags", "direccion_flujo"), 0)
            
            if isinstance(flags_raw, dict):
                flags_value = self.bitmask_converter.to_integer(flags_raw)
            elif isinstance(flags_raw, int):
                flags_value = flags_raw
            else:
                try:
                    flags_value = int(flags_raw)
                except (TypeError, ValueError):
                    flags_value = 0
                
            if tipo_registro == "Medidor":
                return (
                    f"M|{fecha}|{hora}|{config['RFC']}|{config['NSM']}|{config['NSUE']}|"
                    f"{flujo_acum:.3f}|{config['Lat']}|{config['Long']}|{flags_value:03d}"
                )
            elif tipo_registro == "SistemaMedicion":
                return (
                    f"QA|{fecha}|{hora}|{config['RFC']}|{flujo_inst:.3f}|"
                    f"{flujo_acum:.3f}|{config['Lat']}|{config['Long']}|{flags_value:03d}"
                )
            else:
                raise ValueError("Tipo de registro inválido")
        except Exception as e:
            return f"ERR|{datetime.now().strftime('%Y%m%d|%H%M%S')}|{type(e).__name__}|{str(e)}"
