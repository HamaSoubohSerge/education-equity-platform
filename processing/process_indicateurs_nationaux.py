import io
import json
import pandas as pd
from utils import (
    list_files_in_prefix,
    download_file_from_minio,
    upload_dataframe_to_minio_csv,
    upload_dataframe_to_mongo,
    RAW_BUCKET,
    PROCESSED_BUCKET,
)

API_PREFIX = "api/world_bank/"


def extract_indicator_name(key):
    """Extrait le nom de l'indicateur depuis le nom de fichier (retire le préfixe et la date)."""
    filename = key.split("/")[-1]
    name = filename.rsplit("_", 1)[0]  # retire le suffixe date (_20260908)
    return name


def parse_world_bank_json(content):
    """Parse le format JSON spécifique de l'API Banque mondiale : [metadata, records]."""
    data = json.loads(content)
    if len(data) < 2 or data[1] is None:
        return []
    return data[1]


def process_indicateurs_nationaux():
    files = list_files_in_prefix(RAW_BUCKET, API_PREFIX)
    print(f"{len(files)} fichier(s) d'indicateurs trouvé(s) sous '{API_PREFIX}'\n")

    all_rows = []

    for key in files:
        indicator_name = extract_indicator_name(key)
        content = download_file_from_minio(RAW_BUCKET, key)
        records = parse_world_bank_json(content)

        for record in records:
            all_rows.append({
                "indicateur": indicator_name,
                "annee": record.get("date"),
                "valeur": record.get("value"),
            })

        print(f"📄 {key} -> {len(records)} années")

    df = pd.DataFrame(all_rows)
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
    df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")

    # Format long -> wide : une colonne par indicateur, une ligne par année
    df_wide = df.pivot_table(index="annee", columns="indicateur", values="valeur").reset_index()
    df_wide = df_wide.sort_values("annee")

    print(f"\n=== Aperçu final ===")
    print(df_wide)

    upload_dataframe_to_minio_csv(df_wide, PROCESSED_BUCKET, "indicateurs_nationaux/indicateurs_togo.csv")
    upload_dataframe_to_mongo(df_wide, "indicateurs_nationaux")


if __name__ == "__main__":
    process_indicateurs_nationaux()