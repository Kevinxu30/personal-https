#!/usr/bin/env python3
"""
接收 Ant Monitor 告警并推送到 GitHub
用法：python3 alert_receiver.py <alert_json_file>
或直接作为 HTTP 服务器：python3 alert_receiver.py --server
"""

import os
import sys
import json
import base64
import requests
from datetime import datetime

# 配置
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # 从环境变量读取
OWNER = "Kevinxu30"
REPO = "personal-https"
BRANCH = "main"
ALERTS_DIR = "alerts"

def get_file_sha(path):
    """获取文件的当前 SHA（用于更新）"""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}?ref={BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code == 404:
        return None  # 文件不存在
    resp.raise_for_status()
    return resp.json().get("sha")

def commit_alert(alert):
    """提交告警到 GitHub"""
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().isoformat()
    filename = f"{ALERTS_DIR}/{today}.md"
    
    # 格式化告警内容
    content = f"""# 告警日志 - {today}

## {alert.get('alert_name', '未知告警')}

| 字段 | 值 |
|------|-----|
| 时间 | {timestamp} |
| 级别 | {alert.get('severity', 'UNKNOWN')} |
| 值 | {alert.get('alert_value', 'N/A')} |
| 主机 | {alert.get('host', 'N/A')} |

### 详情
{alert.get('alert_detail', alert.get('message', '无详细信息'))}

---
"""
    
    # Base64 编码
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    # 获取当前 SHA（如果是更新）
    sha = get_file_sha(filename)
    
    # 提交
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    data = {
        "message": f"Alert: {alert.get('alert_name', 'Unknown')} [{alert.get('severity', 'UNKNOWN')}]",
        "content": content_b64,
        "branch": BRANCH
    }
    if sha:
        data["sha"] = sha
    
    resp = requests.put(url, headers=headers, json=data)
    resp.raise_for_status()
    print(f"✅ 告警已提交：{filename}")
    return resp.json()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        # HTTP 服务器模式
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class AlertHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                alert = json.loads(post_data.decode('utf-8'))
                commit_alert(alert)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
            
            def log_message(self, format, *args):
                print(f"[{datetime.now()}] {args[0]}")
        
        port = 8080
        server = HTTPServer(('0.0.0.0', port), AlertHandler)
        print(f"🚀 告警接收服务启动在 http://0.0.0.0:{port}")
        server.serve_forever()
    else:
        # 从文件读取
        if len(sys.argv) < 2:
            print("用法：python3 alert_receiver.py <alert.json> 或 --server")
            sys.exit(1)
        
        with open(sys.argv[1]) as f:
            alert = json.load(f)
        commit_alert(alert)

if __name__ == "__main__":
    main()
