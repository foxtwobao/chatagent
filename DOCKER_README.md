# Docker 部署指南

本文档提供了智能对话助手应用的Docker容器化部署完整指南。

## 📋 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [部署方式](#部署方式)
- [常见问题](#常见问题)
- [维护和监控](#维护和监控)

## 🔧 系统要求

### 硬件要求
- **CPU**: 1核心以上
- **内存**: 512MB以上
- **存储**: 1GB可用空间

### 软件要求
- **Docker**: 20.10.0+
- **Docker Compose**: 1.29.0+
- **操作系统**: Linux/Windows/macOS

## 🚀 快速开始

### 方式一：使用 Docker Compose（推荐）

1. **克隆项目**
```bash
git clone <repository-url>
cd chatagent
```

2. **配置API密钥**
编辑 `config.py` 文件，填入您的API配置：
```python
# 火山引擎API配置
VOLCANO_ACCESS_KEY = "your-volcano-access-key"

# 语音合成配置
VOICE_APP_ID = "your-voice-app-id"
VOICE_ACCESS_TOKEN = "your-voice-access-token"

# 飞书Aily配置（可选）
FEISHU_APP_ID = "your-feishu-app-id"
FEISHU_APP_SECRET = "your-feishu-app-secret"
```

3. **启动应用**
```bash
docker-compose up -d
```

4. **访问应用**
打开浏览器访问: http://localhost:8001

### 方式二：使用 Docker 命令

1. **构建镜像**
```bash
docker build -t chatagent:latest .
```

2. **运行容器**
```bash
docker run -d \
  --name chatagent-app \
  -p 8001:8001 \
  -v $(pwd)/config.py:/app/config.py:ro \
  -v $(pwd)/resources:/app/resources:ro \
  --restart unless-stopped \
  chatagent:latest
```

## ⚙️ 详细配置

### 环境变量配置

可以通过环境变量覆盖默认配置：

```bash
# Docker Compose 方式
docker-compose up -d \
  -e FLASK_ENV=production \
  -e PYTHONUNBUFFERED=1

# Docker 命令方式
docker run -d \
  --name chatagent-app \
  -p 8001:8001 \
  -e FLASK_ENV=production \
  -e PYTHONUNBUFFERED=1 \
  chatagent:latest
```

### 端口配置

默认端口为8001，可以通过以下方式修改：

```bash
# 映射到其他端口（如8080）
docker run -p 8080:8001 chatagent:latest

# Docker Compose 修改 docker-compose.yml
ports:
  - "8080:8001"
```

### 数据持久化

如需持久化数据，可以挂载数据卷：

```yaml
# docker-compose.yml 添加
volumes:
  - ./data:/app/data
  - ./logs:/app/logs
```

## 🏗️ 部署方式

### 开发环境部署

```bash
# 使用开发模式
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 生产环境部署

```bash
# 生产环境配置
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 集群部署

```bash
# 使用 Docker Swarm
docker stack deploy -c docker-compose.yml chatagent-stack
```

## 🔍 监控和日志

### 查看容器状态
```bash
# 查看运行状态
docker-compose ps

# 查看容器详情
docker inspect chatagent-app
```

### 查看日志
```bash
# 实时查看日志
docker-compose logs -f chatagent

# 查看最近100行日志
docker-compose logs --tail=100 chatagent
```

### 健康检查
```bash
# 检查应用健康状态
curl http://localhost:8001/api/health

# 查看健康检查状态
docker inspect --format='{{.State.Health.Status}}' chatagent-app
```

## 🛠️ 维护操作

### 更新应用
```bash
# 停止服务
docker-compose down

# 重新构建镜像
docker-compose build --no-cache

# 启动服务
docker-compose up -d
```

### 备份和恢复
```bash
# 备份配置文件
cp config.py config.py.backup

# 备份容器数据
docker run --rm -v chatagent_data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz /data
```

### 清理资源
```bash
# 停止并删除容器
docker-compose down

# 清理未使用的镜像
docker image prune -f

# 清理未使用的卷
docker volume prune -f
```

## ❓ 常见问题

### Q1: 容器启动失败
**A**: 检查端口是否被占用，查看日志排查问题
```bash
docker-compose logs chatagent
```

### Q2: API调用失败
**A**: 确认config.py中的API密钥配置正确
```bash
# 进入容器检查配置
docker exec -it chatagent-app cat /app/config.py
```

### Q3: 内存不足
**A**: 增加Docker内存限制
```yaml
# docker-compose.yml 添加
deploy:
  resources:
    limits:
      memory: 1G
```

### Q4: 网络连接问题
**A**: 检查防火墙和网络配置
```bash
# 测试网络连通性
docker exec -it chatagent-app curl -I https://ark.cn-beijing.volces.com
```

## 🔒 安全建议

1. **API密钥安全**
   - 不要在代码中硬编码API密钥
   - 使用环境变量或密钥管理服务

2. **网络安全**
   - 使用HTTPS代理
   - 配置防火墙规则

3. **容器安全**
   - 定期更新基础镜像
   - 使用非root用户运行

## 📞 技术支持

如遇到问题，请：
1. 查看应用日志
2. 检查Docker状态
3. 确认配置文件
4. 联系技术支持

---

**版本**: 1.0.0  
**更新时间**: 2024年12月  
**维护者**: 开发团队