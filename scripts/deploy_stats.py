import os
import requests
import json
from datetime import datetime, timedelta

# === 配置区 ===
TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
# 必须与你 deploy.yml 中的 name 字段完全一致
WORKFLOW_NAME = "Docker Build and Standard Deploy"
DAYS = 30

def send_to_feishu_interactive(stats):
    """发送带有交互按钮的飞书卡片"""
    if not FEISHU_WEBHOOK:
        print("⚠️ 未配置 FEISHU_WEBHOOK，跳过通知")
        return

    duration_min = f"{stats['avg_duration'] / 60:.2f}"
    
    # 根据成功率决定卡片颜色：100% 蓝色，低于 100% 橙色，低于 50% 红色
    status_color = "blue"
    if stats['success_rate'] < 100: status_color = "orange"
    if stats['success_rate'] < 50: status_color = "red"

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "🚀 研发效能度量与交互控制"},
                "template": status_color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**项目:** {REPO}\n**周期:** 过去 {DAYS} 天"}
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**成功部署**\n{stats['success_count']} 次"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**成功率**\n{stats['success_rate']:.1f}%"}}
                    ]
                },
                {
                    "tag": "div",
                    "fields": [
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**平均耗时**\n{duration_min} Min"}},
                        {"is_short": True, "text": {"tag": "lark_md", "content": f"**失败/总计**\n{stats['failure_count']}/{stats['total_count']}"}}
                    ]
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": "💡 快捷运维操作："}]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "🔄 重启 K3s 服务"},
                            "type": "primary",
                            "value": {
                                "action_type": "retry_deploy",
                                "repo": REPO
                            },
                            "confirm": {
                                "title": {"tag": "plain_text", "content": "确认重启？"},
                                "text": {"tag": "plain_text", "content": "这将触发 kubectl rollout restart 指令。"}
                            }
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "📋 获取最近日志"},
                            "type": "default",
                            "value": {
                                "action_type": "get_logs"
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    res = requests.post(FEISHU_WEBHOOK, json=payload)
    print(f"飞书通知状态: {res.status_code}")

def create_github_issue(stats):
    """在 GitHub 创建 Issue 存档"""
    url = f"https://api.github.com/repos/{REPO}/issues"
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
    
    body = f"""
## 📊 效能存档 ({datetime.now().strftime('%Y-%m-%d')})
- **成功率**: {stats['success_rate']:.1f}%
- **总次数**: {stats['total_count']}
- **平均耗时**: {stats['avg_duration']/60:.2f} 分钟
    """
    requests.post(url, headers=headers, json={"title": f"效能报告 {datetime.now().date()}", "body": body})

def main():
    since_date = (datetime.now() - timedelta(days=DAYS)).isoformat()
    url = f"https://api.github.com/repos/{REPO}/actions/runs"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"created": f">{since_date}", "per_page": 100}

    response = requests.get(url, headers=headers, params=params)
    runs = response.json().get("workflow_runs", [])
    
    target_runs = [run for run in runs if run['name'] == WORKFLOW_NAME]
    
    if not target_runs:
        print("未发现匹配的运行记录。")
        return

    success_runs = [r for r in target_runs if r['conclusion'] == 'success']
    failure_count = len([r for r in target_runs if r['conclusion'] == 'failure'])
    
    total_count = len(target_runs)
    success_count = len(success_runs)
    
    total_duration = 0
    for run in success_runs:
        start = datetime.strptime(run['run_started_at'], "%Y-%m-%dT%H:%M:%SZ")
        end = datetime.strptime(run['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
        total_duration += (end - start).total_seconds()

    stats = {
        "total_count": total_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
        "avg_duration": total_duration / success_count if success_count > 0 else 0,
        "avg_freq": success_count / DAYS
    }

    create_github_issue(stats)
    send_to_feishu_interactive(stats)

if __name__ == "__main__":
    main()