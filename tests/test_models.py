"""Tests for all 8 models."""

from datetime import datetime, timezone
from app.models import Agent, AgentCredential, ApiNonce, SecurityEventLog, LearningRecord, Post, PostVersion, PostAsset


def test_agent_model():
    agent = Agent(
        agent_code="test-agent-001",
        name="Test Agent",
    )
    assert agent.name == "Test Agent"
    assert agent.agent_code == "test-agent-001"


def test_agent_credential_model():
    cred = AgentCredential(
        agent_id="agent-001",
        access_key="key123",
        secret_key_encrypted="encrypted_secret",
    )
    assert cred.access_key == "key123"


def test_api_nonce_model():
    nonce = ApiNonce(
        agent_id="agent-001",
        nonce="test-nonce-123",
        expires_at=datetime.utcnow(),
    )
    assert nonce.nonce == "test-nonce-123"


def test_security_event_log_model():
    event = SecurityEventLog(
        agent_id="agent-001",
        event_type="authentication",
        detail="Test event",
    )
    assert event.event_type == "authentication"


def test_learning_record_model():
    record = LearningRecord(
        learner_agent_id="agent-001",
        post_id="post-001",
        learned_version_id="version-001",
        learned_version_no=1,
    )
    assert record.learned_version_no == 1


def test_post_model():
    post = Post(
        author_agent_id="agent-001",
        title="Test Post",
    )
    assert post.title == "Test Post"


def test_post_version_model():
    version = PostVersion(
        post_id="post-001",
        version_no=1,
        title_snapshot="Test Title",
        change_type="MINOR",
        created_by_agent_id="agent-001",
    )
    assert version.version_no == 1


def test_post_asset_model():
    asset = PostAsset(
        post_id="post-001",
        original_filename="test.pdf",
        stored_object_key="obj-key-001",
        file_size=1024,
        sha256="abc123",
        created_by_agent_id="agent-001",
    )
    assert asset.original_filename == "test.pdf"
