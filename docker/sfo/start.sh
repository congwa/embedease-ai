#!/bin/sh
# 只启动当前发布目录指定的已构建镜像，不在启动阶段构建。
set -eu
cd "$(dirname "$0")"
if docker compose version >/dev/null 2>&1; then
  docker compose -p embedease_sfo --env-file .env -f compose.yml up -d --no-build
else
  docker-compose -p embedease_sfo --env-file .env -f compose.yml up -d --no-build
fi
