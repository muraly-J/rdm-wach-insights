# Deployment Guide: WACH Insight

## Security Requirements for Production

### Environment Variables (REQUIRED)

Before deploying, ensure the following environment variables are set in your `.env` file:

```bash
# InfluxDB Configuration (HTTPS required for production)
INFLUX_URL=https://your-influxdb-host.cloud.influxdata.com
INFLUX_TOKEN=secure-api-token-with-read-access

# API Authentication (REQUIRED for all /api endpoints)
API_KEY=generate-a-long-random-string-here

# Optional: Developer API key for local testing
DEV_API_KEY=dev-key-change-in-production
```

### Generating Secure API Keys

```bash
# Generate a secure random string for API_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Or use OpenSSL
openssl rand -base64 64 | tr -d '\n'
```

## Architecture

### Local Development (Recommended)
```
Frontend (localhost:3000) --> Backend API (localhost:8081) --> InfluxDB Cloud
```
- Run backend locally with `./start.sh`
- Run frontend with `npm run dev`
- Best for development and testing

### Production Deployment
For production, deploy the backend to a server and configure CORS:
1. Set `CORS_ORIGIN` environment variable to your domain
2. Ensure InfluxDB credentials are set
3. Deploy frontend to your hosting provider

## Local Development Setup

### 1. Run Backend
```bash
cd /Users/rdmasia/wach-insight
./start.sh
```

The backend will start on port 8081.

### 2. Run Frontend
```bash
cd frontend
npm run dev
```

The frontend will start on port 3000.

### 3. Open Browser
Visit http://localhost:3000

## Environment Variables

Create a `.env` file in the project root with:

```bash
# InfluxDB Configuration (HTTPS required for production)
INFLUX_URL=https://us-east-1-1.aws.cloud.influxdata.com
INFLUX_TOKEN=your-influx-token-here
INFLUX_ORG=wach
INFLUX_BUCKET=wach_bucket_3

# API Authentication (REQUIRED for /api endpoints)
API_KEY=your-api-key-here
```

Optional:
```bash
# Developer API key for local testing without authentication
DEV_API_KEY=dev-key-change-in-production

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://your-production-domain.com

# Rate Limiting (default: 20 requests per minute)
RATE_LIMIT_REQUESTS=20
RATE_LIMIT_WINDOW=60

# LLM Configuration (optional)
ENABLE_LLM=true
LMS_BASE_URL=http://localhost:1234/v1
LMS_API_KEY=lm-studio
```

## Build for Production

```bash
cd frontend
npm install
npm run build
```

Output: `frontend/dist/`

To serve the built frontend:

```bash
# Using Python's built-in server
cd frontend/dist
python3 -m http.server 8080

# Or use any static file server
```

## Troubleshooting

### "Could not reach InfluxDB"
1. Check `INFLUX_URL`, `INFLUX_TOKEN` are set
2. Verify your InfluxDB token has read access
3. Check `INFLUX_BUCKET` matches your bucket name

### "CORS error" in browser
Set `CORS_ORIGIN` to your domain (default is http://localhost:3000)

### "Model file not found"
Ensure `paraquet_data/models/saved/*.pkl` files exist in the project.
