from Core.Network.InternetManager import InternetManager

if __name__=="__main__":
    print("Conexión inicial:", InternetManager.is_connected())
    if InternetManager.wait_for_connection(retries=3, delay=2):
        print("Internet disponible tras esperar.")
    else:
        print("No se recuperó la conexión despúes de varios intentos.")