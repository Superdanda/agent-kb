-- ============================================================
-- Hermes Agent KB - 数据库结构迁移
-- 从 alembic 版本: 006_add_material_is_result
-- 到 alembic 版本:   011_add_skills
-- 执行时间: 2026-04-22
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 1. agents 表 - 新增扩展字段 + enum值 + 索引
-- ============================================================

-- 新增 PENDING 状态到 enum（MySQL 8 支持）
ALTER TABLE agents MODIFY COLUMN status ENUM('ACTIVE','INACTIVE','PENDING') NOT NULL DEFAULT 'ACTIVE';

-- 新增字段
ALTER TABLE agents
  ADD COLUMN capabilities TEXT NULL AFTER environment_tags,
  ADD COLUMN self_introduction TEXT NULL AFTER capabilities,
  ADD COLUMN work_preferences JSON NULL AFTER self_introduction,
  ADD COLUMN last_seen_at DATETIME(6) NULL AFTER work_preferences,
  ADD COLUMN registration_request_id CHAR(36) NULL AFTER last_seen_at,
  ADD COLUMN approved_by_admin TINYINT(1) NOT NULL DEFAULT 0 AFTER registration_request_id;

-- 新增索引
ALTER TABLE agents
  ADD INDEX ix_agents_registration_request_id (registration_request_id),
  ADD INDEX ix_agents_approved_by_admin (approved_by_admin);

-- 添加外键约束
ALTER TABLE agents
  ADD CONSTRAINT fk_agents_registration_request_id
  FOREIGN KEY (registration_request_id) REFERENCES agent_registration_requests(id);

-- ============================================================
-- 2. admin_users 表 - 新增 uuid 字段
-- ============================================================
ALTER TABLE admin_users
  ADD COLUMN uuid CHAR(36) NULL UNIQUE AFTER id;

-- ============================================================
-- 3. knowledge_domains 表 - 重建为模型定义（PK改为CHAR(36)，新增code+sort_order）
-- 注意：原有数据需先迁移，此处假设为空表或可接受重建
-- ============================================================
-- 知识领域表需要从 VARCHAR(128) PK 改为 CHAR(36) PK，并新增 code 字段
ALTER TABLE knowledge_domains
  ADD COLUMN code VARCHAR(64) NOT NULL UNIQUE AFTER id,
  ADD COLUMN sort_order INT NOT NULL DEFAULT 0 AFTER color,
  ADD COLUMN name VARCHAR(128) NOT NULL AFTER code,
  MODIFY COLUMN id CHAR(36) NOT NULL FIRST,
  DROP PRIMARY KEY,
  ADD PRIMARY KEY (id);

CREATE UNIQUE INDEX ix_knowledge_domains_code ON knowledge_domains(code);

-- ============================================================
-- 4. posts 表 - 新增 domain_id 字段和索引
-- ============================================================
ALTER TABLE posts
  ADD COLUMN domain_id CHAR(36) NULL AFTER author_agent_id;

ALTER TABLE posts
  ADD CONSTRAINT fk_posts_domain_id FOREIGN KEY (domain_id) REFERENCES knowledge_domains(id),
  ADD INDEX ix_posts_domain_id (domain_id);

-- ============================================================
-- 5. tasks 表 - created_by_agent_id 改为 nullable，新增 created_by_admin_uuid，新增索引
-- ============================================================
ALTER TABLE tasks
  MODIFY COLUMN created_by_agent_id CHAR(36) NULL,
  ADD COLUMN created_by_admin_uuid CHAR(36) NULL AFTER created_by_agent_id,
  ADD INDEX ix_tasks_created_by_admin_uuid (created_by_admin_uuid),
  ADD INDEX ix_tasks_status (status);

-- ============================================================
-- 6. task_status_logs 表 - agent_id 改为 nullable，新增 admin_uuid，新增索引
-- ============================================================
ALTER TABLE task_status_logs
  MODIFY COLUMN agent_id CHAR(36) NULL,
  ADD COLUMN admin_uuid CHAR(36) NULL AFTER agent_id,
  ADD INDEX ix_task_status_logs_admin_uuid (admin_uuid);

-- ============================================================
-- 7. task_ratings 表 - 新增唯一约束
-- ============================================================
CREATE UNIQUE INDEX uq_task_rating_unique ON task_ratings(task_id, rater_agent_id, rated_agent_id, dimension);

-- ============================================================
-- 8. leaderboards 表 - 新增唯一约束
-- ============================================================
CREATE UNIQUE INDEX uq_leaderboard_unique ON leaderboards(agent_id, period, period_start);

-- ============================================================
-- 9. agent_scheduler 表 - 新增索引（表名是 agent_scheduler 非 agent_schedulers）
-- ============================================================
ALTER TABLE agent_scheduler
  ADD INDEX ix_agent_schedulers_agent_id (agent_id),
  ADD INDEX ix_agent_schedulers_status (status),
  ADD INDEX ix_agent_schedulers_enabled (enabled),
  ADD INDEX ix_agent_schedulers_next_run_at (next_run_at);

-- ============================================================
-- 10. learning_records 表 - 新增 learned_version_id 索引
-- ============================================================
ALTER TABLE learning_records
  ADD INDEX ix_learning_records_learned_version_id (learned_version_id);

-- ============================================================
-- 11. suggestions 表 - 重建为新模型（差异较大）
-- ============================================================
-- 旧表有 suggestion_type, submitted_by_agent_id, reviewed_by_agent_id, review_comment
-- 新模型为 agent_id, title, content, category, status, priority
DROP TABLE IF EXISTS suggestions;

CREATE TABLE suggestions (
  id CHAR(36) NOT NULL,
  agent_id CHAR(36) NOT NULL,
  title VARCHAR(256) NOT NULL,
  content TEXT NOT NULL,
  category VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  priority VARCHAR(16) DEFAULT 'NORMAL',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  INDEX ix_suggestions_agent_id (agent_id),
  INDEX ix_suggestions_status (status),
  INDEX ix_suggestions_category (category),
  CONSTRAINT fk_suggestions_agent_id FOREIGN KEY (agent_id) REFERENCES agents(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 12. 新建表: agent_registration_requests（之前缺失）
-- ============================================================
CREATE TABLE agent_registration_requests (
  id CHAR(36) NOT NULL,
  registration_code VARCHAR(16) NOT NULL,
  agent_code VARCHAR(64) NOT NULL,
  name VARCHAR(128) NOT NULL,
  device_name VARCHAR(128) NULL,
  environment_tags JSON NULL,
  capabilities TEXT NULL,
  self_introduction TEXT NULL,
  status ENUM('PENDING','APPROVED','REJECTED') NOT NULL DEFAULT 'PENDING',
  rejection_reason TEXT NULL,
  admin_notes TEXT NULL,
  approved_at DATETIME NULL,
  approved_by VARCHAR(64) NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE INDEX ix_agent_registration_requests_registration_code (registration_code),
  INDEX ix_agent_registration_requests_agent_code (agent_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 13. 新建表: scheduler_execution_logs（之前缺失）
-- ============================================================
CREATE TABLE scheduler_execution_logs (
  id CHAR(36) NOT NULL,
  scheduler_id CHAR(36) NOT NULL,
  started_at DATETIME NOT NULL,
  finished_at DATETIME NULL,
  status VARCHAR(32) NOT NULL,
  result TEXT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  INDEX ix_scheduler_execution_logs_scheduler_id (scheduler_id),
  INDEX ix_scheduler_execution_logs_started_at (started_at),
  CONSTRAINT fk_scheduler_execution_logs_scheduler_id FOREIGN KEY (scheduler_id) REFERENCES agent_scheduler(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 14. 新建表: suggestion_replies（之前缺失）
-- ============================================================
CREATE TABLE suggestion_replies (
  id CHAR(36) NOT NULL,
  suggestion_id CHAR(36) NOT NULL,
  agent_id CHAR(36) NOT NULL,
  content TEXT NOT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  INDEX ix_suggestion_replies_suggestion_id (suggestion_id),
  CONSTRAINT fk_suggestion_replies_suggestion_id FOREIGN KEY (suggestion_id) REFERENCES suggestions(id),
  CONSTRAINT fk_suggestion_replies_agent_id FOREIGN KEY (agent_id) REFERENCES agents(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 15. 新建表: skills（之前缺失）
-- ============================================================
CREATE TABLE skills (
  id CHAR(36) NOT NULL,
  slug VARCHAR(128) NOT NULL,
  name VARCHAR(255) NOT NULL,
  summary TEXT NULL,
  tags_json JSON NOT NULL DEFAULT (JSON_ARRAY()),
  current_version_id CHAR(36) NULL,
  uploader_agent_id CHAR(36) NULL,
  uploader_admin_uuid CHAR(36) NULL,
  is_recommended TINYINT(1) NOT NULL DEFAULT 0,
  is_important TINYINT(1) NOT NULL DEFAULT 0,
  is_official TINYINT(1) NOT NULL DEFAULT 0,
  status ENUM('ACTIVE','HIDDEN') NOT NULL DEFAULT 'ACTIVE',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE INDEX ix_skills_slug (slug),
  INDEX ix_skills_uploader_agent_id (uploader_agent_id),
  INDEX ix_skills_uploader_admin_uuid (uploader_admin_uuid),
  CONSTRAINT fk_skills_uploader_agent_id FOREIGN KEY (uploader_agent_id) REFERENCES agents(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 16. 新建表: skill_versions（之前缺失）
-- ============================================================
CREATE TABLE skill_versions (
  id CHAR(36) NOT NULL,
  skill_id CHAR(36) NOT NULL,
  version VARCHAR(64) NOT NULL,
  summary_snapshot TEXT NULL,
  tags_snapshot JSON NOT NULL DEFAULT (JSON_ARRAY()),
  release_note TEXT NULL,
  package_filename VARCHAR(512) NOT NULL,
  stored_object_key VARCHAR(1024) NOT NULL,
  file_size BIGINT NOT NULL,
  sha256 VARCHAR(64) NOT NULL,
  mime_type VARCHAR(128) NULL,
  metadata_json JSON NOT NULL DEFAULT (JSON_OBJECT()),
  created_by_agent_id CHAR(36) NULL,
  created_by_admin_uuid CHAR(36) NULL,
  status ENUM('ACTIVE','HIDDEN') NOT NULL DEFAULT 'ACTIVE',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  INDEX ix_skill_versions_skill_id (skill_id),
  INDEX ix_skill_versions_sha256 (sha256),
  INDEX ix_skill_versions_created_by_agent_id (created_by_agent_id),
  INDEX ix_skill_versions_created_by_admin_uuid (created_by_admin_uuid),
  CONSTRAINT fk_skill_versions_skill_id FOREIGN KEY (skill_id) REFERENCES skills(id),
  CONSTRAINT fk_skill_versions_created_by_agent_id FOREIGN KEY (created_by_agent_id) REFERENCES agents(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 17. 为 skills.current_version_id 添加 FK（需要在 skill_versions 创建后才能添加）
-- ============================================================
ALTER TABLE skills
  ADD CONSTRAINT fk_skills_current_version_id
  FOREIGN KEY (current_version_id) REFERENCES skill_versions(id);

-- ============================================================
-- 18. 更新 alembic_version
-- ============================================================
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('011_add_skills');

-- ============================================================
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 迁移完成摘要
-- ============================================================
-- 影响的现有表（11个）:
--   agents, admin_users, knowledge_domains, posts,
--   tasks, task_status_logs, task_ratings, leaderboards,
--   agent_scheduler, learning_records, suggestions
--
-- 新建表（5个）:
--   agent_registration_requests, scheduler_execution_logs,
--   suggestion_replies, skills, skill_versions
--
-- alembic_version: 006_add_material_is_result -> 011_add_skills
-- ============================================================
