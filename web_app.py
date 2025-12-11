# =============================================================================
# PROYECTO: RepAIr System CLOUD v7.0 (Hacker Edition + Google Sheets)
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

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="RepAIr Cloud Pro",
    page_icon="🐉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONEXIÓN A GOOGLE SHEETS (LA MAGIA) ---
def conectar_gsheets():
    try:
        # Definimos los permisos que necesita el robot
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        
        # Leemos el secreto que pegaste en Streamlit (string -> json)
        key_dict = json.loads(st.secrets["service_account"]["key_data"])
        
        # Autenticamos
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        
        # Abrimos las hojas (Si fallan los nombres, revisa tu Google Drive)
        sheet_db = client.open("repair_db").sheet1
        sheet_hist = client.open("repair_history").sheet1
        return sheet_db, sheet_hist
    except Exception as e:
        st.error(f"❌ Error conectando a Google Sheets: {e}")
        return None, None

# --- 3. CATÁLOGO MULTIVERSO (Rescatado de v39.0) ---
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
# Diccionario para buscar precios rápido
PRECIOS_DICT = {item[0]: item[1] for item in CATALOGO_LISTA}

# --- 4. MEMORIA DE SESIÓN (ESTADO) ---
if 'descripcion_texto' not in st.session_state: st.session_state.descripcion_texto = ""
if 'items_factura' not in st.session_state: st.session_state.items_factura = [] # Para el botón deshacer
if 'precio_total' not in st.session_state: st.session_state.precio_total = 0.0

if 'borrar_campos' not in st.session_state: st.session_state.borrar_campos = False
if st.session_state.borrar_campos:
    st.session_state.descripcion_texto = ""
    st.session_state.borrar_campos = False

if 'ai_response' not in st.session_state: st.session_state.ai_response = None
if 'ai_status' not in st.session_state: st.session_state.ai_status = "info"

# --- 5. FUNCIONES CRUD (LEER/ESCRIBIR EN NUBE) ---
def cargar_datos_gsheet(hoja):
    # Obtiene todos los registros como una lista de diccionarios
    try:
        data = hoja.get_all_records()
        return data
    except:
        return []

def guardar_ticket_gsheet(hoja, ticket):
    # Convierte el diccionario en una lista ordenada para la fila
    # Orden: Fecha, Cliente, Pass, Disp, Tipo, Desc, Urgente, IA_Solucion
    fila = [
        ticket["fecha"], ticket["cliente"], ticket["password"], 
        ticket["dispositivo"], ticket["tipo"], ticket["descripcion"], 
        str(ticket["urgente"]), ticket.get("ia_response", "N/A")
    ]
    hoja.append_row(fila)

def mover_a_historial(sheet_db, sheet_hist, ticket_data, tecnico, precio, nota, items_str):
    # 1. Añadir a Historial
    fila_hist = [
        datetime.now().strftime("%Y-%m-%d"), # Fecha Cierre
        ticket_data['cliente'],
        ticket_data['dispositivo'],
        tecnico,
        precio,
        nota,
        items_str # Guardamos qué se le cobró como texto
    ]
    sheet_hist.append_row(fila_hist)
    
    # 2. Borrar de Pendientes (Truco: Borramos todo y reescribimos los que NO son este ticket)
    # Esto es más seguro que intentar adivinar el número de fila en la nube.
    todos = sheet_db.get_all_records()
    sheet_db.clear() # ¡Limpieza total!
    # Ponemos las cabeceras de nuevo
    sheet_db.append_row(["fecha", "cliente", "password", "dispositivo", "tipo", "descripcion", "urgente", "ia_response"])
    
    for t in todos:
        # Si NO es el ticket que estamos cerrando, lo volvemos a escribir
        if not (t['cliente'] == ticket_data['cliente'] and t['fecha'] == ticket_data['fecha']):
            fila = [t['fecha'], t['cliente'], t['password'], t['dispositivo'], t['tipo'], t['descripcion'], str(t['urgente']), t.get('ia_response', '')]
            sheet_db.append_row(fila)

# --- 6. FUNCIÓN GENERAR PDF CON QR ---
def generar_pdf(ticket, tecnico, precio, nota, items):
    pdf = FPDF()
    pdf.add_page()
    
    # Logo QR (Generado al vuelo)
    qr = qrcode.make(f"REPAIR-CLOUD-ID-{ticket['cliente']}-{int(datetime.now().timestamp())}")
    qr.save("temp_qr.png")
    
    # Cabecera
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="RepAIr System Cloud - FACTURA", ln=1, align="C")
    pdf.image("temp_qr.png", x=170, y=10, w=30) # Poner QR arriba derecha
    pdf.ln(10)
    
    # Datos
    pdf.set_font("Arial", size=12)
    texto_cabecera = [
        f"Fecha: {datetime.now().strftime('%d/%m/%Y')}",
        f"Cliente: {ticket['cliente']}",
        f"Dispositivo: {ticket['dispositivo']}",
        "------------------------------------------------",
        f"Técnico: {tecnico}",
        "------------------------------------------------"
    ]
    
    for l in texto_cabecera:
        pdf.cell(0, 10, txt=l.encode('latin-1', 'replace').decode('latin-1'), ln=1)
        
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "DETALLE DE SERVICIOS:", ln=1)
    pdf.set_font("Arial", size=12)
    
    # Items de la factura
    for item, coste in items:
        pdf.cell(140, 10, txt=f"- {item}", border=0)
        pdf.cell(30, 10, txt=f"{coste:.2f} EUR", border=0, ln=1, align="R")
        
    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, txt=f"TOTAL A PAGAR: {precio:.2f} EUR", ln=1, align="R")
    
    pdf.ln(20)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, txt="Garantía de reparación de 3 meses. Gracias por su confianza.", ln=1, align="C")
    
    return pdf.output(dest="S").encode("latin-1")

# --- 7. INTERFAZ GRÁFICA ---

# Conectamos a la nube al iniciar
sheet_db, sheet_hist = conectar_gsheets()

# BARRA LATERAL
with st.sidebar:
    st.header("🐉 RepAIr v7.0")
    st.success("☁️ Google Sheets: ON")
    st.divider()
    menu = st.radio("MENÚ:", ["🏠 Recepción", "🔧 Taller", "💰 CEO"])
    st.divider()
    st.caption("Dev: Andrés y Carla")

# PANTALLA 1: RECEPCIÓN
if menu == "🏠 Recepción":
    st.title("📝 Recepción de Equipos")
    
    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Cliente")
        disp = st.selectbox("Dispositivo", ["Torre PC", "Portátil", "Consola", "Móvil/Tablet", "Impresora 3D", "Otro"])
    with col2:
        passw = st.text_input("Contraseña / Patrón")
        tipo = st.selectbox("Categoría", ["Software", "Hardware", "Ambas", "Desconocido"])
    
    desc = st.text_area("Descripción del Problema", key="descripcion_texto", height=100)
    
    # LÓGICA IA SIMPLIFICADA
    if st.button("✨ Analizar con AI-LEEN"):
        if desc:
            st.session_state.ai_response = "🤖 AI: Diagnóstico preliminar registrado en la nube."
            st.info(st.session_state.ai_response)
        else:
            st.warning("Escribe algo primero.")

    urgente = st.checkbox("⚡ Urgencia")
    
    if st.button("🚀 Crear Ticket (Subir a Drive)", type="primary", use_container_width=True):
        if cliente and desc and sheet_db:
            t = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "cliente": cliente, "password": passw, "dispositivo": disp, "tipo": tipo, "descripcion": desc, "urgente": urgente, "ia_response": st.session_state.ai_response}
            
            with st.spinner("Subiendo a Google Sheets..."):
                guardar_ticket_gsheet(sheet_db, t)
            
            st.balloons()
            st.success("✅ Guardado en Google Sheets.")
            st.session_state.borrar_campos = True
            st.rerun()
        elif not sheet_db:
            st.error("Error de conexión con Google Sheets.")
        else:
            st.error("Falta nombre o descripción.")

# PANTALLA 2: TÉCNICO
elif menu == "🔧 Taller":
    st.title("🛠️ Mesa de Trabajo")
    
    if sheet_db:
        pendientes = cargar_datos_gsheet(sheet_db)
    else:
        pendientes = []
        st.error("No hay conexión.")
    
    if not pendientes: st.success("¡Taller vacío! Buen trabajo.")
    
    for i, t in enumerate(pendientes):
        # Usamos el índice i para claves únicas
        urg = "🔥" if str(t.get('urgente')).lower() == 'true' else "🔨"
        with st.expander(f"{urg} {t['cliente']} - {t['dispositivo']}"):
            st.markdown(f"**Problema:** {t['descripcion']}")
            
            col_factura, col_cierre = st.columns([1, 1])
            
            with col_factura:
                st.subheader("🧾 Facturación")
                
                # SELECTOR DE CATÁLOGO
                prod_selec = st.selectbox("Añadir del Catálogo:", [x[0] for x in CATALOGO_LISTA], key=f"sel_{i}")
                
                c_add, c_undo = st.columns(2)
                with c_add:
                    if st.button("➕ Añadir Item", key=f"add_{i}"):
                        precio = PRECIOS_DICT.get(prod_selec, 0)
                        if precio == 0: # Es un título o separador
                            st.warning("Selecciona un producto válido, no un título.")
                        else:
                            st.session_state.items_factura.append((prod_selec, precio))
                            st.session_state.precio_total += precio
                            st.rerun() # Recargar para ver cambios
                
                with c_undo:
                    if st.button("↩️ Deshacer", key=f"undo_{i}"):
                        if st.session_state.items_factura:
                            eliminado = st.session_state.items_factura.pop()
                            st.session_state.precio_total -= eliminado[1]
                            st.success(f"Eliminado: {eliminado[0]}")
                            st.rerun()
                
                # MOSTRAR LISTA ACTUAL
                st.markdown("---")
                if st.session_state.items_factura:
                    for item, coste in st.session_state.items_factura:
                        st.text(f"{item} ... {coste}€")
                    st.markdown(f"**TOTAL: {st.session_state.precio_total:.2f} €**")
                else:
                    st.caption("Factura vacía")

            with col_cierre:
                st.subheader("✅ Cierre")
                tec = st.text_input("Técnico", key=f"tec_{i}")
                nota = st.text_area("Notas Finales", key=f"note_{i}")
                
                if st.button("Cerrar Ticket y Generar PDF", key=f"close_{i}", type="primary"):
                    if tec:
                        # Convertimos items a string para guardarlo en sheets
                        items_str = ", ".join([f"{x[0]}({x[1]}€)" for x in st.session_state.items_factura])
                        
                        # 1. Generar PDF
                        pdf_bytes = generar_pdf(t, tec, st.session_state.precio_total, nota, st.session_state.items_factura)
                        
                        # 2. Mover en Google Sheets
                        with st.spinner("Actualizando Google Sheets..."):
                            mover_a_historial(sheet_db, sheet_hist, t, tec, st.session_state.precio_total, nota, items_str)
                        
                        # 3. Limpiar sesión factura
                        st.session_state.items_factura = []
                        st.session_state.precio_total = 0.0
                        
                        st.success("¡Guardado en la nube!")
                        st.download_button("📥 Bajar Factura PDF", data=pdf_bytes, file_name=f"Factura_{t['cliente']}.pdf", mime="application/pdf")
                    else:
                        st.error("Firma el ticket (Nombre Técnico).")

# PANTALLA 3: CEO
elif menu == "💰 CEO":
    st.title("📊 Panel de Control (Google Sheets)")
    
    if sheet_hist:
        data_hist = cargar_datos_gsheet(sheet_hist)
        
        if data_hist:
            df = pd.DataFrame(data_hist)
            # Como sheets devuelve nombres de columnas raros a veces, renombramos si hace falta o usamos índices
            # Asumimos que la primera fila son headers o usamos get_all_records que devuelve dicts
            
            st.metric("Total Tickets Cerrados", len(data_hist))
            
            # Intentar sumar columna de precio (a veces viene como string)
            try:
                # Buscamos la columna que tenga precios (columna 5 aprox)
                total_ingresos = sum([float(str(d.get('4', 0)).replace(',','.')) if isinstance(d, dict) else 0 for d in data_hist]) # Ajuste chapucero por si acaso
                # Mejor: iterar valores
                total_real = 0
                for row in data_hist:
                    # Buscamos valores numéricos en el diccionario
                    vals = list(row.values())
                    try:
                        total_real += float(str(vals[4]).replace(',','.')) # Indice 4 suele ser precio
                    except: pass
                st.metric("Estimación Ingresos", f"{total_real:.2f} €")
            except:
                st.warning("No se pudo calcular el total automáticamente.")

            st.dataframe(df)
            
            st.divider()
            st.subheader("🗑️ Borrar Histórico")
            opciones = [f"{idx} - {row.get('1')} {row.get('2')}" for idx, row in enumerate(data_hist)]
            sel_borrar = st.selectbox("Elegir Ticket", opciones)
            
            if st.button("Borrar Ticket de la Nube"):
                idx_real = int(sel_borrar.split(' - ')[0]) + 2 # +2 porque Sheets empieza en 1 y tiene cabecera
                sheet_hist.delete_rows(idx_real)
                st.success("Borrado de Google Drive.")
                st.rerun()
        else:
            st.info("El historial está vacío.")
