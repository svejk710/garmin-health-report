import os
import datetime
import json
from garminconnect import Garmin
import anthropic

# 从环境变量读取密码（GitHub Actions 会自动注入）
GARMIN_EMAIL = os.environ['GARMIN_EMAIL']
GARMIN_PASSWORD = os.environ['GARMIN_PASSWORD']
CLAUDE_API_KEY = os.environ['CLAUDE_API_KEY']

def get_garmin_data():
    """登录 Garmin,拉取最少的数据"""
    try:
        client = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
        client.login()
        
        today = datetime.date.today().isoformat()
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        
        # 只拿这 3 个数据,减少请求次数
        sleep = client.get_sleep_data(yesterday)
        steps = client.get_steps_data(today)
        
        summary = {
            "日期": today,
            "睡眠时长(小时)": round(sleep.get("dailySleepDTO", {}).get("sleepTimeSeconds", 0) / 3600, 1),
            "深睡(小时)": round(sleep.get("dailySleepDTO", {}).get("deepSleepSeconds", 0) / 3600, 1),
            "睡眠分数": sleep.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value", "N/A"),
            "今日步数": sum([s.get("steps", 0) for s in steps]) if steps else 0,
        }
        return summary
    except Exception as e:
        return {"错误": str(e)}

def analyze_with_claude(data):
    """让 Claude 分析"""
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    
    prompt = f"""你是我的私人健康教练。基于以下数据,给出 3 条具体建议。

要求:
- 口语化、像朋友聊天
- 每条不超过 50 字
- 优先指出异常和趋势
- 用 Markdown 格式

数据:
{json.dumps(data, ensure_ascii=False, indent=2)}
"""
    
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def generate_html(data, analysis):
    """生成一个好看的网页"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>今日健康报告 - {data.get('日期', '')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            max-width: 600px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{ margin-top: 0; color: #333; }}
        .data {{ font-size: 18px; line-height: 1.8; color: #666; }}
        .analysis {{ white-space: pre-wrap; line-height: 1.8; }}
        .timestamp {{ text-align: center; color: #999; font-size: 14px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>📊 今日健康数据</h1>
        <div class="data">
            睡眠时长: {data.get('睡眠时长(小时)', 'N/A')} 小时<br>
            深睡时长: {data.get('深睡(小时)', 'N/A')} 小时<br>
            睡眠分数: {data.get('睡眠分数', 'N/A')}<br>
            今日步数: {data.get('今日步数', 'N/A')}
        </div>
    </div>
    
    <div class="card">
        <h1>💡 AI 教练建议</h1>
        <div class="analysis">{analysis}</div>
    </div>
    
    <div class="timestamp">
        生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>
"""
    return html

def main():
    print("📊 拉取 Garmin 数据...")
    data = get_garmin_data()
    print(f"数据: {data}")
    
    if "错误" in data:
        print(f"❌ 登录失败: {data['错误']}")
        # 生成错误页面
        html = f"<h1>登录失败</h1><p>{data['错误']}</p>"
    else:
        print("🤖 Claude 分析中...")
        analysis = analyze_with_claude(data)
        print("生成网页...")
        html = generate_html(data, analysis)
    
    # 保存到 output 文件夹
    os.makedirs("output", exist_ok=True)
    with open("output/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ 完成!")

if __name__ == "__main__":
    main()
