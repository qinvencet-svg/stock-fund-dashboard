# 📊 股票+基金智能分析仪表盘

AI驱动的投资决策仪表盘，支持持仓管理、实时行情、AI分析报告，手机随时查看。

## ✨ 功能

- **持仓仪表盘** - 股票/基金实时涨跌概览
- **AI智能分析** - DeepSeek大模型生成买卖建议
- **动态管理** - 随时添加/删除持仓，无需改代码
- **手机适配** - 响应式设计，移动端优先
- **数据缓存** - 分析结果缓存24小时，节省API调用

## 🚀 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
cd backend
python main.py

# 3. 打开浏览器访问
# http://localhost:8000
```

## 🌐 Railway 部署

### 方式一：一键部署

1. 点击 [Railway](https://railway.app) 登录
2. New Project → Deploy from GitHub repo
3. 选择本仓库
4. 在 Variables 中添加环境变量（见下方）
5. 等待部署完成，自动分配域名

### 方式二：CLI 部署

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 设置环境变量
railway variables set OPENAI_API_KEY=sk-xxx
railway variables set OPENAI_BASE_URL=https://api.deepseek.com/v1

# 部署
railway up
```

## ⚙️ 环境变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `OPENAI_API_KEY` | DeepSeek API Key | ✅ |
| `OPENAI_BASE_URL` | API 地址 | ❌ (默认 DeepSeek) |
| `OPENAI_MODEL` | 模型名称 | ❌ (默认 deepseek-chat) |
| `CACHE_HOURS` | 缓存时长(小时) | ❌ (默认 24) |
| `DB_PATH` | 数据库路径 | ❌ (自动) |

## 📱 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stocks` | 获取持仓股票 |
| GET | `/api/funds` | 获取持仓基金 |
| POST | `/api/stocks` | 添加股票 `{code, name}` |
| POST | `/api/funds` | 添加基金 `{code, name}` |
| DELETE | `/api/stocks/{code}` | 删除股票 |
| DELETE | `/api/funds/{code}` | 删除基金 |
| GET | `/api/analyze/stock/{code}` | 分析股票 |
| GET | `/api/analyze/fund/{code}` | 分析基金 |
| GET | `/api/dashboard` | 仪表盘数据 |

## 🛠 技术栈

- **后端**: Python FastAPI + SQLite + AkShare
- **前端**: 单HTML + Tailwind CSS + ECharts
- **AI**: DeepSeek API
- **部署**: Railway (Nixpacks)

## ⚠️ 免责声明

本工具仅供学习和参考，不构成任何投资建议。投资有风险，入市需谨慎。
