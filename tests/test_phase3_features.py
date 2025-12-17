"""Tests for Phase 3: Scale & Production-Ready features"""
import pytest
from pathlib import Path

from senytl import expect, multi_agent
from senytl.coverage import CoverageTracker, get_coverage_tracker
from senytl.generation import AgentAnalyzer, TestGenerator
from senytl.ci import CIReport, TestResult
from senytl.models import ToolCall


def test_coverage_tracker():
    """Test that coverage tracker records tools and generates reports"""
    tracker = CoverageTracker()
    
    tracker.register_available_tools(["search", "create", "delete", "update"])
    tracker.record_tool_call(ToolCall(name="search", args={}))
    tracker.record_tool_call(ToolCall(name="create", args={}))
    tracker.increment_test_count()
    tracker.record_input("test input 1")
    tracker.record_input("test input 2")
    
    assert len(tracker.stats.tools_tested) == 2
    assert len(tracker.stats.tools_available) == 4
    assert tracker.stats.tool_coverage_percent() == 50.0
    
    report = tracker.generate_report()
    assert "Coverage Report" in report
    assert "2/4 tools" in report


def test_multi_agent_system():
    """Test multi-agent system orchestration"""
    def agent1(msg: str) -> str:
        return f"Agent1 processed: {msg}"
    
    def agent2(msg: str) -> str:
        return f"Agent2 processed: {msg}"
    
    system = multi_agent.System([
        ("agent1", agent1),
        ("agent2", agent2),
    ])
    
    system.route("agent1", "agent2")
    
    result = system.run_scenario([
        ("agent1", "Hello"),
    ])
    
    assert result.completed
    assert len(result.executions) == 2
    assert result.agent("agent1").executions[0].output == "Agent1 processed: Hello"


def test_multi_agent_assertions():
    """Test multi-agent assertion helpers"""
    def agent1(msg: str) -> str:
        return "success"
    
    system = multi_agent.System([("agent1", agent1)])
    result = system.run_scenario([("agent1", "test")])
    
    multi_agent.assert_workflow_completed(result)
    multi_agent.assert_no_deadlocks(result)


def test_agent_analyzer():
    """Test agent code analysis for test generation"""
    test_code = '''
def search_tool(query):
    """Search for items"""
    pass

def delete_account(user_id):
    """Delete user account"""
    pass
'''
    
    test_file = Path("/tmp/test_agent.py")
    test_file.write_text(test_code)
    
    analyzer = AgentAnalyzer(test_file)
    analysis = analyzer.analyze()
    
    assert "tools" in analysis
    assert "patterns" in analysis
    
    test_file.unlink()


def test_test_generator():
    """Test that test generator creates valid test code"""
    generator = TestGenerator()
    
    generator._generate_tool_tests(["search", "create"])
    
    assert len(generator.test_cases) == 2
    assert "test_search_usage" in generator.test_cases[0]
    assert "test_create_usage" in generator.test_cases[1]


def test_ci_report_generation():
    """Test CI report generation"""
    report = CIReport(
        total_tests=10,
        passed_tests=8,
        failed_tests=2,
        duration=5.5,
        coverage_percent=75.0,
    )
    
    report.test_results.append(TestResult(
        name="test_example",
        passed=False,
        duration=0.5,
        error="AssertionError: expected true"
    ))
    
    summary = report.generate_summary()
    assert "8/10 tests passed" in summary
    assert "2 tests failed" in summary
    assert "test_example" in summary
    
    pr_comment = report.generate_pr_comment()
    assert "Senytl Test Results" in pr_comment
    assert "80%" in pr_comment


def test_ci_report_pass_rate():
    """Test CI report calculates pass rate correctly"""
    report = CIReport(total_tests=100, passed_tests=85, failed_tests=15)
    assert report.pass_rate() == 85.0


def test_coverage_quality_scoring():
    """Test coverage quality score calculation"""
    tracker = CoverageTracker()
    tracker.register_available_tools(["tool1", "tool2", "tool3", "tool4"])
    tracker.record_tool_call(ToolCall(name="tool1", args={}))
    tracker.record_tool_call(ToolCall(name="tool2", args={}))
    tracker.record_tool_call(ToolCall(name="tool3", args={}))
    
    for i in range(10):
        tracker.record_input(f"input {i}")
        tracker.increment_test_count()
    
    score = tracker.stats.overall_quality_score()
    assert score > 50.0
    assert score <= 100.0


def test_multi_agent_message_passing():
    """Test that messages are recorded in multi-agent systems"""
    def agent1(msg: str) -> str:
        return "response1"
    
    def agent2(msg: str) -> str:
        return "response2"
    
    system = multi_agent.System([
        ("agent1", agent1),
        ("agent2", agent2),
    ])
    
    system.route("agent1", "agent2")
    result = system.run_scenario([("agent1", "start")])
    
    assert len(result.messages) >= 2
    assert result.messages[0].from_agent == "user"
    assert result.messages[0].to_agent == "agent1"


def test_multi_agent_error_handling():
    """Test that multi-agent systems handle errors gracefully"""
    def failing_agent(msg: str) -> str:
        raise ValueError("Agent error")
    
    system = multi_agent.System([("agent1", failing_agent)])
    result = system.run_scenario([("agent1", "test")])
    
    assert not result.completed
    assert result.executions[0].error is not None


def test_multi_agent_visualization():
    """Test that flow visualization generates output"""
    def agent1(msg: str) -> str:
        return "response"
    
    system = multi_agent.System([("agent1", agent1)])
    result = system.run_scenario([("agent1", "test")])
    
    flow = result.visualize_flow()
    assert "Agent Interaction Flow" in flow
    assert "agent1" in flow


def test_ci_report_json_serialization():
    """Test CI report can be saved and loaded from JSON"""
    import tempfile
    
    report = CIReport(
        total_tests=5,
        passed_tests=4,
        failed_tests=1,
        duration=2.0,
        coverage_percent=80.0,
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "report.json"
        report.save_json(path)
        
        loaded = CIReport.load_json(path)
        assert loaded.total_tests == 5
        assert loaded.passed_tests == 4
        assert loaded.coverage_percent == 80.0
