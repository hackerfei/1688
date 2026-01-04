# 1688 Quote System - Docker 配置
# 使用 Playwright 官方镜像，已包含所有浏览器依赖

FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# 复制项目文件
COPY requirements.txt .
COPY server.py .
COPY static/ ./static/

# 创建上传目录
RUN mkdir -p uploads

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# Railway 使用 PORT 环境变量
ENV PORT=8080

# 暴露端口
EXPOSE 8080

# 启动服务
CMD ["python", "server.py"]
