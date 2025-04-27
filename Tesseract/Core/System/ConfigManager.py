import json
import os
import re
from passlib.hash import pbkdf2_sha256
from typing import Dict, Any

class ConfigManager:
    GENERAL_CONFIG = "Config/config.json"
    SENSOR_CONFIG = "Config/sensor_config.json"
    FTP_CONFIG = "Config/ftp_config.json"
    LOGIN_CONFIG = "Config/login_config.json"

    @classmethod
    def cargar_config_general(cls) -> Dict[str, Any]:
        config = cls._cargar_archivo(cls.GENERAL_CONFIG)
        obligatorias = ["RFC", "NSM", "NSUE", "Lat", "Long"]
        for clave in obligatorias:
            if clave not in config:
                raise ValueError(f"Clave obligatoria '{clave}' faltante en config.json")
        return config

    @classmethod
    def guardar_config_general(cls, config: Dict[str, Any]) -> None:
        cls._validar_rfc(config.get("RFC", ""))
        cls._validar_coordenadas(config.get("Lat"), config.get("Long"))
        cls._guardar_archivo(cls.GENERAL_CONFIG, config)

    @classmethod
    def cargar_config_sensor(cls) -> Dict[str, Any]:
        return cls._cargar_archivo(cls.SENSOR_CONFIG)

    @classmethod
    def cargar_config_ftp(cls) -> Dict[str, Any]:
        return cls._cargar_archivo(cls.FTP_CONFIG)

    @classmethod
    def cargar_config_login(cls) -> Dict[str, Any]:
        return cls._cargar_archivo(cls.LOGIN_CONFIG)

    @classmethod
    def guardar_config_login(cls, config: Dict[str, Any]) -> None:
        if "contraseña_maestra" in config and not config["contraseña_maestra"].startswith("$pbkdf2-sha256$"):
            config["contraseña_maestra"] = pbkdf2_sha256.hash(config["contraseña_maestra"], salt_size=16)
        if "usuarios" in config:
            for usuario, contraseña in config["usuarios"].items():
                if not contraseña.startswith("$pbkdf2-sha256$"):
                    config["usuarios"][usuario] = pbkdf2_sha256.hash(contraseña, salt_size=16)
        cls._guardar_archivo(cls.LOGIN_CONFIG, config)

    @classmethod
    def validar_credenciales(cls, usuario: str, contraseña: str) -> bool:
        config = cls.cargar_config_login()
        if pbkdf2_sha256.verify(contraseña, config.get("contraseña_maestra", "")):
            return True
        hash_usuario = config.get("usuarios", {}).get(usuario, "")
        return pbkdf2_sha256.verify(contraseña, hash_usuario) if hash_usuario else False

    @staticmethod
    def _cargar_archivo(ruta: str) -> Dict[str, Any]:
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"Archivo {ruta} no encontrado")
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
            lat_f = float(str(lat).strip())
            long_f = float(str(long).strip())
            if not (-90 <= lat_f <= 90) or not (-180 <= long_f <= 180):
                raise ValueError("Coordenadas fuera de rango")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Formato de coordenadas inválido: {str(e)}")