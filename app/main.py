import os
import redis
import uuid
import aio_pika
import asyncio
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from models import QueryRequest, QueryResponse, ResultResponse

# Store connections in a dictionary for easy access within the app
state = {}


async def connect_to_rabbitmq():
    """Connect to RabbitMQ with retry logic"""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            connection = await aio_pika.connect_robust(
                f"amqp://{os.getenv('RABBITMQ_HOST', 'localhost')}/"
            )
            channel = await connection.channel()
            await channel.declare_queue("rag_queries", durable=True)
            print(f"Connected to RabbitMQ successfully on attempt {attempt + 1}")
            return connection, channel
        except Exception as e:
            print(
                f"RabbitMQ connection attempt {attempt + 1}/{max_retries} failed: {e}"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                print("Failed to connect to RabbitMQ after all retries")
                raise


# Use FastAPI's lifespan event to manage the connection state
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to Redis
    state["redis_client"] = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"), port=6379, db=0
    )

    # Connect to RabbitMQ with retry logic
    state["rabbitmq_connection"], state["rabbitmq_channel"] = (
        await connect_to_rabbitmq()
    )

    yield
    # Close connections on shutdown
    await state["rabbitmq_connection"].close()


app = FastAPI(lifespan=lifespan)


@app.post("/query", response_model=QueryResponse)
async def submit_query(request: QueryRequest):
    job_id = str(uuid.uuid4())
    message = f"{job_id}|{request.query}"

    # Publish the message to the queue
    await state["rabbitmq_channel"].default_exchange.publish(
        aio_pika.Message(body=message.encode()),
        routing_key="rag_queries",
    )

    # Store a status key in Redis to confirm the job was queued
    state["redis_client"].set(f"status_{job_id}", "queued")

    return {"job_id": job_id, "status": "queued"}


@app.get("/result/{job_id}", response_model=ResultResponse)
async def get_result(job_id: str):
    # First, check if the job ID exists in the system at all
    status_key = f"status_{job_id}"
    job_status = state["redis_client"].get(status_key)

    if job_status is None:
        raise HTTPException(status_code=404, detail="Job ID not found.")

    # Now check if the final result is available
    result = state["redis_client"].get(job_id)
    if result:
        # The result is ready, delete the status key to free up memory
        state["redis_client"].delete(status_key)
        return {"job_id": job_id, "status": "completed", "result": result.decode()}
    else:
        return {"job_id": job_id, "status": "pending"}
