import requests
import os
from datetime import datetime, timedelta


# 配置信息
TOKEN = os.getenv("GITHUB_TOKEN") 
REPO = os.getenv("GITHUB_REPOSITORY") # Actions 自动提供当前仓库名
WORKFLOW_NAME = "Docker Build and Standard Deploy"  # 部署任务名称
DAYS = 90


def get_deploy_frequency():
    since_date = (datetime.now() - timedelta(days=DAYS)).isoformat()
    url = f"https://api.github.com/repos/{REPO}/actions/runs"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {
        "event": "push",
        "status": "success",
        "created": f">{since_date}"
    }

    response = requests.get(url, headers=headers, params=params)
    runs = response.json().get("workflow_runs", [])

    # 过滤出真正的部署工作流（如果你有多个工作流）
    deploy_runs = [run for run in runs if run['name'] == WORKFLOW_NAME]

    count = len(deploy_runs)
    avg = count / DAYS

    print(f"📊 过去 {DAYS} 天共成功部署: {count} 次")
    print(f"📈 平均每天部署频率: {avg:.2f} 次/天")


get_deploy_frequency()