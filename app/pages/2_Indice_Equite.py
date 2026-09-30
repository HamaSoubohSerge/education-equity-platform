import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Indice d'équité", page_icon="⚖️", layout="wide")

st.title("⚖️ Indice d'équité régional")
st.markdown("Comparaison des 5 régions administratives du Togo selon l'infrastructure scolaire et les résultats.")

st.caption("""
ℹ️ L'indice combine deux dimensions : le score d'infrastructure (ratio bâtiments/sanitaires/bibliothèques/terrains
par école) et le score de réussite (inverse des taux de redoublement primaire et secondaire). Les scores sont
normalisés entre les 5 régions — un score de 0 signifie « la moins bonne des 5 régions sur ce critère », pas une
absence totale de réussite.
""")

try:
    response = requests.get(f"{API_URL}/indice-equite", timeout=15)
    data = response.json().get("data", [])
    df = pd.DataFrame(data)
except requests.exceptions.RequestException as e:
    st.error(f"Erreur de connexion à l'API : {e}")
    df = pd.DataFrame()

if df.empty:
    st.warning("Aucune donnée d'indice d'équité disponible.")
else:
    df = df.sort_values("indice_equite", ascending=False).reset_index(drop=True)
    df.insert(0, "rang", df.index + 1)

    st.divider()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Classement des régions")
        display_df = df[["rang", "region", "indice_equite", "score_infra", "score_reussite"]].copy()
        display_df.columns = ["Rang", "Région", "Indice d'équité", "Score infra.", "Score réussite"]
        display_df["Score infra."] = (display_df["Score infra."] * 100).round(1)
        display_df["Score réussite"] = (display_df["Score réussite"] * 100).round(1)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Indice d'équité par région")
        fig_bar = px.bar(
            df,
            x="region",
            y="indice_equite",
            color="indice_equite",
            color_continuous_scale="RdYlGn",
            labels={"region": "Région", "indice_equite": "Indice d'équité (0-100)"},
            text="indice_equite"
        )
        fig_bar.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_bar.update_layout(showlegend=False, coloraxis_showscale=False, height=400)
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    st.subheader("Profil détaillé par région")
    st.caption("Chaque axe est normalisé entre 0 et 1 pour permettre la comparaison sur le même graphique.")

    radar_cols = ["score_infra", "score_reussite", "ratio_batiments", "ratio_sanitaires", "ratio_bibliotheques", "ratio_terrains"]
    radar_labels = ["Infrastructure", "Réussite", "Bâtiments", "Sanitaires", "Bibliothèques", "Terrains sportifs"]

    radar_df = df[radar_cols].copy()
    for col in ["ratio_batiments", "ratio_sanitaires", "ratio_bibliotheques", "ratio_terrains"]:
        col_max = radar_df[col].max()
        radar_df[col] = radar_df[col] / col_max if col_max > 0 else 0

    fig_radar = go.Figure()
    for i, row in df.iterrows():
        values = radar_df.loc[i].tolist()
        values += [values[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=values,
            theta=radar_labels + [radar_labels[0]],
            fill="toself",
            name=row["region"]
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        height=550
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    st.divider()
    st.subheader("Données brutes")
    st.dataframe(df, use_container_width=True, hide_index=True)