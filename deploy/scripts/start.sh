# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend

echo "✅ 服务已启动!"
echo "📝 前端: http://localhost:3000"
echo "🔧 后端 API: http://localhost:8000"
echo "📊 API 文档: http://localhost:8000/docs"
echo "🌸 Celery 监控: http://localhost:5555"
echo "💾 MinIO 控制台: http://localhost:9001"
