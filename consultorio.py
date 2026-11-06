import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Configuración de la página
st.set_page_config(page_title="Agenda del Consultorio", page_icon=":D", layout="wide")

ARCHIVO_DATOS = "citas.csv"
# Cambiamos el alcance (scope) para Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']


def obtener_servicio_calendar():
    creds = None
    
    if "google_creds" in st.secrets:
        pass
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


def crear_evento_google_calendar(nombre, telefono, fecha, hora, motivo):
    try:
        service = obtener_servicio_calendar()
        
        
        inicio_dt = datetime.combine(fecha, hora)
        fin_dt = inicio_dt + timedelta(minutes=120)
        
        evento = {
            'summary': f"Cita: {nombre} ({telefono})",
            'description': f"Motivo: {motivo}",
            'start': {
                'dateTime': inicio_dt.isoformat(),
                'timeZone': 'America/Guayaquil',  
            },
            'end': {
                'dateTime': fin_dt.isoformat(),
                'timeZone': 'America/Guayaquil',
            },
        }
        
        service.events().insert(calendarId='primary', body=evento).execute()
        return True
    except Exception as e:
        print(f"Error al crear evento en el calendario: {e}")
        return False


def cargar_citas():
    if os.path.exists(ARCHIVO_DATOS):
        df = pd.read_csv(ARCHIVO_DATOS)
        if not df.empty:
            df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
            df["hora_inicio"] = pd.to_datetime(df["hora_inicio"], format="%H:%M:%S", errors="coerce").dt.time
            return df.to_dict("records")
    return []


def guardar_citas():
    if st.session_state.citas:
        df = pd.DataFrame(st.session_state.citas)
        df.to_csv(ARCHIVO_DATOS, index=False)
    else:
        if os.path.exists(ARCHIVO_DATOS):
            os.remove(ARCHIVO_DATOS)


if "citas" not in st.session_state:
    st.session_state.citas = cargar_citas()

# Título
st.title("Agenda")
st.markdown("Agenda de citas")


st.sidebar.header("Agendar Nueva Cita")

nombre = st.sidebar.text_input("Nombre del Paciente")
telefono = st.sidebar.text_input("Teléfono / Celular")
fecha = st.sidebar.date_input("Fecha de la cita", min_value=datetime.today())
hora_inicio = st.sidebar.time_input("Hora de Inicio", value=time(9, 0))

motivo = st.sidebar.text_area("Motivo de la consulta")
estado = st.sidebar.selectbox("Estado", ["Confirmada", "Pendiente", "Atendida", "Cancelada"])


def hay_solapamiento(nueva_fecha, nueva_hora_ini):
    for cita in st.session_state.citas:
        c_fecha = cita["fecha"] if isinstance(cita["fecha"], type(fecha)) else datetime.strptime(str(cita["fecha"]), "%Y-%m-%d").date()
        
        if isinstance(cita["hora_inicio"], time):
            c_hora = cita["hora_inicio"]
        else:
            c_hora = datetime.strptime(str(cita["hora_inicio"]), "%H:%M:%S").time()
        
        if c_fecha == nueva_fecha and c_hora == nueva_hora_ini and cita["estado"] != "Cancelada":
            return True, cita["nombre"]
    return False, ""

# Botón Guardar
if st.sidebar.button("Guardar Cita", use_container_width=True):
    if not nombre.strip():
        st.sidebar.error("El nombre del paciente es obligatorio.")
    else:
        se_cruza, paciente_conflictivo = hay_solapamiento(fecha, hora_inicio)
        if se_cruza:
            st.sidebar.error(f"Ya tienes una cita programada a esa misma hora con **{paciente_conflictivo}**.")
        else:
            nuevo_id = int(datetime.now().timestamp())
            st.session_state.citas.append({
                "id": nuevo_id,
                "nombre": nombre,
                "telefono": telefono,
                "fecha": fecha,
                "hora_inicio": hora_inicio,
                "motivo": motivo,
                "estado": estado
            })
            guardar_citas()
            
            # Crear el evento en Google Calendar
            exito_calendar = crear_evento_google_calendar(nombre, telefono, fecha, hora_inicio, motivo)
            if exito_calendar:
                st.sidebar.success(f"Cita agendada y sincronizada con Google Calendar")
            else:
                st.sidebar.success(f"Cita agendada para {nombre} (Aviso: Google Calendar requiere credenciales configuradas).")
            
            st.rerun()

# Panel Principal - Filtros y Visualización
st.subheader("Citas Registradas")

if not st.session_state.citas:
    st.info("No hay citas registradas aún. Agrega una desde el panel izquierdo.")
else:
    df = pd.DataFrame(st.session_state.citas)
    
    df["fecha_obj"] = pd.to_datetime(df["fecha"]).dt.date
    dias_espanol = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    df["Día"] = df["fecha_obj"].apply(lambda d: dias_espanol[d.weekday()])
    
    def formatear_hora(h):
        if isinstance(h, time):
            return h.strftime("%H:%M")
        return str(h)[:5]

    df["Hora"] = df["hora_inicio"].apply(formatear_hora)
    
    col_f1, col_f2 = st.columns(2)
    filtro_dia = col_f1.selectbox("Filtrar por Día", ["Todos"] + list(dias_espanol.values()))
    filtro_estado = col_f2.selectbox("Filtrar por Estado", ["Todos", "Confirmada", "Pendiente", "Atendida", "Cancelada"])

    df_filtrado = df.copy()
    if filtro_dia != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Día"] == filtro_dia]
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["estado"] == filtro_estado]

    df_filtrado = df_filtrado.sort_values(by=["fecha", "hora_inicio"])

    col_tabla = ["Día", "fecha", "Hora", "nombre", "telefono", "motivo", "estado"]
    st.dataframe(
        df_filtrado[col_tabla].rename(columns={
            "fecha": "Fecha", 
            "nombre": "Paciente", 
            "telefono": "Teléfono", 
            "motivo": "Motivo", 
            "estado": "Estado"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.subheader("Eliminar una Cita")
    
    opciones_eliminar = {}
    for c in st.session_state.citas:
        h_str = c['hora_inicio'].strftime("%H:%M") if isinstance(c['hora_inicio'], time) else str(c['hora_inicio'])[:5]
        opciones_eliminar[f"{c['nombre']} - {c['fecha']} a las {h_str}"] = c['id']
    
    if opciones_eliminar:
        cita_seleccionada_txt = st.selectbox("Selecciona la cita que deseas eliminar:", list(opciones_eliminar.keys()))
        
        if st.button("Eliminar Cita Seleccionada", type="primary"):
            id_a_borrar = opciones_eliminar[cita_seleccionada_txt]
            st.session_state.citas = [c for c in st.session_state.citas if c['id'] != id_a_borrar]
            guardar_citas()
            st.success("¡Cita eliminada correctamente!")
            st.rerun()

    st.markdown("---")
    csv = df.drop(columns=["fecha_obj"], errors="ignore").to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descargar Agenda en Excel",
        data=csv,
        file_name='agenda_consultorio.csv',
        mime='text/csv',
    )
