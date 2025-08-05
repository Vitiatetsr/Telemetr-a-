# Tesseract/Core/System/StateManager.py

import threading

class StateManager:
    """Gestiona el estado de preparación del sistema mediante checkpoints"""
    _states = {
        "settings": False,
        "ftp_email": False,
        "meter_config": False,
        "report_templates": False
    }
    _lock = threading.RLock()

    @classmethod
    def set_ready(cls, state_name: str):
        with cls._lock:
            if state_name in cls._states:
                cls._states[state_name] = True
                print(f"✅ Checkpoint [{state_name}] completado")

    @classmethod
    def is_system_ready(cls) -> bool:
        with cls._lock:
            return all(cls._states.values())
    
    @classmethod
    def is_ready(cls, state_name: str) -> bool:
        """Verifica si un checkpoint específico está listo"""
        with cls._lock:
            return cls._states.get(state_name, False)
    
    @classmethod
    def reset_all(cls):
        with cls._lock:
            for key in cls._states:
                cls._states[key] = False
            print("🔄 Todos los checkpoints reiniciados")