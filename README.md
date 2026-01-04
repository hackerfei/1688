# 1688 智能报价系统

基于图片搜索的1688批发价格查询和报价工具，帮助跨境卖家快速获取产品信息。

## 功能特点

- 📷 **图片搜索**：上传产品图片，自动搜索1688相似商品
- 💰 **价格提取**：获取批发价格和USD报价
- ⚖️ **重量提取**：从详情页表格自动提取产品重量
- 🏭 **供应商信息**：显示厂家名称、回购率、销量
- 📦 **运费信息**：识别包邮和条件包邮
- 💵 **利润计算**：自动计算建议售价和利润率

## 系统要求

- Python 3.8+
- Playwright

## 安装

```bash
# 1. 安装依赖
pip install playwright

# 2. 安装浏览器
playwright install chromium
```

## 使用方法

```bash
# 启动服务器
python server.py

# 访问
http://localhost:8080
```

## 项目结构

```
1688/
├── server.py          # 主服务器（Python + Playwright）
├── static/
│   ├── index.html     # 前端页面
│   ├── style.css      # 样式文件
│   └── app.js         # 前端逻辑
├── uploads/           # 上传图片临时目录
└── README.md          # 说明文档
```

## API接口

### POST /api/search

上传图片搜索商品

**请求**：
```
Content-Type: multipart/form-data
Field: image (文件)
```

**响应**：
```json
{
  "success": true,
  "products": [
    {
      "title": "商品标题",
      "price": "49",
      "weight": "500",
      "shipping": "包邮",
      "repurchase_rate": "58%",
      "sold": "1200件",
      "supplier": "厂家名称",
      "image_url": "图片URL",
      "product_url": "详情页URL"
    }
  ],
  "search_url": "1688搜索结果URL"
}
```

## 数据提取说明

| 字段 | 来源 | 提取率 |
|------|------|--------|
| 价格 | 搜索结果页 | ~100% |
| 重量 | 详情页包装表格 | ~60-80% |
| 回购率 | 搜索结果页 | ~100% |
| 销量 | 搜索结果页 | ~80% |
| 运费 | 详情页 | ~30-50% |
| 供应商 | 详情页 | ~100% |

## 已知限制

1. **登录限制**：部分商品需要登录才能查看完整SKU和精确运费
2. **验证码**：直接访问详情页可能触发滑块验证
3. **访问频率**：频繁访问可能被临时限制

## 技术栈

- **后端**：Python + SimpleHTTPServer
- **浏览器自动化**：Playwright
- **前端**：原生HTML/CSS/JavaScript

## 更新日志

### v1.0.0 (2024-12)
- 基于Playwright实现图片搜索
- 支持提取价格、重量、回购率、销量、供应商
- 自动计算USD报价和利润率
- 识别包邮和条件包邮
- 简洁的列表式UI界面

## 部署指南

### ⚠️ 重要：本项目不适合 Vercel

由于使用了 Playwright 浏览器自动化，本项目**不能**部署到 Vercel 等 Serverless 平台。

### 推荐部署方式

#### 方式一：Railway（推荐）

1. 访问 [railway.app](https://railway.app) 并登录
2. 点击 "New Project" → "Deploy from GitHub repo"
3. 选择你的仓库
4. Railway 会自动检测 Dockerfile 并部署
5. 设置端口环境变量：`PORT=8080`

#### 方式二：Render

1. 访问 [render.com](https://render.com) 并登录
2. 创建 "New Web Service"
3. 连接 GitHub 仓库
4. 选择 Docker 环境
5. 设置端口 8080

#### 方式三：本地 / VPS

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/1688.git
cd 1688

# 2. 安装依赖
pip install playwright
playwright install chromium

# 3. 启动服务
python server.py

# 4. 访问 http://localhost:8080
```

### 为什么不能用 Vercel？

| 需求 | Vercel 支持 | 本项目需要 |
|------|-------------|------------|
| 持续运行服务器 | ❌ | ✅ HTTPServer |
| Playwright/浏览器 | ❌ | ✅ Chromium |
| 文件系统写入 | ❌ | ✅ 上传图片 |
| 长时间执行(>10秒) | ❌ | ✅ 30-60秒 |

## License

MIT
