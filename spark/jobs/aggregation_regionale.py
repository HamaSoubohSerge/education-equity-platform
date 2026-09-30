from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, avg, count, regexp_replace, when
from pyspark.sql.types import StringType, DoubleType


def build_spark_session():
    return (
        SparkSession.builder
        .appName("AgregationRegionale")
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "minioadminpassword")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .getOrCreate()
    )


def load_collection(spark, collection_name):
    return (
        spark.read.format("mongodb")
        .option("connection.uri", "mongodb://mongodb:27017")
        .option("database", "education_db")
        .option("collection", collection_name)
        .load()
    )


def normalize_region_python(raw):
    """Normalise un nom de région brut vers l'une des 5 régions administratives du Togo."""
    if raw is None:
        return None
    clean = raw.upper().replace(" ", "").replace("DRE", "").strip()

    if clean == "" or "ENSEMBLE" in clean:
        return None
    if clean.startswith("GRANDLOME") or clean.startswith("MARITIME"):
        return "Maritime"
    if clean.startswith("PLATEAUX"):
        return "Plateaux"
    if clean == "CENTRALE":
        return "Centrale"
    if clean == "KARA":
        return "Kara"
    if clean == "SAVANES":
        return "Savanes"
    return None


normalize_region = udf(normalize_region_python, StringType())


def percent_to_float(colname):
    """Convertit une chaîne '12,7%' en nombre décimal 12.7."""
    return regexp_replace(regexp_replace(col(colname), ",", "."), "%", "").cast(DoubleType())


def process_aggregation():
    spark = build_spark_session()

    # --- Comptages d'infrastructure ---
    ecoles = load_collection(spark, "ecoles").withColumn("region_norm", normalize_region(col("region")))
    ecoles_agg = ecoles.filter(col("region_norm").isNotNull()).groupBy("region_norm").agg(count("*").alias("nb_ecoles"))

    batiments = load_collection(spark, "batiments").withColumn("region_norm", normalize_region(col("region")))
    batiments_agg = batiments.filter(col("region_norm").isNotNull()).groupBy("region_norm").agg(count("*").alias("nb_batiments"))

    sanitaires = load_collection(spark, "sanitaires").withColumn("region_norm", normalize_region(col("region")))
    sanitaires_agg = sanitaires.filter(col("region_norm").isNotNull()).groupBy("region_norm").agg(count("*").alias("nb_sanitaires"))

    bibliotheques = load_collection(spark, "bibliotheques").withColumn("region_norm", normalize_region(col("region")))
    bibliotheques_agg = bibliotheques.filter(col("region_norm").isNotNull()).groupBy("region_norm").agg(count("*").alias("nb_bibliotheques"))

    terrains = load_collection(spark, "terrains_sportifs").withColumn("region_norm", normalize_region(col("region")))
    terrains_agg = terrains.filter(col("region_norm").isNotNull()).groupBy("region_norm").agg(count("*").alias("nb_terrains_sportifs"))

    # --- Taux de redoublement (lignes "Total" uniquement, par DRE) ---
    redoub_primaire = load_collection(spark, "redoublement_primaire")
    redoub_primaire = redoub_primaire.filter(col("INSPECTION") == "Total")
    redoub_primaire = redoub_primaire.withColumn("region_norm", normalize_region(col("DRE")))
    redoub_primaire = redoub_primaire.withColumn("taux_redoublement_primaire", percent_to_float("taux_total"))
    redoub_primaire_agg = (
        redoub_primaire.filter(col("region_norm").isNotNull())
        .groupBy("region_norm")
        .agg(avg("taux_redoublement_primaire").alias("taux_redoublement_primaire"))
    )

    redoub_secondaire = load_collection(spark, "redoublement_secondaire")
    redoub_secondaire = redoub_secondaire.filter(col("inspection") == "Total")
    redoub_secondaire = redoub_secondaire.withColumn("region_norm", normalize_region(col("region")))
    redoub_secondaire = redoub_secondaire.withColumn("taux_redoublement_sec1", percent_to_float("sec1_total"))
    redoub_secondaire = redoub_secondaire.withColumn("taux_redoublement_sec2", percent_to_float("sec2_total"))
    redoub_secondaire_agg = (
        redoub_secondaire.filter(col("region_norm").isNotNull())
        .groupBy("region_norm")
        .agg(
            avg("taux_redoublement_sec1").alias("taux_redoublement_sec1"),
            avg("taux_redoublement_sec2").alias("taux_redoublement_sec2"),
        )
    )

    # --- Jointure finale de toutes les sources par région ---
    result = ecoles_agg
    for df in [batiments_agg, sanitaires_agg, bibliotheques_agg, terrains_agg, redoub_primaire_agg, redoub_secondaire_agg]:
        result = result.join(df, on="region_norm", how="outer")

    result = result.withColumnRenamed("region_norm", "region")
    result = result.fillna(0, subset=["nb_ecoles", "nb_batiments", "nb_sanitaires", "nb_bibliotheques", "nb_terrains_sportifs"])

    print("=== Agrégation régionale ===")
    result.show(truncate=False)

    # --- Écriture des résultats ---
    result.write.format("mongodb") \
        .option("connection.uri", "mongodb://mongodb:27017") \
        .option("database", "education_db") \
        .option("collection", "aggregation_regionale") \
        .mode("overwrite") \
        .save()

    result.coalesce(1).write.mode("overwrite").option("header", "true") \
        .csv("s3a://processed/aggregation/aggregation_regionale")

    print("✅ Agrégation régionale terminée et sauvegardée (MongoDB + MinIO)")

    spark.stop()


if __name__ == "__main__":
    process_aggregation()