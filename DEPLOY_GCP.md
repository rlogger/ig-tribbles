# Deploying to Google Cloud Platform

Discord bots require a persistent connection, so we'll use **Google Compute Engine (GCE)** or **Cloud Run (always-on)**.

## Option 1: Google Compute Engine (Recommended)

Best for: Persistent connections, simple setup, cost-effective for single bot

### Step 1: Create a VM Instance

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Create a small VM (e2-micro is free tier eligible)
gcloud compute instances create ig-follower-bot \
    --zone=us-central1-a \
    --machine-type=e2-micro \
    --image-family=debian-11 \
    --image-project=debian-cloud \
    --boot-disk-size=10GB \
    --tags=discord-bot
```

### Step 2: SSH into the VM

```bash
gcloud compute ssh ig-follower-bot --zone=us-central1-a
```

### Step 3: Install Docker

```bash
# Update system
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Step 4: Deploy the Bot

```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/ig-discord.git
cd ig-discord

# Create .env file
echo "DISCORD_TOKEN=your_token_here" > .env

# Start the bot
docker-compose up -d

# View logs
docker-compose logs -f
```

### Step 5: Set Up Auto-Restart on Reboot

```bash
# Enable Docker to start on boot
sudo systemctl enable docker

# The docker-compose 'restart: unless-stopped' handles container restarts
```

---

## Option 2: Cloud Run (Always-On)

Best for: Managed infrastructure, auto-scaling (though not needed for bots)

> Note: Cloud Run charges for always-on instances. GCE is usually cheaper for Discord bots.

### Step 1: Build and Push to Container Registry

```bash
# Configure Docker for GCP
gcloud auth configure-docker

# Build and tag
docker build -t gcr.io/YOUR_PROJECT_ID/ig-follower-bot .

# Push to Container Registry
docker push gcr.io/YOUR_PROJECT_ID/ig-follower-bot
```

### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy ig-follower-bot \
    --image gcr.io/YOUR_PROJECT_ID/ig-follower-bot \
    --platform managed \
    --region us-central1 \
    --no-allow-unauthenticated \
    --min-instances 1 \
    --max-instances 1 \
    --cpu-always-allocated \
    --set-env-vars "DISCORD_TOKEN=your_token_here"
```

---

## Option 3: Google Kubernetes Engine (GKE)

Best for: Multiple bots, complex deployments

### kubernetes.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ig-follower-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ig-follower-bot
  template:
    metadata:
      labels:
        app: ig-follower-bot
    spec:
      containers:
      - name: bot
        image: gcr.io/YOUR_PROJECT_ID/ig-follower-bot
        env:
        - name: DISCORD_TOKEN
          valueFrom:
            secretKeyRef:
              name: discord-secrets
              key: token
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: bot-data-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: bot-data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

---

## Database Persistence

The bot uses SQLite stored at `/app/data/follower_data.db`. For production:

### Option A: Local Volume (Simple)
The `docker-compose.yml` already handles this with a named volume.

### Option B: Cloud Storage (Backup)
Add periodic backups to Cloud Storage:

```bash
# Add to crontab
0 * * * * gsutil cp /app/data/follower_data.db gs://your-bucket/backups/follower_data_$(date +\%Y\%m\%d).db
```

### Option C: Cloud SQL (Scalable)
For multiple bot instances, migrate to PostgreSQL on Cloud SQL. Requires code changes to use `asyncpg` instead of `aiosqlite`.

---

## Monitoring

### View Logs (GCE)

```bash
# SSH into VM
gcloud compute ssh ig-follower-bot --zone=us-central1-a

# View logs
cd ig-discord
docker-compose logs -f
```

### Set Up Alerts

```bash
# Create uptime check (requires HTTP endpoint, add health check to bot)
gcloud monitoring uptime-check-configs create ig-bot-health \
    --display-name="IG Bot Health" \
    --http-check-path="/health" \
    --monitored-resource-type="uptime_url"
```

---

## Cost Estimate

| Option | Monthly Cost |
|--------|--------------|
| GCE e2-micro | ~$0 (free tier) or ~$6-10 |
| Cloud Run (always-on) | ~$15-25 |
| GKE | ~$70+ (cluster overhead) |

**Recommendation**: Start with GCE e2-micro for a single Discord bot.
