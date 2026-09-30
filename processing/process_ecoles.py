import io
import yaml
import pandas as pd
from utils import (
    list_files_in_prefix,
    download_file_from_minio,
    upload_dataframe_to_minio_csv,
    upload_dataframe_to_mongo,
    normalize_columns,
    RAW_BUCKET,
    PROCESSED_BUCKET,
)

EXCEL_PREFIX = "excel/"
SCHEMA_PATH = "schemas/ecoles_schema.yaml"


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def merge_excel_files():
    files = list_files_in_prefix(RAW_BUCKET, EXCEL_PREFIX)
    print(f"{len(files)} fichier(s) Excel trouvé(s) sous '{EXCEL_PREFIX}'\n")

    dataframes = []
    for key in files:
        content = download_file_from_minio(RAW_BUCKET, key)
        df = pd.read_excel(io.BytesIO(content))
        dataframes.append(df)
        print(f"📄 {key} -> {len(df)} lignes")

    merged = pd.concat(dataframes, ignore_index=True)
    print(f"\n✅ Fusion terminée : {len(merged)} lignes au total\n")
    return merged


def clean_data(df, schema):
    # Renommage des colonnes selon le schéma
    df = normalize_columns(df, schema["column_aliases"])

    # Suppression des espaces superflus dans les colonnes texte
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        df[col] = df[col].astype(str).str.strip()

    # Conversion des coordonnées en numérique (les valeurs invalides deviennent NaN)
    if "latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    if "longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Suppression des doublons sur le code établissement (garde la première occurrence)
    before = len(df)
    if "code_etablissement" in df.columns:
        df = df.drop_duplicates(subset="code_etablissement", keep="first")
    after = len(df)
    if before != after:
        print(f"⚠️  {before - after} doublon(s) supprimé(s) sur 'code_etablissement'")

    return df


def process_ecoles():
    schema = load_schema()
    merged = merge_excel_files()
    cleaned = clean_data(merged, schema)

    print(f"\n=== Aperçu final ===")
    print(f"Lignes : {len(cleaned)}")
    print(f"Colonnes : {list(cleaned.columns)}")
    print(cleaned.head(3))

    upload_dataframe_to_minio_csv(cleaned, PROCESSED_BUCKET, "ecoles/ecoles_togo.csv")
    upload_dataframe_to_mongo(cleaned, "ecoles")


if __name__ == "__main__":
    process_ecoles()