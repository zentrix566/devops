import uvicorn
from fastapi import FastAPI, Request
import os
import json

app = FastAPI()

@app.post("/feishu/callback")
async def feishu_callback(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"error": "invalid json"}
    
    # 1. 应对飞书后台的首次地址验证 (Challenge)
    if "challenge" in data:
        print("🔍 收到 Challenge 验证请求")
        return {"challenge": data["challenge"]}
        
    # 2. 解析点击动作
    action = data.get("action", {})
    action_value = action.get("value", {})
    action_type = action_value.get("action_type")
    
    print(f"执行动作: {action_type}")

    if action_type == "retry_deploy":
        # 执行重启指令
        # 建议加上完整路径，防止系统环境变量找不到 kubectl
        os.system("/usr/local/bin/kubectl rollout restart deployment zentrix-lab")
        
        # 核心修复：飞书卡片回调要求的标准响应格式
        return {
            "toast": {
                "type": "info",
                "content": "✅ 已触发 K3s 重启指令"
            }
        }
    
    elif action_type == "get_logs":
        # 如果你点击了获取日志按钮
        return {
            "toast": {
                "type": "info",
                "content": "📝 日志获取功能开发中..."
            }
        }

    # 默认返回空对象，告知飞书请求已收到
    return {}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
