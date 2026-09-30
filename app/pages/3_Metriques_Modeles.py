import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Métriques des modèles", page_icon="🤖", layout="wide")

st.title("🤖 Métriques des modèles Big Data")
st.markdown("Performance des modèles entraînés avec PySpark MLlib sur les données scolaires du Togo.")

st.divider()

try:
    response = requests.get(f"{API_URL}/model-metrics", timeout=15)
    data = response.json().get("data", [])
    df = pd.DataFrame(data)
except requests.exceptions.RequestException as e:
    st.error(f"Erreur de connexion à l'API : {e}")
    df = pd.DataFrame()

if df.empty:
    st.warning("Aucune métrique disponible.")
else:
    tab1, tab2 = st.tabs(["🗺️ Clustering géospatial", "🏫 Classification du statut"])

    with tab1:
        st.subheader("Clustering K-Means des écoles (latitude/longitude)")
        st.caption("Regroupement non supervisé des 15 445 écoles en zones géographiques cohérentes.")

        cluster_df = df[df["model"] == "clustering_ecoles"].copy()

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("**Recherche du meilleur nombre de clusters (k)**")
            k_scores = cluster_df[cluster_df["param"].str.startswith("k=")].copy()
            k_scores["k"] = k_scores["param"].str.replace("k=", "").astype(int)
            k_scores = k_scores.sort_values("k")

            fig_k = px.line(
                k_scores, x="k", y="value", markers=True,
                labels={"k": "Nombre de clusters (k)", "value": "Score de silhouette"}
            )
            fig_k.update_traces(line_color="#2E86AB", marker=dict(size=10))
            fig_k.update_layout(height=350)
            st.plotly_chart(fig_k, use_container_width=True)

        with col2:
            st.markdown("**Résultat retenu**")
            best = cluster_df[cluster_df["metric"] == "silhouette_best"]
            if not best.empty:
                best_k = best.iloc[0]["param"].replace("k_choisi=", "")
                best_score = best.iloc[0]["value"]
                st.metric("Nombre de clusters choisi", best_k)
                st.metric("Score de silhouette", f"{best_score:.4f}")
                st.info("""
                **Interprétation** : un score > 0.7 indique une structure de clusters forte
                (regroupements nets et bien séparés).
                """)

        st.markdown("**Détail des scores testés**")
        display_k = k_scores[["k", "value"]].copy()
        display_k.columns = ["k", "Score de silhouette"]
        st.dataframe(display_k, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Classification du statut d'établissement (Random Forest)")
        st.caption("Prédiction du statut (Public, Privé Laïc, Privé Catholique, etc.) à partir de la localisation, région et milieu.")

        class_df = df[df["model"] == "classification_statut"].copy()

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("**Métriques de performance (jeu de test)**")
            perf_metrics = class_df[class_df["param"] == "test_set"].copy()
            metric_labels = {
                "accuracy": "Accuracy (précision globale)",
                "f1": "Score F1",
                "precision_ponderee": "Précision pondérée",
                "rappel_pondere": "Rappel pondéré",
            }
            perf_metrics["Métrique"] = perf_metrics["metric"].map(metric_labels)

            for _, row in perf_metrics.iterrows():
                st.metric(row["Métrique"], f"{row['value']*100:.1f}%")

        with col2:
            st.markdown("**Volume de données**")
            info_metrics = class_df[class_df["param"] == "info"]
            nb_train = info_metrics[info_metrics["metric"] == "nb_train"]["value"].values
            nb_test = info_metrics[info_metrics["metric"] == "nb_test"]["value"].values

            if len(nb_train) and len(nb_test):
                st.metric("Écoles - entraînement", f"{int(nb_train[0]):,}".replace(",", " "))
                st.metric("Écoles - test", f"{int(nb_test[0]):,}".replace(",", " "))

            st.info("""
            **Référence** : la classe majoritaire ("Public") représente environ 62,5% des écoles.
            Un modèle qui prédirait toujours "Public" atteindrait déjà ~62,5% d'accuracy — le modèle
            entraîné (78,4%) apporte donc une vraie valeur prédictive.
            """)

        st.markdown("**Graphique comparatif des métriques**")
        fig_metrics = px.bar(
            perf_metrics, x="Métrique", y="value",
            labels={"value": "Score"}, color="Métrique",
            text="value"
        )
        fig_metrics.update_traces(texttemplate="%{text:.2%}", textposition="outside")
        fig_metrics.update_layout(showlegend=False, height=400, yaxis_tickformat=".0%")
        st.plotly_chart(fig_metrics, use_container_width=True)

    st.divider()
    st.subheader("Toutes les métriques (données brutes)")
    st.dataframe(df, use_container_width=True, hide_index=True)