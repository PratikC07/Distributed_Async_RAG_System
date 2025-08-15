import os
import pika
import redis
import time
from rag_core import process_rag_query

# Connect to Redis
redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, db=0)


def callback(ch, method, properties, body):
    try:
        message = body.decode().split("|")
        job_id = message[0]
        query = message[1]
        print(f" [x] Received job {job_id} for query: {query}")

        # Process the RAG query
        rag_response = process_rag_query(query)

        # Store the result in Redis
        redis_client.set(job_id, rag_response)

        # In a real-world scenario, the worker would also update the status key here
        redis_client.set(f"status_{job_id}", "completed")

        print(f" [x] Processed job {job_id}. Result stored in Redis.")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f" [!] Error processing job: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)


def start_worker():
    print("🚀 Starting RAG Worker Service...")
    while True:
        try:
            # Connect to RabbitMQ
            print("🔌 Connecting to RabbitMQ...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=os.getenv("RABBITMQ_HOST", "localhost"))
            )
            channel = connection.channel()
            channel.queue_declare(queue="rag_queries", durable=True)

            print("✅ Connected to RabbitMQ successfully!")
            print("👂 Waiting for RAG queries...")
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue="rag_queries", on_message_callback=callback)

            # Start consuming messages
            channel.start_consuming()

        except pika.exceptions.ConnectionClosedByBroker:
            print(" [!] Connection closed by broker. Reconnecting...")
            time.sleep(5)
            continue
        except pika.exceptions.AMQPChannelError as e:
            print(f" [!] Caught a channel error: {e}. Reconnecting...")
            time.sleep(5)
            continue
        except pika.exceptions.AMQPConnectionError:
            print(" [!] Connection to RabbitMQ lost. Reconnecting...")
            time.sleep(5)
            continue
        except Exception as e:
            print(f" [!] An unexpected error occurred: {e}. Retrying connection...")
            time.sleep(5)
            continue


if __name__ == "__main__":
    start_worker()
