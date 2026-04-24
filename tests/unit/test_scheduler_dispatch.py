from app.services.scheduler_dispatch import TaskBoardDispatchHandler, resolve_dispatch_handler


def test_scheduler_dispatch_title_prefix_is_removed():
    handler = TaskBoardDispatchHandler()

    assert handler._normalize_title("task:整理 OpenAPI 文档") == "整理 OpenAPI 文档"
    assert handler._normalize_title("nightly") == "Scheduled task: nightly"


def test_scheduler_resolves_default_handler_for_unknown_task_name():
    assert isinstance(resolve_dispatch_handler("nightly"), TaskBoardDispatchHandler)
