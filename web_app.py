# =============================================================================
# PROYECTO: RepAIr System CLOUD v7.1 (Dark Knight + Panic Button Fixed)
# AUTORAS: Carla y Aileen
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

# --- 1. CONFIGURACIÓN DE PÁGINA (ESTILO DARK FORZADO) ---
st.set_page_config(
    page_title="RepAIr Cloud Pro",
    page_icon="🐉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS HACKER / DARK MODE ---
st.markdown("""
    <style>
        /* Fondo general más oscuro */
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        /* Botones personalizados */
        div.stButton > button:first-child {
            background-color: #262730;
            color: #ffffff;
            border: 1px solid #4B4B4B;
        }
        div.stButton > button:hover {
            border-color: #00ADB5;
            color: #00ADB5;
        }
        /* Botón de Pánico (Rojo) */
        .panic-btn { border: 2px solid red !important; color: red !important; }
        
        /* Cajas de texto */
        .stTextInput > div > div > input {
            background-color: #262730;
            color: white;
        }
        /* Eliminar header blanco de Streamlit */
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. CONEXIÓN A GOOGLE SHEETS ---
def conectar_gsheets():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        # Leemos el secreto con cuidado de errores de formato
        key_content = st.secrets["service_account"]["key_data"]
        # Limpieza básica por si se colaron caracteres raros al copiar
        key_content = key_content.strip() 
        
        key_dict = json.loads(key_content)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        
        sheet_db = client.open("repair_db").sheet1
        sheet_hist = client.open("repair_history").sheet1
        return sheet_db, sheet_hist
    except Exception as e:
        # Mostramos el error solo si es necesario depurar
        # st.error(f"Error técnico: {e}") 
        return None, None

# --- 4. CATÁLOGO ---
CATALOGO_LISTA = [
    ("--- SERVICIOS ---", 0),
    ("Mano de Obra (Estándar)", 30.00),
    ("Mano de Obra (Avanzada)", 60.00),
    ("Diagnóstico Completo", 25.00),
    ("Limpieza Integral", 35.00),
    ("Recuperación Datos", 80.00),
    ("--- COMPONENTES ---", 0),
    ("SSD Kingston 480GB", 38.99),
    ("SSD Samsung 1TB NVMe", 85.00),
    ("RAM 8GB DDR4", 26.00),
    ("RAM 16GB DDR4", 45.00),
    ("RTX 3060 12GB", 295.00),
    ("RTX 4060 8GB", 330.00),
    ("Fuente 750W Gold", 110.00),
    ("--- IMPRESIÓN 3D ---", 0),
    ("Desatasco Nozzle", 40.00),
    ("Nivelado Cama", 35.00),
    ("Cambio Nozzle", 15.00),
    ("Bobina PLA", 22.00)
]
PRECIOS_DICT = {item[0]: item[1] for item in CATALOGO_LISTA}

# --- 5. MEMORIA DE SESIÓN ---
if 'descripcion_texto' not in st.session_state: st.session_state.descripcion_texto = ""
if 'items_factura' not in st.session_state: st.session_state.items_factura = []
if 'precio_total' not in st.session_state: st.session_state.precio_total = 0.0
if 'borrar_campos' not in st.session_state: st.session_state.borrar_campos = False
if 'ai_response' not in st.session_state: st.session_state.ai_response = None

# Lógica de borrado seguro
if st.session_state.borrar_campos:
    st.session_state.descripcion_texto = ""
    st.session_state.borrar_campos = False

# --- 6. FUNCIONES AUXILIARES ---
def cargar_datos_gsheet(hoja):
    try: return hoja.get_all_records()
    except: return []

def guardar_ticket_gsheet(hoja, ticket):
    fila = [ticket["fecha"], ticket["cliente"], ticket["password"], ticket["dispositivo"], ticket["tipo"], ticket["descripcion"], str(ticket["urgente"]), ticket.get("ia_response", "N/A")]
    hoja.append_row(fila)

def mover_a_historial(sheet_db, sheet_hist, ticket_data, tecnico, precio, nota, items_str):
    fila_hist = [datetime.now().strftime("%Y-%m-%d"), ticket_data['cliente'], ticket_data['dispositivo'], tecnico, precio, nota, items_str]
    sheet_hist.append_row(fila_hist)
    # Borrado seguro: Reescribimos todo menos el actual
    todos = sheet_db.get_all_records()
    sheet_db.clear()
    sheet_db.append_row(["fecha", "cliente", "password", "dispositivo", "tipo", "descripcion", "urgente", "ia_response"])
    for t in todos:
        if not (t['cliente'] == ticket_data['cliente'] and t['fecha'] == ticket_data['fecha']):
            fila = [t['fecha'], t['cliente'], t['password'], t['dispositivo'], t['tipo'], t['descripcion'], str(t['urgente']), t.get('ia_response', '')]
            sheet_db.append_row(fila)

def generar_pdf(ticket, tecnico, precio, nota, items):
    pdf = FPDF()
    pdf.add_page()
    qr = qrcode.make(f"REPAIR-CLOUD-{ticket['cliente']}")
    qr.save("temp_qr.png")
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="RepAIr System Cloud - FACTURA", ln=1, align="C")
    pdf.image("temp_qr.png", x=170, y=10, w=30)
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    texto = [f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", f"Cliente: {ticket['cliente']}", f"Dispositivo: {ticket['dispositivo']}", f"Técnico: {tecnico}"]
    for l in texto: pdf.cell(0, 10, txt=l.encode('latin-1','replace').decode('latin-1'), ln=1)
    pdf.ln(5); pdf.cell(0, 10, "DETALLE:", ln=1)
    for item, coste in items:
        pdf.cell(140, 10, txt=f"- {item}", border=0)
        pdf.cell(30, 10, txt=f"{coste:.2f} EUR", border=0, ln=1, align="R")
    pdf.ln(10); pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, txt=f"TOTAL: {precio:.2f} EUR", ln=1, align="R")
    return pdf.output(dest="S").encode("latin-1")

# --- 7. INTERFAZ ---
sheet_db, sheet_hist = conectar_gsheets()

with st.sidebar:
    st.title("🐉 RepAIr v7.1")
    if sheet_db: st.success("☁️ Nube Conectada")
    else: st.error("❌ Error de Conexión (Revisar Secrets)")
    menu = st.radio("MENÚ:", ["🏠 Recepción", "🔧 Taller", "💰 CEO"])
    st.divider(); st.caption("Dev: Andrés y Carla")

# --- PANTALLA RECEPCIÓN ---
if menu == "🏠 Recepción":
    st.markdown("## 📝 Recepción de Equipos")
    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Cliente")
        disp = st.selectbox("Dispositivo", ["Torre PC", "Portátil", "Consola", "Móvil/Tablet", "Impresora 3D", "Otro"])
    with col2:
        passw = st.text_input("Contraseña / Patrón")
        tipo = st.selectbox("Categoría", ["Software", "Hardware", "Ambas", "Desconocido"])
    
    # --- BOTÓN PÁNICO RECUPERADO ---
    c_panico, c_ai = st.columns([1, 4])
    with c_panico:
        if st.button("🚨 SOS", help="Modo Pánico"):
            st.session_state.descripcion_texto = "SOS ACTIVADO - Responde:\n1. ¿Luces? (Si/No)\n2. ¿Ruidos?\n3. ¿Pantalla?"
            st.rerun()
    
    desc = st.text_area("Descripción", key="descripcion_texto", height=100)

    with c_ai:
        if st.button("✨ Analizar con AI-LEEN"):
            if desc: st.info("🤖 AI: Diagnóstico preliminar registrado."); st.session_state.ai_response = "Diagnóstico AI OK"
            else: st.warning("Escribe algo primero.")

    urgente = st.checkbox("⚡ Urgencia")
    
    if st.button("🚀 Crear Ticket", type="primary", use_container_width=True):
        if cliente and desc and sheet_db:
            t = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "cliente": cliente, "password": passw, "dispositivo": disp, "tipo": tipo, "descripcion": desc, "urgente": urgente, "ia_response": st.session_state.ai_response}
            with st.spinner("Subiendo a la nube..."): guardar_ticket_gsheet(sheet_db, t)
            st.balloons(); st.success("✅ Guardado."); st.session_state.borrar_campos = True; st.rerun()
        elif not sheet_db: st.error("No hay conexión con la base de datos.")
        else: st.error("Faltan datos.")

# --- PANTALLA TALLER ---
elif menu == "🔧 Taller":
    st.markdown("## 🛠️ Mesa de Trabajo")
    pendientes = cargar_datos_gsheet(sheet_db) if sheet_db else []
    
    if not pendientes: st.info("👍 No hay equipos pendientes.")
    
    for i, t in enumerate(pendientes):
        urg = "🔥" if str(t.get('urgente')).lower() == 'true' else "🔨"
        with st.expander(f"{urg} {t['cliente']} - {t['dispositivo']}"):
            st.info(f"Problema: {t['descripcion']}")
            c_fact, c_close = st.columns(2)
            
            with c_fact:
                st.caption("FACTURACIÓN")
                prod = st.selectbox("Catálogo", [x[0] for x in CATALOGO_LISTA], key=f"s{i}")
                c1, c2 = st.columns(2)
                if c1.button("➕ Añadir", key=f"a{i}"):
                    p = PRECIOS_DICT.get(prod, 0)
                    if p > 0: st.session_state.items_factura.append((prod, p)); st.session_state.precio_total += p; st.rerun()
                if c2.button("↩️ Deshacer", key=f"u{i}"):
                    if st.session_state.items_factura: 
                        rem = st.session_state.items_factura.pop(); st.session_state.precio_total -= rem[1]; st.rerun()
                
                st.markdown("---")
                for it, cost in st.session_state.items_factura: st.text(f"{it}: {cost}€")
                st.markdown(f"**TOTAL: {st.session_state.precio_total:.2f} €**")

            with c_close:
                st.caption("CIERRE")
                tec = st.text_input("Técnico", key=f"t{i}")
                nota = st.text_area("Notas", key=f"n{i}")
                if st.button("✅ Cerrar y PDF", key=f"c{i}", type="primary"):
                    if tec and sheet_hist:
                        items_str = ", ".join([f"{x[0]}" for x in st.session_state.items_factura])
                        pdf = generar_pdf(t, tec, st.session_state.precio_total, nota, st.session_state.items_factura)
                        mover_a_historial(sheet_db, sheet_hist, t, tec, st.session_state.precio_total, nota, items_str)
                        st.session_state.items_factura = []; st.session_state.precio_total = 0.0
                        st.success("¡Cerrado!"); st.download_button("📥 PDF", data=pdf, file_name=f"Factura_{t['cliente']}.pdf", mime="application/pdf")

# --- PANTALLA CEO ---
elif menu == "💰 CEO":
    st.markdown("## 📊 Panel de Control")
    if sheet_hist:
        data = cargar_datos_gsheet(sheet_hist)
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df)
            opciones = [f"{idx+2} - {row.get('cliente','?')} ({row.get('precio','?')})" for idx, row in enumerate(data)]
            sel = st.selectbox("Borrar Ticket", opciones)
            if st.button("🗑️ Eliminar Definitivamente"):
                row_id = int(sel.split(' - ')[0])
                sheet_hist.delete_rows(row_id); st.success("Eliminado."); st.rerun()
        else: st.warning("Historial vacío.")
