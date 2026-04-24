#!/bin/bash

# Configuration
PROJECT_ID="your-gcp-project-id"
REGION="us-central1"
REPO_NAME="mentor-mentee-repo"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"

# 1. Authenticate with GCP
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 2. Build and Push Backend Services
SERVICES=("user-service" "ai-recommendation-service" "gamification-service" "notification-service")

for SERVICE_DIR in "${SERVICES[@]}"; do
    echo "Processing $SERVICE_DIR..."
    
    # Map directory name to image name if they differ
    IMAGE_NAME=$SERVICE_DIR
    if [ "$SERVICE_DIR" == "ai-recommendation-service" ]; then IMAGE_NAME="ai-service"; fi
    
    TAG="${REGISTRY}/${IMAGE_NAME}:latest"
    
    docker build -t $TAG ./$SERVICE_DIR
    docker push $TAG
done

# 3. Build and Push Mentoring Service (nested directory)
echo "Processing mentoring-service..."
docker build -t ${REGISTRY}/mentoring-service:latest ./mentor-mentee-module/backend
docker push ${REGISTRY}/mentoring-service:latest

echo "Done! All images pushed to Artifact Registry."
