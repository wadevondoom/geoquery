import boto3
import os

aws_access_key = os.environ.get("AWS_ACCESS_KEY")
aws_secret_key = os.environ.get("AWS_SECRET_KEY")
aws_region = os.environ.get("AWS_REGION")
aws_sqs_queue = os.environ.get("AWS_SQS_QUEUE")

sqs = boto3.resource(
    "sqs",
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=aws_region,
)

queue = sqs.get_queue_by_name(QueueName=aws_sqs_queue)

print("Queue URL:", queue.url)
