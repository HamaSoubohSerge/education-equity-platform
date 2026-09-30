import os
import io
import json
import boto3
from botocore.exceptions import ClientError
from pymongo import MongoClient

# --- Configuration MinIO ---
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadminpassword")

RAW_BUCKET = "raw"
PROCESSED_BUCKET = "processed"

# --- Configuration MongoDB ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/education_db")
MONGO_DB_NAME = "education_db"


def get_s3_client():
    """Retourne un client boto3 connecté à MinIO."""
    return boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name='us-east-1'
    )


def get_mongo_db():
    """Retourne une référence à la base MongoDB."""
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB_NAME]


def ensure_bucket_exists(bucket_name):
    """Crée le bucket MinIO s'il n'existe pas déjà."""
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3.create_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' créé.")


def download_file_from_minio(bucket, key):
    """Télécharge un fichier depuis MinIO et le retourne en mémoire (bytes)."""
    s3 = get_s3_client()
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read()


def list_files_in_prefix(bucket, prefix):
    """Liste tous les fichiers dans un bucket sous un préfixe donné (ex: 'excel/')."""
    s3 = get_s3_client()
    paginator = s3.get_paginator('list_objects_v2')
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            keys.append(obj['Key'])
    return keys


def upload_dataframe_to_minio_csv(df, bucket, key):
    """Upload un DataFrame pandas en CSV vers MinIO."""
    ensure_bucket_exists(bucket)
    s3 = get_s3_client()
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer.getvalue().encode('utf-8'))
    print(f"✅ Upload processed -> {bucket}/{key}")


def upload_dataframe_to_mongo(df, collection_name, replace=True):
    """Charge un DataFrame pandas dans une collection MongoDB."""
    db = get_mongo_db()
    collection = db[collection_name]

    records = df.to_dict(orient='records')

    if replace:
        collection.delete_many({})

    if records:
        collection.insert_many(records)

    print(f"✅ {len(records)} document(s) chargé(s) dans MongoDB -> collection '{collection_name}'")


def normalize_columns(df, column_aliases):
    """
    Renomme les colonnes d'un DataFrame selon un dictionnaire d'alias.
    Signale (sans planter) toute colonne non reconnue.
    """
    rename_map = {}
    unknown_columns = []

    for col in df.columns:
        col_clean = col.strip()
        if col_clean in column_aliases:
            rename_map[col] = column_aliases[col_clean]
        elif col_clean not in column_aliases.values():
            unknown_columns.append(col)

    df = df.rename(columns=rename_map)

    if unknown_columns:
        print(f"⚠️  Colonnes non reconnues (ignorées, à ajouter au schéma si pertinent) : {unknown_columns}")

    return df