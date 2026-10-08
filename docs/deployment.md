# 部署指南

本指南使用通用参数。服务器地址、SSH 密钥、生产配置和发布记录保留在私有运维资料中，不放入公开仓库。

## 首次部署

1. 安装 Docker 与 Docker Compose v2。
2. 复制根目录 `.env.example` 为 `.env`，设置数据库密码、JWT 密钥、两个管理员密码、访问来源和前端端口。
3. 如需 Word 报告，补齐 `backend/app/templates/README.md` 中的已授权模板。
4. 使用固定项目名启动：

```bash
docker compose -p ailitewms up --build -d
curl -fsS http://127.0.0.1:8080/api/health
```

外部流量由 Nginx 处理，`/api` 转发到后端。数据库和后端不直接发布端口。正式部署由维护者配置域名、HTTPS 和对应 `CORS_ORIGINS`。

## 预构建镜像发布

资源有限的服务器只加载镜像并启动，在开发机或构建机完成编译。以下命令从根目录执行，发布号每次更新，平台与目标服务器一致：

```bash
RELEASE_ID=20261008-example
npm --prefix frontend ci
npm --prefix frontend run build
docker buildx build --platform linux/amd64 --load \
  -t "ailitewms-backend:$RELEASE_ID" backend
docker buildx build --platform linux/amd64 --load \
  -f frontend/Dockerfile.deploy -t "ailitewms-frontend:$RELEASE_ID" frontend
docker save "ailitewms-backend:$RELEASE_ID" "ailitewms-frontend:$RELEASE_ID" \
  -o "ailitewms-images-$RELEASE_ID.tar"
```

上传镜像包和源码到独立发布目录。切换前备份数据库、检查可读性，并留存异地或本机副本。在服务器发布目录执行：

```bash
export RELEASE_ID=20261008-example
docker load -i "ailitewms-images-$RELEASE_ID.tar"
docker compose -f docker-compose.yml -f docker-compose.deploy.yml \
  -p ailitewms --env-file /absolute/path/to/production.env up -d --no-build
```

替换示例配置路径，并沿用已有 Compose 项目名。不要先执行 `down`，更不能使用 `down -v` 删除正式数据卷。

## 数据库备份

在正确的 Compose 目录和配置上下文中执行：

```bash
umask 077
docker compose -p ailitewms exec -T database \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > before-release.dump
test -s before-release.dump
docker compose -p ailitewms exec -T database pg_restore -l < before-release.dump
```

不要覆盖上一份尚未确认可用的备份。比较上传／下载副本的 SHA-256，按实际私有环境的保留策略清理。结构变更还需要验证迁移和恢复方案。

## 验证与回滚

- 检查容器、数据库健康、首页、`/api/health` 和本次变更的只读接口。
- 浏览器刷新后确认加载的新资源与构建包一致。
- 检查通过后才更新当前版本标记或发布软链接。
- 回滚使用上一版本镜像和配置重新 `up -d --no-build`，继续使用原数据卷。
- 包含不可逆数据迁移时，应用回滚不等于数据库恢复，需另行确认停写与恢复方案。

用户和库存数据不得用于公开截图、示例库或有写操作的线上回归测试。
