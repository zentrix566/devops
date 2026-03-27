import os
import requests
import json
from datetime import datetime, timedelta

# === 配置区 ===
TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")
# 飞书应用凭证
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
CHAT_ID = os.getenv("FEISHU_CHAT_ID")  # 接收卡片的群 ID

WORKFLOW_NAME = "Docker Build and Standard Deploy"
DAYS = 30

def get_tenant_access_token():
    """获取飞书接口调用凭据"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    try:
        res = requests.post(url, json=payload)
        return res.json().get("tenant_access_token")
    except Exception as e:
        print(f"❌ 获取 Token 失败: {e}")
        return None

def send_to_feishu_as_app(stats):
    """以机器人应用身份发送可交互卡片"""
    token = get_tenant_access_token()
    if not token or not CHAT_ID:
        print("⚠️ 配置不足，无法发送飞书通知")
        return

    duration_min = f"{stats['avg_duration'] / 60:.2f}"
    status_color = "blue"
    if stats['success_rate'] < 100: status_color = "orange"
    if stats['success_rate'] < 50: status_color = "red"

    # 构造交互卡片内容
    card_content = {
        "header": {
            "title": {"tag": "plain_text", "content": "🚀 研发效能度量 (交互版)"},
            "template": status_color
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**项目:** {REPO}\n**周期:** 过去 {DAYS} 天"}},
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
            {"tag": "note", "elements": [{"tag": "plain_text", "content": "💡 点击下方按钮直接操作服务器："}]},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔄 重启 K3s 服务"},
                        "type": "primary",
                        "value": {"action_type": "retry_deploy"},
                        "confirm": {
                            "title": {"tag": "plain_text", "content": "确认重启？"},
                            "text": {"tag": "plain_text", "content": "这将向服务器下发 kubectl rollout restart 指令。"}
                        }
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📋 查看最近日志"},
                        "type": "default",
                        "value": {"action_type": "get_logs"}
                    }
                ]
            }
        ]
    }

    # 发送消息给群聊
    send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    payload = {
        "receive_id": CHAT_ID,
        "msg_type": "interactive",
        "content": json.dumps(card_content)
    }
    
    res = requests.post(send_url, headers=headers, json=payload)
    print(f"飞书消息发送状态: {res.json().get('msg')}")

def create_github_issue(stats):
    """在 GitHub 创建 Issue 存档"""
    url = f"https://api.github.com/repos/{REPO}/issues"
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
    body = f"## 📊 效能存档 ({datetime.now().strftime('%Y-%m-%d')})\n- **成功率**: {stats['success_rate']:.1f}%\n- **总次数**: {stats['total_count']}"
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
        print("未发现记录")
        return

    success_runs = [r for r in target_runs if r['conclusion'] == 'success']
    success_count = len(success_runs)
    total_count = len(target_runs)
    
    total_duration = 0
    for run in success_runs:
        start = datetime.strptime(run['run_started_at'], "%Y-%m-%dT%H:%M:%SZ")
        end = datetime.strptime(run['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
        total_duration += (end - start).total_seconds()

    stats = {
        "total_count": total_count,
        "success_count": success_count,
        "failure_count": total_count - success_count,
        "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
        "avg_duration": total_duration / success_count if success_count > 0 else 0,
        "avg_freq": success_count / DAYS
    }

    create_github_issue(stats)
    send_to_feishu_as_app(stats)

if __name__ == "__main__":
    main()