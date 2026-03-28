# 每日股票分析工具

基于 GitHub Actions + Tushare + 通义千问 + 飞书的零成本自动股票分析系统。

## 功能特点

- 📊 自动获取股票行情数据（Tushare）
- 🤖 AI 智能分析（通义千问）
- 📱 飞书推送报告
- ⏰ 定时运行（盘前 8:00 + 盘后 20:00）
- 💰 零成本部署（GitHub Actions 免费额度）

## 快速开始

### 1. Fork 本仓库

点击右上角 **Fork** 按钮，将仓库复制到你的 GitHub 账号。

### 2. 配置 Secrets

进入仓库 **Settings** → **Secrets and variables** → **Actions** → **New repository secret**，添加以下 Secrets：

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `TUSHARE_TOKEN` | Tushare Token | `73052992ec7d...` |
| `LLM_API_KEY` | 通义千问 API Key | `sk-e266b97c...` |
| `FEISHU_WEBHOOK` | 飞书机器人 Webhook | `https://open.feishu.cn/...` |
| `STOCK_POOL` | 股票代码（逗号分隔） | `002821,600519` |

### 3. 启用 GitHub Actions

进入仓库 **Actions** 页面，点击 **Enable workflow** 启用工作流。

### 4. 手动测试

在 Actions 页面点击 **Run workflow** 手动触发测试，检查飞书是否收到报告。

## 定时规则

- **盘前分析**：每个交易日早上 8:00（北京时间）
- **盘后复盘**：每个交易日晚上 20:00（北京时间）

## 自定义配置

### 修改股票池

在 Secrets 中更新 `STOCK_POOL`，例如：`002821,600519,000001`

### 修改推送时间

编辑 `.github/workflows/daily-analysis.yml` 中的 cron 表达式：

```yaml
on:
  schedule:
    # UTC 时间 = 北京时间 - 8 小时
    - cron: '0 0 * * 1-5'   # 北京时间 8:00
    - cron: '0 12 * * 1-5'  # 北京时间 20:00
```

### 修改 AI 模型

在 `main.py` 中修改模型名称：

```python
response = client.chat.completions.create(
    model="qwen-turbo",  # 可选: qwen-turbo, qwen-plus, qwen-max
    ...
)
```

## 报告示例

📊 **【每日股票盘后复盘】凯莱英(002821)**

**股票**: 凯莱英 (002821) | 医药制造

**最新行情**:
• 收盘价: **150.50** 元
• 涨跌幅: **+2.35%**
• 成交量: 5.23 万手
• 最高/最低: 152.00 / 148.20 元

**技术指标**:
• MA5/MA10/MA20: 149.50 / 148.00 / 145.30
• MACD: 0.5234

**AI 分析**:
技术面显示该股近期呈现上涨趋势，MACD 金叉形成，短期有望继续上行...

⚠️ 本报告由 AI 生成，仅供参考，不构成投资建议。股市有风险，投资需谨慎。

## 注意事项

1. **API 额度**：免费版 Tushare 和通义千问有每日请求限制，建议股票池控制在 10 只以内
2. **节假日**：A 股节假日期间仍会触发，但可能无数据更新
3. **风险提示**：AI 分析仅供参考，不构成投资建议

## 技术栈

- Python 3.10
- Tushare（股票数据）
- 通义千问（AI 分析）
- 飞书机器人（消息推送）
- GitHub Actions（定时任务）

## License

MIT
