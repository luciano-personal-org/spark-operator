import boto3
import random
import time
import json

def generate_alert():
    alert = {
        "id": str(random.randint(1000, 9999)),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "alert_type": random.choice(["INFO", "WARNING", "ERROR"]),
        "severity": random.choice(["LOW", "MEDIUM", "HIGH"]),
        "description": "This is a test alert"
    }
    return alert

def send_alert_to_sqs(alert):
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(alert)
    )
    return response

queue_url = "https://sqs.us-east-1.amazonaws.com/992382765082/luciano-spark-queue"
sqs = boto3.client('sqs')

if __name__ == "__main__":
    while True:
        alert = generate_alert()
        response = send_alert_to_sqs(alert)
        print(f"Sent alert: {alert}")
        #time.sleep()  # Wait for 5 seconds before sending the next alert
