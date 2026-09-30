from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

NETWORK = "education-data-platform_default"
PROJECT_DIR = "/home/sergio/education-data-platform"

default_args = {
    "owner": "education-platform",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

spark_jobs_mount = Mount(
    source=f"{PROJECT_DIR}/spark/jobs",
    target="/opt/spark-apps/jobs",
    type="bind",
    read_only=True,
)

ingestion_data_mount = Mount(
    source=f"{PROJECT_DIR}/data",
    target="/data",
    type="bind",
    read_only=True,
)

with DAG(
    dag_id="pipeline_education_togo",
    default_args=default_args,
    description="Pipeline complet : ingestion → nettoyage → agrégation → modèles",
    schedule="@weekly",
    start_date=datetime(2026, 9, 1),
    catchup=False,
    tags=["education", "togo", "big-data"],
) as dag:

    ingestion = DockerOperator(
        task_id="ingestion",
        image="education-data-platform-ingestion",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode=NETWORK,
        mounts=[ingestion_data_mount],
        environment={
            "MONGO_URI": "mongodb://education-mongodb:27017/education_db",
            "MINIO_ENDPOINT": "http://education-minio:9000",
            "MINIO_ACCESS_KEY": "minioadmin",
            "MINIO_SECRET_KEY": "minioadminpassword",
            "LOCAL_DATA_DIR": "/data",
        },
    )

    nettoyage_ecoles = DockerOperator(
        task_id="nettoyage_ecoles",
        image="education-data-platform-processing",
        command="python process_ecoles.py",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode=NETWORK,
        environment={
            "MONGO_URI": "mongodb://education-mongodb:27017/education_db",
            "MINIO_ENDPOINT": "http://education-minio:9000",
        },
    )

    nettoyage_batiments = DockerOperator(
        task_id="nettoyage_batiments",
        image="education-data-platform-processing",
        command="python process_batiments.py",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode=NETWORK,
        environment={
            "MONGO_URI": "mongodb://education-mongodb:27017/education_db",
            "MINIO_ENDPOINT": "http://education-minio:9000",
        },
    )

    agregation_regionale = DockerOperator(
        task_id="agregation_regionale",
        image="education-data-platform-spark",
        command="spark-submit /opt/spark-apps/jobs/aggregation_regionale.py",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode=NETWORK,
        mounts=[spark_jobs_mount],
    )

    indice_equite = DockerOperator(
        task_id="indice_equite",
        image="education-data-platform-processing",
        command="python indice_equite.py",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode=NETWORK,
        environment={
            "MONGO_URI": "mongodb://education-mongodb:27017/education_db",
        },
    )

    modele_clustering = DockerOperator(
        task_id="modele_clustering",
        image="education-data-platform-spark",
        command="spark-submit /opt/spark-apps/jobs/model_clustering_ecoles.py",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode=NETWORK,
        mounts=[spark_jobs_mount],
    )

    modele_classification = DockerOperator(
        task_id="modele_classification",
        image="education-data-platform-spark",
        command="spark-submit /opt/spark-apps/jobs/model_classification_etablissement.py",
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode=NETWORK,
        mounts=[spark_jobs_mount],
    )

    ingestion >> [nettoyage_ecoles, nettoyage_batiments] >> agregation_regionale
    agregation_regionale >> indice_equite
    agregation_regionale >> [modele_clustering, modele_classification]