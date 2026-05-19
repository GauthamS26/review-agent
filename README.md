# Code Review Agent

A Python-based code review agent powered by Ollama and the Llama model. This tool analyzes code from local folders or Git repositories and provides comprehensive code review feedback.

## Features

- **Local and Remote Support**: Review code from local folders or clone and review Git repositories
- **Multi-Language Support**: Supports Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, Ruby, PHP, and more
- **Comprehensive Review**: Analyzes code quality, security, performance, testing, documentation, and best practices
- **Structured Output**: Provides organized review with categories like critical issues, major issues, recommendations, and positive aspects
- **File Export**: Save reviews to a file for documentation and sharing
- **Configurable**: Choose different Ollama models and customize the analysis

## Prerequisites

### 1. Install Ollama
Download and install Ollama from [ollama.ai](https://ollama.ai)

### 2. Download Llama Model
Run Ollama and pull the Llama model:
```bash
ollama pull llama2
# or for a larger model:
ollama pull llama2:13b
```

### 3. Start Ollama Server
Keep Ollama running:
```bash
ollama serve
```

### 4. Install Git (for Git repository support)
Download and install Git from [git-scm.com](https://git-scm.com)

### 5. Install Python Dependencies
```bash
pip install -r requirements.txt
```
Or just ensure you have Python 3.8+ (no additional packages required for core functionality)

## Usage

### Review a Local Folder
```bash
python code_review_agent.py /path/to/my/project
```

### Review a Git Repository
```bash
python code_review_agent.py https://github.com/user/repo --git
```
Or just pass the URL (it auto-detects Git URLs):
```bash
python code_review_agent.py https://github.com/user/repo
```

### Save Review to File
```bash
python code_review_agent.py /path/to/project --output review.txt
```

### Use a Different Model
```bash
python code_review_agent.py /path/to/project --model llama2:13b
```

### Custom Ollama Host
```bash
python code_review_agent.py /path/to/project --ollama_host http://localhost:11434
```

Or set environment variable:
```bash
export OLLAMA_HOST=http://localhost:11434
python code_review_agent.py /path/to/project
```

## Examples

### Example 1: Review a Local Python Project
```bash
python code_review_agent.py ./my_python_project --output my_review.txt
```

### Example 2: Review a GitHub Repository with Larger Model
```bash
python code_review_agent.py https://github.com/django/django --model llama2:13b --output django_review.txt
```

### Example 3: Interactive Review
```bash
python code_review_agent.py ./my_project
# Review will be printed to console
```

## Review Categories

The code review provides feedback in the following categories:

1. **SUMMARY**: Brief overview of code quality
2. **CRITICAL ISSUES**: High-priority issues that must be fixed
3. **MAJOR ISSUES**: Important improvements needed
4. **MINOR ISSUES**: Nice-to-have improvements
5. **RECOMMENDATIONS**: Specific actionable recommendations
6. **POSITIVE ASPECTS**: What was done well

## Supported File Types

The agent reviews the following code file types:
- Python (.py)
- JavaScript (.js)
- TypeScript (.ts, .tsx)
- JSX (.jsx)
- Java (.java)
- C++ (.cpp)
- C (.c)
- C# (.cs)
- Go (.go)
- Rust (.rs)
- Ruby (.rb)
- PHP (.php)

## Command Line Options

```
usage: code_review_agent.py [-h] [--git] [--model MODEL] 
                            [--ollama_host OLLAMA_HOST] [--output OUTPUT]
                            source

positional arguments:
  source                Git repository URL or local folder path to review

optional arguments:
  -h, --help            show this help message and exit
  --git                 Treat source as a git URL and clone it
  --model MODEL         Ollama model name (default: llama2)
  --ollama_host OLLAMA_HOST
                        Ollama server URL (default: env OLLAMA_HOST or
                        http://localhost:11434)
  --output OUTPUT       Save review output to file
```

## Troubleshooting

### Error: "Could not reach Ollama at http://localhost:11434"
- Make sure Ollama is running: `ollama serve`
- Check if Ollama is available on the specified host
- Set correct `--ollama_host` if Ollama is on a different machine

### Error: "Git is not installed or not in PATH"
- Install Git from [git-scm.com](https://git-scm.com)
- Make sure git command is available in your PATH

### Error: "No code files found in the provided directory"
- Check if the directory contains code files in supported languages
- Make sure the path is correct and readable

### Slow Performance
- Llama2 is resource-intensive; ensure your machine has sufficient CPU/GPU
- For faster reviews, consider smaller models or fewer files
- GPU acceleration with CUDA or Metal will significantly improve performance

## Configuration

You can set environment variables to customize behavior:

```bash
# Set default Ollama host
export OLLAMA_HOST=http://your-ollama-server:11434

# Then run without specifying host
python code_review_agent.py /path/to/project
```

## Performance Tips

1. **Use GPU Acceleration**: Ollama can use GPU (CUDA on NVIDIA, Metal on Mac)
2. **Smaller Models**: Use `llama2` instead of `llama2:13b` for faster results
3. **Limit Files**: The agent automatically limits to ~20 files for review
4. **Batch Reviews**: Review similar projects together to warm up the model

## Limitations

- Reviews up to 20 code files (largest files are included first)
- Each file is limited to 200 lines of code for analysis
- Requires Ollama to be running locally or accessible remotely
- Review quality depends on the underlying Llama model's capabilities
- Internet connection required for cloning public Git repositories

## Advanced Usage

### Review Multiple Projects
```bash
for repo in repo1 repo2 repo3; do
  python code_review_agent.py https://github.com/user/$repo --output ${repo}_review.txt
done
```

### Batch Process with Different Models
```bash
python code_review_agent.py /project1 --model llama2 --output p1_review.txt
python code_review_agent.py /project2 --model llama2:13b --output p2_review.txt
```

## FastAPI Service

This project also includes a FastAPI wrapper so the code review agent can be called over HTTP.

### Start API Locally
```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

Swagger UI:
- `http://localhost:8000/docs`

Available endpoints:
- `GET /health`
- `GET /models/default`
- `POST /review/local`
- `POST /review/git`

### Example Request (Local Path)
```bash
curl -X POST http://localhost:8000/review/local \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": ".",
    "model": "llama2",
    "ollama_host": "http://localhost:11434"
  }'
```

### Example Request (Git URL)
```bash
curl -X POST http://localhost:8000/review/git \
  -H "Content-Type: application/json" \
  -d '{
    "git_url": "https://github.com/user/repo",
    "model": "llama2",
    "ollama_host": "http://localhost:11434"
  }'
```

## Docker

### Build and Run with Docker
```bash
docker build -t review-agent-api .
docker run -p 8000:8000 -e OLLAMA_HOST=http://host.docker.internal:11434 review-agent-api
```

### Build and Run with Docker Compose
```bash
docker compose up --build
```

Notes:
- Ensure Ollama is running on the host machine.
- Default compose config uses `http://host.docker.internal:11434` for Ollama.

## Contributing

Feel free to extend this tool with additional features like:
- Support for more programming languages
- Metrics and scoring system
- Integration with GitHub comments/PRs
- Comparison between multiple code versions
- Custom review prompts and templates

## License

This project is provided as-is for educational and development purposes.
