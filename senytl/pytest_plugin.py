from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from . import get_default_senytl
from .ci import CIReport, TestResult, is_ci_environment, save_ci_report
from .coverage import get_coverage_tracker, reset_coverage_tracker


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("senytl")
    group.addoption(
        "--senytl-coverage",
        action="store_true",
        default=False,
        help="Enable Senytl coverage tracking and reporting"
    )
    group.addoption(
        "--ci",
        action="store_true",
        default=False,
        help="Enable CI mode with enhanced reporting"
    )


def pytest_configure(config: Any) -> None:
    config.addinivalue_line("markers", "senytl_agent: enable Senytl agent helpers")
    config.addinivalue_line("markers", "senytl_mock: enable Senytl mock engine")
    config.addinivalue_line("markers", "senytl_adversarial: adversarial test case")
    
    if config.getoption("--senytl-coverage") or config.getoption("--ci"):
        reset_coverage_tracker()
        config._senytl_start_time = time.time()
        config._senytl_ci_report = CIReport()


def pytest_runtest_logreport(report: Any) -> None:
    if not hasattr(report, "config"):
        return
    
    config = report.config
    if not hasattr(config, "_senytl_ci_report"):
        return
    
    if not (config.getoption("--senytl-coverage") or config.getoption("--ci")):
        return
    
    if report.when == "call":
        ci_report: CIReport = config._senytl_ci_report
        ci_report.total_tests += 1
        
        if report.passed:
            ci_report.passed_tests += 1
        elif report.failed:
            ci_report.failed_tests += 1
        elif report.skipped:
            ci_report.skipped_tests += 1
        
        test_result = TestResult(
            name=report.nodeid,
            passed=report.passed,
            duration=report.duration,
            error=str(report.longrepr) if report.failed else None
        )
        ci_report.test_results.append(test_result)


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: Any) -> None:
    if not (config.getoption("--senytl-coverage") or config.getoption("--ci")):
        return
    
    tracker = get_coverage_tracker()
    ci_report: CIReport = config._senytl_ci_report
    
    if config.getoption("--senytl-coverage"):
        report_dir = Path.cwd() / ".senytl"
        report_dir.mkdir(parents=True, exist_ok=True)
        tracker.save_report(report_dir / "coverage.json")
        
        terminalreporter.write_line("")
        terminalreporter.write_line(tracker.generate_report())
        
        if ci_report:
            ci_report.coverage_percent = tracker.stats.tool_coverage_percent()
    
    if config.getoption("--ci") or is_ci_environment():
        ci_report.duration = time.time() - config._senytl_start_time
        save_ci_report(ci_report)
        
        terminalreporter.write_line("")
        terminalreporter.write_line(ci_report.generate_summary())


def pytest_runtest_setup(item: Any) -> None:
    if item.get_closest_marker("senytl_agent") or item.get_closest_marker("senytl_mock"):
        if "senytl" not in item.fixturenames:
            item.fixturenames.append("senytl")
    
    if item.config.getoption("--senytl-coverage") or item.config.getoption("--ci"):
        tracker = get_coverage_tracker()
        tracker.increment_test_count()


@pytest.fixture
def senytl() -> Any:
    s = get_default_senytl()
    s.reset()
    s.install()
    yield s
    s.reset()
    s.uninstall()


@pytest.fixture
def senytl_agent(senytl: Any):
    def _wrap(agent: Any) -> Any:
        return senytl.wrap(agent)

    return _wrap
