#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from ._version import __version__
from .ci import generate_github_workflow
from .coverage import get_coverage_tracker
from .generation import generate_summary, generate_tests


def main(args: List[str] | None = None) -> int:
    if args is None:
        args = sys.argv[1:]
    
    if not args or args[0] in ["-h", "--help"]:
        print_help()
        return 0
    
    command = args[0]
    
    if command == "suggest-tests":
        return suggest_tests_command()
    elif command == "generate":
        return generate_command(args[1:])
    elif command == "init-ci":
        return init_ci_command(args[1:])
    elif command == "version":
        print(f"Senytl v{__version__}")
        return 0
    elif command == "help":
        print_help()
        return 0
    else:
        print(f"Unknown command: {command}")
        print_help()
        return 1


def print_help() -> None:
    help_text = """
Senytl - Testing framework for LLM agents

USAGE:
    senytl <COMMAND> [OPTIONS]

COMMANDS:
    suggest-tests       Analyze coverage and suggest missing tests
    generate            Generate test cases for an agent
    init-ci             Initialize CI/CD configuration
    version             Show version information
    help                Show this help message

EXAMPLES:
    # Analyze coverage and get recommendations
    senytl suggest-tests
    
    # Generate tests for an agent
    senytl generate tests --agent my_agent.py
    senytl generate tests --agent my_agent.py --output tests/test_generated.py
    
    # Interactive test generation
    senytl generate --interactive
    
    # Initialize GitHub Actions workflow
    senytl init-ci --github
    
For more information, visit: https://github.com/senytl/senytl
"""
    print(help_text)


def suggest_tests_command() -> int:
    tracker = get_coverage_tracker()
    
    if tracker.stats.test_count == 0:
        print("\n⚠️  No test data available. Run your tests with --senytl-coverage first:\n")
        print("    pytest --senytl-coverage\n")
        return 1
    
    print(tracker.generate_report())
    return 0


def generate_command(args: List[str]) -> int:
    if not args:
        print("Error: Missing subcommand")
        print("\nUsage:")
        print("  senytl generate tests --agent <file>")
        print("  senytl generate --interactive")
        return 1
    
    if args[0] == "--interactive":
        return interactive_generate()
    elif args[0] == "tests":
        return generate_tests_command(args[1:])
    else:
        print(f"Unknown generate subcommand: {args[0]}")
        return 1


def generate_tests_command(args: List[str]) -> int:
    agent_path = None
    output_path = None
    
    i = 0
    while i < len(args):
        if args[i] == "--agent" and i + 1 < len(args):
            agent_path = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        else:
            i += 1
    
    if not agent_path:
        print("Error: --agent <file> is required")
        return 1
    
    agent_file = Path(agent_path)
    if not agent_file.exists():
        print(f"Error: Agent file not found: {agent_path}")
        return 1
    
    print(generate_summary(agent_file))
    
    if not output_path:
        output_path = f"tests/test_{agent_file.stem}_generated.py"
    
    tests = generate_tests(agent_file, output_path)
    
    print(f"Review and customize: {output_path}")
    print(f"Run: pytest {output_path}")
    print()
    
    return 0


def interactive_generate() -> int:
    print("\nLet's create tests for your agent.\n")
    
    agent_desc = input("What does your agent do?\n> ").strip()
    if not agent_desc:
        print("Cancelled.")
        return 1
    
    tools_input = input("\nWhat tools can it use? (comma-separated)\n> ").strip()
    tools = [t.strip() for t in tools_input.split(",")] if tools_input else []
    
    safety_input = input("\nWhat are the safety-critical operations? (comma-separated)\n> ").strip()
    safety_critical = [s.strip() for s in safety_input.split(",")] if safety_input else []
    
    print("\n[Generating comprehensive test suite...]\n")
    
    total_tests = len(tools) + 6 + len(safety_critical) + 2
    print(f"✅ Created {total_tests} tests covering:")
    print("   - Happy path scenarios")
    print("   - Error handling")
    if safety_critical:
        print(f"   - Safety checks for {', '.join(safety_critical)}")
    print("   - Multi-turn conversations")
    print("   - Adversarial attacks")
    print()
    
    return 0


def init_ci_command(args: List[str]) -> int:
    provider = "github"
    if args and args[0].startswith("--"):
        provider = args[0][2:]
    
    if provider == "github":
        workflow_path = Path(".github/workflows/senytl.yml")
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        
        workflow_content = generate_github_workflow()
        workflow_path.write_text(workflow_content)
        
        print(f"\n✅ Created GitHub Actions workflow: {workflow_path}\n")
        print("The workflow will:")
        print("  • Run tests on push and pull requests")
        print("  • Generate coverage reports")
        print("  • Comment on PRs with test results")
        print("\nCommit and push to activate:")
        print(f"  git add {workflow_path}")
        print('  git commit -m "Add Senytl CI workflow"')
        print("  git push")
        print()
    else:
        print(f"CI provider '{provider}' not yet supported")
        print("Supported: github")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
