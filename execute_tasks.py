#!/usr/bin/env python3
"""Execute the full task闭环: poll → claim → compute → submit"""
import json
import sys
from urllib.parse import urlparse
sys.path.insert(0, '/home/lulz1/.hermes/skills/software-development/knowledge-platform/scripts')

import requests
from _signer import build_headers

# Load credentials
with open('/home/lulz1/.hermes/skills/software-development/knowledge-platform/credentials.json') as f:
    creds = json.load(f)

AGENT_ID = creds['agent_id']
ACCESS_KEY = creds['access_key']
SECRET_KEY = creds['secret_key']
BASE_URL = creds['base_url']

TASKS = [
    ("88548619-0f5c-4a21-bffa-398c753c4ed7", "3"),  # 1+2=3
    ("d2e2f1e5-83c5-4b9d-a259-42e1f51d3120", "2"),  # 1+1=2
]

def make_request(method, path, body=""):
    """Make authenticated request"""
    url = BASE_URL + path
    parsed = urlparse(path)
    path_only = parsed.path
    query = parsed.query
    
    print(f"DEBUG: method={method}, path_only={path_only}, query={query}, body={repr(body)}")
    
    headers = build_headers(AGENT_ID, ACCESS_KEY, SECRET_KEY, method, path_only, query, body)
    print(f"DEBUG headers: {json.dumps({k:v for k,v in headers.items()}, indent=2)}")
    
    if method == "GET":
        resp = requests.get(url, headers=headers)
    elif method == "POST":
        resp = requests.post(url, headers=headers, data=body if body else None)
    else:
        raise ValueError(f"Unknown method: {method}")
    return resp

# Step 1: Heartbeat
print("=== HEARTBEAT ===")
resp = make_request("POST", "/api/agent/heartbeat")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:200]}")

# Step 2: Process each task
for task_id, answer in TASKS:
    print(f"\n=== TASK: {task_id} ===")
    
    # Claim task
    print("--- CLAIM ---")
    path = f"/api/agent/tasks/{task_id}/claim"
    resp = make_request("POST", path)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")
    
    # Submit task
    print("--- SUBMIT ---")
    path = f"/api/agent/tasks/{task_id}/submit?result_summary={answer}"
    resp = make_request("POST", path)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")

print("\n=== VERIFYING IN DB ===")
import pymysql
conn = pymysql.connect(host='192.168.160.1', user='hermes_kb', password='123456', database='agent-platform')
cursor = conn.cursor()
task_ids = "', '".join([t[0] for t in TASKS])
cursor.execute(f"SELECT id, status, metadata_json FROM tasks WHERE id IN ('{task_ids}')")
for row in cursor.fetchall():
    print(f"Task {row[0]}: status={row[1]}, metadata={row[2]}")
conn.close()
