#!/usr/bin/env python3
"""Code review agent powered by Ollama and Llama model."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_MODEL = "llama2"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".cs", ".go", ".rs", ".rb", ".php"}
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".env", "dist", "build", ".pytest_cache"}


def is_valid_code_file(file_path: Path) -> bool:
    """Check if file is a code file we should review."""
    return file_path.is_file() and file_path.suffix in CODE_EXTENSIONS


def collect_code_files(directory: Path, max_files: int = 50) -> List[Path]:
    """Collect code files from directory, respecting exclusions."""
    code_files = []
    
    for item in directory.rglob("*"):
        if len(code_files) >= max_files:
            break
        
        # Skip excluded directories
        if any(excluded in item.parts for excluded in EXCLUDE_DIRS):
            continue
        
        if is_valid_code_file(item):
            code_files.append(item)
    
    return sorted(code_files)


def read_code_file(file_path: Path, max_lines: int = 200) -> str:
    """Read code file with line limit."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[:max_lines]
            return "".join(lines)
    except Exception as e:
        return f"Error reading file: {e}"


def clone_git_repo(git_url: str, temp_dir: str) -> Path:
    """Clone a git repository to a temporary directory."""
    print(f"Cloning repository from {git_url}...")
    try:
        result = subprocess.run(
            ["git", "clone", git_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr}")
        print("Repository cloned successfully.")
        return Path(temp_dir)
    except FileNotFoundError:
        raise RuntimeError("Git is not installed or not in PATH.")
    except Exception as e:
        raise RuntimeError(f"Failed to clone repository: {e}")


def prepare_code_context(code_files: List[Path]) -> str:
    """Prepare code context from multiple files."""
    context = "=== CODE FILES TO REVIEW ===\n\n"
    
    for file_path in code_files[:20]:  # Review up to 20 files
        rel_path = file_path.name
        try:
            content = read_code_file(file_path)
            context += f"\n--- File: {rel_path} ---\n"
            context += content
            context += "\n"
        except Exception as e:
            context += f"\n--- File: {rel_path} (Error) ---\n{e}\n"
    
    return context


def get_code_review(code_context: str, model: str = DEFAULT_MODEL, host: str = DEFAULT_OLLAMA_HOST) -> str:
    """Get code review from Ollama API."""
    prompt = f"""You are an experienced code reviewer. Analyze the following code and provide a comprehensive code review.

Focus on:
1. Code Quality - readability, maintainability, and best practices
2. Security Issues - potential vulnerabilities or security concerns
3. Performance - inefficiencies or potential optimizations
4. Error Handling - proper exception handling and error management
5. Testing - test coverage and testability
6. Documentation - comments and documentation quality
7. Naming Conventions - variable, function, and class naming clarity
8. Code Duplication - repeated code patterns that could be refactored
9. Architectural Issues - design pattern issues or structural problems
10. Compliance - adherence to coding standards

Provide your review in a structured format with:
- SUMMARY: Brief overview of the code quality
- CRITICAL ISSUES: High-priority issues that must be fixed
- MAJOR ISSUES: Important improvements needed
- MINOR ISSUES: Nice-to-have improvements
- RECOMMENDATIONS: Specific actionable recommendations
- POSITIVE ASPECTS: What was done well

{code_context}

Provide detailed, actionable feedback:"""

    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        f"{host.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = response.getcode()
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(
            f"Failed to get code review with model '{model}'. "
            f"Ollama API error: HTTP {exc.code} - {error_body.strip() or 'unknown error'}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach Ollama at {host}. Error: {exc.reason}\n"
            "Make sure Ollama is running: ollama serve"
        ) from exc

    if status != 200:
        raise RuntimeError(
            f"Failed to get code review. Ollama API error: HTTP {status} - {body.strip() or 'unknown error'}"
        )

    data = json.loads(body)
    return (data.get("response") or "").strip()


def process_code_review(source_path: str, is_git: bool = False, 
                        model: str = DEFAULT_MODEL, 
                        host: str = DEFAULT_OLLAMA_HOST,
                        output_file: Optional[str] = None) -> str:
    """Process code review for a git repo or local folder."""
    temp_dir = None
    
    try:
        # Get the code directory
        if is_git:
            temp_dir = tempfile.mkdtemp()
            code_dir = clone_git_repo(source_path, temp_dir)
        else:
            code_dir = Path(source_path).resolve()
            if not code_dir.exists():
                raise ValueError(f"Directory does not exist: {code_dir}")
            if not code_dir.is_dir():
                raise ValueError(f"Path is not a directory: {code_dir}")
            print(f"Using directory: {code_dir}")
        
        # Collect code files
        print("Collecting code files...")
        code_files = collect_code_files(code_dir)
        if not code_files:
            raise ValueError("No code files found in the provided directory.")
        
        print(f"Found {len(code_files)} code files. Preparing review...")
        
        # Prepare code context
        code_context = prepare_code_context(code_files)
        
        # Get code review from Ollama
        print("Analyzing code with Llama model (this may take a moment)...")
        review = get_code_review(code_context, model=model, host=host)
        
        # Format output
        output = f"""
{'=' * 80}
CODE REVIEW REPORT
{'=' * 80}

Source: {source_path}
Model: {model}
Files Analyzed: {len(code_files)}

{'-' * 80}
REVIEW:
{'-' * 80}

{review}

{'=' * 80}
"""
        
        # Save to file if requested
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"\nReview saved to: {output_file}")
        
        return output
        
    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Code review agent using Ollama and Llama model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review a local folder
  python code_review_agent.py /path/to/my/project
  
  # Review a git repository
  python code_review_agent.py https://github.com/user/repo --git
  
  # Review with custom model and save output
  python code_review_agent.py /path/to/project --model llama2 --output review.txt
  
  # Review with custom Ollama host
  python code_review_agent.py /path/to/project --ollama_host http://localhost:11434
        """
    )
    
    parser.add_argument(
        "source",
        help="Git repository URL or local folder path to review"
    )
    parser.add_argument(
        "--git",
        action="store_true",
        help="Treat source as a git URL and clone it"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--ollama_host",
        default=os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST),
        help=f"Ollama server URL (default: env OLLAMA_HOST or {DEFAULT_OLLAMA_HOST})"
    )
    parser.add_argument(
        "--output",
        help="Save review output to file"
    )
    
    args = parser.parse_args()
    
    try:
        # Detect if source is a git URL
        is_git = args.git or (args.source.startswith("http://") or args.source.startswith("https://"))
        
        review = process_code_review(
            args.source,
            is_git=is_git,
            model=args.model,
            host=args.ollama_host,
            output_file=args.output
        )
        
        print(review)
        return 0
        
    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
