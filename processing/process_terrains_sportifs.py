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

CSV_KEY = "csv/terrains_sportifs.csv"
SCHEMA_PATH = "schemas/terrains_sportifs_schema.yaml"

MISSING_VALUES = {"Nsp", "NSP", "nsp", "N/A", "n/a", ""}


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_data():
    content = download_file_from_minio(RAW_BUCKET, CSV_KEY)
    df = pd.read_csv(io.BytesIO(content))
    print(f"📄 {CSV_KEY} -> {len(df)} lignes")
    return df


def extract_centroid(wkt_string):
    try:
        geom = wkt.loads(wkt_string)
        centroid = geom.centroid
        return pd.Series({"longitude": centroid.x, "latitude": centroid.y})
    except Exception:
        return pd.Series({"longitude": None, "latitude": None})


def clean_data(df, schema):
    df = normalize_columns(df, schema["column_aliases"])

    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        df[col] = df[col].astype(str).str.strip()

    # Nettoyage des accolades sur la liste de sports (format liste PostgreSQL)
    if "liste_sports" in df.columns:
        df["liste_sports"] = df["liste_sports"].str.strip("{}")

    # Normalisation des valeurs "non renseigné" en NaN
    df = df.replace(list(MISSING_VALUES), pd.NA)

    if "geometry_wkt" in df.columns:
        print("📍 Extraction des coordonnées depuis les géométries...")
        centroids = df["geometry_wkt"].apply(extract_centroid)
        df = pd.concat([df, centroids], axis=1)

    before = len(df)
    df = df.drop_duplicates(subset="fid", keep="first")
    after = len(df)
    if before != after:
        print(f"⚠️  {before - after} doublon(s) supprimé(s) sur 'fid'")

    return df


def process_terrains_sportifs():
    schema = load_schema()
    raw_df = load_data()
    cleaned = clean_data(raw_df, schema)

    print(f"\n=== Aperçu final ===")
    print(f"Lignes : {len(cleaned)}")
    print(f"Colonnes : {list(cleaned.columns)}")
    print(cleaned[["region", "commune", "nombre_sports", "liste_sports", "latitude", "longitude"]].head(5))

    upload_dataframe_to_minio_csv(cleaned, PROCESSED_BUCKET, "terrains_sportifs/terrains_sportifs_togo.csv")
    upload_dataframe_to_mongo(cleaned, "terrains_sportifs")


if __name__ == "__main__":
    process_terrains_sportifs()