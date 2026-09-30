import os
import glob
import boto3
from botocore.exceptions import ClientError

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadminpassword")
BUCKET_NAME = "raw"
LOCAL_DATA_DIR = os.getenv("LOCAL_DATA_DIR", "/data")

s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name='us-east-1'
)


def ensure_bucket_exists(bucket_name):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' créé.")


def upload_local_files():
    ensure_bucket_exists(BUCKET_NAME)

    extensions = {
        "*.csv": "csv",
        "*.xlsx": "excel",
        "*.xls": "excel",
        "*.pdf": "pdf",
    }

    uploaded_count = 0
    for pattern, subfolder in extensions.items():
        files = glob.glob(os.path.join(LOCAL_DATA_DIR, "**", pattern), recursive=True)
        for filepath in files:
            filename = os.path.basename(filepath)
            s3_key = f"{subfolder}/{filename}"
            try:
                s3_client.upload_file(filepath, BUCKET_NAME, s3_key)
                print(f"✅ Uploadé : {filepath} -> {BUCKET_NAME}/{s3_key}")
                uploaded_count += 1
            except ClientError as e:
                print(f"❌ Erreur upload {filepath} : {e}")

    print(f"\n{uploaded_count} fichier(s) uploadé(s) vers MinIO.")
    return uploaded_count


if __name__ == "__main__":
    upload_local_files()