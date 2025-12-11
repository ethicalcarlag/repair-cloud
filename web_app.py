# =============================================================================
# PROYECTO: RepAIr System CLOUD v7.2 (Turbo Mode + Forms)
# AUTORA: Carla
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

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="RepAIr Cloud Turbo", page_icon="🐉", layout="wide")
st.markdown("""
    <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        header {visibility: hidden;}
        /* Estilo para formularios */
        [data-testid="stForm"] { border: 1px solid #262730; padding: 20px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN GOOGLE SHEETS ---
def conectar_gsheets():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        key_content = st.secrets["service_account"]["key_data"].strip()
        key_dict = json.loads(key_content)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        # Intentamos abrir las hojas
        sheet_db = client.open("repair_db").sheet1
        sheet_hist = client.open("repair_history").sheet1
        return sheet_db, sheet_hist
    except Exception as e:
        return None, None

# --- VARIABLES DE SESIÓN ---
if 'ai_response' not in st.session_state: st.session_state.ai_response = ""
if 'items_factura' not in st.session_state: st.session_state.items_factura = []
if 'precio_total' not in st.session_state: st.session_state.precio_total = 0.0

# --- CATÁLOGO ---
CATALOGO_LISTA = [
    ("--- SERVICIOS ---", 0), ("Mano de Obra", 30.00), ("Diagnóstico", 25.00), ("Limpieza", 35.00),
    ("--- COMPONENTES ---", 0), ("SSD 480GB", 38.99), ("SSD 1TB", 85.00), ("RAM 8GB", 26.00),
    ("RTX 3060", 295.00), ("RTX 4060", 330.00), ("Fuente 750W", 110.00)
]
PRECIOS_DICT = {item[0]: item[1] for item in CATALOGO_LISTA}

# --- FUNCIONES AUXILIARES ---
def cargar_datos_gsheet(hoja):
    try: return hoja.get_all_records()
    except: return []

def guardar_ticket_gsheet(hoja, ticket):
    # Validar que la hoja tenga cabeceras
    if not hoja.row_values(1):
        st.error("⚠️ ¡LA HOJA DE GOOGLE SHEETS ESTÁ VACÍA! Pon las cabeceras en la Fila 1.")
        return False
    
    fila = [ticket["fecha"], ticket["cliente"], ticket["password"], ticket["dispositivo"], ticket["tipo"], ticket["descripcion"], str(ticket["urgente"]), ticket.get("ia_response", "N/A")]
    hoja.append_row(fila)
    return True

def generar_pdf(ticket, tecnico, precio, nota, items):
    pdf = FPDF(); pdf.add_page()
    qr = qrcode.make(f"ID-{ticket['cliente']}"); qr.save("temp.png")
    pdf.set_font("Arial", "B", 16); pdf.cell(0, 10, "RepAIr Cloud - FACTURA", ln=1, align="C")
    pdf.image("temp.png", x=170, y=10, w=30)
    pdf.ln(10); pdf.set_font("Arial", size=12)
    datos = [f"Fecha: {datetime.now().strftime('%d/%m')}", f"Cliente: {ticket['cliente']}", f"Técnico: {tecnico}"]
    for d in datos: pdf.cell(0, 10, d.encode('latin-1','replace').decode('latin-1'), ln=1)
    pdf.ln(5); pdf.cell(0, 10, "DETALLE:", ln=1)
    for i, c in items: pdf.cell(150, 10, f"- {i}"); pdf.cell(30, 10, f"{c} E", ln=1, align="R")
    pdf.ln(5); pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, f"TOTAL: {precio} EUR", ln=1, align="R")
    return pdf.output(dest="S").encode("latin-1")

def mover_historial(sheet_db, sheet_hist, ticket, tec, precio, nota, items):
    # Guardar en historial
    hist_row = [datetime.now().strftime("%Y-%m-%d"), ticket['cliente'], ticket['dispositivo'], tec, precio, nota, items]
    sheet_hist.append_row(hist_row)
    # Borrar de pendientes (Reescribiendo)
    todos = sheet_db.get_all_records()
    sheet_db.clear(); sheet_db.append_row(["fecha", "cliente", "password", "dispositivo", "tipo", "descripcion", "urgente", "ia_response"])
    for t in todos:
        if not (t['cliente'] == ticket['cliente'] and t['fecha'] == ticket['fecha']):
            row = [t['fecha'], t['cliente'], t['password'], t['dispositivo'], t['tipo'], t['descripcion'], str(t['urgente']), t.get('ia_response','')]
            sheet_db.append_row(row)

# --- INTERFAZ ---
sheet_db, sheet_hist = conectar_gsheets()

with st.sidebar:
    st.title("🐉 RepAIr Turbo")
    if sheet_db: st.success("✅ Conectado")
    else: st.error("❌ Error Conexión")
    menu = st.radio("MENÚ", ["🏠 Recepción", "🔧 Taller", "💰 CEO"])

# === RECEPCIÓN (OPTIMIZADA CON FORMULARIO) ===
if menu == "🏠 Recepción":
    st.header("📝 Nueva Entrada")
    
    # -- IA FUERA DEL FORMULARIO (Para que sea interactiva) --
    c_ia, c_desc = st.columns([1, 3])
    with c_ia:
        if st.button("✨ CONSULTAR AI-LEEN"):
            st.session_state.ai_response = "🤖 Análisis: Fallo probable en placa/software. Se recomienda test general."
    with c_desc:
        if st.session_state.ai_response:
            st.info(st.session_state.ai_response)

    # -- FORMULARIO (Evita el parpadeo y lentitud) --
    with st.form("form_recepcion"):
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente")
        passw = c2.text_input("Contraseña")
        disp = c1.selectbox("Dispositivo", ["PC", "Portátil", "Consola", "Móvil", "Otro"])
        tipo = c2.selectbox("Categoría", ["Software", "Hardware", "Ambos"])
        desc = st.text_area("Descripción Problema")
        urgente = st.checkbox("⚡ Urgente")
        
        # El botón de enviar está DENTRO del formulario
        enviado = st.form_submit_button("🚀 GUARDAR TICKET")
    
    if enviado:
        if cliente and desc and sheet_db:
            t = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "cliente": cliente, "password": passw, "dispositivo": disp, "tipo": tipo, "descripcion": desc, "urgente": urgente, "ia_response": st.session_state.ai_response}
            exito = guardar_ticket_gsheet(sheet_db, t)
            if exito:
                st.success("✅ ¡Guardado en la Nube!"); st.session_state.ai_response = ""
        else:
            st.error("Faltan datos o conexión.")

# === TALLER ===
elif menu == "🔧 Taller":
    st.header("🛠️ Taller")
    pendientes = cargar_datos_gsheet(sheet_db) if sheet_db else []
    
    if not pendientes: st.info("Nada pendiente.")
    
    for i, t in enumerate(pendientes):
        with st.expander(f"🔨 {t['cliente']} ({t['dispositivo']})"):
            st.write(f"**Fallo:** {t['descripcion']}")
            if t.get('ia_response'): st.caption(f"Nota IA: {t['ia_response']}")
            
            c_cat, c_act = st.columns(2)
            with c_cat:
                sel = st.selectbox("Añadir", [x[0] for x in CATALOGO_LISTA], key=f"s{i}")
                if st.button("➕", key=f"add{i}"):
                    p = PRECIOS_DICT.get(sel, 0)
                    if p>0: st.session_state.items_factura.append((sel, p)); st.session_state.precio_total += p; st.rerun()
                if st.session_state.items_factura:
                    st.caption("Ticket Actual:")
                    for it, pr in st.session_state.items_factura: st.text(f"{it}: {pr}€")
                    st.markdown(f"**TOTAL: {st.session_state.precio_total}€**")
                    if st.button("Limpiar Factura", key=f"cl{i}"): st.session_state.items_factura=[]; st.session_state.precio_total=0; st.rerun()
            
            with c_act:
                tec = st.text_input("Técnico", key=f"tec{i}")
                nota = st.text_area("Solución", key=f"sol{i}")
                if st.button("✅ FINALIZAR", key=f"fin{i}", type="primary"):
                    if tec:
                        items_str = ", ".join([x[0] for x in st.session_state.items_factura])
                        pdf = generar_pdf(t, tec, st.session_state.precio_total, nota, st.session_state.items_factura)
                        mover_historial(sheet_db, sheet_hist, t, tec, st.session_state.precio_total, nota, items_str)
                        st.session_state.items_factura=[]; st.session_state.precio_total=0
                        st.success("Cerrado"); st.download_button("📥 PDF", pdf, f"Factura_{t['cliente']}.pdf")
                        st.rerun() # Recarga para quitar el ticket de la lista

# === CEO ===
elif menu == "💰 CEO":
    st.header("📊 Finanzas")
    if sheet_hist:
        df = pd.DataFrame(cargar_datos_gsheet(sheet_hist))
        if not df.empty:
            st.dataframe(df)
            st.metric("Tickets", len(df))
        else: st.warning("Sin datos.")
