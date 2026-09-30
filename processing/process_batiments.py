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

CSV_KEY = "csv/batiments.csv"
SCHEMA_PATH = "schemas/batiments_schema.yaml"


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_data():
    content = download_file_from_minio(RAW_BUCKET, CSV_KEY)
    df = pd.read_csv(io.BytesIO(content))
    print(f"📄 {CSV_KEY} -> {len(df)} lignes")
    return df


def extract_centroid(wkt_string):
    """Calcule le centre (latitude, longitude) d'une géométrie WKT."""
    try:
        geom = wkt.loads(wkt_string)
        centroid = geom.centroid
        return pd.Series({"longitude": centroid.x, "latitude": centroid.y})
    except Exception:
        return pd.Series({"longitude": None, "latitude": None})


def clean_data(df, schema):
    df = normalize_columns(df, schema["column_aliases"])

    # Nettoyage des colonnes texte
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        df[col] = df[col].astype(str).str.strip()

    # Nettoyage de l'année de construction : "Nsp" et autres non-numériques -> NaN
    if "annee_construction" in df.columns:
        df["annee_construction"] = pd.to_numeric(df["annee_construction"], errors="coerce")

    # Extraction du centroïde (latitude/longitude) depuis la géométrie WKT
    if "geometry_wkt" in df.columns:
        print("📍 Extraction des coordonnées depuis les géométries...")
        centroids = df["geometry_wkt"].apply(extract_centroid)
        df = pd.concat([df, centroids], axis=1)

    # Suppression des doublons exacts
    before = len(df)
    df = df.drop_duplicates(subset="fid", keep="first")
    after = len(df)
    if before != after:
        print(f"⚠️  {before - after} doublon(s) supprimé(s) sur 'fid'")

    return df


def process_batiments():
    schema = load_schema()
    raw_df = load_data()
    cleaned = clean_data(raw_df, schema)

    print(f"\n=== Aperçu final ===")
    print(f"Lignes : {len(cleaned)}")
    print(f"Colonnes : {list(cleaned.columns)}")
    print(cleaned[["region", "commune", "fonction", "annee_construction", "latitude", "longitude"]].head(3))

    upload_dataframe_to_minio_csv(cleaned, PROCESSED_BUCKET, "batiments/batiments_togo.csv")
    upload_dataframe_to_mongo(cleaned, "batiments")


if __name__ == "__main__":
    process_batiments()