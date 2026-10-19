# 按本次 SFO 发布授权在服务器构建；运行镜像不包含包管理器构建步骤。
FROM node:22.14.0-bookworm-slim AS build
RUN corepack enable && corepack prepare pnpm@10.28.2 --activate
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/chat-sdk/package.json ./packages/chat-sdk/package.json
COPY packages/chat-sdk-react/package.json ./packages/chat-sdk-react/package.json
ENV NEXT_TELEMETRY_DISABLED=1 API_PROXY_TARGET=http://backend:8000 NEXT_PUBLIC_WS_URL=""
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build:packages && pnpm build:embed && pnpm build
FROM node:22.14.0-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000 API_PROXY_TARGET=http://backend:8000
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
COPY --from=build /app/dist/embed ./public/embed
EXPOSE 3000
CMD ["node", "server.js"]
