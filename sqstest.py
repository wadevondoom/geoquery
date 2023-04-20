import boto3
import os

aws_access_key_id = os.environ.get("aws_access_key_id")
aws_secret_access_key = os.environ.get("aws_secret_access_key")
aws_region = os.environ.get("aws_region")
aws_sqs_queue_name = os.environ.get("aws_sqs_queue_name")

sqs = boto3.resource(
    "sqs",
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region,
)

queue = sqs.get_queue_by_name(QueueName=aws_sqs_queue_name)
print("Queue URL:", queue.url)
