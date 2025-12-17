"""Comprehensive tests for CLI module"""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from senytl.cli import (
    main,
    print_help,
    suggest_tests_command,
    generate_command,
    generate_tests_command,
    interactive_generate,
    init_ci_command,
)


class TestCLIMain:
    """Test main CLI function"""
    
    def test_main_no_args(self, capsys):
        """Test main with no arguments"""
        result = main([])
        captured = capsys.readouterr()
        
        assert result == 0
        assert "USAGE" in captured.out or "help" in captured.out.lower()
    
    def test_main_help_flag(self, capsys):
        """Test main with --help"""
        result = main(["--help"])
        captured = capsys.readouterr()
        
        assert result == 0
        assert "USAGE" in captured.out
    
    def test_main_version(self, capsys):
        """Test version command"""
        result = main(["version"])
        captured = capsys.readouterr()
        
        assert result == 0
        assert "Senytl v" in captured.out
    
    def test_main_unknown_command(self, capsys):
        """Test unknown command"""
        result = main(["unknown-command"])
        captured = capsys.readouterr()
        
        assert result == 1
        assert "Unknown command" in captured.out


class TestSuggestTestsCommand:
    """Test suggest-tests command"""
    
    def test_suggest_tests_no_data(self, capsys):
        """Test suggest-tests with no coverage data"""
        from senytl.coverage import reset_coverage_tracker
        reset_coverage_tracker()
        
        result = suggest_tests_command()
        captured = capsys.readouterr()
        
        assert result == 1
        assert "No test data available" in captured.out
    
    def test_suggest_tests_with_data(self, capsys):
        """Test suggest-tests with coverage data"""
        from senytl.coverage import get_coverage_tracker
        tracker = get_coverage_tracker()
        tracker.increment_test_count()
        tracker.register_available_tools(["tool1", "tool2"])
        
        result = suggest_tests_command()
        captured = capsys.readouterr()
        
        assert result == 0
        assert "Coverage Report" in captured.out


class TestGenerateCommand:
    """Test generate command"""
    
    def test_generate_no_subcommand(self, capsys):
        """Test generate without subcommand"""
        result = generate_command([])
        captured = capsys.readouterr()
        
        assert result == 1
        assert "Missing subcommand" in captured.out
    
    def test_generate_tests_no_agent(self, capsys):
        """Test generate tests without agent file"""
        result = generate_tests_command([])
        captured = capsys.readouterr()
        
        assert result == 1
        assert "--agent" in captured.out
    
    def test_generate_tests_nonexistent_file(self, capsys):
        """Test generate tests with nonexistent file"""
        result = generate_tests_command(["--agent", "/tmp/nonexistent.py"])
        captured = capsys.readouterr()
        
        assert result == 1
        assert "not found" in captured.out
    
    def test_generate_tests_success(self, capsys):
        """Test successful test generation"""
        code = '''
def agent(prompt):
    return "Hello"
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "agent.py"
            agent_file.write_text(code)
            output_file = Path(tmpdir) / "test_agent.py"
            
            result = generate_tests_command([
                "--agent", str(agent_file),
                "--output", str(output_file)
            ])
            captured = capsys.readouterr()
            
            assert result == 0
            assert "Analyzing agent" in captured.out
            assert output_file.exists()
    
    def test_interactive_generate(self, capsys):
        """Test interactive generate mode"""
        with patch('builtins.input', side_effect=['Customer support', 'search,create', 'delete']):
            result = interactive_generate()
            captured = capsys.readouterr()
            
            assert result == 0
            assert "created" in captured.out.lower() or "generated" in captured.out.lower()
    
    def test_interactive_generate_cancelled(self, capsys):
        """Test cancelling interactive mode"""
        with patch('builtins.input', return_value=''):
            result = interactive_generate()
            captured = capsys.readouterr()
            
            assert result == 1
            assert "Cancelled" in captured.out


class TestInitCICommand:
    """Test init-ci command"""
    
    def test_init_ci_github(self, capsys):
        """Test initializing GitHub Actions workflow"""
        import os
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                
                result = init_ci_command(["--github"])
                captured = capsys.readouterr()
                
                assert result == 0
                assert "Created GitHub Actions workflow" in captured.out
                
                workflow_file = Path(".github/workflows/senytl.yml")
                assert workflow_file.exists()
        finally:
            os.chdir(cwd)
    
    def test_init_ci_default(self, capsys):
        """Test init-ci with default (GitHub)"""
        import os
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                
                result = init_ci_command([])
                captured = capsys.readouterr()
                
                assert result == 0
                workflow_file = Path(".github/workflows/senytl.yml")
                assert workflow_file.exists()
        finally:
            os.chdir(cwd)
    
    def test_init_ci_unsupported_provider(self, capsys):
        """Test init-ci with unsupported provider"""
        import os
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                
                result = init_ci_command(["--jenkins"])
                captured = capsys.readouterr()
                
                assert result == 1
                assert "not yet supported" in captured.out
        finally:
            os.chdir(cwd)


class TestPrintHelp:
    """Test help printing"""
    
    def test_print_help(self, capsys):
        """Test help output"""
        print_help()
        captured = capsys.readouterr()
        
        assert "USAGE" in captured.out
        assert "COMMANDS" in captured.out
        assert "suggest-tests" in captured.out
        assert "generate" in captured.out
        assert "init-ci" in captured.out


class TestCLIIntegration:
    """Integration tests for CLI"""
    
    def test_full_workflow(self, capsys):
        """Test complete workflow: generate → init-ci"""
        code = '''
def search(query):
    pass

def agent(prompt):
    return "response"
'''
        import os
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                
                # Create agent file
                agent_file = Path("agent.py")
                agent_file.write_text(code)
                
                # Generate tests
                result1 = main(["generate", "tests", "--agent", "agent.py"])
                assert result1 == 0
                
                # Init CI
                result2 = main(["init-ci", "--github"])
                assert result2 == 0
                
                # Check files created
                assert Path(".github/workflows/senytl.yml").exists()
        finally:
            os.chdir(cwd)
    
    def test_version_command(self, capsys):
        """Test version command output"""
        result = main(["version"])
        captured = capsys.readouterr()
        
        assert result == 0
        assert "0.1.0" in captured.out
