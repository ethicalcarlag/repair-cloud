# =============================================================================
# PROYECTO: RepAIr System CLOUD v8.0 (Arcane Hextech Edition)
# AUTORAS: Carla 
# =============================================================================

import streamlit as st
import pandas as pd
import json
import os
import qrcode
from datetime import datetime
from fpdf import FPDF
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIGURACIÓN VISUAL (ESTILO ARCANE/HEXTECH) ---
st.set_page_config(page_title="RepAIr Hextech", page_icon="💎", layout="wide")

st.markdown("""
    <style>
        /* FONDO Y TEXTOS GENERALES */
        .stApp {
            background-color: #1A1C2C; /* Azul oscuro Piltover */
            background-image: linear-gradient(180deg, #1A1C2C 0%, #0D0E15 100%);
            color: #C8AA6E; /* Dorado Hextech */
        }
        
        /* FUENTES Y TITULOS */
        h1, h2, h3 {
            font-family: 'Cinzel', serif;
            color: #F0E6D2 !important;
            text-shadow: 0px 0px 10px #0078D7;
        }
        
        /* CAJAS DE TEXTO (INPUTS) */
        .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div {
            background-color: #090A0F;
            color: #F0E6D2;
            border: 1px solid #C8AA6E;
            border-radius: 4px;
        }
        
        /* BOTONES NORMALES (Bronce/Dorado) */
        div.stButton > button {
            background: linear-gradient(45deg, #785A28, #C8AA6E);
            color: #000000;
            font-weight: bold;
            border: 2px solid #F0E6D2;
            transition: all 0.3s;
        }
        div.stButton > button:hover {
            background: linear-gradient(45deg, #C8AA6E, #F0E6D2);
            box-shadow: 0 0 15px #C8AA6E;
            border-color: #FFFFFF;
        }

        /* BOTÓN PÁNICO (Rojo Brillante) */
        .panic-btn {
            border: 2px solid #FF0000 !important;
            color: #FF0000 !important;
            text-shadow: 0 0 5px red;
        }

        /* MENSAJES DE ÉXITO/INFO */
        .stAlert {
            background-color: #090A0F;
            border: 1px solid #0078D7;
            color: #00B4FF;
        }
        
        /* OCULTAR HEADER */
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN GOOGLE SHEETS ---
def conectar_gsheets():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        key_content = st.secrets["service_account"]["key_data"].strip()
        key_dict = json.loads(key_content)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        sheet_db = client.open("repair_db").sheet1
        sheet_hist = client.open("repair_history").sheet1
        return sheet_db, sheet_hist
    except Exception as e:
        return None, None

# --- VARIABLES SESIÓN ---
if 'ai_response' not in st.session_state: st.session_state.ai_response = ""
if 'items_factura' not in st.session_state: st.session_state.items_factura = []
if 'precio_total' not in st.session_state: st.session_state.precio_total = 0.0

# --- CATÁLOGO ---
CATALOGO_LISTA = [("--- SERVICIOS ---", 0), ("Mano de Obra", 30.0), ("Diagnóstico", 25.0), ("Limpieza", 35.0), ("--- COMPONENTES ---", 0), ("SSD 1TB", 85.0), ("RAM 8GB", 26.0), ("RTX 4060", 330.0)]
PRECIOS_DICT = {item[0]: item[1] for item in CATALOGO_LISTA}

# --- FUNCIONES ---
def cargar_datos_gsheet(hoja):
    try: return hoja.get_all_records()
    except: return []

def guardar_ticket_gsheet(hoja, ticket):
    if not hoja.row_values(1): # Chequeo de seguridad
        st.error("⚠️ ERROR CRÍTICO: Las cabeceras del Excel están mal. Fila 1 vacía."); return False
    fila = [ticket["fecha"], ticket["cliente"], ticket["password"], ticket["dispositivo"], ticket["tipo"], ticket["descripcion"], str(ticket["urgente"]), ticket.get("ia_response", "N/A")]
    hoja.append_row(fila); return True

def generar_pdf(ticket, tecnico, precio, nota, items):
    pdf = FPDF(); pdf.add_page(); qr = qrcode.make(f"HEX-ID-{ticket['cliente']}"); qr.save("temp.png")
    pdf.set_fill_color(26, 28, 44); pdf.rect(0,0,210,297,"F") # Fondo oscuro PDF
    pdf.set_text_color(200, 170, 110) # Texto dorado
    pdf.set_font("Arial", "B", 16); pdf.cell(0, 10, "RepAIr Cloud - FACTURA HEXTECH", ln=1, align="C")
    pdf.image("temp.png", x=170, y=10, w=30)
    pdf.ln(10); pdf.set_font("Arial", size=12)
    datos = [f"Fecha: {datetime.now().strftime('%d/%m')}", f"Cliente: {ticket['cliente']}", f"Dispositivo: {ticket['dispositivo']}", f"Técnico: {tecnico}"]
    for d in datos: pdf.cell(0, 10, d.encode('latin-1','replace').decode('latin-1'), ln=1)
    pdf.ln(5); pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, "DETALLE:", ln=1)
    pdf.set_font("Arial", size=12)
    for i, c in items: pdf.cell(150, 10, f"- {i}"); pdf.cell(30, 10, f"{c} E", ln=1, align="R")
    pdf.ln(10); pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, f"TOTAL: {precio} EUR", ln=1, align="R")
    return pdf.output(dest="S").encode("latin-1")

def mover_historial(sheet_db, sheet_hist, ticket, tec, precio, nota, items):
    hist_row = [datetime.now().strftime("%Y-%m-%d"), ticket['cliente'], ticket['dispositivo'], tec, precio, nota, items]
    sheet_hist.append_row(hist_row)
    todos = sheet_db.get_all_records()
    sheet_db.clear(); sheet_db.append_row(["fecha", "cliente", "password", "dispositivo", "tipo", "descripcion", "urgente", "ia_response"])
    for t in todos:
        if not (t['cliente'] == ticket['cliente'] and t['fecha'] == ticket['fecha']):
            row = [t['fecha'], t['cliente'], t['password'], t['dispositivo'], t['tipo'], t['descripcion'], str(t['urgente']), t.get('ia_response','')]
            sheet_db.append_row(row)

# --- INTERFAZ PRINCIPAL ---
sheet_db, sheet_hist = conectar_gsheets()

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Unofficial_JavaScript_logo_2.svg/1200px-Unofficial_JavaScript_logo_2.svg.png", width=50) # Pon aquí tu logo si quieres
    st.title("💎 RepAIr Hextech")
    if sheet_db: st.success("✅ EN LÍNEA")
    else: st.error("❌ DESCONECTADO")
    menu = st.radio("NAVEGACIÓN", ["🏠 Recepción", "🔧 Taller", "💰 Finanzas"])

# === RECEPCIÓN (AI MEJORADA) ===
if menu == "🏠 Recepción":
    st.markdown("## 📝 Nueva Entrada")
    
    # --- PARTE 1: DATOS (Fuera del form para interactividad) ---
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Cliente")
    passw = c2.text_input("Contraseña")
    disp = c1.selectbox("Dispositivo", ["PC", "Portátil", "Consola", "Móvil", "Otro"])
    tipo = c2.selectbox("Categoría", ["Software", "Hardware", "Ambas"])
    
    # --- PARTE 2: DESCRIPCIÓN + AI (Aquí estaba el fallo antes) ---
    st.markdown("### 🔍 Diagnóstico")
    desc = st.text_area("Describe el problema:", height=100)
    
    # Botón AI justo debajo
    if st.button("✨ CONSULTAR A AI-LEEN"):
        if desc:
            txt = desc.lower()
            resp = "🤖 AI: Diagnóstico genérico. Se recomienda revisión manual."
            if "mojado" in txt or "agua" in txt: resp = "🤖 AI: 💧 PELIGRO LÍQUIDOS. No encender. Baño isopropílico."
            elif "pantalla" in txt and "rota" in txt: resp = "🤖 AI: 🔨 Cambio de Display necesario."
            elif "lento" in txt: resp = "🤖 AI: 🐌 Posible fallo HDD. Recomendar SSD."
            st.session_state.ai_response = resp
        else:
            st.warning("Escribe el problema primero.")
            
    if st.session_state.ai_response:
        st.info(st.session_state.ai_response)

    # --- PARTE 3: GUARDAR (Formulario final) ---
    with st.form("save_form"):
        urgente = st.checkbox("⚡ PRIORIDAD HEXTECH")
        # El botón final
        enviado = st.form_submit_button("🚀 REGISTRAR TICKET EN LA NUBE")
    
    if enviado:
        if cliente and desc and sheet_db:
            t = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "cliente": cliente, "password": passw, "dispositivo": disp, "tipo": tipo, "descripcion": desc, "urgente": urgente, "ia_response": st.session_state.ai_response}
            exito = guardar_ticket_gsheet(sheet_db, t)
            if exito:
                st.balloons()
                st.success("✅ TICKET ENVIADO A LA BASE DE DATOS")
                st.session_state.ai_response = ""
        else:
            st.error("Faltan datos o falló la conexión.")

# === TALLER ===
elif menu == "🔧 Taller":
    st.markdown("## 🛠️ Mesa de Trabajo")
    pendientes = cargar_datos_gsheet(sheet_db) if sheet_db else []
    
    if not pendientes: st.info("👍 Taller limpio. Buen trabajo.")
    
    for i, t in enumerate(pendientes):
        # Diseño de Tarjeta
        with st.expander(f"{'🔥' if str(t['urgente'])=='True' else '⚙️'} {t['cliente']} | {t['dispositivo']}"):
            st.markdown(f"**Síntomas:** {t['descripcion']}")
            if t.get('ia_response'): st.code(f"{t['ia_response']}")
            
            c_cat, c_act = st.columns(2)
            with c_cat:
                st.markdown("#### 🧾 Piezas y Servicios")
                sel = st.selectbox("Catálogo", [x[0] for x in CATALOGO_LISTA], key=f"s{i}")
                
                b1, b2 = st.columns(2)
                if b1.button("➕ Añadir", key=f"add{i}"):
                    p = PRECIOS_DICT.get(sel, 0)
                    if p>0: st.session_state.items_factura.append((sel, p)); st.session_state.precio_total += p; st.rerun()
                if b2.button("↩️ Deshacer", key=f"undo{i}"):
                    if st.session_state.items_factura: 
                        rem = st.session_state.items_factura.pop(); st.session_state.precio_total -= rem[1]; st.rerun()
                
                st.markdown("---")
                for it, pr in st.session_state.items_factura: st.text(f"{it} ... {pr}€")
                st.markdown(f"### TOTAL: {st.session_state.precio_total} €")

            with c_act:
                st.markdown("#### ✅ Finalización")
                tec = st.text_input("Técnico Responsable", key=f"tec{i}")
                nota = st.text_area("Informe Técnico", key=f"nota{i}")
                
                if st.button("GENERAR FACTURA Y CERRAR", key=f"fin{i}"):
                    if tec:
                        items_str = ", ".join([x[0] for x in st.session_state.items_factura])
                        pdf = generar_pdf(t, tec, st.session_state.precio_total, nota, st.session_state.items_factura)
                        mover_historial(sheet_db, sheet_hist, t, tec, st.session_state.precio_total, nota, items_str)
                        st.session_state.items_factura=[]; st.session_state.precio_total=0
                        st.success("TICKET CERRADO"); st.download_button("📥 DESCARGAR FACTURA", pdf, f"Factura_{t['cliente']}.pdf")
                        st.rerun()

# === FINANZAS ===
elif menu == "💰 Finanzas":
    st.markdown("## 📊 Bóveda")
    if sheet_hist:
        df = pd.DataFrame(cargar_datos_gsheet(sheet_hist))
        if not df.empty:
            st.dataframe(df)
            st.metric("Total Reparaciones", len(df))
        else: st.warning("Bóveda vacía.")
