#!/bin/bash
# 버전 동기화 스크립트

if [ "$1" = "sync" ]; then
    # 루트 VERSION을 각 서비스로 복사
    ROOT_VERSION=$(cat VERSION)
    echo $ROOT_VERSION > backend/VERSION
    echo $ROOT_VERSION > frontend/VERSION
    echo $ROOT_VERSION > vllm/VERSION
    echo "Synced all versions to $ROOT_VERSION"
elif [ "$1" = "check" ]; then
    # 버전 차이 확인
    echo "Root: $(cat VERSION)"
    echo "Backend: $(cat backend/VERSION)"
    echo "Frontend: $(cat frontend/VERSION)"
    echo "VLLM: $(cat vllm/VERSION)"
fi
