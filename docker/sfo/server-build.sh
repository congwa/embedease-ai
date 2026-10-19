#!/bin/sh
# 本次发布按用户明确要求在 SFO 构建；限制资源，避免挤占已有服务。
set -eu
: "${RELEASE_VERSION:?set RELEASE_VERSION}"
cd "$(dirname "$0")/../.."
docker build --memory=2300m --memory-swap=3g --cpu-period=100000 --cpu-quota=200000 -f docker/sfo/backend.Dockerfile -t "embedease/backend:$RELEASE_VERSION" backend
docker build --memory=2300m --memory-swap=3g --cpu-period=100000 --cpu-quota=200000 -f docker/sfo/frontend.Dockerfile -t "embedease/frontend:$RELEASE_VERSION" frontend
docker image inspect "embedease/backend:$RELEASE_VERSION" "embedease/frontend:$RELEASE_VERSION" --format '{{.RepoTags}} {{.Os}}/{{.Architecture}} {{.Id}}'
