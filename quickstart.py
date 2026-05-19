#!/usr/bin/env python3
"""
Quick Start Guide for Code Review Agent
========================================

This script demonstrates how to use the Code Review Agent.
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_section(text):
    print(f"\n► {text}")
    print("-" * 70)


def check_ollama():
    """Check if Ollama is installed and running."""
    print_section("CHECKING OLLAMA")
    
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Ollama is installed: {result.stdout.strip()}")
            return True
        else:
            print("✗ Ollama command failed")
            return False
    except FileNotFoundError:
        print("✗ Ollama is not installed or not in PATH")
        print("  Download from: https://ollama.ai")
        return False


def check_git():
    """Check if Git is installed."""
    print_section("CHECKING GIT")
    
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Git is installed: {result.stdout.strip()}")
            return True
        else:
            print("✗ Git command failed")
            return False
    except FileNotFoundError:
        print("✗ Git is not installed or not in PATH")
        print("  Note: Git is only needed for reviewing GitHub repositories")
        print("  Download from: https://git-scm.com")
        return False


def check_ollama_running():
    """Check if Ollama server is running."""
    print_section("CHECKING OLLAMA SERVER")
    
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        print("✓ Ollama server is running at http://localhost:11434")
        return True
    except Exception:
        print("✗ Ollama server is not running at http://localhost:11434")
        print("\nTo start Ollama, run:")
        print("  ollama serve")
        return False


def show_usage_examples():
    """Show usage examples."""
    print_header("QUICK START - USAGE EXAMPLES")
    
    examples = [
        {
            "title": "1. Review a Local Python Project",
            "command": "python code_review_agent.py /path/to/my/project",
            "description": "Analyzes all code files in the local folder"
        },
        {
            "title": "2. Review a Local Project and Save Output",
            "command": "python code_review_agent.py /path/to/project --output review.txt",
            "description": "Saves the review to a text file"
        },
        {
            "title": "3. Review a GitHub Repository",
            "command": "python code_review_agent.py https://github.com/user/repo",
            "description": "Clones and reviews a GitHub repository"
        },
        {
            "title": "4. Review with a Specific Model",
            "command": "python code_review_agent.py /path/to/project --model llama2:13b",
            "description": "Uses a larger/different Llama model"
        },
        {
            "title": "5. Review with Custom Ollama Host",
            "command": "python code_review_agent.py /path/to/project --ollama_host http://remote-server:11434",
            "description": "Connects to Ollama on a remote server"
        },
        {
            "title": "6. Use Enhanced Version with Better Formatting",
            "command": "python code_review_agent_enhanced.py /path/to/project --output review.txt",
            "description": "Uses the enhanced version with colored output and progress tracking"
        },
    ]
    
    for example in examples:
        print(f"\n{example['title']}")
        print(f"Description: {example['description']}")
        print(f"\nCommand:")
        print(f"  $ {example['command']}\n")


def show_requirements():
    """Show system requirements."""
    print_header("SYSTEM REQUIREMENTS")
    
    requirements = [
        ("Python", "3.8 or higher"),
        ("Ollama", "Latest version (https://ollama.ai)"),
        ("Llama Model", "llama2 or llama2:13b (pulled via ollama)"),
        ("Git", "For reviewing GitHub repositories (optional)"),
        ("RAM", "8GB minimum (16GB+ recommended for larger models)"),
        ("Disk Space", "10GB+ for Llama models"),
    ]
    
    print("Requirement                 | Details")
    print("-" * 70)
    for req, detail in requirements:
        print(f"{req:<27} | {detail}")


def show_next_steps():
    """Show next steps."""
    print_header("NEXT STEPS")
    
    steps = [
        "1. Make sure Ollama is running:",
        "   $ ollama serve",
        "",
        "2. Pull the Llama model:",
        "   $ ollama pull llama2",
        "",
        "3. Review your first project:",
        "   $ python code_review_agent.py /path/to/your/project",
        "",
        "4. For enhanced output, use the enhanced version:",
        "   $ python code_review_agent_enhanced.py /path/to/your/project",
        "",
        "5. For more help:",
        "   $ python code_review_agent.py --help",
    ]
    
    for step in steps:
        print(step)


def main():
    """Run the quick start guide."""
    print_header("CODE REVIEW AGENT - QUICK START GUIDE")
    
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Check requirements
    has_ollama = check_ollama()
    has_git = check_git()
    
    # Try to check if Ollama is running (don't fail if it's not)
    ollama_running = check_ollama_running()
    
    if not ollama_running and has_ollama:
        print("\n⚠ Ollama server is not running.")
        print("You'll need to start it before running reviews.")
    
    # Show requirements
    show_requirements()
    
    # Show examples
    show_usage_examples()
    
    # Show next steps
    show_next_steps()
    
    print_header("ADDITIONAL RESOURCES")
    
    print("Documentation:")
    print("  - README.md: Comprehensive documentation")
    print("  - code_review_agent.py: Simple version (no dependencies)")
    print("  - code_review_agent_enhanced.py: Enhanced version with better output")
    print("\nLinks:")
    print("  - Ollama: https://ollama.ai")
    print("  - Llama Models: https://github.com/facebookresearch/llama")
    print("  - Git: https://git-scm.com")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
