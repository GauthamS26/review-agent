# Code Review Agent Configuration Template
# Copy this file to config.py and customize as needed

import os
from pathlib import Path

# ============================================================================
# OLLAMA CONFIGURATION
# ============================================================================

# Ollama server host and port
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Default model to use
DEFAULT_MODEL = "llama2"

# Alternative models (uncomment to use):
# DEFAULT_MODEL = "llama2:13b"  # Larger model, slower but better quality
# DEFAULT_MODEL = "mistral"     # Faster alternative
# DEFAULT_MODEL = "neural-chat" # Good for code

# Model timeout (seconds)
MODEL_TIMEOUT = 300

# ============================================================================
# CODE ANALYSIS CONFIGURATION
# ============================================================================

# File extensions to include in review
CODE_EXTENSIONS = {
    ".py",      # Python
    ".js",      # JavaScript
    ".ts",      # TypeScript
    ".tsx",     # TypeScript React
    ".jsx",     # JavaScript React
    ".java",    # Java
    ".cpp",     # C++
    ".c",       # C
    ".cs",      # C#
    ".go",      # Go
    ".rs",      # Rust
    ".rb",      # Ruby
    ".php",     # PHP
}

# Directories to exclude from scanning
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    "dist",
    "build",
    ".pytest_cache",
    ".egg-info",
    "coverage",
    ".mypy_cache",
    "htmlcov",
}

# Maximum files to review per project
MAX_FILES_TO_REVIEW = 50

# Maximum lines per file to analyze
MAX_LINES_PER_FILE = 200

# ============================================================================
# REVIEW CONFIGURATION
# ============================================================================

# Focus areas for code review (customize for your needs)
REVIEW_FOCUS_AREAS = [
    "Code Quality - readability, maintainability, and best practices",
    "Security Issues - potential vulnerabilities or security concerns",
    "Performance - inefficiencies or potential optimizations",
    "Error Handling - proper exception handling and error management",
    "Testing - test coverage and testability",
    "Documentation - comments and documentation quality",
    "Naming Conventions - variable, function, and class naming clarity",
    "Code Duplication - repeated code patterns that could be refactored",
    "Architectural Issues - design pattern issues or structural problems",
    "Compliance - adherence to coding standards",
]

# Review output format
REVIEW_SECTIONS = [
    "SUMMARY",
    "CRITICAL ISSUES",
    "MAJOR ISSUES",
    "MINOR ISSUES",
    "RECOMMENDATIONS",
    "POSITIVE ASPECTS",
]

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

# Default output directory for review files
OUTPUT_DIR = Path.home() / "code_reviews"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Date format for output files
OUTPUT_DATE_FORMAT = "%Y%m%d_%H%M%S"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Enable verbose logging
VERBOSE = False

# Log file path (set to None to disable file logging)
LOG_FILE = OUTPUT_DIR / "code_review_agent.log"

# ============================================================================
# GIT CONFIGURATION
# ============================================================================

# Git clone timeout (seconds)
GIT_CLONE_TIMEOUT = 120

# Use shallow clone (faster, less bandwidth)
GIT_SHALLOW_CLONE = True

# Clone depth for shallow clone
GIT_CLONE_DEPTH = 1

# ============================================================================
# ADVANCED CONFIGURATION
# ============================================================================

# Cache reviews locally
ENABLE_CACHE = False

# Cache directory
CACHE_DIR = Path.home() / ".code_review_cache"

# Use streaming for large models (experimental)
USE_STREAMING = False

# ============================================================================
# CUSTOM PROMPTS (Advanced)
# ============================================================================

# You can override the default review prompt here
CUSTOM_REVIEW_PROMPT_TEMPLATE = """You are an experienced code reviewer. Analyze the following code and provide comprehensive feedback.

Focus on:
{focus_areas}

Provide your review in structured format with these sections:
{sections}

{code_context}

Provide detailed, actionable feedback:"""

# ============================================================================
# FEATURE FLAGS
# ============================================================================

# Enable/disable features
FEATURES = {
    "syntax_checking": True,
    "security_scanning": True,
    "performance_analysis": True,
    "code_duplication_detection": False,  # Requires additional tools
    "metrics_collection": False,  # Experimental
}
