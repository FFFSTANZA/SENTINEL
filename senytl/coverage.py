from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set

from .models import ToolCall


@dataclass
class CoverageStats:
    tools_tested: Set[str] = field(default_factory=set)
    tools_available: Set[str] = field(default_factory=set)
    conversation_paths: Set[str] = field(default_factory=set)
    decision_branches: Set[str] = field(default_factory=set)
    input_samples: List[str] = field(default_factory=list)
    test_count: int = 0
    
    def tool_coverage_percent(self) -> float:
        if not self.tools_available:
            return 100.0
        return (len(self.tools_tested) / len(self.tools_available)) * 100
    
    def input_diversity_score(self) -> int:
        unique_inputs = len(set(self.input_samples))
        if unique_inputs >= 20:
            return 5
        elif unique_inputs >= 15:
            return 4
        elif unique_inputs >= 10:
            return 3
        elif unique_inputs >= 5:
            return 2
        else:
            return 1
    
    def overall_quality_score(self) -> float:
        tool_score = self.tool_coverage_percent()
        diversity_score = self.input_diversity_score() * 20
        test_count_score = min(self.test_count * 5, 100)
        
        return (tool_score * 0.4 + diversity_score * 0.3 + test_count_score * 0.3)


class CoverageTracker:
    def __init__(self):
        self.stats = CoverageStats()
        self._untested_tools: Set[str] = set()
        self._untested_scenarios: List[str] = []
        self._recommendations: List[str] = []
    
    def record_tool_call(self, tool_call: ToolCall) -> None:
        self.stats.tools_tested.add(tool_call.name)
    
    def record_conversation_path(self, path_id: str) -> None:
        self.stats.conversation_paths.add(path_id)
    
    def record_decision_branch(self, branch_id: str) -> None:
        self.stats.decision_branches.add(branch_id)
    
    def record_input(self, input_text: str) -> None:
        self.stats.input_samples.append(input_text)
    
    def increment_test_count(self) -> None:
        self.stats.test_count += 1
    
    def register_available_tools(self, tools: List[str]) -> None:
        self.stats.tools_available.update(tools)
    
    def analyze_gaps(self) -> None:
        self._untested_tools = self.stats.tools_available - self.stats.tools_tested
        
        self._untested_scenarios = []
        if not any("error" in p for p in self.stats.conversation_paths):
            self._untested_scenarios.append("User asks follow-up question after error")
        if not any("empty" in p for p in self.stats.conversation_paths):
            self._untested_scenarios.append("Agent receives empty response from tool")
        if not any("multi" in p for p in self.stats.conversation_paths):
            self._untested_scenarios.append("User switches topic mid-conversation")
        
        self._recommendations = []
        high_risk_tools = {"delete", "remove", "cancel", "refund", "payment"}
        for tool in self._untested_tools:
            risk = "HIGH RISK" if any(keyword in tool.lower() for keyword in high_risk_tools) else "MEDIUM RISK"
            self._recommendations.append(f"Add tests for {tool} ({risk})")
        
        if len(self._untested_scenarios) > 0:
            self._recommendations.append(f"Test error recovery paths ({len(self._untested_scenarios)} missing)")
        
        if self.stats.test_count < 10:
            self._recommendations.append("Add more comprehensive test coverage")
    
    def generate_report(self) -> str:
        self.analyze_gaps()
        
        tool_coverage = self.stats.tool_coverage_percent()
        diversity_score = self.stats.input_diversity_score()
        quality_score = self.stats.overall_quality_score()
        
        stars = "⭐" * diversity_score + "☆" * (5 - diversity_score)
        
        grade = "A+" if quality_score >= 95 else \
                "A" if quality_score >= 90 else \
                "A-" if quality_score >= 85 else \
                "B+" if quality_score >= 80 else \
                "B" if quality_score >= 70 else \
                "C" if quality_score >= 60 else "D"
        
        report = [
            "",
            "Senytl Coverage Report",
            "─────────────────────────────────────",
            f"Tool Coverage:        {len(self.stats.tools_tested)}/{len(self.stats.tools_available)} tools ({tool_coverage:.0f}%)",
            f"Conversation Paths:   {len(self.stats.conversation_paths)} paths tested",
            f"Decision Branches:    {len(self.stats.decision_branches)} branches tested",
            f"Input Diversity:      {stars} ({'Excellent' if diversity_score == 5 else 'Good' if diversity_score >= 3 else 'Fair'})",
            f"Overall Quality:      {grade} ({quality_score:.0f}/100)",
            "",
        ]
        
        if self._untested_tools or self._untested_scenarios:
            report.append("⚠️  GAPS DETECTED:")
            report.append("")
            
            if self._untested_tools:
                report.append("Untested Tools:")
                for tool in sorted(self._untested_tools)[:5]:
                    risk = "HIGH RISK" if any(keyword in tool.lower() for keyword in {"delete", "remove", "cancel", "refund", "payment"}) else "MEDIUM RISK"
                    report.append(f"  • {tool} ({risk})")
                report.append("")
            
            if self._untested_scenarios:
                report.append("Untested Scenarios:")
                for scenario in self._untested_scenarios[:5]:
                    report.append(f"  • {scenario}")
                report.append("")
            
            if self._recommendations:
                report.append("Recommendations:")
                for i, rec in enumerate(self._recommendations[:5], 1):
                    report.append(f"  {i}. {rec}")
                report.append("")
                report.append("Run: senytl suggest-tests")
                report.append("To auto-generate missing test cases")
        else:
            report.append("✅ Excellent coverage! No gaps detected.")
        
        return "\n".join(report)
    
    def save_report(self, path: Path) -> None:
        data = {
            "tools_tested": list(self.stats.tools_tested),
            "tools_available": list(self.stats.tools_available),
            "conversation_paths": list(self.stats.conversation_paths),
            "decision_branches": list(self.stats.decision_branches),
            "test_count": self.stats.test_count,
            "quality_score": self.stats.overall_quality_score(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


_GLOBAL_TRACKER: CoverageTracker | None = None


def get_coverage_tracker() -> CoverageTracker:
    global _GLOBAL_TRACKER
    if _GLOBAL_TRACKER is None:
        _GLOBAL_TRACKER = CoverageTracker()
    return _GLOBAL_TRACKER


def reset_coverage_tracker() -> None:
    global _GLOBAL_TRACKER
    _GLOBAL_TRACKER = CoverageTracker()
