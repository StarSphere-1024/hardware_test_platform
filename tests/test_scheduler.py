"""
Tests for scheduler module.

测试调度器模块
"""
import time
import pytest
from typing import List, Any

from framework.core.scheduler import Scheduler, ExecutionContext


class TestExecutionContext:
    """测试执行上下文"""

    def test_create_default(self):
        """测试创建默认上下文"""
        ctx = ExecutionContext(fixture_name="test_fixture", case_name="test_case")
        assert ctx.fixture_name == "test_fixture"
        assert ctx.case_name == "test_case"
        assert ctx.loop_idx == 0
        assert ctx.retry_count == 0
        assert ctx.sn is None
        assert ctx.sku is None

    def test_create_with_values(self):
        """测试带值创建上下文"""
        ctx = ExecutionContext(
            fixture_name="test_fixture",
            case_name="test_case",
            loop_idx=5,
            retry_count=2,
            sn="SN12345",
            sku="CM4",
        )
        assert ctx.loop_idx == 5
        assert ctx.retry_count == 2
        assert ctx.sn == "SN12345"
        assert ctx.sku == "CM4"

    def test_elapsed_seconds(self):
        """测试经过时间计算"""
        ctx = ExecutionContext(fixture_name="test", case_name="test")
        time.sleep(0.1)
        assert ctx.elapsed_seconds >= 0.1


class TestSchedulerSequential:
    """测试串行执行"""

    def test_execute_sequential_all_success(self):
        """测试串行执行全部成功"""
        scheduler = Scheduler()
        results = []

        def make_task(value):
            def task():
                results.append(value)
                return {"status": "pass", "value": value}
            return task

        tasks = [make_task(1), make_task(2), make_task(3)]
        scheduler.execute_sequential(tasks)

        assert results == [1, 2, 3]

    def test_execute_sequential_stop_on_failure(self):
        """测试串行执行失败停止"""
        scheduler = Scheduler()
        results = []

        def make_task(value, fail=False):
            def task():
                results.append(value)
                if fail:
                    return type('Result', (), {"status": "fail"})()
                return type('Result', (), {"status": "pass"})()
            return task

        tasks = [
            make_task(1),
            make_task(2, fail=True),
            make_task(3),
        ]
        scheduler.execute_sequential(tasks, stop_on_failure=True)

        # 应该在第二个任务失败后停止
        assert results == [1, 2]

    def test_execute_sequential_exception_handling(self):
        """测试串行执行异常处理"""
        scheduler = Scheduler()

        def good_task():
            return {"status": "pass"}

        def bad_task():
            raise RuntimeError("Task failed")

        tasks = [good_task, bad_task, good_task]
        results = scheduler.execute_sequential(tasks)

        assert len(results) == 3
        assert results[0] == {"status": "pass"}
        assert "error" in results[1]


class TestSchedulerParallel:
    """测试并行执行"""

    def test_execute_parallel(self):
        """测试并行执行"""
        scheduler = Scheduler(max_workers=2)
        results = {}

        def make_task(name, value):
            def task():
                return {name: value}
            return task

        tasks = [
            ("task1", make_task("task1", 1)),
            ("task2", make_task("task2", 2)),
        ]
        results = scheduler.execute_parallel(tasks, max_workers=2)

        assert len(results) == 2
        assert results["task1"] == {"task1": 1}
        assert results["task2"] == {"task2": 2}

    def test_execute_parallel_exception_handling(self):
        """测试并行执行异常处理"""
        scheduler = Scheduler(max_workers=2)

        def good_task():
            return {"status": "pass"}

        def bad_task():
            raise RuntimeError("Parallel task failed")

        tasks = [
            ("good", good_task),
            ("bad", bad_task),
        ]
        results = scheduler.execute_parallel(tasks)

        assert "good" in results
        assert "error" in results["bad"]


class TestSchedulerLoops:
    """测试循环执行"""

    def test_run_with_loops(self):
        """测试循环运行"""
        scheduler = Scheduler()
        loop_count = 3
        results = []

        def run_func():
            results.append(len(results) + 1)
            return {"status": "pass"}

        scheduler.run_with_loops(
            run_func,
            loop_count=loop_count,
            loop_interval=0,
        )

        assert len(results) == loop_count
        assert results == [1, 2, 3]

    def test_run_with_loops_with_interval(self):
        """测试带间隔的循环运行"""
        scheduler = Scheduler()
        loop_count = 3
        start_time = time.time()

        def run_func():
            return {"status": "pass"}

        scheduler.run_with_loops(
            run_func,
            loop_count=loop_count,
            loop_interval=1,  # 1 second interval
        )

        # Should take at least 2 seconds (intervals between loops)
        elapsed = time.time() - start_time
        assert elapsed >= 2.0

    def test_run_with_loops_progress_callback(self):
        """测试循环运行的进度回调"""
        scheduler = Scheduler()
        progress_calls = []

        def run_func():
            return {"status": "pass"}

        def progress_callback(current, total):
            progress_calls.append((current, total))

        scheduler.run_with_loops(
            run_func,
            loop_count=5,
            loop_interval=0,
            progress_callback=progress_callback,
        )

        assert len(progress_calls) == 5
        assert progress_calls[0] == (1, 5)
        assert progress_calls[-1] == (5, 5)


class TestSchedulerRetry:
    """测试重试机制"""

    def test_run_with_retry_success_first_try(self):
        """测试重试 - 第一次就成功"""
        scheduler = Scheduler()
        call_count = 0

        def run_func():
            nonlocal call_count
            call_count += 1
            return {"code": 0}

        result, retry_count = scheduler.run_with_retry(
            run_func,
            retry_count=3,
            retry_interval=0,
        )

        assert call_count == 1
        assert retry_count == 0
        assert result["code"] == 0

    def test_run_with_retry_success_after_failures(self):
        """测试重试 - 失败后成功"""
        scheduler = Scheduler()
        call_count = 0

        def run_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return {"code": -1}  # Fail
            return {"code": 0}  # Success

        result, retry_count = scheduler.run_with_retry(
            run_func,
            retry_count=3,
            retry_interval=0,
        )

        assert call_count == 3
        assert retry_count == 2
        assert result["code"] == 0

    def test_run_with_retry_all_failures(self):
        """测试重试 - 全部失败"""
        scheduler = Scheduler()
        call_count = 0

        def run_func():
            nonlocal call_count
            call_count += 1
            return {"code": -1}

        result, retry_count = scheduler.run_with_retry(
            run_func,
            retry_count=3,
            retry_interval=0,
        )

        assert call_count == 4  # Initial + 3 retries
        assert retry_count == 3
        assert result["code"] == -1

    def test_run_with_retry_result_object(self):
        """测试重试 - 使用结果对象"""
        scheduler = Scheduler()

        class Result:
            def __init__(self, success):
                self.success = success

        call_count = 0

        def run_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return Result(success=False)
            return Result(success=True)

        result, retry_count = scheduler.run_with_retry(
            run_func,
            retry_count=3,
            retry_interval=0,
        )

        assert call_count == 2
        assert result.success is True


class TestSchedulerContext:
    """测试上下文管理"""

    def test_create_context(self):
        """测试创建上下文"""
        scheduler = Scheduler()
        ctx = scheduler.create_context(
            fixture_name="test_fixture",
            case_name="test_case",
            sn="SN12345",
            sku="CM4",
            loop_idx=2,
        )

        assert ctx.fixture_name == "test_fixture"
        assert ctx.case_name == "test_case"
        assert ctx.sn == "SN12345"
        assert ctx.sku == "CM4"
        assert ctx.loop_idx == 2

    def test_current_context(self):
        """测试当前上下文获取"""
        scheduler = Scheduler()
        assert scheduler.current_context is None

        scheduler.create_context("test")
        assert scheduler.current_context is not None
        assert scheduler.current_context.fixture_name == "test"


class TestSchedulerSummary:
    """测试汇总"""

    def test_get_summary_dict_results(self):
        """测试获取字典结果汇总"""
        scheduler = Scheduler()
        results = [
            {"code": 0},
            {"code": 0},
            {"code": -1},
        ]
        summary = scheduler.get_summary(results)

        assert summary["total"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert abs(summary["pass_rate"] - 2/3) < 0.01

    def test_get_summary_object_results(self):
        """测试获取对象结果汇总"""
        scheduler = Scheduler()

        class Result:
            def __init__(self, success):
                self.success = success

        results = [
            Result(success=True),
            Result(success=True),
            Result(success=False),
        ]
        summary = scheduler.get_summary(results)

        assert summary["total"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1

    def test_get_summary_empty(self):
        """测试空结果汇总"""
        scheduler = Scheduler()
        summary = scheduler.get_summary([])

        assert summary["total"] == 0
        assert summary["passed"] == 0
        assert summary["failed"] == 0
        assert summary["pass_rate"] == 0.0
