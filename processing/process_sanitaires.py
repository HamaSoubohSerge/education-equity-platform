import io
import yaml
import pandas as pd
from shapely import wkt
from utils import (
    download_file_from_minio,
    upload_dataframe_to_minio_csv,
    upload_dataframe_to_mongo,
    normalize_columns,
    RAW_BUCKET,
    PROCESSED_BUCKET,
)

CSV_KEY = "csv/sanitaires.csv"
SCHEMA_PATH = "schemas/sanitaires_schema.yaml"

# Valeurs considérées comme "non renseigné"
MISSING_VALUES = {"Nsp", "NSP", "nsp", "N/A", "n/a", ""}


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_data():
    content = download_file_from_minio(RAW_BUCKET, CSV_KEY)
    df = pd.read_csv(io.BytesIO(content))
    print(f"📄 {CSV_KEY} -> {len(df)} lignes")
    return df


def extract_point_coords(wkt_string):
    """Extrait latitude/longitude depuis une géométrie POINT."""
    try:
        geom = wkt.loads(wkt_string)
        return pd.Series({"longitude": geom.x, "latitude": geom.y})
    except Exception:
        return pd.Series({"longitude": None, "latitude": None})

def clean_data(df, schema):
    df = normalize_columns(df, schema["column_aliases"])

    # Nettoyage des colonnes texte
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        df[col] = df[col].astype(str).str.strip()

    # Nettoyage des accolades autour du type de toilette (format liste PostgreSQL)
    if "type_toilette" in df.columns:
        df["type_toilette"] = df["type_toilette"].str.strip("{}")

    # Normalisation des valeurs "non renseigné" en NaN
    df = df.replace(list(MISSING_VALUES), pd.NA)

    # Extraction des coordonnées depuis la géométrie POINT
    if "geometry_wkt" in df.columns:
        print("📍 Extraction des coordonnées depuis les géométries...")
        coords = df["geometry_wkt"].apply(extract_point_coords)
        df = pd.concat([df, coords], axis=1)

    # Suppression des doublons exacts
    before = len(df)
    df = df.drop_duplicates(subset="fid", keep="first")
    after = len(df)
    if before != after:
        print(f"⚠️  {before - after} doublon(s) supprimé(s) sur 'fid'")

    return df


def process_sanitaires():
    schema = load_schema()
    raw_df = load_data()
    cleaned = clean_data(raw_df, schema)

    print(f"\n=== Aperçu final ===")
    print(f"Lignes : {len(cleaned)}")
    print(f"Colonnes : {list(cleaned.columns)}")
    print(cleaned[["region", "commune", "type_toilette", "nom_etablissement", "latitude", "longitude"]].head(3))

    upload_dataframe_to_minio_csv(cleaned, PROCESSED_BUCKET, "sanitaires/sanitaires_togo.csv")
    upload_dataframe_to_mongo(cleaned, "sanitaires")


if __name__ == "__main__":
    process_sanitaires()