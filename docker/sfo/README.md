# SFO 部署

正式入口：https://embedease-ai.sub2.org。服务器为 Debian 12 / linux/amd64。本次发布按用户明确要求直接在 SFO 构建镜像，源码由服务器从 GitHub 拉取；不从开发电脑上传镜像。使用独立 SQLite、Qdrant 与 MinIO，不复制本机业务数据。

## 构建与启动

每次发布从 GitHub 的已推送提交建立独立源码目录 `/srv/embedease-ai/build/<版本>`，发布目录为 `/srv/embedease-ai/releases/<版本>`。依赖由 `uv.lock`、`pnpm-lock.yaml` 锁定，SDK、嵌入组件和 Next 应用一并编译，不再依赖未提交补丁。

```sh
# 在 SFO 上 checkout 已推送的精确提交后执行
RELEASE_VERSION=<日期-提交短哈希> ./docker/sfo/server-build.sh
# 将 compose.yml、start.sh 与记录 RELEASE_VERSION 的 .env 放入同名发布目录后启动
cd /srv/embedease-ai/releases/<版本>
./start.sh
```

只更新应用时可使用 `docker-compose -p embedease_sfo --env-file .env -f compose.yml up -d --no-build --no-deps backend frontend`，保留正在运行的 Qdrant 和 MinIO。已有存储不必重复初始化。

`server-build.sh` 依次构建前后端，限制为 2 CPU、2300 MB 内存和合计 3 GB 内存加交换空间，避免挤占现有服务。`start.sh` 只运行已有版本化镜像。存储初始化脚本可重复运行，不清空现有数据。

## 配置与持久化

- `/srv/embedease-ai/config/backend.env`：模型、数据库路径、Qdrant、MinIO、CORS 等配置，权限 600。
- `/srv/embedease-ai/config/minio.env`：独立 MinIO 凭据，权限 600。
- `/srv/embedease-ai/config/env-json/`：模型能力和默认 Agent 配置。
- `/srv/embedease-ai/data/`：SQLite、Qdrant 和 MinIO 数据。
- `/srv/embedease-ai/logs/`：应用与 Nginx 日志。
- `/srv/embedease-ai/current`：当前发布目录链接。

Compose 项目名为 `embedease_sfo`。后端 19360、前端 19361、MinIO 19362 仅监听回环地址；Qdrant 只在容器网络访问。Nginx 代理 API、SSE、WebSocket 和图片，HTTP 跳转 HTTPS。

现有默认 Agent 和经过真实调用验证的模型已登记为精简配置完成，向导状态保存在持久化数据目录。运行日志使用 `simple` 模式。

证书由已有 Certbot Cloudflare DNS 插件签发，自动续期后由已有 deploy hook 验证并重载 Nginx；DNS 凭据沿用服务器受限文件。图片 bucket 允许公开读取，写入使用服务私有凭据。

## 验收与回滚

发布记录保存源码提交、补丁及运行文件摘要、镜像 ID、平台和入口。验证健康接口、管理统计、创建会话、真实模型 SSE、消息落库、WSS、图片上传与读取，并使用真实浏览器操作聊天页和后台；重启后确认会话仍可读取。

更新前保留旧发布目录、版本化镜像、配置与数据快照。SQLite 使用在线 backup API，Qdrant/MinIO 使用各自快照或停写备份。回滚时恢复匹配的运行配置，在旧发布目录运行 `./start.sh`，验收后将 `current` 切回；涉及数据库结构变化时同时恢复匹配的数据快照。首次上线没有旧业务版本，撤销时只停止本项目、移除其 Nginx 配置并重载，不删除数据。

项目当前沿用匿名用户和现有管理接口访问机制，本部署没有新增账号或权限系统。
