# 查看服务状态
docker-compose ps

# 查看资源使用情况
docker stats --no-stream

# 查看日志
echo "=== 后端日志 ==="
docker-compose logs --tail=50 backend

echo "=== Celery 日志 ==="
docker-compose logs --tail=50 celery-worker

echo "=== 数据库日志 ==="
docker-compose logs --tail=20 postgres
