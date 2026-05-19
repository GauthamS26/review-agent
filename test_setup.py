#!/usr/bin/env python3
"""Test script to verify Code Review Agent setup."""

import subprocess
import sys
import urllib.request
from pathlib import Path


class Colors:
    """ANSI color codes."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(name, passed, message=""):
    """Print test result."""
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"  [{status}] {name}")
    if message:
        print(f"        {message}")


def print_section(text):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}━━ {text} ━━{Colors.RESET}")


def test_python():
    """Test Python version."""
    print_section("TESTING PYTHON")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    passed = sys.version_info >= (3, 8)
    print_test("Python >= 3.8", passed, f"Found: Python {version}")
    return passed


def test_ollama_installed():
    """Test if Ollama is installed."""
    print_section("TESTING OLLAMA INSTALLATION")
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        passed = result.returncode == 0
        if passed:
            version = result.stdout.strip()
            print_test("Ollama installed", True, version)
        else:
            print_test("Ollama installed", False, "Command failed")
        return passed
    except FileNotFoundError:
        print_test("Ollama installed", False, "Not found in PATH")
        return False
    except Exception as e:
        print_test("Ollama installed", False, str(e))
        return False


def test_ollama_running():
    """Test if Ollama server is running."""
    print_section("TESTING OLLAMA SERVER")
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        print_test("Ollama server running", True, "Accessible at http://localhost:11434")
        return True
    except urllib.error.URLError:
        print_test("Ollama server running", False, "Not accessible at http://localhost:11434")
        print(f"        Run: {Colors.BOLD}ollama serve{Colors.RESET}")
        return False
    except Exception as e:
        print_test("Ollama server running", False, str(e))
        return False


def test_llama_model():
    """Test if Llama model is available."""
    print_section("TESTING LLAMA MODEL")
    try:
        import json
        response = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        data = json.loads(response.read())
        models = [m.get("name", "") for m in data.get("models", [])]
        
        llama_models = [m for m in models if "llama" in m.lower()]
        
        if llama_models:
            print_test("Llama model available", True, f"Found: {', '.join(llama_models)}")
            return True
        else:
            print_test("Llama model available", False, "No Llama models found")
            print(f"        Run: {Colors.BOLD}ollama pull llama2{Colors.RESET}")
            return False
    except Exception as e:
        print_test("Llama model available", False, str(e))
        return False


def test_git():
    """Test if Git is installed."""
    print_section("TESTING GIT")
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        passed = result.returncode == 0
        if passed:
            version = result.stdout.strip()
            print_test("Git installed", True, version)
        else:
            print_test("Git installed", False, "Command failed")
        return passed
    except FileNotFoundError:
        print_test("Git installed", False, "(Optional) Not found in PATH")
        return False
    except Exception as e:
        print_test("Git installed", False, str(e))
        return False


def test_scripts_exist():
    """Test if all scripts exist."""
    print_section("TESTING SCRIPT FILES")
    script_dir = Path(__file__).parent
    scripts = [
        "code_review_agent.py",
        "code_review_agent_enhanced.py",
        "README.md",
    ]
    
    all_exist = True
    for script in scripts:
        path = script_dir / script
        exists = path.exists()
        all_exist = all_exist and exists
        print_test(f"{script} exists", exists)
    
    return all_exist


def test_colorama():
    """Test if colorama is available."""
    print_section("TESTING OPTIONAL DEPENDENCIES")
    try:
        import colorama
        print_test("colorama installed", True, "(Optional) For enhanced output")
        return True
    except ImportError:
        print_test("colorama installed", False, "(Optional) Can be installed later")
        return True  # Not critical


def print_summary(results):
    """Print test summary."""
    print_section("TEST SUMMARY")
    
    all_critical_passed = all([
        results.get("python"),
        results.get("ollama_installed"),
        results.get("scripts"),
    ])
    
    ollama_ready = (
        results.get("ollama_running") and
        results.get("llama_model")
    )
    
    print(f"\n{Colors.BOLD}Critical Requirements:{Colors.RESET}")
    print(f"  ✓ Python >= 3.8: {'Yes' if results.get('python') else 'No'}")
    print(f"  ✓ Ollama Installed: {'Yes' if results.get('ollama_installed') else 'No'}")
    print(f"  ✓ Script Files: {'Yes' if results.get('scripts') else 'No'}")
    
    print(f"\n{Colors.BOLD}Optional/Runtime Requirements:{Colors.RESET}")
    print(f"  • Ollama Server Running: {'Yes' if results.get('ollama_running') else 'No'}")
    print(f"  • Llama Model Available: {'Yes' if results.get('llama_model') else 'No'}")
    print(f"  • Git Installed: {'Yes' if results.get('git') else 'No (only needed for GitHub URLs)'}")
    print(f"  • Colorama Module: {'Yes' if results.get('colorama') else 'No (optional enhancement)'}")
    
    print(f"\n{Colors.BOLD}Status:{Colors.RESET}")
    if all_critical_passed:
        if ollama_ready:
            print(f"{Colors.GREEN}✓ READY TO USE!{Colors.RESET}")
            print("  You can start reviewing code immediately:")
            print(f"    {Colors.BOLD}python code_review_agent.py /path/to/project{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}⚠ SETUP NEEDED{Colors.RESET}")
            print("  Before using the agent, you need to:")
            if not results.get("ollama_running"):
                print(f"    1. Start Ollama server: {Colors.BOLD}ollama serve{Colors.RESET}")
            if not results.get("llama_model"):
                print(f"    2. Pull Llama model: {Colors.BOLD}ollama pull llama2{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ SETUP INCOMPLETE{Colors.RESET}")
        print("  Critical requirements not met. Please fix the above issues.")
        return False
    
    return all_critical_passed


def main():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}╔══════════════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}║  CODE REVIEW AGENT - SETUP TEST                                    ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}╚══════════════════════════════════════════════════════════════════╝{Colors.RESET}")
    
    results = {
        "python": test_python(),
        "ollama_installed": test_ollama_installed(),
        "ollama_running": test_ollama_running(),
        "llama_model": test_llama_model(),
        "git": test_git(),
        "scripts": test_scripts_exist(),
        "colorama": test_colorama(),
    }
    
    success = print_summary(results)
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}For more information, see README.md{Colors.RESET}\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
