import uvicorn
from fastapi import FastAPI, Request
import os
import requests
import json
import threading
import time

app = FastAPI()

# === 配置区 ===
# APP_ID = os.getenv("FEISHU_APP_ID") 
# APP_SECRET = os.getenv("FEISHU_APP_SECRET")
# CHAT_ID = os.getenv("FEISHU_CHAT_ID")

APP_ID = "FEISHU_APP_ID"
APP_SECRET = "FEISHU_APP_SECRET"
CHAT_ID = "FEISHU_CHAT_ID"

DEPLOY_NAME = "zentrix-lab"
KUBECFG = "--kubeconfig=/root/.kube/config"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    return res.json().get("tenant_access_token")

def send_feishu_msg(text):
    """通用发消息函数"""
    token = get_token()
    if not token: return
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    # 使用 Markdown 格式让日志更好看
    payload = {
        "receive_id": CHAT_ID,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    requests.post(url, headers=headers, json=payload)

def handle_get_logs():
    """专门处理日志抓取的函数"""
    print(f"📋 正在为 {DEPLOY_NAME} 抓取日志...")
    
    # 1. 先定位 Pod 名字（取最近的一个）
    pod_cmd = f"kubectl {KUBECFG} get pods -l app={DEPLOY_NAME} --sort-by=.metadata.creationTimestamp -o jsonpath='{{.items[-1].metadata.name}}'"
    pod_name = os.popen(pod_cmd).read().strip()
    
    if not pod_name:
        send_feishu_msg(f"❌ 未找到部署名为 {DEPLOY_NAME} 的 Pod，请检查 Label 配置。")
        return

    # 2. 抓取最后 50 行日志
    log_cmd = f"kubectl {KUBECFG} logs {pod_name} --tail=50"
    logs = os.popen(log_cmd).read()

    # 3. 组合消息并发送
    report = f"📋 **日志回显内容**\n**Pod:** `{pod_name}`\n---\n```text\n{logs if logs else '日志内容为空'}\n```"
    send_feishu_msg(report)

def async_ops_flow():
    """重启流水线 (保持不变)"""
    os.system(f"kubectl {KUBECFG} rollout restart deployment {DEPLOY_NAME}")
    time.sleep(5)
    status = os.popen(f"kubectl {KUBECFG} get pods -l app={DEPLOY_NAME}").read()
    send_feishu_msg(f"✅ 重启指令已完成！\n\n当前状态：\n{status}")

@app.post("/feishu/callback")
async def feishu_callback(request: Request):
    data = await request.json()
    
    # URL 验证
    if "challenge" in data:
        return {"challenge": data["challenge"]}
        
    # 2.0 协议解析路径
    event_obj = data.get("event", {})
    action_val = event_obj.get("action", {}).get("value", {})
    action_type = action_val.get("action_type")
    
    # 兼容手动测试
    if not action_type:
        action_type = data.get("action", {}).get("value", {}).get("action_type")

    print(f"🔍 触发动作: {action_type}")

    if action_type == "retry_deploy":
        threading.Thread(target=async_ops_flow).start()
        return {"toast": {"type": "success", "content": "🚀 已开始重启流程..."}}
    
    elif action_type == "get_logs":
        # 核心修复：点击查看日志后，开启异步任务发消息
        threading.Thread(target=handle_get_logs).start()
        return {"toast": {"type": "info", "content": "📋 正在抓取最新 50 行日志，请稍后..."}}

    return {}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)