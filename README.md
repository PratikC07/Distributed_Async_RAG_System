# Distributed Async RAG System

A distributed, asynchronous RAG (Retrieval-Augmented Generation) system using Docker Compose.

## 📥 Getting Started

### Clone the Repository

```bash
git clone https://github.com/your-username/Distributed_Async_RAG.git
cd Distributed_Async_RAG
```

### Prerequisites

- Docker and Docker Compose
- Google Gemini API key

## 🚀 Quick Start

### Setup

1. **Create a `.env` file in the project root:**

   ```bash
   touch .env
   ```

2. **Add your Gemini API key to the `.env` file:**

   ```bash
   echo "GEMINI_API_KEY=your_gemini_api_key_here" >> .env
   ```

   Or manually edit the `.env` file and add:

   ```
   GEMINI_API_KEY=your_actual_gemini_api_key
   ```

   > **⚠️ Important:** Replace `your_actual_gemini_api_key` with your actual Google Gemini API key. You can get one from [Google AI Studio](https://makersuite.google.com/app/apikey).

3. **First time setup (includes data ingestion):**

   ```bash
   docker compose --profile full up --build
   ```

4. **Subsequent runs (smart - skips ingestion if data exists):**

   ```bash
   docker compose up --build
   ```

5. **Force re-ingestion when needed:**

   ```bash
   export FORCE_REINGEST=true
   docker compose --profile full up --build
   ```

6. **Watch the logs to see progress:**
   ```bash
   # In another terminal, watch ingest progress
   docker compose logs -f ingest
   ```

### Usage

Once the system is running:

1. **Submit a query:**

   ```bash
   curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is Node.js?"}'
   ```

2. **Get the result:**
   ```bash
   curl "http://localhost:8000/result/{job_id}"
   ```

## 🏗️ Architecture

- **API Service** (port 8000): REST API for submitting queries
- **Worker Service**: Processes queries asynchronously
- **Ingest Service**: One-time data ingestion into vector database
- **Qdrant** (port 6333): Vector database
- **Redis** (port 6379): Result caching
- **RabbitMQ** (ports 5672, 15672): Message queue
- **RedisInsight** (port 8001): Redis monitoring

## 📊 Service UIs & Monitoring

Once the system is running, you can access various service dashboards:

### RabbitMQ Management UI

- **URL**: http://localhost:15672
- **Credentials**:
  - Username: `guest`
  - Password: `guest`
- **Features**: Monitor message queues, exchanges, connections, and system performance

### Qdrant Vector Database Dashboard

- **URL**: http://localhost:6333/dashboard
- **Features**:
  - Browse collections and points
  - View vector database statistics
  - Monitor search performance
  - Explore stored embeddings

### RedisInsight

- **URL**: http://localhost:8001
- **Features**:
  - Visualize Redis data structures
  - Monitor cache performance
  - View stored query results
  - Real-time Redis metrics

> **💡 Tip:** Keep these dashboards open in separate browser tabs to monitor your RAG system's performance in real-time!

## 🔧 Troubleshooting

### Missing API Key

If you see "GEMINI_API_KEY is not set", make sure your `.env` file contains the API key:

1. **Check your `.env` file exists:**

   ```bash
   ls -la .env
   ```

2. **Verify the content:**

   ```bash
   cat .env
   ```

   Should show: `GEMINI_API_KEY=your_actual_key`

3. **Restart the services:**
   ```bash
   docker compose down
   docker compose up --build
   ```

### Quota Exceeded

If you hit API limits, the ingest service will automatically retry with exponential backoff.

### View Logs

```bash
# View all services
docker compose logs

# View specific service
docker compose logs ingest
docker compose logs worker
docker compose logs api
```

## 🚀 Deployment & Contributing

### Environment Variables

The system uses the following environment variables (configured in `.env`):

- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `FORCE_REINGEST`: Set to `true` to force data re-ingestion (optional)

### Production Deployment

For production deployment, consider:

1. **Securing API endpoints**
2. **Using environment-specific `.env` files**
3. **Setting up proper monitoring and logging**
4. **Configuring persistent volumes for data**

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test locally using the setup instructions above
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Create a Pull Request
