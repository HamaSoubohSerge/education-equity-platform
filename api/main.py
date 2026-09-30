import os
import math
from fastapi import FastAPI
from pymongo import MongoClient

app = FastAPI(title="Education Data Platform API")

mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017/education_db")
client = MongoClient(mongo_uri)
db = client["education_db"]


def clean_nan(obj):
    """Remplace récursivement les NaN par None pour la compatibilité JSON."""
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    return obj


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Education Data Platform API is running"}


@app.get("/health")
def health_check():
    try:
        client.admin.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/stats")
def get_stats():
    """Statistiques globales du projet, pour la page d'accueil."""
    try:
        return {
            "ecoles": db["ecoles"].count_documents({}),
            "batiments": db["batiments"].count_documents({}),
            "sanitaires": db["sanitaires"].count_documents({}),
            "bibliotheques": db["bibliotheques"].count_documents({}),
            "terrains_sportifs": db["terrains_sportifs"].count_documents({}),
            "regions": db["aggregation_regionale"].count_documents({}),
            "modeles_entraines": len(db["model_metrics"].distinct("model")),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/ecoles")
def get_ecoles(region: str = None, limit: int = 500):
    query = {}
    if region:
        query["region"] = region
    docs = list(db["ecoles"].find(query, {"_id": 0}).limit(limit))
    return {"count": len(docs), "data": clean_nan(docs)}


@app.get("/ecoles/clusters")
def get_ecoles_clusters(limit: int = 2000):
    docs = list(db["ecoles_clusters"].find({}, {"_id": 0}).limit(limit))
    return {"count": len(docs), "data": clean_nan(docs)}


@app.get("/aggregation-regionale")
def get_aggregation_regionale():
    docs = list(db["aggregation_regionale"].find({}, {"_id": 0}))
    return {"count": len(docs), "data": clean_nan(docs)}


@app.get("/indice-equite")
def get_indice_equite():
    docs = list(db["indice_equite_regional"].find({}, {"_id": 0}))
    return {"count": len(docs), "data": clean_nan(docs)}


@app.get("/model-metrics")
def get_model_metrics(model: str = None):
    query = {}
    if model:
        query["model"] = model
    docs = list(db["model_metrics"].find(query, {"_id": 0}))
    return {"count": len(docs), "data": clean_nan(docs)}


@app.get("/indicateurs-nationaux")
def get_indicateurs_nationaux():
    docs = list(db["indicateurs_nationaux"].find({}, {"_id": 0}).sort("annee", 1))
    return {"count": len(docs), "data": clean_nan(docs)}