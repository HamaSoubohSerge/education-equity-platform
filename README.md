# Educational Equity Analysis Platform — Performance Valorization (Togo)

*[Version française plus bas ↓ / French version below ↓](#plateforme-danalyse-de-léquité-pédagogique--valorisation-des-performances-togo)*

Big Data platform developed as part of a graduation internship (Professional Bachelor's in Artificial Intelligence & Big Data, ESGIS) at **CNDP-TICE** (National Center for Pedagogical Documentation and Information & Communication Technologies for Education), under Togo's Ministry of Primary and Secondary Education.

The project implements an end-to-end pipeline — ingestion, cleaning, regional aggregation, machine learning modeling, and dashboarding — to compare Togo's five administrative regions on school infrastructure (buildings, sanitation, libraries, sports facilities) and academic outcomes (grade repetition rates).

## Architecture

The project is fully containerized with **Docker Compose**, built on 8 services:

| Service | Role |
|---|---|
| `mongodb` | NoSQL database centralizing cleaned data and computed results (13 collections) |
| `minio` | S3-compatible object storage for raw/processed files |
| `spark` | Distributed processing: regional aggregation + Spark MLlib model training |
| `airflow` | Pipeline orchestration via a DAG (`pipeline_education_togo`) |
| `ingestion` | Retrieves source data into MinIO |
| `processing` | Data cleaning (pandas) and equity index computation |
| `api` | FastAPI service exposing MongoDB data to the dashboard |
| `streamlit` | Interactive visualization dashboard (4 pages) |

Pipeline flow orchestrated by Airflow:

ingestion → [nettoyage_ecoles, nettoyage_batiments] → agregation_regionale
├── indice_equite
├── modele_clustering
└── modele_classification


## Machine Learning Models (Spark MLlib)

- **Geospatial clustering (K-Means)**: groups geolocated schools into 4 coherent zones (k chosen via silhouette score, best score obtained: 0.72).
- **Classification (Random Forest, 100 trees)**: predicts institution status (Public / Private secular / Private Catholic...) — 78.4% accuracy, 73.5% weighted F1-score.

## Setup & Run

### Requirements
- Docker and Docker Compose
- A `.env` file at the project root (see `.env.example`)

### Configuration

```bash
cp .env.example .env
```

Then fill in your own values (the defaults in `.env.example` work locally but should be changed before any shared deployment).

### Start

```bash
docker compose up -d --build
```

Available interfaces:
- Streamlit dashboard: http://localhost:8600
- FastAPI: http://localhost:8000
- Airflow UI: http://localhost:8081
- MinIO console: http://localhost:9001
- Spark UI: http://localhost:8085

The `pipeline_education_togo` DAG can be triggered manually from the Airflow UI (also scheduled `@weekly`).

## Project Structure

├── airflow/dags/ # Airflow DAG (pipeline orchestration)
├── ingestion/ # Source data retrieval
├── processing/ # Cleaning (pandas) + equity index computation
├── spark/jobs/ # Regional aggregation + Spark MLlib models
├── api/ # FastAPI service
├── app/ # Streamlit dashboard
├── docker/ # Per-service Dockerfiles
├── data/ # Source data (not versioned, see below)
└── docker-compose.yml


## Data

Source data is **not included** in this repository (property of CNDP-TICE). To run the pipeline, place your own files in the expected format inside the `data/` folder.

## Known Limitations

- No multi-fold cross-validation on the models (single train/test split).
- Local development environment only (no production setup: authentication, high availability).
- The pipeline's update frequency (`@weekly`) is arbitrary and not tied to CNDP-TICE's actual data publication cadence.

## Author

Project developed as part of a graduation internship — Professional Bachelor's in Artificial Intelligence & Big Data, ESGIS.

---

# Plateforme d'Analyse de l'Équité Pédagogique — Valorisation des Performances (Togo)

Plateforme Big Data développée dans le cadre d'un stage de fin d'études (Licence Professionnelle Intelligence Artificielle et Big Data, ESGIS) au **CNDP-TICE** (Centre National de Documentation Pédagogique et des Technologies de l'Information et de la Communication pour l'Éducation), sous tutelle du Ministère des Enseignements Primaire et Secondaire du Togo.

Le projet met en place un pipeline complet — ingestion, nettoyage, agrégation régionale, modélisation par apprentissage automatique et restitution — permettant de comparer les cinq régions administratives du Togo selon leurs infrastructures scolaires (bâtiments, sanitaires, bibliothèques, terrains sportifs) et leurs indicateurs de réussite (taux de redoublement).

## Architecture

Le projet est entièrement conteneurisé avec **Docker Compose** et repose sur 8 services :

| Service | Rôle |
|---|---|
| `mongodb` | Base NoSQL centralisant les données nettoyées et les résultats (13 collections) |
| `minio` | Stockage objet compatible S3 pour les fichiers bruts/traités |
| `spark` | Traitement distribué : agrégation régionale + entraînement des modèles Spark MLlib |
| `airflow` | Orchestration du pipeline via un DAG (`pipeline_education_togo`) |
| `ingestion` | Récupération des données sources vers MinIO |
| `processing` | Nettoyage des données (pandas) et calcul de l'indice d'équité |
| `api` | API FastAPI exposant les données MongoDB au dashboard |
| `streamlit` | Dashboard interactif de visualisation (4 pages) |

Le pipeline est orchestré par Airflow selon l'enchaînement suivant :

ingestion → [nettoyage_ecoles, nettoyage_batiments] → agregation_regionale
├── indice_equite
├── modele_clustering
└── modele_classification


## Modèles de machine learning (Spark MLlib)

- **Clustering géospatial (K-Means)** : regroupement des écoles géolocalisées en 4 zones cohérentes (k choisi par score de silhouette, meilleur score obtenu : 0,72).
- **Classification (Random Forest, 100 arbres)** : prédiction du statut d'établissement (Public / Privé Laïc / Privé Catholique...) — accuracy de 78,4 %, F1-score pondéré de 73,5 %.

## Installation et lancement

### Prérequis
- Docker et Docker Compose
- Un fichier `.env` à la racine du projet (voir `.env.example`)

### Configuration

```bash
cp .env.example .env
```

Puis renseigne des valeurs (les valeurs par défaut de `.env.example` fonctionnent en local, mais sont à changer avant tout déploiement partagé).

### Démarrage

```bash
docker compose up -d --build
```

Les interfaces sont ensuite accessibles sur :
- Dashboard Streamlit : http://localhost:8600
- API FastAPI : http://localhost:8000
- Interface Airflow : http://localhost:8081
- Console MinIO : http://localhost:9001
- Interface Spark : http://localhost:8085

Le DAG `pipeline_education_togo` peut être déclenché manuellement depuis l'interface Airflow (il est aussi planifié en `@weekly`).

## Structure du projet

├── airflow/dags/ # DAG Airflow (orchestration du pipeline)
├── ingestion/ # Récupération des données sources
├── processing/ # Nettoyage (pandas) + calcul de l'indice d'équité
├── spark/jobs/ # Agrégation régionale + modèles Spark MLlib
├── api/ # API FastAPI
├── app/ # Dashboard Streamlit
├── docker/ # Dockerfiles par service
├── data/ # Données sources (non versionnées, voir ci-dessous)
└── docker-compose.yml


## Données

Les données sources ne sont **pas incluses** dans ce dépôt (propriété du CNDP-TICE). Pour faire fonctionner le pipeline, place tes propres fichiers au format attendu dans le dossier `data/`.

## Limites connues

- Pas de validation croisée multi-plis sur les modèles (un seul découpage entraînement/test).
- Environnement de développement local uniquement (pas de configuration production : authentification, haute disponibilité).
- Fréquence de mise à jour du pipeline (`@weekly`) arbitraire, non connectée au rythme réel de publication des données du CNDP-TICE.

## Auteur

Projet réalisé dans le cadre d'un stage de fin d'études — Licence Professionnelle Intelligence Artificielle et Big Data, ESGIS.