#!/usr/bin/env python3
"""
每日股票分析工具
使用 Tushare 获取数据，通义千问生成分析报告，飞书推送
"""

import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak
from openai import OpenAI

# 配置信息
LLM_API_KEY = os.environ.get('LLM_API_KEY')
FEISHU_WEBHOOK = os.environ.get('FEISHU_WEBHOOK')
STOCK_POOL = os.environ.get('STOCK_POOL', '002821')

# 初始化通义千问客户端
client = OpenAI(
    api_key=LLM_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


def get_stock_basic_info(stock_code):
    """获取股票基本信息"""
    try:
        df = ak.stock_individual_info_em(symbol=stock_code)
        if df is not None and not df.empty:
            info = {}
            for _, row in df.iterrows():
                info[row['item']] = row['value']
            return {
                'ts_code': stock_code,
                'name': info.get('股票简称', ''),
                'industry': info.get('所属行业', ''),
                'area': info.get('所属地域', '')
            }
        return None
    except Exception as e:
        print(f"获取股票基本信息失败 {stock_code}: {e}")
        return None


def get_daily_data(stock_code):
    """获取日线数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=(datetime.now() - timedelta(days=60)).strftime('%Y%m%d'),
                                end_date=datetime.now().strftime('%Y%m%d'), adjust="qfq")
        if df is not None and not df.empty:
            # 重命名列以兼容原有代码
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'vol',
                '涨跌幅': 'pct_chg'
            })
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
            return df
        return None
    except Exception as e:
        print(f"获取日线数据失败 {stock_code}: {e}")
        return None


def get_index_data():
    """获取大盘指数数据"""
    try:
        # 上证指数
        sh_df = ak.index_zh_a_hist(symbol="000001", period="daily")
        # 深证成指
        sz_df = ak.index_zh_a_hist(symbol="399001", period="daily")
        # 创业板指
        cy_df = ak.index_zh_a_hist(symbol="399006", period="daily")
        
        def get_latest(df):
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    'close': latest['收盘'],
                    'pct_chg': latest['涨跌幅']
                }
            return None
        
        return {
            'sh': get_latest(sh_df),
            'sz': get_latest(sz_df),
            'cy': get_latest(cy_df)
        }
    except Exception as e:
        print(f"获取指数数据失败: {e}")
        return None


def calculate_technical_indicators(df):
    """计算技术指标"""
    if df is None or df.empty:
        return {}
    
    df = df.sort_values('trade_date')
    
    # 计算均线
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma10'] = df['close'].rolling(window=10).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    
    # 计算 MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['histogram'] = df['macd'] - df['signal']
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    return {
        'close': round(latest['close'], 2),
        'open': round(latest['open'], 2),
        'high': round(latest['high'], 2),
        'low': round(latest['low'], 2),
        'vol': round(latest['vol'] / 10000, 2),  # 万手
        'pct_chg': round(latest['pct_chg'], 2),
        'ma5': round(latest['ma5'], 2),
        'ma10': round(latest['ma10'], 2),
        'ma20': round(latest['ma20'], 2),
        'macd': round(latest['macd'], 4),
        'signal': round(latest['signal'], 4),
        'histogram': round(latest['histogram'], 4),
        'trend': '上涨' if latest['close'] > prev['close'] else '下跌'
    }


def generate_analysis_prompt(stock_info, tech_data, index_data, is_pre_market=True):
    """生成 AI 分析提示词"""
    
    market_type = "盘前分析" if is_pre_market else "盘后复盘"
    current_time = datetime.now().strftime('%Y年%m月%d日')
    
    index_info = ""
    if index_data:
        if index_data['sh']:
            sh = index_data['sh']
            index_info += f"上证指数: {sh['close']} ({sh['pct_chg']:.2f}%)\n"
        if index_data['sz']:
            sz = index_data['sz']
            index_info += f"深证成指: {sz['close']} ({sz['pct_chg']:.2f}%)\n"
        if index_data['cy']:
            cy = index_data['cy']
            index_info += f"创业板指: {cy['close']} ({cy['pct_chg']:.2f}%)\n"
    
    prompt = f"""你是一位专业的股票分析师，请为以下股票生成{market_type}报告。

**分析日期**: {current_time}

**股票信息**:
- 股票代码: {stock_info['ts_code']}
- 股票名称: {stock_info['name']}
- 所属行业: {stock_info.get('industry', '未知')}
- 所属地区: {stock_info.get('area', '未知')}

**最新行情数据**:
- 收盘价: {tech_data['close']} 元
- 开盘价: {tech_data['open']} 元
- 最高价: {tech_data['high']} 元
- 最低价: {tech_data['low']} 元
- 成交量: {tech_data['vol']} 万手
- 涨跌幅: {tech_data['pct_chg']}%
- 趋势: {tech_data['trend']}

**技术指标**:
- MA5: {tech_data['ma5']} 元
- MA10: {tech_data['ma10']} 元
- MA20: {tech_data['ma20']} 元
- MACD: {tech_data['macd']}
- Signal: {tech_data['signal']}
- Histogram: {tech_data['histogram']}

**大盘指数**:
{index_info}

请生成一份专业的{market_type}报告，包含以下内容：
1. 技术面分析（基于均线、MACD等指标）
2. 趋势判断
3. 操作建议（仅供参考，不构成投资建议）

要求：
- 语言简洁专业
- 突出重点
- 字数控制在300字以内
"""
    return prompt


def get_ai_analysis(prompt):
    """调用通义千问生成分析"""
    try:
        response = client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {"role": "system", "content": "你是一位专业的股票分析师，擅长技术分析和趋势判断。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI 分析失败: {e}")
        return "AI 分析暂时不可用，请查看原始数据。"


def send_feishu_report(title, content):
    """发送飞书报告"""
    try:
        # 构建飞书消息格式
        message = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": content
                        }
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "⚠️ 本报告由 AI 生成，仅供参考，不构成投资建议。股市有风险，投资需谨慎。"
                            }
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(
            FEISHU_WEBHOOK,
            json=message,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            print("飞书消息发送成功")
            return True
        else:
            print(f"飞书消息发送失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"发送飞书消息失败: {e}")
        return False


def analyze_stock(stock_code, is_pre_market=True):
    """分析单只股票"""
    print(f"\n正在分析股票: {stock_code}")
    
    # 转换股票代码格式（Tushare 格式）
    if stock_code.startswith('6'):
        ts_code = f"{stock_code}.SH"
    else:
        ts_code = f"{stock_code}.SZ"
    
    # 获取数据
    stock_info = get_stock_basic_info(ts_code)
    daily_data = get_daily_data(ts_code)
    index_data = get_index_data()
    
    if not stock_info or not daily_data:
        return f"获取股票 {stock_code} 数据失败"
    
    # 计算技术指标
    tech_data = calculate_technical_indicators(daily_data)
    
    # 生成 AI 分析
    prompt = generate_analysis_prompt(stock_info, tech_data, index_data, is_pre_market)
    analysis = get_ai_analysis(prompt)
    
    # 构建报告内容
    market_type = "盘前分析" if is_pre_market else "盘后复盘"
    title = f"📊 【每日股票{market_type}】{stock_info['name']}({stock_code})"
    
    content = f"""**股票**: {stock_info['name']} ({stock_code}) | {stock_info.get('industry', '未知')}

**最新行情**:
• 收盘价: **{tech_data['close']}** 元
• 涨跌幅: **{tech_data['pct_chg']}%**
• 成交量: {tech_data['vol']} 万手
• 最高/最低: {tech_data['high']} / {tech_data['low']} 元

**技术指标**:
• MA5/MA10/MA20: {tech_data['ma5']} / {tech_data['ma10']} / {tech_data['ma20']}
• MACD: {tech_data['macd']}

**AI 分析**:
{analysis}
"""
    
    return title, content


def main():
    """主函数"""
    print("=" * 50)
    print("每日股票分析工具启动")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 检查环境变量
    if not all([LLM_API_KEY, FEISHU_WEBHOOK]):
        print("错误: 缺少必要的环境变量配置")
        return
    
    # 解析股票池
    stock_list = [code.strip() for code in STOCK_POOL.split(',')]
    print(f"股票池: {stock_list}")
    
    # 判断是盘前还是盘后（UTC 时间转换）
    # 早上 8 点 UTC = 0 点，晚上 8 点 UTC = 12 点
    current_hour = datetime.now().hour
    is_pre_market = current_hour < 12  # UTC 0点为盘前，12点为盘后
    
    market_type = "盘前分析" if is_pre_market else "盘后复盘"
    print(f"当前分析类型: {market_type}")
    
    # 分析每只股票
    for stock_code in stock_list:
        try:
            result = analyze_stock(stock_code, is_pre_market)
            if isinstance(result, tuple):
                title, content = result
                send_feishu_report(title, content)
            else:
                print(result)
        except Exception as e:
            print(f"分析股票 {stock_code} 时出错: {e}")
    
    print("\n分析完成!")


if __name__ == '__main__':
    main()
