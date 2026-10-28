import streamlit as st
import pandas as pd
from datetime import datetime, time

# Configuración de la página
st.set_page_config(page_title="Agenda del Consultorio", page_icon=":D", layout="wide")


if "citas" not in st.session_state:
    st.session_state.citas = []

# Título
st.title("Agenda")
st.markdown("horario para consultas")


st.sidebar.header("Agendar Nueva Cita")

nombre = st.sidebar.text_input("Nombre del Paciente")
telefono = st.sidebar.text_input("Teléfono / Celular")
fecha = st.sidebar.date_input("Fecha de la cita", min_value=datetime.today())
hora_inicio = st.sidebar.time_input("Hora de Inicio", value=time(9, 0))

motivo = st.sidebar.text_area("Motivo de la consulta")
estado = st.sidebar.selectbox("Estado", ["Confirmada", "Pendiente", "Atendida", "Cancelada"])


def hay_solapamiento(nueva_fecha, nueva_hora_ini):
    for cita in st.session_state.citas:
        if cita["fecha"] == nueva_fecha and cita["hora_inicio"] == nueva_hora_ini and cita["estado"] != "Cancelada":
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
            st.sidebar.success(f"Cita agendada para {nombre}.")

# Panel Principal 
st.subheader("Citas Registradas")

if not st.session_state.citas:
    st.info("No hay citas registradas aún. Agrega una desde el panel izquierdo.")
else:
    
    df = pd.DataFrame(st.session_state.citas)
    
    
    dias_espanol = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    df["Día"] = df["fecha"].apply(lambda d: dias_espanol[d.weekday()])
    df["Hora"] = df["hora_inicio"].apply(lambda h: h.strftime("%H:%M"))
    
    # Filtros
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
    st.subheader("Eliminar una Citas")
    
    opciones_eliminar = {
        f"{c['nombre']} - {c['fecha']} a las {c['hora_inicio'].strftime('%H:%M')}": c['id'] 
        for c in st.session_state.citas
    }
    
    if opciones_eliminar:
        cita_seleccionada_txt = st.selectbox("Selecciona la cita que deseas eliminar:", list(opciones_eliminar.keys()))
        
        if st.button("Eliminar Cita Seleccionada", type="primary"):
            id_a_borrar = opciones_eliminar[cita_seleccionada_txt]
            st.session_state.citas = [c for c in st.session_state.citas if c['id'] != id_a_borrar]
            st.success("¡Cita eliminada correctamente!")
            st.rerun()

    
    st.markdown("---")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descargar Agenda en Excel (CSV)",
        data=csv,
        file_name='agenda_consultorio.csv',
        mime='text/csv',
    )