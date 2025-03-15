import os
import shutil
import ftplib
import requests
from datetime import datetime

def guardar_datos_txt(datos, rfc, nsm, nsue, lat, long, ker="000", fecha=None, hora=None, nombre_archivo="datos_telemetria.txt"):
    """
    Guarda los datos en un archivo .txt con el formato especificado.
    """
    try:
        # Usar la fecha y hora actual si no se proporcionan
        if not fecha:
            fecha = datetime.now().strftime("%Y%m%d")  # Formato: aaaammdd
        if not hora:
            hora = datetime.now().strftime("%H%M%S")   # Formato: hhmmss

        # Crear la cadena de datos en el formato especificado
        cadena_datos = (
            f"M|{fecha}|{hora}|{rfc}|{nsm}|{nsue}|"
            f"{datos['volumen_acumulado']}|{lat}|{long}|{ker}"
        )

        # Guardar la cadena de datos en el archivo .txt
        with open(nombre_archivo, "w") as archivo:
            archivo.write(cadena_datos)
        print(f"Datos guardados en {nombre_archivo}")
        return True
    except Exception as e:
        print(f"Error al guardar los datos en el archivo: {e}")
        return False

def copiar_a_usb(nombre_archivo, ruta_usb):
    """
    Copia el archivo .txt a una USB conectada.
    """
    try:
        if os.path.exists(ruta_usb):
            shutil.copy(nombre_archivo, ruta_usb)
            print(f"Archivo copiado a la USB en {ruta_usb}")
            return True
        else:
            print("La ruta de la USB no existe.")
            return False
    except Exception as e:
        print(f"Error al copiar el archivo a la USB: {e}")
        return False

def enviar_por_ftp(nombre_archivo, servidor_ftp, usuario, contraseña, ruta_remota):
    """
    Envía el archivo .txt a un servidor FTP.
    """
    try:
        with ftplib.FTP(servidor_ftp) as ftp:
            ftp.login(usuario, contraseña)
            with open(nombre_archivo, "rb") as archivo:
                ftp.storbinary(f"STOR {ruta_remota}", archivo)
        print(f"Archivo enviado por FTP a {servidor_ftp}")
        return True
    except Exception as e:
        print(f"Error al enviar el archivo por FTP: {e}")
        return False

def enviar_sms(numero, mensaje, api_key):
    """
    Envía un SMS con la información recopilada.
    """
    try:
        url = f"https://api.example.com/send?number={numero}&message={mensaje}&key={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            print("SMS enviado correctamente.")
            return True
        else:
            print(f"Error al enviar el SMS: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error al enviar el SMS: {e}")
        return False