import flet as ft
import datetime

from Core.Hardware.ModbusUtils       import obtener_puertos_com
from Core.Network.InternetManager    import InternetManager
from Core.Hardware.ModbusRTU_Manager import ModbusRTUManager
from Core.System.ConfigManager       import ConfigManager
from Core.Network.FTPManager         import FTPManager
from Core.Hardware.USBManejador      import USBManejador

# ================= LOGIN VIEW =================
def login_view(page: ft.Page):
    page.controls.clear()
    page.bgcolor = "#1A1A2E"
    page.padding = page.margin = 0

    # Logo circular
    logo = ft.Container(
        content=ft.Image(src="images/LOGO2.jpeg", fit=ft.ImageFit.COVER),
        width=200, height=200,
        border_radius=100,
        border=ft.border.all(3, "#E94560")
    )

    # Campos de texto con hint_text (gris) y texto escrito en negro
    txt_user = ft.TextField(
        hint_text="Usuario",
        width=300,
        bgcolor="white",
        border=ft.border.all(2, "#E94560"),
        text_style=ft.TextStyle(color="black")
    )
    txt_pass = ft.TextField(
        hint_text="Contraseña",
        password=True,
        can_reveal_password=True,
        width=300,
        bgcolor="white",
        border=ft.border.all(2, "#E94560"),
        text_style=ft.TextStyle(color="black")
    )
    txt_error = ft.Text("", color=ft.Colors.RED)

    btn_login = ft.ElevatedButton(
        "Ingresar",
        width=200,
        bgcolor="#E94560",
        color="white"
    )
    def on_login(e):
        if ConfigManager.validar_credenciales(txt_user.value, txt_pass.value):
            page.session.set("logueado", True)
            page.update()
            main_view(page)
        else:
            txt_error.value = "⚠️ Usuario o contraseña incorrectos"
            page.update()
    btn_login.on_click = on_login

    form = ft.Container(
        content=ft.Column(
            controls=[txt_user, txt_pass, btn_login, txt_error],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20
        ),
        padding=30,
        bgcolor="#16213E",
        border=ft.border.all(2, "#E94560"),
        border_radius=12,
        width=360
    )

    page.add(
        ft.Row(
            controls=[
                ft.Container(expand=True, alignment=ft.alignment.center, content=logo),
                ft.Container(expand=True, alignment=ft.alignment.center, content=form),
            ],
            expand=True
        )
    )
    page.update()


# ================ CONFIG GENERAL ================
def view_config_general(page: ft.Page):
    cfg   = ConfigManager.cargar_config_general()
    e_rfc = ft.TextField(label="RFC",   value=cfg.get("RFC",""))
    e_nsm = ft.TextField(label="NSM",   value=cfg.get("NSM",""))
    e_nsue= ft.TextField(label="NSUE",  value=cfg.get("NSUE",""))
    e_lat = ft.TextField(label="Latitud", value=str(cfg.get("Lat","")))
    e_lon = ft.TextField(label="Longitud", value=str(cfg.get("Long","")))
    msg   = ft.Text()

    def on_save(e):
        try:
            ConfigManager.guardar_config_general({
                "RFC": e_rfc.value,
                "NSM": e_nsm.value,
                "NSUE":e_nsue.value,
                "Lat": float(e_lat.value),
                "Long":float(e_lon.value)
            })
            msg.value = "✅ Guardado"
        except Exception as ex:
            msg.value = f"⚠️ {ex}"
        page.update()

    return ft.Container(
        padding=20, expand=True, bgcolor="#16213E",
        content=ft.Column(
            controls=[
                ft.Text("⚙️ Configuración General",
                        style="headlineMedium", color="white"),
                e_rfc, e_nsm, e_nsue, e_lat, e_lon,
                ft.ElevatedButton("Guardar", on_click=on_save,
                                  bgcolor="#0F3460", color="white"),
                msg
            ],
            spacing=15
        )
    )


# ================ MODBUS CONFIG ================
def view_modbus(page: ft.Page):
    puertos      = obtener_puertos_com()
    cmb_port     = ft.Dropdown(label="Puerto COM",
                               options=[ft.dropdown.Option(p) for p in puertos])
    e_baud       = ft.TextField(label="Baudrate", value="9600")
    cmb_bytesize = ft.Dropdown(label="Bits de datos",
                               options=[ft.dropdown.Option(s) for s in ["5","6","7","8"]])
    cmb_parity   = ft.Dropdown(label="Paridad",
                               options=[ft.dropdown.Option(l) for l in ["Ninguna","Par","Impar"]])
    cmb_stop     = ft.Dropdown(label="Stop bits",
                               options=[ft.dropdown.Option(s) for s in ["1","1.5","2"]])
    msg          = ft.Text(color="white")

    def on_test(e):
        try:
            m = ModbusRTUManager(
                port=cmb_port.value,
                baudrate=int(e_baud.value),
                slave_id=1,
                parity={"Ninguna":"N","Par":"E","Impar":"O"}[cmb_parity.value],
                stopbits=float(cmb_stop.value),
                bytesize=int(cmb_bytesize.value)
            )
            msg.value = "✅ Conectado" if m.connect() else "❌ Falló"
        except Exception as ex:
            msg.value = f"⚠️ {ex}"
        page.update()

    return ft.Container(
        padding=20, expand=True, bgcolor="#16213E",
        content=ft.Column(
            controls=[
                ft.Text("🔌 Configuración Modbus",
                        style="headlineMedium", color="white"),
                cmb_port, e_baud, cmb_bytesize, cmb_parity, cmb_stop,
                ft.ElevatedButton("Probar conexión", on_click=on_test,
                                  bgcolor="#0F3460", color="white"),
                msg
            ],
            spacing=15
        )
    )



# ================ FTP/SMS & USB ================
def view_envio_usb(page: ft.Page):
    ftp_cfg = ConfigManager.cargar_config_ftp()
    general = ConfigManager.cargar_config_general()
    e_host  = ft.TextField(label="Servidor FTP", value=ftp_cfg.get("host",""))
    e_usr   = ft.TextField(label="Usuario FTP",  value=ftp_cfg.get("usuario",""))
    e_pass  = ft.TextField(label="Contraseña FTP",
                           password=True, can_reveal_password=True)
    e_sms   = ft.TextField(label="Teléfono SMS", value=ftp_cfg.get("numero_destino",""))

    # Dropdowns para hora y minuto
    # Inicializamos con la hora_programada (formato "HH:MM")
    hora_cfg = general.get("hora_programada","00:01")
    hh, mm = hora_cfg.split(":")

    cmb_hour = ft.Dropdown(
        label="Hora (HH)",
        width=100,
        value=hh,
        options=[ft.dropdown.Option(f"{i:02d}") for i in range(24)]
    )
    cmb_min  = ft.Dropdown(
        label="Minuto (MM)",
        width=100,
        value=mm,
        options=[ft.dropdown.Option(f"{i:02d}") for i in range(60)]
    )

    chk_auto = ft.Checkbox(label="Envio automático", value=True)
    msg1, msg2 = ft.Text(), ft.Text()

    def on_save(e):
        try:
            # Guardar FTP/SMS
            ConfigManager.guardar_config_ftp({
                "host": e_host.value,
                "usuario": e_usr.value,
                "clave_cifrada": FTPManager.cifrar_contraseña(e_pass.value),
                "numero_destino": e_sms.value
            })
            # Guardar hora programada en config general
            cg = ConfigManager.cargar_config_general()
            cg["hora_programada"] = f"{cmb_hour.value}:{cmb_min.value}"
            ConfigManager.guardar_config_general(cg)

            msg1.value = "✅ Configuración guardada"
        except Exception as ex:
            msg1.value = f"⚠️ {ex}"
        page.update()

    def on_export(e):
        ok = USBManejador.guardar_en_usb("Archivo TXT", "reporte_diario")
        msg2.value = "✅ Archivo TXT exportado a USB" if ok else "❌ No se detectó USB"
        page.update()

    return ft.Container(
        padding=20, expand=True, bgcolor="#16213E",
        content=ft.Column(
            spacing=15,
            controls=[
                ft.Text("📤 FTP/SMS y Exportación USB",
                        style="headlineMedium", color="white"),
                e_host, e_usr, e_pass, e_sms,

                # Row con Hour y Minute dropdowns
                ft.Row(
                    controls=[
                        ft.Text("Hora de envío automático:", color="white", width=200),
                        cmb_hour,
                        ft.Text(":", color="white"),
                        cmb_min
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=5
                ),

                chk_auto,
                ft.ElevatedButton("Guardar configuración", on_click=on_save,
                                  bgcolor="#0F3460", color="white"),
                msg1,
                ft.Divider(),
                ft.Text("Exportar archivo TXT a USB:", color="white"),
                ft.ElevatedButton("Exportar ahora", on_click=on_export,
                                  bgcolor="#E94560", color="white"),
                msg2
            ]
        )
    )





# ================ CUENTA ================
def view_cuenta(page: ft.Page):
    txt_u = ft.TextField(label="Nuevo usuario")
    txt_p = ft.TextField(label="Nueva contraseña",
                         password=True, can_reveal_password=True)
    msg   = ft.Text()

    def on_update(e):
        try:
            cfg = ConfigManager.cargar_config_login()
            cfg["usuarios"][txt_u.value] = txt_p.value
            ConfigManager.guardar_config_login(cfg)
            msg.value = "✅ Actualizado"
        except Exception as ex:
            msg.value = f"⚠️ {ex}"
        page.update()

    return ft.Container(
        padding=20, expand=True, bgcolor="#16213E",
        content=ft.Column(
            controls=[
                ft.Text("👤 Cuenta", style="headlineMedium", color="white"),
                txt_u, txt_p,
                ft.ElevatedButton("Actualizar", on_click=on_update,
                                  bgcolor="#0F3460", color="white"),
                msg
            ],
            spacing=15
        )
    )


# ================ MONITOREO ================
def view_monitoreo(page: ft.Page):
    graph_box = ft.Container(
        width=600, height=200,
        bgcolor="#1E1E1E",
        border=ft.border.all(2, ft.Colors.GREY),
        border_radius=8,
        content=ft.Text("📈 Gráfico de flujo acumulado",
                        color="white", text_align="center")
    )
    conectado = InternetManager.is_connected()

    return ft.Container(
        padding=20, expand=True, bgcolor="#16213E",
        content=ft.Column(
            controls=[
                ft.Text("📊 Monitoreo", style="headlineLarge",
                        color="white", text_align="center"),
                ft.Text(f"Internet: {'🟩 Conectado' if conectado else '🟥 Desconectado'}",
                        style="titleMedium", color="white", text_align="center"),
                graph_box,
                ft.Text("Flujo instantáneo: --", style="titleMedium",
                        color="white", text_align="center"),
                ft.Text("Flujo acumulado: --",   style="titleMedium",
                        color="white", text_align="center"),
                ft.Text("Velocidad: --",         style="titleMedium",
                        color="white", text_align="center"),
                ft.Text("Temperatura: --",       style="titleMedium",
                        color="white", text_align="center"),
            ],
            spacing=25,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )


# ================= MAIN DASHBOARD =================
def main_view(page: ft.Page):
    page.controls.clear()
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Config. General", content=view_config_general(page)),
            ft.Tab(text="Conexión Modbus", content=view_modbus(page)),
            ft.Tab(text="FTP/SMS & USB",   content=view_envio_usb(page)),
            ft.Tab(text="Cuenta",          content=view_cuenta(page)),
            ft.Tab(text="Monitoreo",       content=view_monitoreo(page)),
        ],
        expand=True
    )
    page.add(tabs)
    page.update()


# ================= APP ENTRYPOINT =================
def main(page: ft.Page):
    page.title = "Tesseract Hydro Monitor"
    page.window_maximized = True
    if page.session.get("logueado"):
        main_view(page)
    else:
        login_view(page)

if __name__ == "__main__":
    ft.app(target=main)
