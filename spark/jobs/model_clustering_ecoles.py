from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.sql.functions import col, isnan
from pymongo import MongoClient

from ml_utils import build_spark_session, load_collection

MONGO_URI = "mongodb://mongodb:27017"
DB_NAME = "education_db"


def save_metrics(rows):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    db["model_metrics"].delete_many({"model": "clustering_ecoles"})
    if rows:
        db["model_metrics"].insert_many(rows)
    client.close()


def run_clustering():
    spark = build_spark_session("ClusteringEcoles")

    ecoles = load_collection(spark, "ecoles")
    ecoles = ecoles.filter(col("latitude").isNotNull() & col("longitude").isNotNull())
    ecoles = ecoles.filter((col("latitude") != 0) & (col("longitude") != 0))
    ecoles = ecoles.filter(~isnan(col("latitude")) & ~isnan(col("longitude")))
    ecoles = ecoles.filter(
        (col("latitude") >= 5.5) & (col("latitude") <= 11.5) &
        (col("longitude") >= -1.0) & (col("longitude") <= 2.0)
    )

    assembler = VectorAssembler(inputCols=["latitude", "longitude"], outputCol="features_raw")
    scaler = StandardScaler(inputCol="features_raw", outputCol="features", withStd=True, withMean=True)

    assembled = assembler.transform(ecoles)
    scaler_model = scaler.fit(assembled)
    scaled = scaler_model.transform(assembled)
    scaled.cache()

    evaluator = ClusteringEvaluator(featuresCol="features", predictionCol="cluster")

    results = []
    best_k, best_score, best_model = None, -1, None

    for k in [3, 4, 5, 6, 7]:
        kmeans = KMeans(featuresCol="features", predictionCol="cluster", k=k, seed=42)
        model = kmeans.fit(scaled)
        predictions = model.transform(scaled)
        score = evaluator.evaluate(predictions)
        results.append({"model": "clustering_ecoles", "param": f"k={k}", "metric": "silhouette", "value": float(score)})
        print(f"k={k} -> silhouette={score:.4f}")
        if score > best_score:
            best_score, best_k, best_model = score, k, model

    print(f"\n✅ Meilleur k : {best_k} (silhouette={best_score:.4f})")

    final_predictions = best_model.transform(scaled)
    output = final_predictions.select(
        "code_etablissement", "nom_etablissement", "region", "milieu",
        "latitude", "longitude", col("cluster").alias("cluster_geo")
    )

    output.write.format("mongodb") \
        .option("connection.uri", MONGO_URI) \
        .option("database", DB_NAME) \
        .option("collection", "ecoles_clusters") \
        .mode("overwrite") \
        .save()

    results.append({"model": "clustering_ecoles", "param": f"k_choisi={best_k}", "metric": "silhouette_best", "value": float(best_score)})
    save_metrics(results)

    print(f"✅ Clustering terminé : {output.count()} écoles classées en {best_k} clusters")
    spark.stop()


if __name__ == "__main__":
    run_clustering()