import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Équité Éducative Togo", page_icon="📊", layout="wide")

st.title("📊 Plateforme d'Analyse de l'Équité Pédagogique")
st.markdown("### Valorisation des Performances — Togo")

st.divider()

st.subheader("État du système")
try:
    response = requests.get(f"{API_URL}/health", timeout=5)
    if response.status_code == 200 and response.json().get("status") == "healthy":
        st.success("✅ API et base de données connectées")
    else:
        st.warning("⚠️ Problème détecté avec l'API")
except requests.exceptions.RequestException as e:
    st.error(f"❌ Impossible de contacter l'API : {e}")

st.divider()

st.subheader("Résumé des données")

try:
    stats = requests.get(f"{API_URL}/stats", timeout=10).json()

    if "error" in stats:
        st.warning(f"Impossible de charger les statistiques : {stats['error']}")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🏫 Écoles", f"{stats['ecoles']:,}".replace(",", " "))
        col2.metric("🏢 Bâtiments", f"{stats['batiments']:,}".replace(",", " "))
        col3.metric("🚻 Sanitaires", f"{stats['sanitaires']:,}".replace(",", " "))
        col4.metric("⚽ Terrains sportifs", f"{stats['terrains_sportifs']:,}".replace(",", " "))

        col5, col6 = st.columns(2)
        col5.metric("🗺️ Régions couvertes", stats['regions'])
        col6.metric("🤖 Modèles entraînés", stats['modeles_entraines'])

except requests.exceptions.RequestException as e:
    st.warning(f"Données indisponibles pour le moment : {e}")

st.divider()

st.markdown("""
### Navigation

Utilisez le menu à gauche pour explorer :

- **🗺️ Carte des écoles** — visualisation géographique et clusters
- **⚖️ Indice d'équité** — comparaison des régions togolaises
- **🤖 Métriques des modèles** — performance des modèles Big Data

---

**Sources de données :** Recensement scolaire national, Banque mondiale, rapport DPSSE 2024-2025
""")