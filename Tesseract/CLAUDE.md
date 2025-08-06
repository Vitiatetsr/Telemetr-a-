# CodeViz Research Context

> **Note**: This file contains research context from CodeViz. Most recent contexts are at the bottom.

---

## Research Query

Explica el flujo del como interactúa todo el sistema junto con la interfaz gráfica

*Session: db3869ccb8a207ab1d7bd896cfc619a7 | Generated: 7/21/2025, 2:17:19 PM*

### Analysis Summary

# Flujo de Interacción del Sistema con la Interfaz Gráfica

El sistema Tesseract está diseñado con una arquitectura modular que permite la interacción entre sus componentes principales y la interfaz gráfica de usuario (GUI). El flujo general comienza con la inicialización de la aplicación, la autenticación del usuario y la posterior interacción con las funcionalidades del sistema a través de la ventana principal.

## Arquitectura de Alto Nivel

El sistema se compone de los siguientes módulos principales que interactúan con la GUI:

*   **GUI**: Módulo encargado de la presentación visual y la interacción del usuario. Contiene las ventanas y elementos gráficos.
*   **Core/System**: Módulo que gestiona la configuración, el manejo de errores y la programación de tareas.
*   **Core/DataProcessing**: Módulo responsable del procesamiento y formateo de datos.
*   **Core/Hardware**: Módulo que maneja la comunicación con dispositivos de hardware, como sensores Modbus y dispositivos USB.
*   **Core/Network**: Módulo encargado de la gestión de la red, incluyendo la transferencia de archivos (FTP) y el envío de alertas (SMS).

## Flujo de Interacción Detallado

### 1. Inicio de la Aplicación y Autenticación

El punto de entrada de la aplicación es el archivo [GUI/App.py](c:/Users/Public/Documents/Tesseract/GUI/App.py).

*   La clase `TesseractApp` ([GUI/App.py](c:/Users/Public/Documents/Tesseract/GUI/App.py)) hereda de `QApplication` y es la encargada de inicializar la aplicación.
*   Durante su inicialización, `TesseractApp` crea instancias de:
    *   `ErrorHandler` ([Core/System/ErrorHandler.py](c:/Users/Public/Documents/Tesseract/Core/System/ErrorHandler.py)): Para el registro y manejo de errores en todo el sistema.
    *   `ConfigManager` ([Core/System/ConfigManager.py](c:/Users/Public/Documents/Tesseract/Core/System/ConfigManager.py)): Para la carga y gestión de configuraciones, como los perfiles de sensores.
*   La aplicación inicia mostrando la `LoginWindow` ([GUI/Windows/LoginWindow.py](c:/Users/Public/Documents/Tesseract/GUI/Windows/LoginWindow.py)).
*   Una vez que el usuario se autentica exitosamente a través de la `LoginWindow`, se emite una señal (`login_success`) que es capturada por `TesseractApp`.
*   Tras el éxito del login, la `LoginWindow` se cierra y se instancia y muestra la `MainWindow` ([GUI/Windows/MainWindow.py](c:/Users/Public/Documents/Tesseract/GUI/Windows/MainWindow.py)), pasando el usuario autenticado, el manejador de errores y los perfiles de sensores cargados.

### 2. Interacción a través de la Ventana Principal (MainWindow)

La `MainWindow` ([GUI/Windows/MainWindow.py](c:/Users/Public/Documents/Tesseract/GUI/MainWindow.py)) actúa como el centro de control principal para el usuario, desde donde se accede a las diferentes funcionalidades del sistema. Aunque no se detalla en el `App.py`, se infiere que la `MainWindow` orquesta las interacciones con los módulos `Core`.

*   **Configuración del Sistema**: La `MainWindow` probablemente permite al usuario acceder a ventanas de configuración como `ConfigWindow` ([GUI/Windows/ConfigWindow.py](c:/Users/Public/Documents/Tesseract/GUI/Windows/ConfigWindow.py)), `ModbusConfigWindow` ([GUI/Windows/ModbusConfigWindow.py](c:/Users/Public/Documents/Tesseract/GUI/ModbusConfigWindow.py)) y `NetworkConfigWindow` ([GUI/Windows/NetworkConfigWindow.py](c:/Users/Public/Documents/Tesseract/GUI/NetworkConfigWindow.py)). Estas ventanas interactuarían con el `ConfigManager` ([Core/System/ConfigManager.py](c:/Users/Public/Documents/Tesseract/Core/System/ConfigManager.py)) para leer y guardar las configuraciones en archivos JSON ubicados en el directorio [Config/](c:/Users/Public/Documents/Tesseract/Config/).
*   **Visualización de Datos y Reportes**: La `DashboardWindow` ([GUI/Windows/DashboardWindow.py](c:/Users/Public/Documents/Tesseract/GUI/Windows/DashboardWindow.py)) y `ReportsWindow` ([GUI/Windows/ReportsWindow.py](c:/Users/Public/Documents/Tesseract/GUI/Windows/ReportsWindow.py)) son responsables de mostrar datos al usuario. Estas ventanas obtendrían los datos procesados del módulo `DataProcessing` ([Core/DataProcessing/DataProcessor.py](c:/Users/Public/Documents/Tesseract/Core/DataProcessing/DataProcessor.py)).
*   **Manejo de Hardware**: La GUI, a través de ventanas específicas o acciones en la `MainWindow`, interactuaría con el módulo `Hardware` para:
    *   Gestionar la comunicación Modbus RTU mediante `ModbusRTU_Manager` ([Core/Hardware/ModbusRTU_Manager.py](c:/Users/Public/Documents/Tesseract/Core/Hardware/ModbusRTU_Manager.py)) y `ModbusUtils` ([Core/Hardware/ModbusUtils.py](c:/Users/Public/Documents/Tesseract/Core/Hardware/ModbusUtils.py)).
    *   Manejar dispositivos USB a través de `USBManejador` ([Core/Hardware/USBManejador.py](c:/Users/Public/Documents/Tesseract/Core/Hardware/USBManejador.py)).
*   **Operaciones de Red**: La GUI permitiría al usuario interactuar con el módulo `Network` para:
    *   Gestionar transferencias de archivos FTP utilizando `FTPManager` ([Core/Network/FTPManager.py](c:/Users/Public/Documents/Tesseract/Core/Network/FTPManager.py)).
    *   Monitorear la conexión a internet con `InternetManager` ([Core/Network/InternetManager.py](c:/Users/Public/Documents/Tesseract/Core/Network/InternetManager.py)).
    *   Enviar alertas a través de `AlertManager` ([Core/Network/AlertManager.py](c:/Users/Public/Documents/Tesseract/Core/Network/AlertManager.py)), que podría utilizar `SMSManager` (inferido por el `__pycache__` en [Core/Network/__pycache__/SMSManager.cpython-313.pyc](c:/Users/Public/Documents/Tesseract/Core/Network/__pycache__/SMSManager.cpython-313.pyc)).
*   **Consola de Errores**: La `ErrorConsoleWindow` ([GUI/Windows/ErrorConsoleWindow.py](c:/Users/Public/Documents/Tesseract/GUI/Windows/ErrorConsoleWindow.py)) mostraría los errores registrados por el `ErrorHandler` ([Core/System/ErrorHandler.py](c:/Users/Public/Documents/Tesseract/Core/System/ErrorHandler.py)), proporcionando retroalimentación al usuario sobre problemas del sistema.

### 3. Persistencia de Datos

*   El sistema utiliza archivos de configuración JSON en el directorio [Config/](c:/Users/Public/Documents/Tesseract/Config/) para almacenar ajustes.
*   Se observa un archivo `pendientes.db` en la raíz del proyecto, lo que sugiere el uso de una base de datos local para la persistencia de datos, posiblemente gestionada por algún componente del `Core/DataProcessing` o `Core/System`.
*   El directorio `pendientes_usb/` indica que se manejan archivos o datos relacionados con operaciones USB pendientes.

