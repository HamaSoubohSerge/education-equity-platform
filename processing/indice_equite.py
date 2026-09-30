from utils import get_mongo_db


def compute_indice_equite():
    db = get_mongo_db()
    import pandas as pd

    docs = list(db["aggregation_regionale"].find({}, {"_id": 0}))
    df = pd.DataFrame(docs)

    df["ratio_batiments"] = df["nb_batiments"] / df["nb_ecoles"]
    df["ratio_sanitaires"] = df["nb_sanitaires"] / df["nb_ecoles"]
    df["ratio_bibliotheques"] = df["nb_bibliotheques"] / df["nb_ecoles"]
    df["ratio_terrains"] = df["nb_terrains_sportifs"] / df["nb_ecoles"]

    def normalize(c):
        return (df[c] - df[c].min()) / (df[c].max() - df[c].min())

    df["score_infra"] = (
        normalize("ratio_batiments") + normalize("ratio_sanitaires") +
        normalize("ratio_bibliotheques") + normalize("ratio_terrains")
    ) / 4

    df["score_reussite"] = 1 - (
        normalize("taux_redoublement_primaire") +
        normalize("taux_redoublement_sec1") +
        normalize("taux_redoublement_sec2")
    ) / 3

    df["indice_equite"] = ((df["score_infra"] + df["score_reussite"]) / 2 * 100).round(1)
    df = df.sort_values("indice_equite", ascending=False)

    print("=== Indice d'équité régional ===")
    print(df[["region", "indice_equite", "score_infra", "score_reussite"]])

    db["indice_equite_regional"].delete_many({})
    records = df[["region", "indice_equite", "score_infra", "score_reussite",
                  "ratio_batiments", "ratio_sanitaires", "ratio_bibliotheques", "ratio_terrains"]].to_dict(orient="records")
    db["indice_equite_regional"].insert_many(records)

    print("✅ Indice d'équité calculé et sauvegardé")


if __name__ == "__main__":
    compute_indice_equite()