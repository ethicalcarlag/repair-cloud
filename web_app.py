# =============================================================================
# PROYECTO: RepAIr System CLOUD v6.2 (PDF Invoice Included)
# AUTORAS: Carla y Aileen
# =============================================================================

import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
from fpdf import FPDF

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="RepAIr Cloud",
    page_icon="🐉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. TRUCO VISUAL (CSS) ---
st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 3rem;} 
        #MainMenu {visibility: hidden;} 
        footer {visibility: hidden;} 
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. MEMORIA (SESSION STATE) ---
if 'descripcion_texto' not in st.session_state:
    st.session_state.descripcion_texto = ""

# --- ARREGLO DE LIMPIEZA (LA BANDERA) ---
if 'borrar_campos' not in st.session_state:
    st.session_state.borrar_campos = False

if st.session_state.borrar_campos:
    st.session_state.descripcion_texto = ""
    st.session_state.borrar_campos = False
# ----------------------------------------

if 'ai_response' not in st.session_state:
    st.session_state.ai_response = None
if 'ai_status' not in st.session_state:
    st.session_state.ai_status = "info"

# --- 4. DATOS ---
ARCHIVO_DB = "repair_db.json"
ARCHIVO_HISTORIAL = "repair_history.json"

PROTOCOLOS = {
    "Torre PC": ["Inspección Visual", "Test Arranque", "Limpieza", "Voltajes", "RAM", "Disco", "GPU", "Drivers"],
    "Portátil": ["Bisagras", "Batería", "Ventilador", "Pasta Térmica", "Teclado", "Pantalla", "Actualizar BIOS"],
    "Consola": ["Encendido", "HDMI", "Lector", "Ventilación", "Mandos", "Firmware"],
    "Móvil/Tablet": ["Pantalla", "Táctil", "Batería", "Puerto Carga", "Cámaras", "Sensores"],
    "Impresora": ["Inyectores", "Alineación", "Rodillos", "Escáner", "WiFi", "Firmware"],
    "Impresora 3D": ["Nivelado", "Nozzle", "Extrusor", "Correas", "Ventiladores"],
    "Otro": ["General", "Seguridad"]
}

# --- 5. FUNCIONES DE CARGA Y GUARDADO ---
def cargar_datos(archivo):
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def guardar_ticket(ticket):
    datos = cargar_datos(ARCHIVO_DB)
    datos.append(ticket)
    with open(ARCHIVO_DB, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4)

def cerrar_ticket(t_orig, tec, prec, nota, proto):
    hist = cargar_datos(ARCHIVO_HISTORIAL)
    t_fin = t_orig.copy()
    t_fin['fecha_cierre'] = datetime.now().strftime("%Y-%m-%d")
    t_fin['tecnico'] = tec
    t_fin['precio_final'] = prec
    t_fin['notas_finales'] = nota
    t_fin['protocolo'] = proto
    hist.append(t_fin)
    with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=4)
    borrar_de_pendientes(t_orig)

def borrar_de_pendientes(t_borrar):
    pendientes = cargar_datos(ARCHIVO_DB)
    nuevos = [t for t in pendientes if not (t['fecha'] == t_borrar['fecha'] and t['cliente'] == t_borrar['cliente'])]
    with open(ARCHIVO_DB, "w", encoding="utf-8") as f:
        json.dump(nuevos, f, indent=4)

# --- FUNCIÓN GENERAR PDF (FACTURA) ---
def generar_pdf(ticket, tecnico, precio, nota):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Cabecera
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="RepAIr System Cloud - FACTURA", ln=1, align="C")
    pdf.ln(10)
    
    # Datos
    pdf.set_font("Arial", size=12)
    texto = [
        f"Fecha: {datetime.now().strftime('%d/%m/%Y')}",
        f"Cliente: {ticket['cliente']}",
        f"Dispositivo: {ticket['dispositivo']}",
        f"Problema: {ticket['descripcion']}",
        "------------------------------------------------",
        f"Técnico: {tecnico}",
        f"Notas: {nota}",
        "------------------------------------------------",
        f"TOTAL A PAGAR: {precio} EUR"
    ]
    
    for linea in texto:
        # Codificación para tildes y ñ
        pdf.cell(200, 10, txt=linea.encode('latin-1', 'replace').decode('latin-1'), ln=1)
        
    # Pie de página
    pdf.ln(20)
    pdf.cell(200, 10, txt="Gracias por confiar en nosotros.", ln=1, align="C")
    
    return pdf.output(dest="S").encode("latin-1")

# --- 6. INTERFAZ GRÁFICA ---

# BARRA LATERAL
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=200)
    else:
        st.header("🐉 RepAIr System")
    
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
        disp = st.selectbox("Dispositivo", list(PROTOCOLOS.keys()))
    with col2:
        passw = st.text_input("Contraseña / Patrón")
        tipo = st.selectbox("Categoría", ["Software", "Hardware", "Ambas", "Desconocido"])
    
    # BOTONES DE ACCIÓN
    c_panico, c_ai = st.columns([1, 4])
    
    with c_panico:
        if st.button("🚨 MODO PÁNICO"):
            st.session_state.descripcion_texto = "SOS ACTIVADO - Responde:\n1. ¿Luces? (Si/No)\n2. ¿Ruidos?\n3. ¿Pantalla?"
            st.rerun()
            
    desc = st.text_area("Descripción del Problema", key="descripcion_texto", height=100)

    with c_ai:
        if st.button("✨ Analizar con AI-LEEN"):
            if not desc:
                st.session_state.ai_response = "⚠️ Escribe algo primero."
                st.session_state.ai_status = "warning"
            else:
                txt = desc.lower()
                # LÓGICA IA
                if any(k in txt for k in ["agua", "mojado", "liquido", "coca-cola", "cafe"]):
                    st.session_state.ai_response = "🤖 AI: ⚠️ DAÑO POR LÍQUIDOS. ¡No encender!. Baño químico."; st.session_state.ai_status="error"
                elif any(k in txt for k in ["lento", "tarda", "fps", "juego"]):
                    st.session_state.ai_response = "🤖 AI: Rendimiento Bajo -> Posible fallo HDD/RAM. Recomiendo SSD."; st.session_state.ai_status="warning"
                elif any(k in txt for k in ["pantalla", "rota"]):
                    st.session_state.ai_response = "🤖 AI: Daño Físico -> Cambio LCD."; st.session_state.ai_status="error"
                elif any(k in txt for k in ["no enciende", "negra"]):
                    st.session_state.ai_response = "🤖 AI: Fallo Eléctrico -> Fuente/Placa."; st.session_state.ai_status="error"
                elif "impresora" in txt:
                    st.session_state.ai_response = "🤖 AI: Mecánica -> Revisar atascos."; st.session_state.ai_status="info"
                else:
                    st.session_state.ai_response = "🤖 AI: Diagnóstico general requerido."; st.session_state.ai_status="info"

    if st.session_state.ai_response:
        if st.session_state.ai_status == "error": st.error(st.session_state.ai_response)
        elif st.session_state.ai_status == "warning": st.warning(st.session_state.ai_response)
        else: st.info(st.session_state.ai_response)

    st.divider()
    urgente = st.checkbox("⚡ Urgencia (+5%)")
    
    if st.button("🚀 Crear Ticket", type="primary", use_container_width=True):
        if cliente and desc:
            t = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "cliente": cliente, "password": passw, "dispositivo": disp, "tipo": tipo, "descripcion": desc, "urgente": urgente}
            guardar_ticket(t)
            st.balloons()
            st.success("✅ Guardado en la nube.")
            
            # Limpieza segura
            st.session_state.borrar_campos = True
            
            st.session_state.ai_response = None
            st.rerun()
        else:
            st.error("Faltan datos.")

# --- PANTALLA 2: TÉCNICO  ---
elif menu == "🔧 Taller":
    st.title("🛠️ Mesa de Trabajo")
    pendientes = cargar_datos(ARCHIVO_DB)
    
    if not pendientes: st.success("¡Todo terminado!")
    
    for i, t in enumerate(pendientes):
        with st.expander(f"{'🔥' if t.get('urgente') else '🔨'} {t['cliente']} - {t['dispositivo']}"):
            st.markdown(f"**Problema:** {t['descripcion']}")
            
            c_check, c_fact = st.columns(2)
            with c_check:
                st.caption("Protocolo")
                lista_p = PROTOCOLOS.get(t.get('dispositivo'), PROTOCOLOS["Otro"])
                hecho = st.multiselect(f"Tareas ({t['cliente']})", lista_p, key=f"m_{i}")
            
            with c_fact:
                st.caption("Cierre")
                tec = st.text_input("Técnico", key=f"tec_{i}")
                money = st.number_input("Precio (€)", value=50.0, key=f"money_{i}")
                nota = st.text_area("Notas", key=f"note_{i}")
                
                c_del, c_ok = st.columns(2)
                with c_del:
                    if st.button("🗑️", key=f"del_{i}"):
                        borrar_de_pendientes(t); st.rerun()
                
                # --- BOTÓN DE CIERRE CON FACTURA ---
                with c_ok:
                    if st.button("✅ Cerrar y Factura", key=f"ok_{i}", type="primary"):
                        if tec:
                            # 1. Generar PDF en memoria
                            pdf_bytes = generar_pdf(t, tec, money, nota)
                            
                            # 2. Guardar en historial y borrar de pendientes
                            cerrar_ticket(t, tec, money, nota, hecho)
                            
                            # 3. Mostrar éxito y botón de descarga
                            st.success("¡Cerrado!")
                            st.download_button(
                                label="📄 Descargar Factura PDF",
                                data=pdf_bytes,
                                file_name=f"Factura_{t['cliente']}.pdf",
                                mime="application/pdf"
                            )
                            # NOTA: No usamos rerun() aquí para que dé tiempo a descargar
                        else: 
                            st.error("Falta Técnico")

# --- PANTALLA 3: CEO ---
elif menu == "💰 CEO":
    st.title("📊 Panel de Control")
    hist = cargar_datos(ARCHIVO_HISTORIAL)
    if hist:
        total = sum(h.get('precio_final', 0) for h in hist)
        st.metric("Total Facturado", f"{total:.2f} €")
        st.dataframe(pd.DataFrame(hist))
    else:
        st.info("No hay datos.")

