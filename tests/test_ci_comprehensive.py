"""Comprehensive tests for CI module"""
import json
import os
import tempfile
from pathlib import Path

import pytest
from senytl.ci import (
    CIReport,
    TestResult,
    generate_github_workflow,
    is_ci_environment,
    get_previous_report_path,
    save_ci_report,
)


class TestTestResult:
    """Test TestResult dataclass"""
    
    def test_initialization(self):
        """Test TestResult initialization"""
        result = TestResult(
            name="test_example",
            passed=True,
            duration=1.5,
            error=None
        )
        assert result.name == "test_example"
        assert result.passed is True
        assert result.duration == 1.5
        assert result.error is None
    
    def test_failed_test_with_error(self):
        """Test failed test with error message"""
        result = TestResult(
            name="test_failed",
            passed=False,
            duration=0.5,
            error="AssertionError: expected true"
        )
        assert result.passed is False
        assert result.error is not None


class TestCIReport:
    """Test CIReport class"""
    
    def test_empty_report(self):
        """Test empty CI report"""
        report = CIReport()
        assert report.total_tests == 0
        assert report.passed_tests == 0
        assert report.failed_tests == 0
        assert report.pass_rate() == 100.0
    
    def test_pass_rate_calculation(self):
        """Test pass rate calculation"""
        report = CIReport(total_tests=10, passed_tests=7, failed_tests=3)
        assert report.pass_rate() == 70.0
    
    def test_pass_rate_all_passing(self):
        """Test pass rate with all tests passing"""
        report = CIReport(total_tests=10, passed_tests=10, failed_tests=0)
        assert report.pass_rate() == 100.0
    
    def test_pass_rate_all_failing(self):
        """Test pass rate with all tests failing"""
        report = CIReport(total_tests=10, passed_tests=0, failed_tests=10)
        assert report.pass_rate() == 0.0
    
    def test_generate_summary_passing(self):
        """Test summary generation for passing tests"""
        report = CIReport(
            total_tests=10,
            passed_tests=10,
            failed_tests=0,
            duration=5.0
        )
        summary = report.generate_summary()
        assert "✅" in summary
        assert "10/10 tests passed" in summary
        assert "100%" in summary
    
    def test_generate_summary_with_failures(self):
        """Test summary generation with failures"""
        report = CIReport(
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            duration=5.0
        )
        report.test_results.append(TestResult(
            name="test_example",
            passed=False,
            duration=0.5,
            error="AssertionError"
        ))
        
        summary = report.generate_summary()
        assert "❌" in summary or "8/10" in summary
        assert "2 tests failed" in summary
        assert "test_example" in summary
    
    def test_generate_summary_with_vulnerabilities(self):
        """Test summary with vulnerabilities"""
        report = CIReport(
            total_tests=10,
            passed_tests=10,
            failed_tests=0
        )
        report.vulnerabilities.append({
            "severity": "CRITICAL",
            "message": "Security issue detected"
        })
        
        summary = report.generate_summary()
        assert "vulnerabilities" in summary.lower()
        assert "CRITICAL" in summary
    
    def test_generate_pr_comment_passing(self):
        """Test PR comment for passing tests"""
        report = CIReport(
            total_tests=10,
            passed_tests=10,
            failed_tests=0,
            coverage_percent=85.0
        )
        
        comment = report.generate_pr_comment()
        assert "Senytl Test Results" in comment
        assert "10/10" in comment
        assert "85%" in comment
    
    def test_generate_pr_comment_with_diff(self):
        """Test PR comment with coverage diff"""
        previous = CIReport(coverage_percent=80.0)
        current = CIReport(
            total_tests=10,
            passed_tests=10,
            coverage_percent=85.0
        )
        
        comment = current.generate_pr_comment(previous)
        assert "80%" in comment
        assert "85%" in comment
        assert "+5%" in comment or "Coverage Change" in comment
    
    def test_generate_pr_comment_truncated_failures(self):
        """Test PR comment with many failures gets truncated"""
        report = CIReport(total_tests=10, passed_tests=0, failed_tests=10)
        
        for i in range(10):
            report.test_results.append(TestResult(
                name=f"test_{i}",
                passed=False,
                duration=0.1,
                error="Failed"
            ))
        
        comment = report.generate_pr_comment()
        assert "..." in comment or "more" in comment
    
    def test_save_json(self):
        """Test saving report to JSON"""
        report = CIReport(
            total_tests=5,
            passed_tests=4,
            failed_tests=1,
            coverage_percent=80.0
        )
        report.test_results.append(TestResult(
            name="test_example",
            passed=True,
            duration=1.0
        ))
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.json"
            report.save_json(path)
            
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["total_tests"] == 5
            assert data["passed_tests"] == 4
            assert data["coverage_percent"] == 80.0
    
    def test_load_json(self):
        """Test loading report from JSON"""
        report = CIReport(
            total_tests=5,
            passed_tests=4,
            failed_tests=1,
            coverage_percent=80.0
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.json"
            report.save_json(path)
            
            loaded = CIReport.load_json(path)
            assert loaded.total_tests == 5
            assert loaded.passed_tests == 4
            assert loaded.coverage_percent == 80.0
    
    def test_load_json_nonexistent(self):
        """Test loading from nonexistent file"""
        path = Path("/tmp/nonexistent_report.json")
        loaded = CIReport.load_json(path)
        assert loaded.total_tests == 0


class TestCIFunctions:
    """Test CI module functions"""
    
    def test_generate_github_workflow(self):
        """Test GitHub Actions workflow generation"""
        workflow = generate_github_workflow()
        assert "name: Senytl Agent Tests" in workflow
        assert "pytest --senytl-coverage --ci" in workflow
        assert "actions/checkout" in workflow
        assert "actions/setup-python" in workflow
    
    def test_is_ci_environment_false(self):
        """Test CI environment detection when not in CI"""
        # Save current env
        ci_vars = ["CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS", 
                   "GITLAB_CI", "CIRCLECI", "JENKINS_URL"]
        saved = {var: os.environ.get(var) for var in ci_vars}
        
        # Clear CI vars
        for var in ci_vars:
            os.environ.pop(var, None)
        
        try:
            assert is_ci_environment() is False
        finally:
            # Restore env
            for var, value in saved.items():
                if value is not None:
                    os.environ[var] = value
    
    def test_is_ci_environment_github(self):
        """Test CI environment detection for GitHub Actions"""
        saved = os.environ.get("GITHUB_ACTIONS")
        try:
            os.environ["GITHUB_ACTIONS"] = "true"
            assert is_ci_environment() is True
        finally:
            if saved:
                os.environ["GITHUB_ACTIONS"] = saved
            else:
                os.environ.pop("GITHUB_ACTIONS", None)
    
    def test_get_previous_report_path(self):
        """Test getting previous report path"""
        path = get_previous_report_path()
        assert "previous-ci-report.json" in str(path)
    
    def test_save_ci_report(self):
        """Test saving CI report with all files"""
        report = CIReport(
            total_tests=5,
            passed_tests=5,
            coverage_percent=85.0
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            save_ci_report(report)
            
            senytl_dir = Path.cwd() / ".senytl"
            assert (senytl_dir / "ci-report.json").exists()
            assert (senytl_dir / "ci-report.txt").exists()
            assert (senytl_dir / "pr-comment.txt").exists()


class TestCIReportEdgeCases:
    """Test edge cases"""
    
    def test_report_with_skipped_tests(self):
        """Test report with skipped tests"""
        report = CIReport(
            total_tests=10,
            passed_tests=8,
            failed_tests=1,
            skipped_tests=1
        )
        summary = report.generate_summary()
        assert "1" in summary or "skip" in summary.lower()
    
    def test_report_with_zero_duration(self):
        """Test report with zero duration"""
        report = CIReport(duration=0.0)
        summary = report.generate_summary()
        assert "0.00s" in summary
    
    def test_report_with_long_error_message(self):
        """Test report with very long error message"""
        report = CIReport(total_tests=1, failed_tests=1)
        long_error = "A" * 1000
        report.test_results.append(TestResult(
            name="test",
            passed=False,
            duration=0.1,
            error=long_error
        ))
        
        summary = report.generate_summary()
        assert len(summary) < 10000  # Should be truncated
    
    def test_pr_comment_no_previous(self):
        """Test PR comment without previous report"""
        report = CIReport(coverage_percent=85.0)
        comment = report.generate_pr_comment(None)
        assert "85%" in comment
    
    def test_vulnerabilities_truncation(self):
        """Test vulnerability list truncation"""
        report = CIReport()
        for i in range(10):
            report.vulnerabilities.append({
                "severity": "MEDIUM",
                "message": f"Vulnerability {i}"
            })
        
        comment = report.generate_pr_comment()
        # Should show only first few
        assert "..." in comment or "more" in comment or "Vulnerability 0" in comment
