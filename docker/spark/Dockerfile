FROM apache/spark:3.5.1

USER root
COPY spark/requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# Connecteurs pour lire/écrire MinIO (S3A) et MongoDB
RUN curl -o /opt/spark/jars/hadoop-aws-3.3.4.jar \
        https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar \
    && curl -o /opt/spark/jars/aws-java-sdk-bundle-1.12.262.jar \
        https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar \
    && curl -o /opt/spark/jars/mongo-spark-connector_2.12-10.3.0.jar \
        https://repo1.maven.org/maven2/org/mongodb/spark/mongo-spark-connector_2.12/10.3.0/mongo-spark-connector_2.12-10.3.0.jar \
    && curl -o /opt/spark/jars/mongodb-driver-sync-4.11.1.jar \
        https://repo1.maven.org/maven2/org/mongodb/mongodb-driver-sync/4.11.1/mongodb-driver-sync-4.11.1.jar \
    && curl -o /opt/spark/jars/mongodb-driver-core-4.11.1.jar \
        https://repo1.maven.org/maven2/org/mongodb/mongodb-driver-core/4.11.1/mongodb-driver-core-4.11.1.jar \
    && curl -o /opt/spark/jars/bson-4.11.1.jar \
        https://repo1.maven.org/maven2/org/mongodb/bson/4.11.1/bson-4.11.1.jar