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
# Lista completa de destinos
DESTINOS = ["LON", "PAR", "ROM", "MIL", "BER", "LIS", "OPO", "BRU", "AMS", "DUB", "RAK", "VCE", "NAP", "PRG", "BUD"]
PRECIO_CHOLLO = 120 # Subimos un pelín el margen para encontrar horarios premium

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# --- FECHAS (Próximo Fin de Semana) ---
hoy = datetime.now()
dias_viernes = (4 - hoy.weekday() + 7) % 7
if dias_viernes == 0: dias_viernes = 7
viernes = (hoy + timedelta(days=dias_viernes)).strftime('%Y-%m-%d')
domingo = (hoy + timedelta(days=dias_viernes+2)).strftime('%Y-%m-%d')

# --- LÓGICA PRINCIPAL ---
try:
    if "PENDIENTE" in API_KEY:
        print("⏳ Claves PENDIENTE.")
        exit()

    # !!! CUANDO TENGAS CLAVES REALES: CAMBIA 'test' POR 'production' !!!
    amadeus = Client(client_id=API_KEY, client_secret=API_SECRET, hostname='test')
    
    msg = f"🗓️ **Escapadas {viernes[5:]} - {domingo[5:]}**\n"
    encontrado = False

    print(f"🔎 Buscando vuelos Viernes(>15h) - Domingo(Todo el día)...")

    for codigo in DESTINOS:
        try:
            # Pedimos 20 opciones para poder elegir el mejor horario
            res = amadeus.shopping.flight_offers_search.get(
                originLocationCode=ORIGEN, destinationLocationCode=codigo,
                departureDate=viernes, returnDate=domingo,
                adults=1, currencyCode='EUR', max=20
            )
            
            if not res.data: continue

            # Variables para guardar candidatos
            mejor_opcion = None
            opcion_tarde = None    # Vuelo que vuelve > 15:00
            opcion_manana = None   # Vuelo que vuelve < 15:00 (Backup)

            for vuelo in res.data:
                # 1. Filtro Precio
                precio = float(vuelo['price']['total'])
                if precio > PRECIO_CHOLLO: continue

                # 2. Filtro Vuelo Directo (Opcional, pero recomendado)
                segs_ida = vuelo['itineraries'][0]['segments']
                segs_vuelta = vuelo['itineraries'][1]['segments']
                if len(segs_ida) > 1 or len(segs_vuelta) > 1: continue

                # 3. FILTRO HORARIO VIERNES (SALIDA)
                # Formato API: "2024-05-20T18:30:00" -> Cogemos la hora
                hora_salida_v = int(segs_ida[0]['departure']['at'].split('T')[1][:2])
                
                if hora_salida_v < 15: continue # Si sale antes de las 15:00 el viernes, lo descartamos
                
                # 4. CLASIFICACIÓN POR HORARIO DOMINGO (REGRESO)
                hora_regreso_d = int(segs_vuelta[0]['departure']['at'].split('T')[1][:2])
                
                if hora_regreso_d >= 15:
                    # ¡Bingo! Vuelve tarde. Si no teníamos uno tarde, guardamos este.
                    if not opcion_tarde: opcion_tarde = vuelo
                else:
                    # Vuelve pronto. Si no teníamos uno de mañana, guardamos este.
                    if not opcion_manana: opcion_manana = vuelo

                # Si ya tenemos uno de tarde (que es el preferido), dejamos de buscar para esta ciudad
                if opcion_tarde: break

            # DECISIÓN FINAL: ¿Cuál mostramos?
            # Prioridad: El de la tarde. Si no hay, el de la mañana.
            if opcion_tarde:
                mejor_opcion = opcion_tarde
                icono = "⭐" # Estrella para horario premium
            elif opcion_manana:
                mejor_opcion = opcion_manana
                icono = "☕" # Café para madrugadores
            
            # Si hemos encontrado algo válido, lo añadimos al mensaje
            if mejor_opcion:
                p = float(mejor_opcion['price']['total'])
                aero = mejor_opcion['itineraries'][0]['segments'][0]['carrierCode']
                h_ida = mejor_opcion['itineraries'][0]['segments'][0]['departure']['at'].split('T')[1][:5]
                h_vuelta = mejor_opcion['itineraries'][1]['segments'][0]['departure']['at'].split('T')[1][:5]
                
                msg += f"✅ {codigo}: **{p}€** ({aero}) | 🛫V {h_ida} - 🛬D {h_vuelta} {icono}\n"
                encontrado = True
                print(f"   -> {codigo}: {p}€ ({icono})")

        except Exception as e:
            print(f"⚠️ Error {codigo}: {e}")
            continue

    if encontrado:
        enviar_telegram(f"🚨 **ALERTA SEMANAL** 🚨\n{msg}\n_⭐: Vuelta tarde | ☕: Vuelta pronto_")
        print("✅ Enviado a Telegram.")
    else:
        print("🤷‍♂️ Sin resultados que cumplan filtros.")

except Exception as e:
    print(f"❌ Error crítico: {e}")
