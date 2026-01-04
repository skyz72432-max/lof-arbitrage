import http.client
import json
import os  # 引入 os 模块，用于读取环境变量

def main_handler(event, context):
    # 1. 从环境变量中安全读取 GitHub Token
    github_token = os.environ.get('GITHUB_TOKEN')
    
    # 2. 安全检查：如果环境变量未设置，则报错
    if not github_token:
        error_msg = "Environment variable 'GITHUB_TOKEN' is not set."
        print(error_msg)
        return {"error": error_msg}
    
    # 3. 配置其他参数（这些非敏感信息可以直接写在代码中或也放入环境变量）
    owner = "skyz72432-max"           # 你的GitHub用户名
    repo = "lof-arbitrage"                # 你的仓库名
    workflow_file = "sync_daily.yml" # 工作流文件名，如 main.yml
    
    # 4. 构建 API 请求
    conn = http.client.HTTPSConnection("api.github.com")
    headers = {
        "Authorization": f"token {github_token}",  # 使用从环境变量读取的Token
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Tencent-SCF-Trigger"
    }
    payload = json.dumps({"ref": "main"}).encode('utf-8')
    
    # 5. 发送 POST 请求以触发工作流
    api_url = f"/repos/{owner}/{repo}/actions/workflows/{workflow_file}/dispatches"
    conn.request("POST", api_url, body=payload, headers=headers)
    
    response = conn.getresponse()
    
    if response.status == 204:
        return "GitHub Actions workflow triggered successfully!"
    else:
        error_msg = f"Failed to trigger workflow. Status: {response.status}, Response: {response.read().decode()}"
        print(error_msg)
        # 注意：返回错误信息时，不要包含敏感的 Token
        return {"error": error_msg}
