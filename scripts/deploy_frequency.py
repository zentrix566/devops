import os
import requests
from datetime import datetime, timedelta

TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")
WORKFLOW_NAME = "Docker Build and Standard Deploy"
DAYS = 30

def create_issue_report(count, avg):
    """通过 API 创建 GitHub Issue 报表"""
    url = f"https://api.github.com/repos/{REPO}/issues"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    # 报表内容（支持 Markdown）
    title = f"🚀 研发效能周报 | {datetime.now().strftime('%Y-%m-%d')}"
    body = f"""
## 📊 部署频率度量报告 (过去 {DAYS} 天)

| 指标项目 | 统计数值 |
| :--- | :--- |
| **目标工作流** | `{WORKFLOW_NAME}` |
| **成功部署总次数** | **{count} 次** |
| **平均部署频率** | **{avg:.2f} 次/天** |

> *此报告由 GitHub Actions 自动化脚本生成。*
    """
    
    data = {"title": title, "body": body}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print("✅ 报表 Issue 已成功创建！")
    else:
        print(f"❌ 创建失败: {response.text}")

def get_deploy_frequency():
    since_date = (datetime.now() - timedelta(days=DAYS)).isoformat()
    url = f"https://api.github.com/repos/{REPO}/actions/runs"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"status": "success", "created": f">{since_date}", "per_page": 100}

    response = requests.get(url, headers=headers, params=params)
    runs = response.json().get("workflow_runs", [])
    deploy_runs = [run for run in runs if run['name'] == WORKFLOW_NAME]
    
    count = len(deploy_runs)
    avg = count / DAYS
    
    # 核心步骤：调用创建 Issue 的函数
    create_issue_report(count, avg)

if __name__ == "__main__":
    get_deploy_frequency()