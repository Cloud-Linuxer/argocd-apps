#!/bin/bash

# vLLM 로컬 빌드 스크립트
VERSION=$(cat vllm/VERSION)
IMAGE_NAME="ghcr.io/cloud-linuxer/argocd-apps/vllm"

echo "Building vLLM image version: $VERSION"

# Docker 빌드
docker build -t "$IMAGE_NAME:$VERSION-amd64" ./vllm/
docker tag "$IMAGE_NAME:$VERSION-amd64" "$IMAGE_NAME:latest"

echo "Build completed: $IMAGE_NAME:$VERSION-amd64"

# 레지스트리 푸시 (선택사항)
read -p "Push to registry? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Logging in to GHCR..."
    echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
    
    echo "Pushing images..."
    docker push "$IMAGE_NAME:$VERSION-amd64"
    docker push "$IMAGE_NAME:latest"
    
    echo "Updating manifest..."
    sed -i "s|image: ghcr.io/.*/vllm:.*|image: $IMAGE_NAME:$VERSION-amd64|g" manifests/vllm-20b/deployment.yaml
    
    git add manifests/vllm-20b/deployment.yaml
    git commit -m "Update vllm image to $VERSION (local build)"
    git push
fi

echo "Done!"
