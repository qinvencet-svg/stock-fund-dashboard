# 股票基金智能分析仪表盘 - 部署指南

## 📱 项目简介

一个支持手机访问的股票+基金分析决策仪表盘，功能包括：
- 📊 持仓仪表盘（涨跌统计、持仓分布）
- 🔍 随时分析（输入任意代码，AI实时分析）
- ➕ 动态管理（随时添加/删除股票和基金）
- 📈 趋势图表（ECharts可视化）

## 🚀 快速开始

### 方案A：本地运行（测试用）

```bash
# 1. 解压项目
unzip stock_fund_dashboard.zip
cd stock_fund_dashboard

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key

# 5. 启动服务
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 6. 访问
# 浏览器打开 http://localhost:8000
```

### 方案B：Railway云端部署（推荐，24小时在线）

#### 第一步：准备GitHub仓库

1. **创建GitHub仓库**
   - 打开 https://github.com/new
   - Repository name: `stock-fund-dashboard`（或你喜欢的名字）
   - 设为 **Private**（私有）
   - 点 **Create repository**

2. **推送代码到GitHub**
   ```bash
   # 在项目目录执行
   cd stock_fund_dashboard
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   
   # 替换为你的GitHub用户名和仓库名
   git remote add origin https://github.com/你的用户名/stock-fund-dashboard.git
   git push -u origin main
   ```

3. **如果push失败（需要Token）**
   - 打开 https://github.com/settings/tokens
   - Generate new token (classic)
   - Note: `dashboard`
   - Expiration: No expiration
   - 勾选 **repo** 权限
   - Generate token，复制 `ghp_xxx...`
   - push时密码填这个token

#### 第二步：部署到Railway

1. **注册Railway账号**
   - 打开 https://railway.app
   - 点击 **Login** → **Login with GitHub**
   - 授权Railway访问你的GitHub

2. **创建新项目**
   - 点击 **New Project**
   - 选择 **Deploy from GitHub repo**
   - 找到并选择 `stock-fund-dashboard`
   - 点击 **Deploy**

3. **配置环境变量**
   - 等待部署开始（约30秒）
   - 点击项目卡片进入详情
   - 切换到 **Variables** 标签
   - 添加以下变量：
   
   ```
   OPENAI_API_KEY=sk-你的DeepSeek-Key
   OPENAI_BASE_URL=https://api.deepseek.com/v1
   EMAIL_SENDER=你的邮箱@qq.com
   EMAIL_PASSWORD=你的邮箱授权码
   SMTP_SERVER=smtp.qq.com
   SMTP_PORT=465
   ```
   
   **注意**：Railway会自动生成 `PORT` 变量，不用手动设置

4. **等待部署完成**
   - 返回 **Deployments** 标签
   - 等待状态变为 **Success**（约2-3分钟）
   - 点击 **Generate Domain** 获取访问地址
   - 地址格式：`https://xxx.up.railway.app`

5. **手机访问**
   - 手机浏览器打开上面的地址
   - 添加到主屏幕（像App一样使用）

#### 第三步：验证部署

1. **测试首页**
   - 打开 https://你的域名.up.railway.app
   - 应该看到持仓仪表盘
   - 默认已预置10只股票+3只基金

2. **测试分析功能**
   - 点击"智能分析"标签
   - 输入任意股票代码（如 000001）
   - 点击"立即分析"
   - 应该看到AI生成的分析报告

3. **测试管理功能**
   - 点击股票列表的"+"按钮
   - 输入新股票代码和名称
   - 应该成功添加到持仓

## 🔧 常见问题

### Q1: Railway免费额度够用吗？
- Railway每月给 $5 免费额度
- 这个项目很小，预计每月消耗 $1-2
- 完全够用，不用担心

### Q2: 数据会丢失吗？
- SQLite数据库存储在 `/data/dashboard.db`
- Railway会持久化 `/data` 目录
- 但建议定期备份重要数据

### Q3: 如何更新代码？
```bash
# 本地修改后
git add .
git commit -m "Update feature"
git push

# Railway会自动重新部署（约1-2分钟）
```

### Q4: 如何查看日志？
- Railway项目页面 → Deployments标签
- 点击当前部署 → View Logs
- 可以看到实时运行日志

### Q5: 股票数据获取失败？
- 检查网络连接（akshare需要访问东方财富）
- 查看日志确认具体错误
- 可能是临时网络问题，稍后重试

### Q6: AI分析很慢？
- DeepSeek API响应通常需要5-15秒
- 这是正常的，耐心等待即可
- 分析结果会缓存24小时

## 📊 功能说明

### 持仓仪表盘
- 显示所有持仓股票和基金
- 实时涨跌统计
- 点击查看详情

### 智能分析
- 输入任意股票/基金代码
- AI生成完整分析报告
- 包含趋势图和技术指标

### 动态管理
- 随时添加新的股票/基金
- 删除不需要的持仓
- 修改无需重启服务

## 🔐 安全提示

1. **不要泄露API Key**
   - DeepSeek Key有额度限制
   - 不要提交到GitHub

2. **使用私有仓库**
   - GitHub仓库设为Private
   - 避免代码被公开访问

3. **定期更换Token**
   - GitHub Token建议每6个月更换
   - Railway环境变量同步更新

## 📞 技术支持

遇到问题？检查以下几点：
1. Railway日志是否有报错
2. 环境变量是否正确配置
3. API Key是否有效
4. 网络连接是否正常

---

**祝你使用愉快！** 🎉

如有问题，随时联系AI助手~
