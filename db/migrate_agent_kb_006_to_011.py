#!/usr/bin/env python3
"""
Hermes Agent KB 数据库迁移脚本
alembic 版本: 006_add_material_is_result -> 011_add_skills
"""
import pymysql
import sys

DB_HOST = '192.168.31.195'
DB_PORT = 3306
DB_USER = 'agent_kb'
DB_PASS = '12345678'
DB_NAME = 'agent_kb'

def get_conn():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME,
        connect_timeout=15, autocommit=False
    )

def exec_sql(conn, cursor, sql, desc=""):
    """执行一条SQL，失败时打印并继续"""
    try:
        cursor.execute(sql)
        print(f"  [OK] {desc}")
        return True
    except Exception as e:
        print(f"  [SKIP/ERR] {desc}: {e}")
        return False

def run_migration():
    conn = get_conn()
    cursor = conn.cursor()

    print("=" * 60)
    print("Hermes Agent KB 迁移: 006 -> 011")
    print("=" * 60)

    # ============================================================
    # 1. agents 表
    # ============================================================
    print("\n[1/17] agents 表 ...")
    exec_sql(conn, cursor,
        "ALTER TABLE agents MODIFY COLUMN status ENUM('ACTIVE','INACTIVE','PENDING') NOT NULL DEFAULT 'ACTIVE'",
        "status 枚举新增 PENDING")
    exec_sql(conn, cursor,
        "ALTER TABLE agents ADD COLUMN capabilities TEXT NULL AFTER environment_tags",
        "新增 capabilities 列")
    exec_sql(conn, cursor,
        "ALTER TABLE agents ADD COLUMN self_introduction TEXT NULL AFTER capabilities",
        "新增 self_introduction 列")
    exec_sql(conn, cursor,
        "ALTER TABLE agents ADD COLUMN work_preferences JSON NULL AFTER self_introduction",
        "新增 work_preferences 列")
    exec_sql(conn, cursor,
        "ALTER TABLE agents ADD COLUMN last_seen_at DATETIME(6) NULL AFTER work_preferences",
        "新增 last_seen_at 列")
    exec_sql(conn, cursor,
        "ALTER TABLE agents ADD COLUMN registration_request_id CHAR(36) NULL AFTER last_seen_at",
        "新增 registration_request_id 列")
    exec_sql(conn, cursor,
        "ALTER TABLE agents ADD COLUMN approved_by_admin TINYINT(1) NOT NULL DEFAULT 0 AFTER registration_request_id",
        "新增 approved_by_admin 列")
    exec_sql(conn, cursor,
        "ALTER TABLE agents ADD INDEX ix_agents_registration_request_id (registration_request_id)",
        "新增 registration_request_id 索引")
    exec_sql(conn, cursor,
        "ALTER TABLE agents ADD INDEX ix_agents_approved_by_admin (approved_by_admin)",
        "新增 approved_by_admin 索引")
    # 注意: registration_request_id FK 稍后等 agent_registration_requests 表建立后再加

    # ============================================================
    # 2. admin_users 表
    # ============================================================
    print("\n[2/17] admin_users 表 ...")
    exec_sql(conn, cursor,
        "ALTER TABLE admin_users ADD COLUMN uuid CHAR(36) NULL UNIQUE AFTER id",
        "新增 uuid 列")

    # ============================================================
    # 3. knowledge_domains 表 - 新增 code 和 sort_order
    # ============================================================
    print("\n[3/17] knowledge_domains 表 ...")
    exec_sql(conn, cursor,
        "ALTER TABLE knowledge_domains ADD COLUMN code VARCHAR(64) NOT NULL UNIQUE AFTER id",
        "新增 code 列 (UNIQUE)")
    exec_sql(conn, cursor,
        "ALTER TABLE knowledge_domains ADD COLUMN sort_order INT NOT NULL DEFAULT 0 AFTER color",
        "新增 sort_order 列")

    # 为现有2条记录填充 code（name列值作为code）
    try:
        cursor.execute("UPDATE knowledge_domains SET code='task_board' WHERE name='任务看板'")
        cursor.execute("UPDATE knowledge_domains SET code='doc_mgmt' WHERE name='文档管理'")
        conn.commit()
        print("  [OK] 现有 knowledge_domains 记录填充 code 完成")
    except Exception as e:
        conn.rollback()
        print(f"  [WARN] 填充 code 失败: {e}")

    # ============================================================
    # 4. posts 表 - 新增 domain_id
    # ============================================================
    print("\n[4/17] posts 表 ...")
    exec_sql(conn, cursor,
        "ALTER TABLE posts ADD COLUMN domain_id CHAR(36) NULL AFTER author_agent_id",
        "新增 domain_id 列")
    exec_sql(conn, cursor,
        "ALTER TABLE posts ADD INDEX ix_posts_domain_id (domain_id)",
        "新增 domain_id 索引")
    exec_sql(conn, cursor,
        "ALTER TABLE posts ADD CONSTRAINT fk_posts_domain_id FOREIGN KEY (domain_id) REFERENCES knowledge_domains(id)",
        "新增 domain_id 外键")

    # ============================================================
    # 5. tasks 表 - created_by_agent_id 改为 nullable，新增 created_by_admin_uuid
    # ============================================================
    print("\n[5/17] tasks 表 ...")
    exec_sql(conn, cursor,
        "ALTER TABLE tasks MODIFY COLUMN created_by_agent_id CHAR(36) NULL",
        "created_by_agent_id 改为 nullable")
    exec_sql(conn, cursor,
        "ALTER TABLE tasks ADD COLUMN created_by_admin_uuid CHAR(36) NULL AFTER created_by_agent_id",
        "新增 created_by_admin_uuid 列")
    exec_sql(conn, cursor,
        "ALTER TABLE tasks ADD INDEX ix_tasks_created_by_admin_uuid (created_by_admin_uuid)",
        "新增 created_by_admin_uuid 索引")
    exec_sql(conn, cursor,
        "ALTER TABLE tasks ADD INDEX ix_tasks_status (status)",
        "新增 status 索引")

    # ============================================================
    # 6. task_status_logs 表 - agent_id 改为 nullable，新增 admin_uuid
    # ============================================================
    print("\n[6/17] task_status_logs 表 ...")
    exec_sql(conn, cursor,
        "ALTER TABLE task_status_logs MODIFY COLUMN agent_id CHAR(36) NULL",
        "agent_id 改为 nullable")
    exec_sql(conn, cursor,
        "ALTER TABLE task_status_logs ADD COLUMN admin_uuid CHAR(36) NULL AFTER agent_id",
        "新增 admin_uuid 列")
    exec_sql(conn, cursor,
        "ALTER TABLE task_status_logs ADD INDEX ix_task_status_logs_admin_uuid (admin_uuid)",
        "新增 admin_uuid 索引")

    # ============================================================
    # 7. task_ratings 表 - 新增唯一约束
    # ============================================================
    print("\n[7/17] task_ratings 表 ...")
    exec_sql(conn, cursor,
        "CREATE UNIQUE INDEX uq_task_rating_unique ON task_ratings(task_id, rater_agent_id, rated_agent_id, dimension)",
        "新增唯一约束 uq_task_rating_unique")

    # ============================================================
    # 8. leaderboards 表 - 新增唯一约束
    # ============================================================
    print("\n[8/17] leaderboards 表 ...")
    exec_sql(conn, cursor,
        "CREATE UNIQUE INDEX uq_leaderboard_unique ON leaderboards(agent_id, period, period_start)",
        "新增唯一约束 uq_leaderboard_unique")

    # ============================================================
    # 9. agent_scheduler 表 - 新增索引
    # ============================================================
    print("\n[9/17] agent_scheduler 表 ...")
    exec_sql(conn, cursor,
        "ALTER TABLE agent_scheduler ADD INDEX ix_agent_schedulers_agent_id (agent_id)",
        "新增 agent_id 索引")
    exec_sql(conn, cursor,
        "ALTER TABLE agent_scheduler ADD INDEX ix_agent_schedulers_status (status)",
        "新增 status 索引")
    exec_sql(conn, cursor,
        "ALTER TABLE agent_scheduler ADD INDEX ix_agent_schedulers_enabled (enabled)",
        "新增 enabled 索引")
    exec_sql(conn, cursor,
        "ALTER TABLE agent_scheduler ADD INDEX ix_agent_schedulers_next_run_at (next_run_at)",
        "新增 next_run_at 索引")

    # ============================================================
    # 10. learning_records 表 - 新增 learned_version_id 索引
    # ============================================================
    print("\n[10/17] learning_records 表 ...")
    exec_sql(conn, cursor,
        "ALTER TABLE learning_records ADD INDEX ix_learning_records_learned_version_id (learned_version_id)",
        "新增 learned_version_id 索引")

    # ============================================================
    # 11. suggestions 表 - 重建（新模型差异大）
    # ============================================================
    print("\n[11/17] suggestions 表重建 ...")
    try:
        cursor.execute("DROP TABLE suggestions")
        conn.commit()
        print("  [OK] 旧 suggestions 表已删除")
    except Exception as e:
        print(f"  [SKIP] 删除旧表: {e}")

    exec_sql(conn, cursor,
        """CREATE TABLE suggestions (
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
          INDEX ix_suggestions_category (category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
        "重建 suggestions 表（新结构）")
    try:
        cursor.execute(
            "ALTER TABLE suggestions ADD CONSTRAINT fk_suggestions_agent_id FOREIGN KEY (agent_id) REFERENCES agents(id)"
        )
        print("  [OK] suggestions FK 添加")
    except Exception as e:
        print(f"  [SKIP] suggestions FK: {e}")

    # ============================================================
    # 12. 新建 agent_registration_requests
    # ============================================================
    print("\n[12/17] 新建 agent_registration_requests 表 ...")
    exec_sql(conn, cursor,
        """CREATE TABLE agent_registration_requests (
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
        "创建 agent_registration_requests 表")

    # ============================================================
    # 13. 新建 scheduler_execution_logs
    # ============================================================
    print("\n[13/17] 新建 scheduler_execution_logs 表 ...")
    exec_sql(conn, cursor,
        """CREATE TABLE scheduler_execution_logs (
          id CHAR(36) NOT NULL,
          scheduler_id CHAR(36) NOT NULL,
          started_at DATETIME NOT NULL,
          finished_at DATETIME NULL,
          status VARCHAR(32) NOT NULL,
          result TEXT NULL,
          created_at DATETIME NOT NULL,
          PRIMARY KEY (id),
          INDEX ix_scheduler_execution_logs_scheduler_id (scheduler_id),
          INDEX ix_scheduler_execution_logs_started_at (started_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
        "创建 scheduler_execution_logs 表")
    try:
        cursor.execute(
            "ALTER TABLE scheduler_execution_logs ADD CONSTRAINT fk_scheduler_execution_logs_scheduler_id FOREIGN KEY (scheduler_id) REFERENCES agent_scheduler(id)"
        )
        print("  [OK] scheduler_execution_logs FK 添加")
    except Exception as e:
        print(f"  [SKIP] scheduler_execution_logs FK: {e}")

    # ============================================================
    # 14. 新建 suggestion_replies
    # ============================================================
    print("\n[14/17] 新建 suggestion_replies 表 ...")
    exec_sql(conn, cursor,
        """CREATE TABLE suggestion_replies (
          id CHAR(36) NOT NULL,
          suggestion_id CHAR(36) NOT NULL,
          agent_id CHAR(36) NOT NULL,
          content TEXT NOT NULL,
          created_at DATETIME NOT NULL,
          PRIMARY KEY (id),
          INDEX ix_suggestion_replies_suggestion_id (suggestion_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
        "创建 suggestion_replies 表")
    try:
        cursor.execute(
            "ALTER TABLE suggestion_replies ADD CONSTRAINT fk_suggestion_replies_suggestion_id FOREIGN KEY (suggestion_id) REFERENCES suggestions(id)"
        )
        cursor.execute(
            "ALTER TABLE suggestion_replies ADD CONSTRAINT fk_suggestion_replies_agent_id FOREIGN KEY (agent_id) REFERENCES agents(id)"
        )
        print("  [OK] suggestion_replies FKs 添加")
    except Exception as e:
        print(f"  [SKIP] suggestion_replies FKs: {e}")

    # ============================================================
    # 15. 新建 skills
    # ============================================================
    print("\n[15/17] 新建 skills 表 ...")
    exec_sql(conn, cursor,
        """CREATE TABLE skills (
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
          INDEX ix_skills_uploader_admin_uuid (uploader_admin_uuid)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
        "创建 skills 表")
    try:
        cursor.execute(
            "ALTER TABLE skills ADD CONSTRAINT fk_skills_uploader_agent_id FOREIGN KEY (uploader_agent_id) REFERENCES agents(id)"
        )
        print("  [OK] skills uploader FK 添加")
    except Exception as e:
        print(f"  [SKIP] skills uploader FK: {e}")

    # ============================================================
    # 16. 新建 skill_versions
    # ============================================================
    print("\n[16/17] 新建 skill_versions 表 ...")
    exec_sql(conn, cursor,
        """CREATE TABLE skill_versions (
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
          INDEX ix_skill_versions_created_by_admin_uuid (created_by_admin_uuid)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
        "创建 skill_versions 表")
    try:
        cursor.execute(
            "ALTER TABLE skill_versions ADD CONSTRAINT fk_skill_versions_skill_id FOREIGN KEY (skill_id) REFERENCES skills(id)"
        )
        cursor.execute(
            "ALTER TABLE skill_versions ADD CONSTRAINT fk_skill_versions_created_by_agent_id FOREIGN KEY (created_by_agent_id) REFERENCES agents(id)"
        )
        print("  [OK] skill_versions FKs 添加")
    except Exception as e:
        print(f"  [SKIP] skill_versions FKs: {e}")

    # ============================================================
    # 17. skills.current_version_id FK（需要 skill_versions 已存在）
    # ============================================================
    print("\n[17/17] skills.current_version_id FK ...")
    try:
        cursor.execute(
            "ALTER TABLE skills ADD CONSTRAINT fk_skills_current_version_id FOREIGN KEY (current_version_id) REFERENCES skill_versions(id)"
        )
        print("  [OK] skills.current_version_id FK 添加")
    except Exception as e:
        print(f"  [SKIP] skills.current_version_id FK: {e}")

    # ============================================================
    # agents.registration_request_id FK（需要 agent_registration_requests 已存在）
    # ============================================================
    print("\n[bonus] agents.registration_request_id FK ...")
    try:
        cursor.execute(
            "ALTER TABLE agents ADD CONSTRAINT fk_agents_registration_request_id FOREIGN KEY (registration_request_id) REFERENCES agent_registration_requests(id)"
        )
        print("  [OK] agents.registration_request_id FK 添加")
    except Exception as e:
        print(f"  [SKIP] agents.registration_request_id FK: {e}")

    # ============================================================
    # 更新 alembic_version
    # ============================================================
    print("\n[alembic] 更新版本号 ...")
    try:
        cursor.execute("DELETE FROM alembic_version")
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('011_add_skills')")
        print("  [OK] alembic_version -> 011_add_skills")
    except Exception as e:
        print(f"  [ERR] alembic_version: {e}")

    # ============================================================
    # 提交所有更改
    # ============================================================
    try:
        conn.commit()
        print("\n[PASS] 所有更改已提交!")
    except Exception as e:
        conn.rollback()
        print(f"\n[FAIL] 提交失败，已回滚: {e}")
        sys.exit(1)

    cursor.close()
    conn.close()

    # ============================================================
    # 验证
    # ============================================================
    print("\n" + "=" * 60)
    print("验证迁移结果...")
    conn2 = get_conn()
    cursor2 = conn2.cursor()

    cursor2.execute("SELECT version_num FROM alembic_version")
    version = cursor2.fetchone()[0]
    print(f"  alembic_version: {version}")

    cursor2.execute("SHOW TABLES")
    tables = sorted([r[0] for r in cursor2.fetchall()])
    print(f"  当前表数量: {len(tables)}")
    print(f"  表清单: {', '.join(tables)}")

    # 验证新增的表存在
    new_tables = ['skills', 'skill_versions', 'agent_registration_requests', 'suggestion_replies', 'scheduler_execution_logs']
    for t in new_tables:
        if t in tables:
            print(f"    [OK] {t} 存在")
        else:
            print(f"    [MISSING] {t} 不存在!")

    cursor2.close()
    conn2.close()
    print("\n迁移完成!")

if __name__ == '__main__':
    run_migration()
