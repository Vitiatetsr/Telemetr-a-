from customtkinter import CTk, CTkFrame, CTkEntry, CTkButton, CTkLabel, set_appearance_mode, set_default_color_theme
from tkinter import messagebox  # Importar messagebox para mostrar errores
from PIL import Image, ImageTk  # Usamos PIL para cargar y redimensionar las imágenes
from PIL.Image import Resampling  # Importar Resampling para versiones recientes de Pillow
import os

# Configuración inicial de customtkinter
set_appearance_mode("dark")  # Modo oscuro
set_default_color_theme("blue")  # Tema de color azul

# Colores personalizados
c_negro = "#010101"
c_morado = "#7f5af0"
c_verde = "#2cb67d"

# Crear la ventana principal
raiz = CTk()
raiz.geometry("1000x800+100+50")  # Tamaño y posición de la ventana (más grande)
raiz.title("Inicio de Sesión")  # Título de la ventana
raiz.minsize(1000, 800)  # Tamaño mínimo de la ventana

# Variables para las imágenes
imagen_izquierda = None
imagen_derecha = None

# Cargar y redimensionar las imágenes usando PIL
try:
    # Ruta relativa a las imágenes
    ruta_imagen_izquierda = "Images/CONAGUA-LOGO.jpg"  # Imagen izquierda
    ruta_imagen_derecha = "Images/LOGO2.jpeg"  # Imagen derecha

    # Verificar si los archivos existen
    if not os.path.exists(ruta_imagen_izquierda):
        raise FileNotFoundError(f"El archivo {ruta_imagen_izquierda} no existe.")
    if not os.path.exists(ruta_imagen_derecha):
        raise FileNotFoundError(f"El archivo {ruta_imagen_derecha} no existe.")

    # Cargar las imágenes con PIL
    imagen_izquierda_pil = Image.open(ruta_imagen_izquierda)
    imagen_derecha_pil = Image.open(ruta_imagen_derecha)

    # Redimensionar las imágenes manteniendo la proporción
    tamaño_maximo = (250, 250)  # Tamaño máximo deseado para las imágenes
    imagen_izquierda_pil.thumbnail(tamaño_maximo, Resampling.LANCZOS)  # Mantener proporción
    imagen_derecha_pil.thumbnail(tamaño_maximo, Resampling.LANCZOS)  # Mantener proporción

    # Convertir las imágenes a un formato compatible con tkinter
    imagen_izquierda = ImageTk.PhotoImage(imagen_izquierda_pil)
    imagen_derecha = ImageTk.PhotoImage(imagen_derecha_pil)

except Exception as e:
    # Mostrar un mensaje de error en lugar de cerrar la ventana
    messagebox.showerror("Error", f"No se pudieron cargar las imágenes: {e}")
    # No destruyas la ventana aquí, permite que el programa continúe

# Solo crear los widgets si las imágenes se cargaron correctamente
if imagen_izquierda and imagen_derecha:
    # Crear un frame principal
    frame_principal = CTkFrame(raiz, fg_color=c_negro)
    frame_principal.pack(fill="both", expand=True)

    # Título de la aplicación (más grande)
    titulo = CTkLabel(frame_principal, text="Inicio de Sesión", font=("Arial", 28), text_color=c_morado)
    titulo.pack(pady=30)

    # Campo de correo electrónico (más grande)
    etiqueta_correo = CTkLabel(frame_principal, text="Correo electrónico", font=("Arial", 18), text_color=c_verde)
    etiqueta_correo.pack(pady=10)
    entrada_correo = CTkEntry(frame_principal, width=400, placeholder_text="Ingresa el usuario", font=("Arial", 16))
    entrada_correo.pack(pady=15)

    # Campo de contraseña (más grande)
    etiqueta_contrasena = CTkLabel(frame_principal, text="Contraseña", font=("Arial", 18), text_color=c_verde)
    etiqueta_contrasena.pack(pady=10)
    entrada_contrasena = CTkEntry(frame_principal, width=400, placeholder_text="Ingresa la contraseña", show="*", font=("Arial", 16))
    entrada_contrasena.pack(pady=15)

    # Checkbox para "Recordarme" (más grande)
    recordarme = CTkButton(frame_principal, text="Recordarme", fg_color="transparent", hover_color=c_morado, border_color=c_morado, border_width=1, font=("Arial", 16))
    recordarme.pack(pady=15)

    # Botón de "Iniciar sesión" (más grande)
    boton_iniciar_sesion = CTkButton(frame_principal, text="INICIAR SESIÓN", fg_color=c_morado, hover_color=c_verde, font=("Arial", 20))
    boton_iniciar_sesion.pack(pady=30)

    # Frame para las imágenes debajo del botón
    frame_imagenes = CTkFrame(frame_principal, fg_color="transparent")
    frame_imagenes.pack(pady=20)

    # Imagen izquierda (más hacia la izquierda)
    label_imagen_izquierda = CTkLabel(frame_imagenes, image=imagen_izquierda, text="")
    label_imagen_izquierda.pack(side="left", padx=50)  # Aumentamos el padx para desplazar más a la izquierda

    # Imagen derecha (más hacia la derecha)
    label_imagen_derecha = CTkLabel(frame_imagenes, image=imagen_derecha, text="")
    label_imagen_derecha.pack(side="right", padx=50)  # Aumentamos el padx para desplazar más a la derecha

# Iniciar el bucle principal
raiz.mainloop()