from pymodbus.client import ModbusSerialClient
import struct
import time 
from datetime import datetime
from telemetria_utils import guardar_datos_txt, copiar_a_usb, enviar_por_ftp, enviar_sms
import logging

# Configuración de logging para depuración
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

# Configuraciones predeterminadas
configuraciones = [
    {
        "nombre": "Configuración 1",
        "puerto_serie": "COM7",  # Cambia esto al puerto correcto
        "baudrate": 4800,
        "parity": "N",
        "stopbits": 1,
        "bytesize": 8,
        "unidad": 1,
    },
    {
        "nombre": "Configuración 2",
        "puerto_serie": "COM7",
        "baudrate": 9600,
        "parity": "N",
        "stopbits": 1,
        "bytesize": 8,
        "unidad": 2,
    },
    {
        "nombre": "Configuración 3",
        "puerto_serie": "COM7",
        "baudrate": 19200,
        "parity": "N",
        "stopbits": 1,
        "bytesize": 8,
        "unidad": 3,
    },
    # Otras configuraciones...
]

# Mostrar configuraciones al usuario
print("Configuraciones disponibles:")
for i, config in enumerate(configuraciones):
    print(f"{i + 1}. {config['nombre']}")

# Solicitar al usuario que seleccione una configuración
while True:
    try:
        seleccion = int(input("Seleccione una configuración (1-{}): ".format(len(configuraciones))))
        if 1 <= seleccion <= len(configuraciones):
            break
        else:
            print("Selección inválida. Intente nuevamente.")
    except ValueError:
        print("Entrada inválida. Intente nuevamente.")

# Utilizar la configuración seleccionada
configuracion_seleccionada = configuraciones[seleccion - 1]
puerto_serie = configuracion_seleccionada["puerto_serie"]
baudrate = configuracion_seleccionada["baudrate"]
parity = configuracion_seleccionada["parity"]
stopbits = configuracion_seleccionada["stopbits"]
bytesize = configuracion_seleccionada["bytesize"]
unidad = configuracion_seleccionada["unidad"]

def leer_datos_sensor_rtu(puerto_serie, baudrate, parity, stopbits, bytesize, unidad):
    """Lee datos del sensor Modbus RTU."""
    try:
        cliente = ModbusSerialClient(
            method="rtu",
            port=puerto_serie,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
            timeout=1
        )

        if cliente.connect():
            print(f"Conectado al dispositivo Modbus RTU en {puerto_serie}")
            # Leer registros específicos
            registros_gasto = cliente.read_holding_registers(address=4, count=2, unit=unidad)  # Gasto instantáneo (0004-0005)
            registros_velocidad = cliente.read_holding_registers(address=6, count=2, unit=unidad)  # Velocidad (0006-0007)
            registros_volumen = cliente.read_holding_registers(address=8, count=2, unit=unidad)  # Volumen acumulado (0008-0009)

            if (
                not registros_gasto.isError()
                and not registros_velocidad.isError()
                and not registros_volumen.isError()
            ):
                # Convertir registros a valores legibles
                gasto_instantaneo = struct.unpack('>f', bytes.fromhex(f"{registros_gasto.registers[0]:04x}{registros_gasto.registers[1]:04x}"))[0]
                velocidad = struct.unpack('>f', bytes.fromhex(f"{registros_velocidad.registers[0]:04x}{registros_velocidad.registers[1]:04x}"))[0]
                volumen_acumulado = (registros_volumen.registers[0] << 16) | registros_volumen.registers[1]

                # Convertir a las unidades deseadas
                gasto_instantaneo_m3s = gasto_instantaneo / 1000  # Convertir litros/segundo a m³/s
                volumen_acumulado_m3 = volumen_acumulado / 1000  # Convertir litros a m³

                cliente.close()
                return {
                    "gasto_instantaneo": gasto_instantaneo_m3s,  # En m³/s
                    "velocidad": velocidad,  # En m/s (ya está en la unidad correcta)
                    "volumen_acumulado": volumen_acumulado_m3,  # En m³
                }
            else:
                print("Error en la respuesta Modbus.")
                cliente.close()
                return None
        else:
            print(f"No se pudo conectar al dispositivo Modbus RTU en {puerto_serie}")
            return None
    except Exception as e:
        print(f"Error al leer datos del sensor: {e}")
        return None

# ==================================================
# 3. Ejecución del programa
# ==================================================

if __name__ == "__main__":
    while True:  # Bucle infinito para lecturas continuas
        # Leer datos del sensor
        datos = leer_datos_sensor_rtu(puerto_serie, baudrate, parity, stopbits, bytesize, unidad)
        if datos:
            print(f"Gasto instantáneo: {datos['gasto_instantaneo']} m³/s")
            print(f"Velocidad del agua: {datos['velocidad']} m/s")
            print(f"Volumen acumulado: {datos['volumen_acumulado']} m³")

            # Solicitar datos adicionales al usuario
            fecha = input("Ingrese la fecha (aaaammdd) o presione Enter para usar la fecha actual: ")
            hora = input("Ingrese la hora (hhmmss) o presione Enter para usar la hora actual: ")
            lat = input("Ingrese la latitud (formato decimal): ")
            long = input("Ingrese la longitud (formato decimal): ")
            rfc = input("Ingrese el RFC del contribuyente: ")
            nsm = input("Ingrese el número de serie del medidor (NSM): ")
            nsue = input("Ingrese el número de serie de la unidad electrónica (NSUE): ")
            ker = input("Ingrese el código de error (ker) o presione Enter para usar '000': ")

            # Usar valores predeterminados si no se ingresan
            if not fecha:
                fecha = datetime.now().strftime("%Y%m%d")
            if not hora:
                hora = datetime.now().strftime("%H%M%S")
            if not ker:
                ker = "000"

            # Guardar los datos en archivos .txt
            if guardar_datos_txt(datos, rfc, nsm, nsue, lat, long, ker, fecha, hora):
                # Copiar el archivo a una USB
                ruta_usb = input("Ingrese la ruta de la USB (ejemplo: E:/) o presione Enter para omitir: ")
                if ruta_usb:
                    copiar_a_usb("datos_telemetria.txt", ruta_usb)

                # Enviar el archivo por FTP
                enviar_ftp = input("¿Desea enviar el archivo por FTP? (s/n): ").strip().lower()
                if enviar_ftp == "s":
                    servidor_ftp = input("Ingrese el host del servidor FTP: ")
                    usuario = input("Ingrese el usuario FTP: ")
                    contraseña = input("Ingrese la contraseña FTP: ")
                    ruta_remota = input("Ingrese la ruta remota en el servidor FTP: ")
                    enviar_por_ftp("datos_telemetria.txt", servidor_ftp, usuario, contraseña, ruta_remota)

                # Enviar un SMS
                enviar_sms_opcion = input("¿Desea enviar un SMS? (s/n): ").strip().lower()
                if enviar_sms_opcion == "s":
                    numero = input("Ingrese el número de teléfono: ")
                    api_key = input("Ingrese la API key para enviar SMS: ")
                    mensaje = f"Gasto: {datos['gasto_instantaneo']} m³/s, Velocidad: {datos['velocidad']} m/s, Volumen: {datos['volumen_acumulado']} m³"
                    enviar_sms(numero, mensaje, api_key)
        else:
            print("No se pudieron leer los datos del sensor.")

        # Esperar 5 segundos antes de la siguiente lectura
        time.sleep(5)