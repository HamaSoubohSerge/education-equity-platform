import os
import json
from datetime import datetime
import requests
import boto3
from botocore.exceptions import ClientError

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadminpassword")
BUCKET_NAME = "raw"

s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name='us-east-1'
)

# Indicateurs d'éducation Banque Mondiale
WORLD_BANK_INDICATORS = {
    "SE.PRM.ENRL": "primary_enrollment",
    "SE.SEC.ENRL": "secondary_enrollment",
    "SE.ADT.LITR.ZS": "adult_literacy_rate",
    "SE.PRM.CMPT.ZS": "primary_completion_rate",
}

COUNTRY_CODE = "TGO"


def fetch_world_bank_indicator(indicator_code, retries=2):
    url = f"https://api.worldbank.org/v2/country/{COUNTRY_CODE}/indicator/{indicator_code}"
    params = {"format": "json", "per_page": 100}

    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                print(f"⚠️  Tentative {attempt + 1} échouée pour {indicator_code}, nouvel essai...")
            else:
                raise


def ensure_bucket_exists(bucket_name):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3_client.create_bucket(Bucket=bucket_name)


def upload_json_to_minio(data, s3_key):
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=json_bytes, ContentType="application/json")


def fetch_and_store_all():
    ensure_bucket_exists(BUCKET_NAME)
    timestamp = datetime.utcnow().strftime("%Y%m%d")

    for code, name in WORLD_BANK_INDICATORS.items():
        try:
            data = fetch_world_bank_indicator(code)
            s3_key = f"api/world_bank/{name}_{timestamp}.json"
            upload_json_to_minio(data, s3_key)
            print(f"✅ {name} -> {BUCKET_NAME}/{s3_key}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur pour {name} : {e}")

    fetch_and_store_unesco()


# --- UNESCO UIS (désactivé tant que UNESCO_API_KEY n'est pas définie) ---

UNESCO_API_KEY = os.getenv("UNESCO_API_KEY", "")
UNESCO_BASE_URL = "https://api.uis.unesco.org/api/public/data/indicators"

UNESCO_INDICATORS = {
    "SE.PRM.ENRL": "primary_enrollment_unesco",
    "SE.SEC.ENRL": "secondary_enrollment_unesco",
    "SE.ADT.LITR.ZS": "literacy_rate_unesco",
}

UNESCO_GEO_UNIT = "TGO"


def fetch_unesco_indicator(indicator_code):
    if not UNESCO_API_KEY:
        raise ValueError("UNESCO_API_KEY non définie.")

    params = {
        "indicator": indicator_code,
        "geoUnit": UNESCO_GEO_UNIT,
    }
    headers = {
        "Ocp-Apim-Subscription-Key": UNESCO_API_KEY,
        "Accept": "application/json",
    }

    response = requests.get(UNESCO_BASE_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_and_store_unesco():
    if not UNESCO_API_KEY:
        print("⚠️  UNESCO_API_KEY non définie, étape UNESCO ignorée.")
        return

    ensure_bucket_exists(BUCKET_NAME)
    timestamp = datetime.utcnow().strftime("%Y%m%d")

    for code, name in UNESCO_INDICATORS.items():
        try:
            data = fetch_unesco_indicator(code)
            s3_key = f"api/unesco/{name}_{timestamp}.json"
            upload_json_to_minio(data, s3_key)
            print(f"✅ {name} -> {BUCKET_NAME}/{s3_key}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur pour {name} (UNESCO) : {e}")


if __name__ == "__main__":
    fetch_and_store_all()