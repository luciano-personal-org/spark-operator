from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType
from pyspark.sql.functions import from_json
import os
import boto3
import json

# Variables
s3_bucket_name = os.getenv("S3_BUCKET_NAME", "my-iceberg-data-bucket")
kafka_address = os.getenv("KAFKA_ADDRESS", 'b-1.kafkademospark.mkjcj4.c12.kafka.us-west-2.amazonaws.com:9092,b-2.kafkademospark.mkjcj4.c12.kafka.us-west-2.amazonaws.com:9092')

def create_spark_session():
    spark = SparkSession.builder \
        .appName("SQSToIceberg") \
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.0.0,org.apache.hadoop:hadoop-aws:3.3.2,org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.2") \
        .config("spark.jars.repositories", "https://repo1.maven.org/maven2/") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.local.type", "hadoop") \
        .config("spark.sql.catalog.local.warehouse", f"s3a://{s3_bucket_name}/iceberg/warehouse/") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain") \
        .config("spark.sql.warehouse.dir", f"s3a://{s3_bucket_name}/iceberg/warehouse/") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.kryo.registrationRequired", "false") \
        .getOrCreate()
    return spark

def consume_and_write():
    spark = create_spark_session()
    # Debug spark DEBUG
    spark.sparkContext.setLogLevel("ERROR")
    # Create the table
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS local.my_table (
            id STRING,
            timestamp STRING,
            alert_type STRING,
            severity STRING,
            description STRING
        )
        USING iceberg
        LOCATION 's3a://{s3_bucket_name}/iceberg/warehouse/my_table'
        TBLPROPERTIES (
            'write.format.default'='parquet'  -- Explicitly specifying Parquet format
        )
    """)

    # Read from SQS
    sqs = boto3.client('sqs')
    queue_url = os.getenv("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/992382765082/luciano-spark-queue")

    def get_messages():
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20
        )
        return response.get('Messages', [])

    messages = get_messages()

    # Define the schema for the JSON data
    json_schema = StructType([
        StructField("id", StringType(), True),
        StructField("timestamp", StringType(), True),
        StructField("alert_type", StringType(), True),
        StructField("severity", StringType(), True),
        StructField("description", StringType(), True)
    ])

    # Create DataFrame from SQS messages
    if messages:
        data = [json.loads(msg['Body']) for msg in messages]
        df = spark.createDataFrame(data, schema=json_schema)

        # Write the DataFrame to Iceberg using table name
        df.write \
            .format("iceberg") \
            .option("path", f"s3a://{s3_bucket_name}/iceberg/warehouse/my_table") \
            .mode("append") \
            .save()

if __name__ == "__main__":
    consume_and_write()
