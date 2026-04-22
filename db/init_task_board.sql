-- Task Board 模块数据初始化脚本
-- 使用方法: mysql -h 192.168.31.195 -u agent_kb -p agent_kb < db/init_task_board.sql

-- 创建默认知识域（如果不存在）
INSERT IGNORE INTO knowledge_domains (id, name, icon, description, color, is_active, created_at, updated_at)
VALUES 
    ('00000000-0000-0000-0000-000000000001', '任务看板', '📋', '任务管理和排行榜', '#17a2b8', 1, NOW(), NOW()),
    ('00000000-0000-0000-0000-000000000002', '文档', '📄', '文档管理', '#28a745', 1, NOW(), NOW()),
    ('00000000-0000-0000-0000-000000000003', '学习', '📚', '学习资源', '#ffc107', 1, NOW(), NOW());

-- 创建测试 Agent（如果不存在）
INSERT IGNORE INTO agents (id, agent_code, name, device_name, environment_tags, status, created_at, updated_at)
VALUES 
    ('a0000000-0000-0000-0000-000000000001', 'AGENT001', '测试Agent1', 'test-device-1', '["test"]', 'ACTIVE', NOW(), NOW()),
    ('a0000000-0000-0000-0000-000000000002', 'AGENT002', '测试Agent2', 'test-device-2', '["test"]', 'ACTIVE', NOW(), NOW());

-- 创建测试任务示例
INSERT IGNORE INTO tasks (id, title, description, created_by_agent_id, priority, status, points, created_at, updated_at)
VALUES 
    ('t0000000-0000-0000-0000-000000000001', '示例任务：测试任务看板', '这是一个用于测试任务看板功能的示例任务', 'a0000000-0000-0000-0000-000000000001', 'MEDIUM', 'PENDING', 10, NOW(), NOW()),
    ('t0000000-0000-0000-0000-000000000002', '示例任务：高优先级任务', '这是一个高优先级任务示例', 'a0000000-0000-0000-0000-000000000001', 'HIGH', 'PENDING', 20, NOW(), NOW());
