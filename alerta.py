import os
import requests
from amadeus import Client, ResponseError
from datetime import datetime, timedelta

# --- CARGA DE SECRETOS ---
try:
    API_KEY = os.environ["AMADEUS_API_KEY"]
    API_SECRET = os.environ["AMADEUS_API_SECRET"]
    TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
    TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
except KeyError:
    print("❌ Error: Faltan secretos en GitHub.")
    exit()

# --- CONFIGURACIÓN ---
ORIGEN = "MAD"
# Reducimos destinos para la prueba rápida
DESTINOS = ["LON", "PAR", "ROM", "MIL", "BER", "LIS"] 
PRECIO_CHOLLO = 100 

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    if res.status_code == 200:
        print("✅ Mensaje enviado a Telegram correctamente.")
    else:
        print(f"❌ Error al enviar a Telegram: {res.text}")

# --- FECHAS ---
hoy = datetime.now()
dias_viernes = (4 - hoy.weekday() + 7) % 7
if dias_viernes == 0: dias_viernes = 7
viernes = (hoy + timedelta(days=dias_viernes)).strftime('%Y-%m-%d')
domingo = (hoy + timedelta(days=dias_viernes+2)).strftime('%Y-%m-%d')

# --- LÓGICA ---
try:
    if "PENDIENTE" in API_KEY:
        print("⏳ Claves no configuradas (PENDIENTE).")
        exit()

    print("🤖 Iniciando Bot con claves de TEST...")
    # Usamos claves de TEST (hostname por defecto es test si no se pone production)
    amadeus = Client(client_id=API_KEY, client_secret=API_SECRET) 
    
    msg = f"🗓️ **Prueba Bot ({viernes})**\n"
    encontrado = False

    for codigo in DESTINOS:
        print(f"🔎 Mirando {codigo}...")
        try:
            res = amadeus.shopping.flight_offers_search.get(
                originLocationCode=ORIGEN, destinationLocationCode=codigo,
                departureDate=viernes, returnDate=domingo,
                adults=1, currencyCode='EUR', max=1
            )
            if res.data:
                vuelo = res.data[0]
                precio = float(vuelo['price']['total'])
                aerolinea = vuelo['itineraries'][0]['segments'][0]['carrierCode']
                
                print(f"   -> Encontrado: {precio}€")
                
                # EN MODO TEST: Guardamos todo para probar que Telegram va
                msg += f"✅ {codigo}: **{precio}€** ({aerolinea})\n"
                encontrado = True
                
        except ResponseError as e:
            print(f"⚠️ Error Amadeus en {codigo}: {e}")
            continue
        except Exception as e:
            print(f"⚠️ Error General en {codigo}: {e}")
            continue

    if encontrado:
        print("📨 Enviando resumen a Telegram...")
        enviar_telegram(f"🚨 **TEST DE CONEXIÓN** 🚨\n{msg}")
    else:
        print("🤷‍♂️ No se encontraron vuelos (o falló la conexión con Amadeus Test).")

except Exception as e:
    print(f"❌ Error Crítico del Script: {e}")
