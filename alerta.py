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
    print("⏳ Esperando claves de Amadeus...")
    exit()

# --- CONFIGURACIÓN ---
ORIGEN = "MAD"
DESTINOS = ["LON", "PAR", "ROM", "MIL", "BER", "LIS", "OPO", "BRU", "AMS", "DUB", "RAK", "VCE"]
PRECIO_CHOLLO = 100 

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# --- FECHAS (Próximo finde) ---
hoy = datetime.now()
dias_viernes = (4 - hoy.weekday() + 7) % 7
if dias_viernes == 0: dias_viernes = 7
viernes = (hoy + timedelta(days=dias_viernes)).strftime('%Y-%m-%d')
domingo = (hoy + timedelta(days=dias_viernes+2)).strftime('%Y-%m-%d')

# --- LÓGICA ---
try:
    # Si las claves son "PENDIENTE", paramos suavemente
    if "PENDIENTE" in API_KEY:
        print("Claves aún no configuradas.")
        exit()

    amadeus = Client(client_id=API_KEY, client_secret=API_SECRET, hostname='production')
    msg = f"🗓️ **Finde {viernes[5:]} al {domingo[5:]}**\n"
    encontrado = False

    for codigo in DESTINOS:
        try:
            res = amadeus.shopping.flight_offers_search.get(
                originLocationCode=ORIGEN, destinationLocationCode=codigo,
                departureDate=viernes, returnDate=domingo,
                adults=1, currencyCode='EUR', max=1
            )
            if res.data:
                vuelo = res.data[0]
                precio = float(vuelo['price']['total'])
                # Filtro: ¿Es directo?
                directo = True
                if len(vuelo['itineraries'][0]['segments']) > 1 or len(vuelo['itineraries'][1]['segments']) > 1:
                    directo = False

                if precio <= PRECIO_CHOLLO and directo:
                    aerolinea = vuelo['itineraries'][0]['segments'][0]['carrierCode']
                    msg += f"✅ {codigo}: **{precio}€** ({aerolinea})\n"
                    encontrado = True
        except: continue

    if encontrado:
        enviar_telegram(f"🚨 **CHOLLOS DETECTADOS** 🚨\n{msg}")
    else:
        print("Sin chollos esta semana.")

except Exception as e:
    print(f"Error: {e}")
