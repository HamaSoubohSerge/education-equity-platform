from pyspark.sql import SparkSession


def build_spark_session(app_name="MLJob"):
    return (
        SparkSession.builder
        .appName(app_name)
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