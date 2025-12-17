from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class TestResult:
    name: str
    passed: bool
    duration: float
    error: str | None = None


@dataclass
class CIReport:
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    duration: float = 0.0
    coverage_percent: float = 0.0
    vulnerabilities: List[Dict[str, str]] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 100.0
        return (self.passed_tests / self.total_tests) * 100
    
    def generate_summary(self) -> str:
        status = "✅" if self.failed_tests == 0 else "❌"
        lines = [
            "",
            f"{status} Senytl Test Results",
            "",
            f"✅ {self.passed_tests}/{self.total_tests} tests passed ({self.pass_rate():.0f}%)",
        ]
        
        if self.failed_tests > 0:
            lines.append(f"❌ {self.failed_tests} tests failed")
        if self.skipped_tests > 0:
            lines.append(f"⏭️  {self.skipped_tests} tests skipped")
        
        if self.vulnerabilities:
            lines.append(f"⚠️  {len(self.vulnerabilities)} vulnerabilities detected")
        
        lines.append("")
        
        if self.failed_tests > 0:
            lines.append("Failed Tests:")
            for result in self.test_results:
                if not result.passed:
                    lines.append(f"  • {result.name}: {result.error or 'Unknown error'}")
            lines.append("")
        
        if self.vulnerabilities:
            lines.append("Vulnerabilities:")
            for vuln in self.vulnerabilities:
                severity_icon = "🔴" if vuln["severity"] == "CRITICAL" else "🟡" if vuln["severity"] == "MEDIUM" else "🟢"
                lines.append(f"  {severity_icon} {vuln['severity']}: {vuln['message']}")
            lines.append("")
        
        if self.coverage_percent > 0:
            lines.append(f"Coverage: {self.coverage_percent:.0f}%")
        
        lines.append(f"Duration: {self.duration:.2f}s")
        lines.append("")
        
        return "\n".join(lines)
    
    def generate_pr_comment(self, previous_report: CIReport | None = None) -> str:
        lines = [
            "🛡️ Senytl Test Results",
            "",
        ]
        
        status = "✅" if self.failed_tests == 0 else "❌"
        lines.append(f"{status} {self.passed_tests}/{self.total_tests} tests passed ({self.pass_rate():.0f}%)")
        
        if self.failed_tests > 0:
            lines.append(f"❌ {self.failed_tests} tests failed")
        if self.vulnerabilities:
            lines.append(f"⚠️  {len(self.vulnerabilities)} new vulnerabilities detected")
        
        lines.append("")
        
        if self.failed_tests > 0:
            lines.append("Failed Tests:")
            for result in self.test_results[:5]:
                if not result.passed:
                    error_msg = result.error[:60] if result.error else "Unknown error"
                    lines.append(f"  • {result.name}: {error_msg}")
            if self.failed_tests > 5:
                lines.append(f"  ... and {self.failed_tests - 5} more")
            lines.append("")
        
        if self.vulnerabilities:
            lines.append("Vulnerabilities:")
            for vuln in self.vulnerabilities[:3]:
                severity_icon = "🔴" if vuln["severity"] == "CRITICAL" else "🟡" if vuln["severity"] == "MEDIUM" else "🟢"
                lines.append(f"  {severity_icon} {vuln['severity']}: {vuln['message']}")
            if len(self.vulnerabilities) > 3:
                lines.append(f"  ... and {len(self.vulnerabilities) - 3} more")
            lines.append("")
        
        if previous_report and self.coverage_percent > 0:
            diff = self.coverage_percent - previous_report.coverage_percent
            sign = "+" if diff > 0 else ""
            lines.append(f"Coverage Change: {previous_report.coverage_percent:.0f}% → {self.coverage_percent:.0f}% ({sign}{diff:.0f}%)")
            lines.append("")
        elif self.coverage_percent > 0:
            lines.append(f"Coverage: {self.coverage_percent:.0f}%")
            lines.append("")
        
        return "\n".join(lines)
    
    def save_json(self, path: Path) -> None:
        data = {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "duration": self.duration,
            "coverage_percent": self.coverage_percent,
            "pass_rate": self.pass_rate(),
            "vulnerabilities": self.vulnerabilities,
            "test_results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration": r.duration,
                    "error": r.error,
                }
                for r in self.test_results
            ],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def load_json(path: Path) -> CIReport:
        if not path.exists():
            return CIReport()
        
        with open(path) as f:
            data = json.load(f)
        
        report = CIReport(
            total_tests=data.get("total_tests", 0),
            passed_tests=data.get("passed_tests", 0),
            failed_tests=data.get("failed_tests", 0),
            skipped_tests=data.get("skipped_tests", 0),
            duration=data.get("duration", 0.0),
            coverage_percent=data.get("coverage_percent", 0.0),
            vulnerabilities=data.get("vulnerabilities", []),
        )
        
        for result_data in data.get("test_results", []):
            report.test_results.append(TestResult(
                name=result_data["name"],
                passed=result_data["passed"],
                duration=result_data["duration"],
                error=result_data.get("error"),
            ))
        
        return report


def generate_github_workflow() -> str:
    return """name: Senytl Agent Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .[pytest]
          pip install pytest-xdist
      
      - name: Run Senytl tests
        run: |
          pytest --senytl-coverage --ci --tb=short
      
      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: senytl-coverage
          path: .senytl/coverage.json
      
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('.senytl/ci-report.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
"""


def is_ci_environment() -> bool:
    ci_vars = ["CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI", "JENKINS_URL"]
    return any(os.getenv(var) for var in ci_vars)


def get_previous_report_path() -> Path:
    return Path.cwd() / ".senytl" / "previous-ci-report.json"


def save_ci_report(report: CIReport) -> None:
    report_dir = Path.cwd() / ".senytl"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report.save_json(report_dir / "ci-report.json")
    
    summary_path = report_dir / "ci-report.txt"
    with open(summary_path, "w") as f:
        f.write(report.generate_summary())
    
    pr_comment_path = report_dir / "pr-comment.txt"
    previous = CIReport.load_json(get_previous_report_path())
    with open(pr_comment_path, "w") as f:
        f.write(report.generate_pr_comment(previous))
    
    report.save_json(get_previous_report_path())
