# Tesseract/Core/System/ConfigManager.py - VERSIÓN PRODUCCIÓN

import json 
import os
import re
import string
from passlib.hash import pbkdf2_sha256
from typing import Dict, Any, List, Optional

class ConfigManager:
    GENERAL_CONFIG  = "Config/config.json"
    SENSOR_CONFIG   = "Config/sensor_config.json"
    FTP_CONFIG      = "Config/ftp_config.json"
    SMS_CONFIG      = "Config/sms_config.json"
    LOGIN_CONFIG    = "Config/login_config.json"
    
    _cache = {}

    @classmethod
    def cargar_config_general(cls) -> Dict[str, Any]:
        if 'general' in cls._cache:
            return cls._cache['general']
            
        cfg = cls._cargar_archivo(cls.GENERAL_CONFIG)
        for key in ["RFC", "NSM", "NSUE", "Lat", "Long"]:
            if key not in cfg:
                raise ValueError(f"Falta '{key}' en {cls.GENERAL_CONFIG}")
            
        # Unidad por defecto garantizada
        cfg.setdefault("unidad_visualizacion", "L/s")
        
        # NUEVO: Valor por defecto para Windows 10
        cfg.setdefault("storage_path", "D:\\TesseractData") 
        
        cls._cache['general'] = cfg
        return cfg

    @classmethod
    def guardar_config_general(cls, config: Dict[str, Any]) -> None:
        cls._validar_rfc(config.get("RFC", ""))
        cls._validar_coordenadas(config.get("Lat"), config.get("Long"))

        # LIMPIAR CACHÉ PARA ACTUALIZACIÓN GLOBAL
        cls._cache.clear()
        
        # Validar y asegurar ruta USB
        if "storage_path" not in config:
            config["storage_path"] = "D:\\TesseractData" 
        
        if not cls._es_ruta_windows_valida(config["storage_path"]):
            config["storage_path"] = "D:\\TesseractData"
        
        cls._guardar_archivo(cls.GENERAL_CONFIG, config)
        
        
    @staticmethod
    def _es_ruta_windows_valida(ruta: str) -> bool:
        """Valida que la ruta tenga formato correcto para Windows"""
        try:
            return len(ruta) > 1 and ruta[1] == ":" and ruta[0].upper() in string.ascii_uppercase
        except:
            return False

    @classmethod
    def cargar_config_ftp(cls) -> Dict[str, Any]:
        if 'ftp' in cls._cache:
            return cls._cache['ftp']
            
        cfg = cls._cargar_archivo(cls.FTP_CONFIG)
        for key in ["host", "usuario", "clave"]:
            if key not in cfg:
                raise ValueError(f"Falta '{key}' en {cls.FTP_CONFIG}")
        cls._cache['ftp'] = cfg
        return cfg

    @classmethod
    def guardar_config_ftp(cls, config: Dict[str, Any]) -> None:
        for key in ["host", "usuario", "clave"]:
            if key not in config:
                raise ValueError(f"Falta '{key}' en la configuración FTP")
        cls._guardar_archivo(cls.FTP_CONFIG, config)
        cls._cache.pop('ftp', None)

    @classmethod
    def cargar_config_sms(cls) -> Dict[str, Any]:
        if 'sms' in cls._cache:
            return cls._cache['sms']
            
        cfg = cls._cargar_archivo(cls.SMS_CONFIG)
        if "numero_destino" not in cfg:
            raise ValueError(f"Falta 'numero_destino' en {cls.SMS_CONFIG}")
        cfg.setdefault("account_sid", "")
        cfg.setdefault("auth_token", "")
        cfg.setdefault("numero_twilio", "")
        cls._cache['sms'] = cfg
        return cfg

    @classmethod
    def guardar_config_sms(cls, config: Dict[str, Any]) -> None:
        for key in ["numero_destino"]:
            if key not in config:
                raise ValueError(f"Falta '{key}' en la configuración SMS")
        cls._guardar_archivo(cls.SMS_CONFIG, config)
        cls._cache.pop('sms', None)

    @classmethod
    def cargar_config_login(cls) -> Dict[str, Any]:
        if 'login' in cls._cache:
            return cls._cache['login']
            
        cfg = cls._cargar_archivo(cls.LOGIN_CONFIG)
        cls._cache['login'] = cfg
        return cfg

    @classmethod
    def guardar_config_login(cls, config: Dict[str, Any]) -> None:
        if "contraseña_maestra" in config and not config["contraseña_maestra"].startswith("$pbkdf2-sha256$"):
            config["contraseña_maestra"] = pbkdf2_sha256.hash(config["contraseña_maestra"], salt_size=16)
        if "usuarios" in config:
            for user, pwd in config["usuarios"].items():
                if not pwd.startswith("$pbkdf2-sha256$"):
                    config["usuarios"][user] = pbkdf2_sha256.hash(pwd, salt_size=16)
        cls._guardar_archivo(cls.LOGIN_CONFIG, config)
        cls._cache.pop('login', None)

    @classmethod
    def validar_credenciales(cls, usuario: str, contraseña: str) -> bool:
        cfg = cls.cargar_config_login()
        if pbkdf2_sha256.verify(contraseña, cfg.get("contraseña_maestra", "")):
            return True
        hash_user = cfg.get("usuarios", {}).get(usuario, "")
        return bool(hash_user and pbkdf2_sha256.verify(contraseña, hash_user))

    @classmethod
    def cargar_config_sensor(cls) -> Dict[str, Any]:
        if 'sensor' in cls._cache:
            return cls._cache['sensor']
            
        cfg = cls._cargar_archivo(cls.SENSOR_CONFIG)
        cls._cache['sensor'] = cfg
        return cfg

    @classmethod
    def guardar_config_sensor(cls, config: Dict[str, Any]) -> None:
        cls._validar_config_sensor(config)
        cls._guardar_archivo(cls.SENSOR_CONFIG, config)
        cls._cache.pop('sensor', None)

    @classmethod
    def _validar_config_sensor(cls, config: Dict[str, Any]):
        if "sensores" not in config:
            raise ValueError("Falta sección 'sensores' en configuración de sensores")
        for sensor in config["sensores"]:
            for param in ["modelo", "puerto_serie", "baudrate", "slave_id", "parity"]:
                if param not in sensor:
                    raise ValueError(f"Falta '{param}' en configuración de sensor")
            if "registros" not in sensor:
                raise ValueError(f"Falta 'registros' en sensor {sensor.get('modelo')}")
            for reg_name, reg_config in sensor["registros"].items():
                for key in ["address", "count", "data_type"]:
                    if key not in reg_config:
                        raise ValueError(f"Registro '{reg_name}' falta '{key}'")
                if reg_config["data_type"] == "bitmask" and "bit_map" not in reg_config:
                    raise ValueError(f"Registro bitmap '{reg_name}' falta 'bit_map'")

    @classmethod
    def obtener_perfiles_sensores(cls) -> List[Dict[str, Any]]:
        return cls.cargar_config_sensor().get("sensores", [])

    @classmethod
    def obtener_perfil_por_modelo(cls, modelo: str) -> Optional[Dict[str, Any]]:
        for sensor in cls.obtener_perfiles_sensores():
            if sensor.get("modelo") == modelo:
                return sensor
        return None

    @classmethod
    def obtener_perfiles_predefinidos(cls) -> List[Dict[str, Any]]:
        return cls.cargar_config_sensor().get("perfiles_predefinidos", [])

    @classmethod
    def guardar_perfil_sensor(cls, perfil: Dict[str, Any], es_nuevo: bool = False):
        # Validación mejorada para direcciones
        for reg_name, reg_config in perfil.get("registros", {}).items():
            if "address" not in reg_config:
                raise ValueError(f"Registro '{reg_name}' falta 'address'")
        
            # Validar que address sea número válido
            try:
                addr = int(reg_config["address"])
                if not (0 <= addr <= 65535):
                    raise ValueError(f"Dirección inválida en registro '{reg_name}': {addr}")
            except (TypeError, ValueError):
                raise ValueError(f"Dirección inválida en registro '{reg_name}': {reg_config['address']}")

        # Continuar con el proceso de guardado
        cfg = cls.cargar_config_sensor()
        sensores = cfg.get("sensores", [])
        
        # ACTUALIZAR CACHÉ
        cls._cache.pop('sensor', None)

    @classmethod
    def obtener_parametro(cls, clave: str) -> Any:
        return cls.cargar_config_general().get(clave)

    @classmethod
    def obtener_config_alertas(cls) -> Dict[str, Any]:
        return cls.cargar_config_general().get("alertas", {})

    @classmethod
    def guardar_config_alertas(cls, alertas: Dict[str, Any]) -> None:
        cfg = cls.cargar_config_general()
        cfg["alertas"] = alertas
        cls._guardar_archivo(cls.GENERAL_CONFIG, cfg)
        cls._cache.pop('general', None)

    @staticmethod
    def _cargar_archivo(ruta: str) -> Dict[str, Any]:
        if not os.path.exists(ruta):
            return {}
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _guardar_archivo(ruta: str, datos: Dict[str, Any]):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)

    @staticmethod
    def _validar_rfc(rfc: str):
        if not re.match(r"^[A-ZÑ&]{3,4}\d{6}[A-V0-9]{3}$", rfc):
            raise ValueError("RFC inválido")

    @staticmethod
    def _validar_coordenadas(lat: Any, long: Any):
        try:
            lat_f, long_f = float(lat), float(long)
            if not (-90 <= lat_f <= 90 and -180 <= long_f <= 180):
                raise ValueError("Coordenadas fuera de rango")
        except Exception as e:
            raise ValueError(f"Coordenadas inválidas: {e}")