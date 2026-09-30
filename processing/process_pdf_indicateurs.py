import io
import pandas as pd
import pdfplumber
from utils import (
    download_file_from_minio,
    upload_dataframe_to_minio_csv,
    upload_dataframe_to_mongo,
    RAW_BUCKET,
    PROCESSED_BUCKET,
)

PDF_KEY = "pdf/RAPPORT_DANALYSE_DES_INDICATEURS_SCOLAIRES_2024-2025.pdf"


def extract_table_from_page(pdf, page_number, table_index=0):
    page = pdf.pages[page_number - 1]
    tables = page.extract_tables()
    if not tables or len(tables) <= table_index:
        print(f"⚠️  Aucun tableau trouvé page {page_number} (index {table_index})")
        return None
    return tables[table_index]


def table_to_dataframe(table, header_row=0):
    header = table[header_row]
    rows = table[header_row + 1:]
    df = pd.DataFrame(rows, columns=header)
    return df


def deduplicate_columns(columns):
    seen = {}
    result = []
    for i, col in enumerate(columns):
        col_clean = str(col).strip() if col else f"col_{i}"
        if col_clean == "" or col_clean == "None":
            col_clean = f"col_{i}"
        if col_clean in seen:
            seen[col_clean] += 1
            col_clean = f"{col_clean}_{seen[col_clean]}"
        else:
            seen[col_clean] = 0
        result.append(col_clean)
    return result


def clean_evolution_etablissements():
    content = download_file_from_minio(RAW_BUCKET, PDF_KEY)
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        table = extract_table_from_page(pdf, 14, table_index=0)

    if table is None:
        return None

    df = table_to_dataframe(table)
    df.columns = [str(c).strip() for c in df.columns]

    print("📄 Évolution des établissements (page 14)")
    print(df)
    return df


def clean_redoublement_primaire():
    """Pages 38-39 : taux de redoublement par inspection au primaire."""
    content = download_file_from_minio(RAW_BUCKET, PDF_KEY)

    all_rows = []
    pages_tables = [(38, 0), (39, 0)]

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page_num, t_idx in pages_tables:
            table = extract_table_from_page(pdf, page_num, table_index=t_idx)
            if table is None:
                continue
            df = table_to_dataframe(table)
            df.columns = deduplicate_columns(df.columns)
            all_rows.append(df)

    if not all_rows:
        return None

    merged = pd.concat(all_rows, ignore_index=True)

    merged["taux_garcons"] = merged["G"].fillna(merged["col_2"])
    merged["taux_filles"] = merged["F"].fillna(merged["col_4"])
    merged = merged.rename(columns={"T": "taux_total"})
    merged = merged.drop(columns=["G", "col_2", "F", "col_4"])

    merged["DRE"] = merged["DRE"].replace("", None).ffill()

    for col in ["DRE", "INSPECTION"]:
        merged[col] = merged[col].astype(str).str.strip()

    print("📄 Redoublement primaire (pages 38-39)")
    print(merged.head(10))
    return merged


def clean_redoublement_secondaire():
    """Page 40 : taux de redoublement par inspection au secondaire (1er et 2e cycle)."""
    content = download_file_from_minio(RAW_BUCKET, PDF_KEY)
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        table = extract_table_from_page(pdf, 40, table_index=0)

    if table is None:
        return None

    df = table_to_dataframe(table)
    df.columns = deduplicate_columns(df.columns)

    df = df.iloc[1:].reset_index(drop=True)

    df["REGIONS"] = df["REGIONS"].ffill()
    df["REGIONS"] = df["REGIONS"].str.replace(" ", "", regex=False)

    result = pd.DataFrame({
        "region": df["REGIONS"].astype(str).str.strip(),
        "inspection": df["INSPECTIONS"].astype(str).str.strip(),
        "sec1_garcons": df["col_4"],
        "sec1_filles": df["nan_3"],
        "sec1_total": df["nan_6"],
        "sec2_garcons": df["col_13"],
        "sec2_filles": df["nan_9"],
        "sec2_total": df["nan_12"],
    })

    print("📄 Redoublement secondaire (page 40)")
    print(result.head(10))
    return result


def process_pdf():
    evolution = clean_evolution_etablissements()
    if evolution is not None:
        upload_dataframe_to_minio_csv(evolution, PROCESSED_BUCKET, "pdf/evolution_etablissements.csv")
        upload_dataframe_to_mongo(evolution, "evolution_etablissements")

    redoublement_primaire = clean_redoublement_primaire()
    if redoublement_primaire is not None:
        upload_dataframe_to_minio_csv(redoublement_primaire, PROCESSED_BUCKET, "pdf/redoublement_primaire.csv")
        upload_dataframe_to_mongo(redoublement_primaire, "redoublement_primaire")

    redoublement_secondaire = clean_redoublement_secondaire()
    if redoublement_secondaire is not None:
        upload_dataframe_to_minio_csv(redoublement_secondaire, PROCESSED_BUCKET, "pdf/redoublement_secondaire.csv")
        upload_dataframe_to_mongo(redoublement_secondaire, "redoublement_secondaire")


if __name__ == "__main__":
    process_pdf()