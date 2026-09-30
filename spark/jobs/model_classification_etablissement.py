from pyspark.sql.functions import col, isnan
from pyspark.ml.feature import StringIndexer, VectorAssembler, OneHotEncoder
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pymongo import MongoClient

from ml_utils import build_spark_session, load_collection

MONGO_URI = "mongodb://mongodb:27017"
DB_NAME = "education_db"


def save_metrics(rows):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    db["model_metrics"].delete_many({"model": "classification_statut"})
    if rows:
        db["model_metrics"].insert_many(rows)
    client.close()


def run_classification():
    spark = build_spark_session("ClassificationStatut")

    ecoles = load_collection(spark, "ecoles")
    ecoles = ecoles.filter(
        col("statut").isNotNull() & col("region").isNotNull() &
        col("milieu").isNotNull() & col("type_etablissement").isNotNull() &
        col("latitude").isNotNull() & col("longitude").isNotNull()
    )
    ecoles = ecoles.filter(~isnan(col("latitude")) & ~isnan(col("longitude")))

    counts = ecoles.groupBy("statut").count().filter(col("count") >= 50)
    valid_statuts = [row["statut"] for row in counts.collect()]
    ecoles = ecoles.filter(col("statut").isin(valid_statuts))

    label_indexer = StringIndexer(inputCol="statut", outputCol="label")
    region_indexer = StringIndexer(inputCol="region", outputCol="region_idx")
    milieu_indexer = StringIndexer(inputCol="milieu", outputCol="milieu_idx")
    type_indexer = StringIndexer(inputCol="type_etablissement", outputCol="type_idx")

    region_encoder = OneHotEncoder(inputCol="region_idx", outputCol="region_vec")
    milieu_encoder = OneHotEncoder(inputCol="milieu_idx", outputCol="milieu_vec")
    type_encoder = OneHotEncoder(inputCol="type_idx", outputCol="type_vec")

    assembler = VectorAssembler(
        inputCols=["region_vec", "milieu_vec", "type_vec", "latitude", "longitude"],
        outputCol="features"
    )

    rf = RandomForestClassifier(featuresCol="features", labelCol="label", numTrees=100, seed=42)

    pipeline = Pipeline(stages=[
        label_indexer, region_indexer, milieu_indexer, type_indexer,
        region_encoder, milieu_encoder, type_encoder,
        assembler, rf
    ])

    train, test = ecoles.randomSplit([0.8, 0.2], seed=42)
    train.cache()
    test.cache()

    model = pipeline.fit(train)
    predictions = model.transform(test)

    metrics_config = [
        ("accuracy", "accuracy"),
        ("f1", "f1"),
        ("weightedPrecision", "precision_ponderee"),
        ("weightedRecall", "rappel_pondere"),
    ]

    results = []
    for metric_name, label in metrics_config:
        evaluator = MulticlassClassificationEvaluator(
            labelCol="label", predictionCol="prediction", metricName=metric_name
        )
        score = evaluator.evaluate(predictions)
        results.append({"model": "classification_statut", "param": "test_set", "metric": label, "value": float(score)})
        print(f"{label} = {score:.4f}")

    results.append({"model": "classification_statut", "param": "info", "metric": "nb_train", "value": float(train.count())})
    results.append({"model": "classification_statut", "param": "info", "metric": "nb_test", "value": float(test.count())})

    save_metrics(results)
    print("✅ Classification terminée et métriques sauvegardées")
    spark.stop()


if __name__ == "__main__":
    run_classification()