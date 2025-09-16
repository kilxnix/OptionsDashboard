#!/bin/bash
# COMPLETE DOCKER SETUP FOR OPTIONS SCANNER PRO
# Save this file, run it, and it will create ALL necessary files

cat > docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  # Backend API Service
  api:
    build: .
    image: optionsscanner/app:latest
    container_name: optionsscanner-api
    env_file: .env
    environment:
      - SERVICE_TYPE=backend
      - PORT=5001
    command: gunicorn -w 2 -b 0.0.0.0:5001 main:app
    volumes:
      - ./TradingPlans:/app/TradingPlans
      - ./output:/app/output
      - ./logs:/app/logs
    ports:
      - "5001:5001"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Frontend Service
  frontend:
    build: .
    image: optionsscanner/app:latest
    container_name: optionsscanner-frontend
    env_file: .env
    environment:
      - SERVICE_TYPE=frontend
      - PORT=5000
      - BACKEND_URL=http://api:5001
    command: gunicorn -w 2 -b 0.0.0.0:5000 simple_frontend:frontend_app
    depends_on:
      - api
    ports:
      - "80:5000"
    restart: unless-stopped

networks:
  default:
    name: optionsscanner-network
COMPOSE_EOF

cat > Dockerfile << 'DOCKER_EOF'
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/logs /app/output /app/TradingPlans && \
    chown -R appuser:appuser /app

WORKDIR /app

COPY --chown=appuser:appuser requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

COPY --chown=appuser:appuser . /app/

USER appuser
EXPOSE 5000 5001

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5001", "main:app"]
DOCKER_EOF

cat > requirements.txt << 'REQ_EOF'
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-CORS==4.0.0
Flask-Migrate==4.0.5
psycopg2-binary==2.9.7
SQLAlchemy==2.0.20
bcrypt==4.0.1
PyJWT==2.8.0
python-dotenv==1.0.0
requests==2.31.0
gunicorn==21.2.0
pandas==2.0.3
numpy==1.24.3
scipy==1.11.2
yfinance==0.2.28
stripe==5.5.0
python-dateutil==2.8.2
pytz==2023.3
REQ_EOF

cat > .env << 'ENV_EOF'
# EDIT THIS FILE WITH YOUR ACTUAL VALUES!
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres

FLASK_ENV=production
FLASK_DEBUG=False
FLASK_SECRET_KEY=CHANGE_THIS_TO_RANDOM_SECRET_KEY
JWT_SECRET_KEY=CHANGE_THIS_TO_ANOTHER_RANDOM_KEY

BACKEND_URL=http://api:5001

STRIPE_SECRET_KEY=sk_live_your_key_here
STRIPE_PUBLISHABLE_KEY=pk_live_your_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_secret_here

SENDGRID_API_KEY=optional_email_key
ENV_EOF

cat > health_endpoint.py << 'HEALTH_EOF'
# ADD THIS TO YOUR main.py FILE

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker"""
    try:
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return jsonify({
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "optionsscanner-api",
        "database": db_status
    }), 200 if db_status == "healthy" else 503

@app.route("/health", methods=["GET"])
def simple_health():
    """Simple health check"""
    return "OK", 200
HEALTH_EOF

# Generate random secrets for .env
FLASK_SECRET=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)

# Update .env with generated secrets
sed -i "s/CHANGE_THIS_TO_RANDOM_SECRET_KEY/$FLASK_SECRET/" .env
sed -i "s/CHANGE_THIS_TO_ANOTHER_RANDOM_KEY/$JWT_SECRET/" .env

echo "========================================="
echo "       ALL FILES CREATED!"
echo "========================================="
echo ""
echo "Files created:"
echo "  ✓ docker-compose.yml"
echo "  ✓ Dockerfile"
echo "  ✓ requirements.txt"
echo "  ✓ .env (with generated secrets)"
echo "  ✓ health_endpoint.py (add to main.py)"
echo ""
echo "NEXT STEPS:"
echo "1. Edit .env and add your Supabase DATABASE_URL"
echo "2. Add the health endpoint code to your main.py"
echo "3. Run: docker-compose build"
echo "4. Run: docker-compose up -d"
echo ""
echo "Your app will be available at:"
echo "  Frontend: http://YOUR_VPS_IP"
echo "  API: http://YOUR_VPS_IP:5001"