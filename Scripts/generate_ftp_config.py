from cryptography.fernet import Fernet

def main():
    clave_fernet = Fernet.generate_key()
    print("=== INSTRUCCIONES ===")
    print("1. Genera una variable de entorno llamada FERNET_KEY:")
    print(f"   export FERNET_KEY='{clave_fernet.decode()}'")
    print("2. Ejecuta el software con esta variable configurada.")
    
    contraseña_ftp = input("Ingresa tu contraseña FTP REAL: ").encode()
    fernet = Fernet(clave_fernet)
    clave_cifrada = fernet.encrypt(contraseña_ftp)
    
    print(f"\n[CLAVE CIFRADA] Copia este valor en ftp_config.json:\n{clave_cifrada.decode()}\n")

if __name__ == "__main__":
    main()