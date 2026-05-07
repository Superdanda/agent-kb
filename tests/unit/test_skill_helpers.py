import pytest

from app.core.exceptions import ValidationError
from app.services.skill_service import SkillService, _version_key


def test_version_key_orders_semver_like_versions():
    assert _version_key("1.1.0") > _version_key("1.0.9")
    assert _version_key("2.0.0") > _version_key("1.999.999")


def test_normalize_tags_lowercases_deduplicates_and_keeps_order():
    service = SkillService.__new__(SkillService)

    assert service._normalize_tags(["Legal", "legal", "contract"]) == ["legal", "contract"]


def test_normalize_tags_rejects_invalid_values():
    service = SkillService.__new__(SkillService)

    with pytest.raises(ValidationError):
        service._normalize_tags(["合同 审核"])


def test_normalize_tags_rejects_more_than_ten_tags():
    service = SkillService.__new__(SkillService)

    with pytest.raises(ValidationError):
        service._normalize_tags([f"tag-{i}" for i in range(11)])
