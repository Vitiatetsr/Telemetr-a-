import requests
import time 
from Core.System.ErrorHandler import ErrorHandler


class InternetManager:
    @staticmethod
    def is_connected(url: str = "http://www.google.com", timeout: int = 5) -> bool:
        """
        Retorna True si puede hacer GET a 'url' en menos de 'timeout' segundos.
        """
        try:
            r = requests.get(url, timeout=timeout)
            return r.status_code == 200
        except Exception as e:
            ErrorHandler().log_error("NET-001", f"No hay conexión: {e}")
            return False
        
        
    @staticmethod
    def wait_for_connection(retries: int = 5, delay: int = 2) -> bool:
        """
        Intenta 'is_connected()' hasta 'retries' veces, dormirá 'delay' segundos
        Retorna True si recupera la conexión.
        """
        for i in range(1, retries + 1):
            if InternetManager.is_connected():
                return True
            time.sleep(delay)
        return False