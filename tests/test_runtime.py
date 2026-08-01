from forge.runtime import RuntimeEngine


def test_runtime_engine_executes_tasks_by_priority() -> None:
    engine = RuntimeEngine()
    second = engine.scheduler.submit(lambda: "second", priority=20)
    first = engine.scheduler.submit(lambda: "first", priority=10)

    outcomes = engine.run()

    assert [outcome.task_id for outcome in outcomes] == [first, second]
    assert [outcome.result for outcome in outcomes] == ["first", "second"]


def test_runtime_engine_captures_task_failure() -> None:
    def fail() -> None:
        raise ValueError("failure")

    engine = RuntimeEngine()
    engine.submit(fail)
    outcome = engine.run()[0]

    assert not outcome.succeeded
    assert isinstance(outcome.error, ValueError)
