from datetime import datetime
from Core.System.ConfigManager import ConfigManager

class DataFormatter:
    @staticmethod
    def generar_nombre_archivo(tipo_registro: str) -> str:
        """Genera nombres de archivo según normativa (sin cambios al código original)"""
        config = ConfigManager.cargar_config_general()
        fecha = datetime.now().strftime("%Y%m%d")
        
        if tipo_registro == "Medidor":
            return f"{config['RFC']}_{fecha}_{config['NSM']}.txt"
        elif tipo_registro == "SistemaMedicion":
            return f"{config['RFC']}_{fecha}_QA.txt"
        else:
            raise ValueError("Tipo de registro no válido")

    @staticmethod
    def formatear_registro(tipo_registro: str, datos_sensor: dict) -> str:
        """Formatea según tablas 1 y 2 con datos originales del sensor"""
        config = ConfigManager.cargar_config_general()
        fecha = datetime.now().strftime("%Y%m%d")
        hora = datetime.now().strftime("%H%M%S")
        
        if tipo_registro == "Medidor":
            return (
                f"M|{fecha}|{hora}|{config['RFC']}|"
                f"{config['NSM']}|{config['NSUE']}|"
                f"{datos_sensor['flujo_acumulado']:.3f}|"  # Lec = flujo_acumulado
                f"{config['Lat']}|{config['Long']}|"
                f"{datos_sensor['flags']:03d}"
            )
        elif tipo_registro == "SistemaMedicion":
            return (
                f"QA|{fecha}|{hora}|{config['RFC']}|"
                f"{datos_sensor['flujo_instantaneo']:.3f}|"  # Q = flujo_instantaneo
                f"{datos_sensor['flujo_acumulado']:.3f}|"     # Vol = flujo_acumulado
                f"{config['Lat']}|{config['Long']}|"
                f"{datos_sensor['flags']:03d}"
            )
        else:
            raise ValueError("Tipo de registro no válido")