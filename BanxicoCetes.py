"""
V1
Fecha: 07/10/2026
Autor: Mildred ER
Solicitud: Programa banxico.
"""
import os
import time
import random
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Carga los datos secretos del archivo .env
load_dotenv()

CORREO_REMITENTE = os.getenv("CORREO_REMITENTE")
PASSWORD_APLICACION = os.getenv("PASSWORD_APLICACION")
TOKEN_BANXICO = os.getenv("TOKEN_BANXICO")

# Series para la opcion 1 (se elige una al azar)
SERIES_ALEATORIAS = ["SF43718", "SF43783", "SF61745", "SP68257"]

# Serie de CETES a 28 dias (opcion 2)
SERIE_CETES = "SF43936"
DIAS_CETES = 28


def validar_correo(correo):
    """Regresa True si el correo tiene formato valido, si no False."""
    if " " in correo or correo.count("@") != 1:
        return False
    usuario, dominio = correo.split("@")
    if usuario == "" or "." not in dominio:
        return False
    if dominio.startswith(".") or dominio.endswith("."):
        return False
    return True


def consultar_banxico(serie):
    """Consulta el dato mas reciente de una serie. Regresa (valor, fecha) o None."""
    # Validamos que exista el token
    if not TOKEN_BANXICO:
        print("Error: falta TOKEN_BANXICO en el archivo .env")
        return None

    url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/" + serie + "/datos/oportuno"
    headers = {"Bmx-Token": TOKEN_BANXICO}

    try:
        print("\nConectando con Banxico para la serie " + serie + "...")
        respuesta = requests.get(url, headers=headers, timeout=10)

        if respuesta.status_code == 200:
            datos = respuesta.json()
            info = datos["bmx"]["series"][0]["datos"][0]
            valor = float(info["dato"])
            fecha = info["fecha"]
            return valor, fecha
        else:
            print("Error: el servidor respondio con el codigo " + str(respuesta.status_code))
            return None

    except requests.exceptions.RequestException as error:
        print("Error de conexion: " + str(error))
        return None
    except (KeyError, IndexError, ValueError) as error:
        print("Error al leer los datos: " + str(error))
        return None


def enviar_email(correo_destino, contenido):
    """Envia el reporte por correo en texto plano. Regresa True o False."""
    # Validamos credenciales y formato del correo
    if not CORREO_REMITENTE or not PASSWORD_APLICACION:
        print("Error: faltan las credenciales de correo en el archivo .env")
        return False
    if not validar_correo(correo_destino):
        print("Error: el correo no tiene un formato valido")
        return False

    try:
        mensaje = MIMEText(contenido, "plain", "utf-8")
        mensaje["Subject"] = "Reporte CETES"
        mensaje["From"] = CORREO_REMITENTE
        mensaje["To"] = correo_destino

        print("Conectando con Gmail...")
        servidor = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
        servidor.starttls()
        servidor.login(CORREO_REMITENTE, PASSWORD_APLICACION)
        servidor.sendmail(CORREO_REMITENTE, correo_destino, mensaje.as_string())
        servidor.quit()

        print("Correo enviado con exito a " + correo_destino)
        return True

    except smtplib.SMTPAuthenticationError:
        print("Error: correo o contrasena de aplicacion incorrectos")
    except smtplib.SMTPException as error:
        print("Error al enviar el correo: " + str(error))
    except OSError as error:
        print("Error de conexion con el servidor de correo: " + str(error))
    return False


def pedir_numero(mensaje):
    """Pide un numero mayor a cero y repite hasta que sea valido."""
    while True:
        try:
            numero = float(input(mensaje))
            if numero > 0:
                return numero
            print("Error: el numero debe ser mayor a cero")
        except ValueError:
            print("Error: debes escribir un numero")


def opcion_aleatoria():
    """Opcion 1: consulta una serie de Banxico elegida al azar."""
    serie = random.choice(SERIES_ALEATORIAS)
    resultado = consultar_banxico(serie)

    if resultado is not None:
        valor, fecha = resultado
        print("Conexion exitosa!")
        print("Serie: " + serie + " | Fecha: " + fecha + " | Valor: " + str(valor))


def opcion_cetes():
    """Opcion 2: consulta CETES, calcula el rendimiento y envia el reporte."""
    resultado = consultar_banxico(SERIE_CETES)

    if resultado is None:
        print("No se pudo obtener la tasa de CETES, no se puede calcular.")
        return

    tasa, fecha = resultado
    print("Tasa de CETES: " + str(tasa) + "% (fecha " + fecha + ")")

    # Pedimos los datos al usuario
    monto = pedir_numero("Ingresa el monto a invertir: ")
    dias = DIAS_CETES

    # Formula: interes = monto * (tasa / 100) * (dias / 360)
    interes = monto * (tasa / 100) * (dias / 360)
    monto_final = monto + interes

    # Reporte con variables dinamicas
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    reporte = "REPORTE DE CALCULO ISC\n"
    reporte = reporte + "Fecha de generacion: " + ahora + "\n"
    reporte = reporte + "Serie consultada: " + SERIE_CETES + "\n"
    reporte = reporte + "Fecha del dato de Banxico: " + fecha + "\n"
    reporte = reporte + "Valor obtenido de Banxico: " + str(tasa) + "\n"
    reporte = reporte + "\n"
    reporte = reporte + "Monto invertido (capital inicial): $" + f"{monto:,.2f}" + "\n"
    reporte = reporte + "Tasa a " + f"{dias:g}" + " dias en CETES con interes de " + str(tasa) + "%\n"
    reporte = reporte + "Dinero ganado sin el capital inicial: $" + f"{interes:,.2f}" + "\n"
    reporte = reporte + "Resultado final del ISC (monto final): $" + f"{monto_final:,.2f}" + "\n"

    print("\n" + reporte)
    time.sleep(2)

    # Preguntamos el correo hasta que sea valido
    while True:
        destino = input("A que correo quieres enviar el reporte? (Enter para omitir): ").strip()
        if destino == "":
            print("Se omite el envio.")
            break
        if validar_correo(destino):
            enviar_email(destino, reporte)
            break
        print("Formato de correo invalido, intenta de nuevo.")


def menu_principal():
    """Muestra el menu hasta que el usuario elige salir."""
    while True:
        print("\nMENU DEL PROGRAMA")
        print("1. Consultar una serie de Banxico aleatoria")
        print("2. Calcular CETES y enviar reporte")
        print("3. Salir")

        opcion = input("Selecciona una opcion (1-3): ").strip()

        try:
            if opcion == "1":
                opcion_aleatoria()
            elif opcion == "2":
                opcion_cetes()
            elif opcion == "3":
                print("Saliendo del programa...")
                time.sleep(2)
                break
            else:
                print("Opcion invalida. Escribe 1, 2 o 3.")
        except Exception as error:
            print("Ocurrio un error inesperado: " + str(error))


# El programa empieza aqui
if __name__ == "__main__":
    menu_principal()
