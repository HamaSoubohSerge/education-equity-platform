import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Carte des écoles", page_icon="🗺️", layout="wide")

st.title("🗺️ Carte des écoles du Togo")
st.markdown("Visualisation géographique des établissements scolaires, avec clustering automatique.")

st.divider()

tab1, tab2 = st.tabs(["Carte par région/milieu", "Carte des clusters géographiques"])

with tab1:
    st.subheader("Répartition des écoles")

    col1, col2 = st.columns([1, 3])
    with col1:
        region_filter = st.selectbox(
            "Filtrer par région",
            options=["Toutes", "DRE MARITIME", "DRE GRAND LOME", "DRE PLATEAUX EST",
                     "DRE PLATEAUX OUEST", "DRE CENTRALE", "DRE KARA", "DRE SAVANES"]
        )
        limit = st.slider("Nombre d'écoles à afficher", 100, 5000, 1000, step=100)

    try:
        params = {"limit": limit}
        if region_filter != "Toutes":
            params["region"] = region_filter

        response = requests.get(f"{API_URL}/ecoles", params=params, timeout=30)

        if response.status_code != 200:
            st.error(f"L'API a répondu avec le code {response.status_code}")
            st.code(response.text[:500])
        else:
            data = response.json().get("data", [])
            df = pd.DataFrame(data)

            if df.empty:
                st.warning("Aucune donnée à afficher pour ce filtre.")
            else:
                df = df.dropna(subset=["latitude", "longitude"])

                center_lat = df["latitude"].mean()
                center_lon = df["longitude"].mean()
                lat_range = df["latitude"].max() - df["latitude"].min()
                lon_range = df["longitude"].max() - df["longitude"].min()
                max_range = max(lat_range, lon_range)

                if max_range < 0.5:
                    zoom_level = 10
                elif max_range < 1:
                    zoom_level = 9
                elif max_range < 2:
                    zoom_level = 8
                else:
                    zoom_level = 7

                fig = px.scatter_mapbox(
                    df,
                    lat="latitude",
                    lon="longitude",
                    color="milieu" if "milieu" in df.columns else None,
                    hover_name="nom_etablissement",
                    hover_data=["region", "statut", "type_etablissement"],
                    zoom=zoom_level,
                    center={"lat": center_lat, "lon": center_lon},
                    height=600,
                    title=f"{len(df)} écoles affichées"
                )
                fig.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 40, "l": 0, "b": 0})
                st.plotly_chart(fig, use_container_width=True)

    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de connexion à l'API : {e}")

with tab2:
    st.subheader("Clusters géographiques (K-Means)")
    st.caption("4 zones identifiées automatiquement par apprentissage non supervisé (score de silhouette : 0.72)")

    try:
        response = requests.get(f"{API_URL}/ecoles/clusters", params={"limit": 3000}, timeout=15)
        data = response.json().get("data", [])
        df = pd.DataFrame(data)

        if df.empty:
            st.warning("Aucune donnée de clustering disponible.")
        else:
            df["cluster_geo"] = df["cluster_geo"].astype(str)

            center_lat = df["latitude"].mean()
            center_lon = df["longitude"].mean()
            lat_range = df["latitude"].max() - df["latitude"].min()
            lon_range = df["longitude"].max() - df["longitude"].min()
            max_range = max(lat_range, lon_range)

            if max_range < 0.5:
                zoom_level = 10
            elif max_range < 1:
                zoom_level = 9
            elif max_range < 2:
                zoom_level = 8
            else:
                zoom_level = 7

            fig = px.scatter_mapbox(
                df,
                lat="latitude",
                lon="longitude",
                color="cluster_geo",
                hover_name="nom_etablissement",
                hover_data=["region", "milieu"],
                zoom=zoom_level,
                center={"lat": center_lat, "lon": center_lon},
                height=600,
                title=f"{len(df)} écoles réparties en {df['cluster_geo'].nunique()} clusters"
            )
            fig.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 40, "l": 0, "b": 0})
            st.plotly_chart(fig, use_container_width=True)

    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de connexion à l'API : {e}")