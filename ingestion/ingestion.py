from local_files import upload_local_files
from api_client import fetch_and_store_all


def main():
    print("=== Ingestion : fichiers locaux ===")
    upload_local_files()

    print("\n=== Ingestion : API Banque Mondiale (éducation Togo) ===")
    fetch_and_store_all()


if __name__ == "__main__":
    main()