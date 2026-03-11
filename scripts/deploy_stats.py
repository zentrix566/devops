import os
import requests
import json
from datetime import datetime, timedelta

# 配置环境
TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
WORKFLOW_NAME = "Docker Build and Standard Deploy"
DAYS = 30

def send_to_feishu(stats):
    """发送精美的飞书卡片消息"""
    if not FEISHU_WEBHOOK:
        print("⚠️ 未配置 FEISHU_WEBHOOK，跳过通知")
        return

    duration_min = f"{stats['avg_duration'] / 60:.2f}"
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "📊 研发效能月度看板"},
                "template": "blue" if stats['success_rate'] >= 90 else "orange"
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": f"**项目:** {REPO}\n**周期:** 过去 {DAYS} 天"}},
                {"tag": "hr"},
                {
                    "tag": "div",
                    "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**部署频率**\n{stats['avg_freq']:.2f} 次/天"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**成功率**\n{stats['success_rate']:.1f}%"}}
                    ]
                },
                {
                    "tag": "div",
                    "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**平均耗时**\n{duration_min} 分钟"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**失败/总计**\n{stats['failure_count']}/{stats['total_count']}"}}
                    ]
                },
                {"tag": "hr"},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": "数据由 DevOps 自动化脚本分析生成"}]}
            ]
        }
    }
    requests.post(FEISHU_WEBHOOK, json=payload)

def create_github_issue(stats):
    """创建 GitHub Issue 归档"""
    url = f"https://api.github.com/repos/{REPO}/issues"
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
    
    title = f"🚀 效能报告 | {datetime.now().strftime('%Y-%m-%d')}"
    body = f"""
## 📈 部署效能度量 (过去 {DAYS} 天)

| 指标 | 数值 | 说明 |
| :--- | :--- | :--- |
| **总触发次数** | {stats['total_count']} | 包含失败的尝试 |
| **部署成功率** | **{stats['success_rate']:.1f}%** | 核心稳定性指标 |
| **平均部署频率** | {stats['avg_freq']:.2f} 次/天 | 交付速率 |
| **平均部署耗时** | {stats['avg_duration']/60:.2f} min | 流水线效率 |

### 🔍 异常分析
- 失败次数：`{stats['failure_count']}`
- 建议：检查是否存在环境抖动或代码合并冲突导致的构建失败。
    """
    requests.post(url, headers=headers, json={"title": title, "body": body})

def get_metrics():
    since_date = (datetime.now() - timedelta(days=DAYS)).isoformat()
    url = f"https://api.github.com/repos/{REPO}/actions/runs"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"created": f">{since_date}", "per_page": 100}

    response = requests.get(url, headers=headers, params=params)
    all_runs = response.json().get("workflow_runs", [])
    
    # 筛选出属于目标部署流的所有运行记录（不限状态）
    target_runs = [run for run in all_runs if run['name'] == WORKFLOW_NAME]
    
    if not target_runs:
        print("未发现匹配记录")
        return

    # 分析 conclusion 字段
    success_runs = [r for r in target_runs if r['conclusion'] == 'success']
    failure_count = len([r for r in target_runs if r['conclusion'] == 'failure'])
    
    total_count = len(target_runs)
    success_count = len(success_runs)
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    # 计算耗时（仅限成功的部署）
    total_duration = 0
    for run in success_runs:
        start = datetime.strptime(run['run_started_at'], "%Y-%m-%dT%H:%M:%SZ")
        end = datetime.strptime(run['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
        total_duration += (end - start).total_seconds()
    
    stats = {
        "total_count": total_count,
        "failure_count": failure_count,
        "success_rate": success_rate,
        "avg_freq": success_count / DAYS,
        "avg_duration": total_duration / success_count if success_count > 0 else 0
    }
    
    create_github_issue(stats)
    send_to_feishu(stats)

if __name__ == "__main__":
    get_metrics()