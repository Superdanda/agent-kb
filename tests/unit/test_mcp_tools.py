from app.mcp.router import PUBLIC_TOOLS, _tool_definitions


def test_mcp_tool_definitions_mark_public_and_protected_auth():
    tools = {tool["name"]: tool for tool in _tool_definitions()}

    assert PUBLIC_TOOLS == {"agent_kb.register", "agent_kb.fetch_credentials"}
    assert tools["agent_kb.register"]["annotations"]["auth"] == "none"
    assert "host_info" in tools["agent_kb.register"]["inputSchema"]["properties"]
    assert tools["agent_kb.fetch_credentials"]["annotations"]["auth"] == "none"
    assert tools["agent_kb.heartbeat"]["annotations"]["auth"] == "hmac"
    assert tools["agent_kb.task_submit"]["annotations"]["auth"] == "hmac"
    assert "result_material_ids" in tools["agent_kb.task_submit"]["inputSchema"]["properties"]

    assert tools["agent_kb.task_materials"]["annotations"]["auth"] == "hmac"
    assert tools["agent_kb.material_preview"]["annotations"]["auth"] == "hmac"
    assert tools["agent_kb.material_download"]["annotations"]["auth"] == "hmac"
    assert tools["agent_kb.material_upload"]["annotations"]["auth"] == "hmac"
    assert "content_base64" in tools["agent_kb.material_upload"]["inputSchema"]["properties"]
