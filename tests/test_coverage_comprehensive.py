"""Comprehensive tests for coverage module"""
import json
from pathlib import Path
import tempfile

import pytest
from senytl.coverage import (
    CoverageTracker,
    CoverageStats,
    get_coverage_tracker,
    reset_coverage_tracker,
)
from senytl.models import ToolCall


class TestCoverageStats:
    """Test CoverageStats class"""
    
    def test_empty_stats(self):
        """Test empty stats initialization"""
        stats = CoverageStats()
        assert len(stats.tools_tested) == 0
        assert len(stats.tools_available) == 0
        assert stats.test_count == 0
        assert stats.tool_coverage_percent() == 100.0
    
    def test_tool_coverage_percent_partial(self):
        """Test tool coverage percentage calculation"""
        stats = CoverageStats()
        stats.tools_available = {"tool1", "tool2", "tool3", "tool4"}
        stats.tools_tested = {"tool1", "tool2"}
        assert stats.tool_coverage_percent() == 50.0
    
    def test_tool_coverage_percent_full(self):
        """Test 100% tool coverage"""
        stats = CoverageStats()
        stats.tools_available = {"tool1", "tool2"}
        stats.tools_tested = {"tool1", "tool2"}
        assert stats.tool_coverage_percent() == 100.0
    
    def test_input_diversity_score_minimal(self):
        """Test diversity score with minimal inputs"""
        stats = CoverageStats()
        stats.input_samples = ["test1", "test2"]
        assert stats.input_diversity_score() == 1
    
    def test_input_diversity_score_low(self):
        """Test diversity score with low inputs"""
        stats = CoverageStats()
        stats.input_samples = [f"test{i}" for i in range(7)]
        assert stats.input_diversity_score() == 2
    
    def test_input_diversity_score_medium(self):
        """Test diversity score with medium inputs"""
        stats = CoverageStats()
        stats.input_samples = [f"test{i}" for i in range(12)]
        assert stats.input_diversity_score() == 3
    
    def test_input_diversity_score_high(self):
        """Test diversity score with high inputs"""
        stats = CoverageStats()
        stats.input_samples = [f"test{i}" for i in range(17)]
        assert stats.input_diversity_score() == 4
    
    def test_input_diversity_score_excellent(self):
        """Test diversity score with excellent inputs"""
        stats = CoverageStats()
        stats.input_samples = [f"test{i}" for i in range(25)]
        assert stats.input_diversity_score() == 5
    
    def test_overall_quality_score(self):
        """Test overall quality score calculation"""
        stats = CoverageStats()
        stats.tools_available = {"t1", "t2", "t3", "t4"}
        stats.tools_tested = {"t1", "t2", "t3"}
        stats.input_samples = [f"test{i}" for i in range(15)]
        stats.test_count = 10
        
        score = stats.overall_quality_score()
        assert 0 <= score <= 100


class TestCoverageTracker:
    """Test CoverageTracker class"""
    
    def test_initialization(self):
        """Test tracker initialization"""
        tracker = CoverageTracker()
        assert tracker.stats.test_count == 0
        assert len(tracker.stats.tools_tested) == 0
    
    def test_record_tool_call(self):
        """Test recording tool calls"""
        tracker = CoverageTracker()
        tracker.record_tool_call(ToolCall(name="search", args={}))
        tracker.record_tool_call(ToolCall(name="create", args={}))
        
        assert "search" in tracker.stats.tools_tested
        assert "create" in tracker.stats.tools_tested
        assert len(tracker.stats.tools_tested) == 2
    
    def test_record_duplicate_tool_call(self):
        """Test recording duplicate tool calls"""
        tracker = CoverageTracker()
        tracker.record_tool_call(ToolCall(name="search", args={}))
        tracker.record_tool_call(ToolCall(name="search", args={}))
        
        assert len(tracker.stats.tools_tested) == 1
    
    def test_record_conversation_path(self):
        """Test recording conversation paths"""
        tracker = CoverageTracker()
        tracker.record_conversation_path("greeting")
        tracker.record_conversation_path("problem_solving")
        
        assert "greeting" in tracker.stats.conversation_paths
        assert "problem_solving" in tracker.stats.conversation_paths
    
    def test_record_decision_branch(self):
        """Test recording decision branches"""
        tracker = CoverageTracker()
        tracker.record_decision_branch("branch1")
        tracker.record_decision_branch("branch2")
        
        assert "branch1" in tracker.stats.decision_branches
        assert "branch2" in tracker.stats.decision_branches
    
    def test_record_input(self):
        """Test recording user inputs"""
        tracker = CoverageTracker()
        tracker.record_input("test input 1")
        tracker.record_input("test input 2")
        
        assert len(tracker.stats.input_samples) == 2
        assert "test input 1" in tracker.stats.input_samples
    
    def test_increment_test_count(self):
        """Test incrementing test count"""
        tracker = CoverageTracker()
        tracker.increment_test_count()
        tracker.increment_test_count()
        assert tracker.stats.test_count == 2
    
    def test_register_available_tools(self):
        """Test registering available tools"""
        tracker = CoverageTracker()
        tracker.register_available_tools(["tool1", "tool2", "tool3"])
        
        assert len(tracker.stats.tools_available) == 3
        assert "tool1" in tracker.stats.tools_available
    
    def test_analyze_gaps_untested_tools(self):
        """Test gap analysis for untested tools"""
        tracker = CoverageTracker()
        tracker.register_available_tools(["search", "delete_account", "create"])
        tracker.record_tool_call(ToolCall(name="search", args={}))
        tracker.analyze_gaps()
        
        assert "delete_account" in tracker._untested_tools
        assert "create" in tracker._untested_tools
    
    def test_analyze_gaps_scenarios(self):
        """Test gap analysis for missing scenarios"""
        tracker = CoverageTracker()
        tracker.analyze_gaps()
        
        assert len(tracker._untested_scenarios) > 0
    
    def test_analyze_gaps_recommendations(self):
        """Test recommendations generation"""
        tracker = CoverageTracker()
        tracker.register_available_tools(["delete_account", "search"])
        tracker.analyze_gaps()
        
        assert len(tracker._recommendations) > 0
    
    def test_generate_report_no_gaps(self):
        """Test report generation with no gaps"""
        tracker = CoverageTracker()
        tracker.stats.test_count = 20
        tracker.stats.input_samples = [f"test{i}" for i in range(20)]
        
        report = tracker.generate_report()
        assert "Coverage Report" in report
        assert "Quality" in report
    
    def test_generate_report_with_gaps(self):
        """Test report generation with gaps"""
        tracker = CoverageTracker()
        tracker.register_available_tools(["tool1", "tool2"])
        tracker.record_tool_call(ToolCall(name="tool1", args={}))
        
        report = tracker.generate_report()
        assert "GAPS DETECTED" in report
        assert "Untested Tools" in report
    
    def test_save_report(self):
        """Test saving report to file"""
        tracker = CoverageTracker()
        tracker.register_available_tools(["tool1", "tool2"])
        tracker.record_tool_call(ToolCall(name="tool1", args={}))
        tracker.stats.test_count = 5
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "coverage.json"
            tracker.save_report(path)
            
            assert path.exists()
            data = json.loads(path.read_text())
            assert "tools_tested" in data
            assert "quality_score" in data


class TestCoverageGlobalFunctions:
    """Test global coverage functions"""
    
    def test_get_coverage_tracker_singleton(self):
        """Test that get_coverage_tracker returns singleton"""
        tracker1 = get_coverage_tracker()
        tracker2 = get_coverage_tracker()
        assert tracker1 is tracker2
    
    def test_reset_coverage_tracker(self):
        """Test resetting coverage tracker"""
        tracker1 = get_coverage_tracker()
        tracker1.increment_test_count()
        
        reset_coverage_tracker()
        
        tracker2 = get_coverage_tracker()
        assert tracker2.stats.test_count == 0


class TestCoverageEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_tool_list(self):
        """Test with no tools"""
        tracker = CoverageTracker()
        tracker.register_available_tools([])
        assert tracker.stats.tool_coverage_percent() == 100.0
    
    def test_quality_score_boundaries(self):
        """Test quality score stays within 0-100"""
        tracker = CoverageTracker()
        tracker.stats.test_count = 0
        score = tracker.stats.overall_quality_score()
        assert 0 <= score <= 100
        
        tracker.stats.test_count = 1000
        score = tracker.stats.overall_quality_score()
        assert 0 <= score <= 100
    
    def test_report_with_many_untested_tools(self):
        """Test report with many untested tools"""
        tracker = CoverageTracker()
        tools = [f"tool{i}" for i in range(20)]
        tracker.register_available_tools(tools)
        tracker.record_tool_call(ToolCall(name="tool0", args={}))
        
        report = tracker.generate_report()
        assert "Untested Tools" in report
