import streamlit as st
import pandas as pd

st.title("Filtrar CSV: Date y Ticker")

uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])

if uploaded_file is not None:
    # Leer CSV
    df = pd.read_csv(uploaded_file)

    # Mostrar columnas disponibles
    st.write("Columnas detectadas en el archivo:")
    st.write(list(df.columns))

    # Verificar que existan Date y Ticker
    required_cols = ["Date", "Ticker"]
    if all(col in df.columns for col in required_cols):
        filtered_df = df[required_cols]

        st.write("Vista previa del CSV filtrado:")
        st.dataframe(filtered_df)

        # Convertir a CSV para descarga
        csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Descargar CSV con Date y Ticker",
            data=csv_bytes,
            file_name="filtered_date_ticker.csv",
            mime="text/csv"
        )
    else:
        st.error("El CSV no contiene las columnas 'Date' y 'Ticker'.")