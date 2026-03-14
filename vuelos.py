# --- ZONA DE CONTROL ---
with st.container(border=True):
    col_auto1, col_auto2, col_dummy = st.columns([1, 1, 2])
    
    # Botón 1: El que ya tenías
    if col_auto1.button("📅 Mes Siguiente (+30d)", type="secondary"):
        hoy = datetime.now()
        futuro = hoy + timedelta(days=30)
        dias_v = (4 - futuro.weekday() + 7) % 7
        v_fut = futuro + timedelta(days=dias_v)
        st.session_state.def_ida = v_fut
        st.session_state.def_vuelta = v_fut + timedelta(days=2)
        st.rerun()

    # Botón 2: NUEVO BOTÓN PARA PROBAR ESCAPADAS DE 1 DÍA
    if col_auto2.button("⚡ Próximo Finde (Sáb-Dom)", type="primary"):
        hoy = datetime.now()
        dias_sabado = (5 - hoy.weekday() + 7) % 7
        if dias_sabado == 0: dias_sabado = 7
        sabado_prox = hoy + timedelta(days=dias_sabado)
        
        st.session_state.def_ida = sabado_prox
        st.session_state.def_vuelta = sabado_prox + timedelta(days=1) # Vuelve el domingo
        st.rerun()

    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    
    def_ida = st.session_state.get('def_ida', datetime.now() + timedelta(days=7))
    def_vuelta = st.session_state.get('def_vuelta', datetime.now() + timedelta(days=8)) # Por defecto 1 día
    
    with c1: f_ida = st.date_input("Ida", def_ida)
    with c2: f_vuelta = st.date_input("Vuelta", def_vuelta)
    with c3: 
        region = st.selectbox("Destino", ["Europa (Recomendado)", "Mundo Entero"])
        region_code = "/m/02j9z" if "Europa" in region else ""
    with c4: presu = st.number_input("Max €", 50, 2000, 150, step=10)

    with st.expander("🕒 Filtros de Horario (Salida y Regreso)", expanded=True):
        ch1, ch2 = st.columns(2)
        # Ajustados a Sábado mañana y Domingo tarde
        h_ida = ch1.slider("Salida Ida (Hasta las)", 0, 23, 12, format="%dh") 
        h_vuelta = ch2.slider("Salida Vuelta (Desde las)", 0, 23, 16, format="%dh")
        
        # Filtros exactos: Ida de 05h hasta la hora elegida, vuelta desde la hora elegida hasta 23h
        str_ida = f"05,{h_ida}" 
        str_vuelta = f"{h_vuelta},23"

    if st.button("🔎 ESCANEAR CIELO", type="primary", use_container_width=True):
        s_ida = f_ida.strftime('%Y-%m-%d')
        s_vuelta = f_vuelta.strftime('%Y-%m-%d')
        
        with st.spinner("Conectando satélites... (Esto gasta 1 llamada API)"):
            st.session_state.resultados = buscar_vuelos(
                "MAD", region_code, s_ida, s_vuelta, presu, str_ida, str_vuelta
            )
            
            if st.session_state.resultados:
                msg = f"🚀 **VUELINGTON MANUAL**\n📅 {f_ida.strftime('%d/%b')} - {f_vuelta.strftime('%d/%b')}\n\n"
                for v in st.session_state.resultados[:8]:
                    msg += f"✈️ {v['destino']}: **{v['precio']}€** ({v['aerolinea']})\n🔗 [Ver]({v['link']})\n\n"
                st.session_state.msg_telegram = msg
