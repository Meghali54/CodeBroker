# Code Broker: AI-Powered Code Assessment Agent 🤖

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![ADK](https://img.shields.io/badge/Google-ADK-4285F4?logo=google)](https://google.github.io/adk-docs/)

> **Agents Intensive Capstone Project** - A multi-agent system for comprehensive code analysis and quality assessment

## 🎯 What is Code Broker?

Code Broker is an intelligent multi-agent system built with Google's Agent Development Kit (ADK) that automatically analyzes code files, directories, or GitHub repositories and generates detailed assessment reports with actionable improvement recommendations. The system features both a command-line interface via Jupyter notebooks and a modern web dashboard for interactive analysis.



## ✨ Key Features

- 🔍 **Multi-Source Analysis**: Analyze files, directories, or GitHub repositories in real-time
- 📊 **Comprehensive Scoring**: Security, architecture, code quality, and maintainability metrics
- 🤖 **6-Agent System**: Parallel processing with specialized AI agents
  - Repository Agent: Analyzes project structure and frameworks
  - Security Agent: Identifies vulnerabilities and security issues
  - Architecture Agent: Evaluates design patterns and structure
  - Quality Agent: Assesses code quality and standards
  - Improvement Agent: Generates actionable recommendations
  - Executive Report Agent: Creates executive summaries with scores
- 📝 **Beautiful Reports**: Interactive dashboards and detailed Markdown/HTML reports
- 🌐 **Web Dashboard**: Live agent pipeline visualization with real-time updates
- ⚡ **Fast & Reliable**: Async processing with retry mechanisms and graceful fallback
- 🎨 **Code Analysis Tools**: Pylint, Bandit, Radon integration

## 📂 Project Structure

```
agents_intensive_dev/
├── src/
│   ├── llm_adk_agent_module.py    # Core LLM and agent utilities
│   └── tools/
│       ├── lint_code.py           # Code linting and analysis
│       ├── read_files.py          # File reading utilities
│       └── read_github_repository.py  # GitHub repository tools
├── notebooks/
│   ├── code_broker.ipynb          # Main analysis notebook (executable)
│   └── code_broker_documented.ipynb  # Documented version
├── webapp/
│   ├── backend/                   # FastAPI backend
│   │   ├── main.py               # FastAPI application server
│   │   ├── job_manager.py        # Job queue and WebSocket management
│   │   ├── models.py             # Data models and schemas
│   │   ├── agents/               # Multi-agent pipeline
│   │   │   ├── pipeline.py       # Orchestrates 6-stage analysis
│   │   │   ├── repository_agent.py
│   │   │   ├── security_agent.py
│   │   │   ├── architecture_agent.py
│   │   │   ├── quality_agent.py
│   │   │   ├── improvement_agent.py
│   │   │   ├── executive_report_agent.py
│   │   │   └── llm_utils.py      # Shared LLM utilities
│   │   └── tools/                # Analysis tools
│   │       ├── github_tool.py
│   │       ├── repo_clone.py
│   │       ├── static_analysis.py
│   │       └── architecture_analysis.py
│   └── frontend/                  # HTML/CSS/JS dashboard
│       ├── index.html
│       ├── app.js
│       └── styles.css
├── Docs/
│   ├── KAGGLE_WRITEUP.md         # Detailed competition writeup
│   ├── SUBMISSION_SUMMARY.md     # Project summary
│   └── CHECKLIST.md              # Feature checklist
├── requirements.txt               # Python dependencies
└── README.md                       # This file
```

## 🚀 Quick Start

### Option 1: Command-Line Interface (Jupyter Notebook)

```bash
# 1. Clone repository
git clone https://github.com/Samir-atra/agents_intensive_dev.git
cd agents_intensive_dev

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment variables
# Create a .env file with:
# GOOGLE_API_KEY=your_google_api_key
# GITHUB_TOKEN=your_github_token

# 6. Run the notebook
jupyter notebook notebooks/code_broker.ipynb
```

### Option 2: Web Dashboard

```bash
# 1-5. Follow steps 1-5 above

# 6. Install web dependencies
pip install -r webapp/requirements.txt

# 7. Run the FastAPI server
cd webapp/backend
python main.py

# 8. Open browser
# Navigate to http://localhost:8000

# 9. The frontend will be served on the root URL
# WebSocket connection for live agent updates: ws://localhost:8000/ws/jobs/{job_id}
```

## 📋 Requirements

- **Python 3.14+**
- **Google Cloud API Key** (for Gemini/ADK)
- **GitHub Token** (for repository analysis)
- **Git** (for repository cloning)

### Key Dependencies

- `google-adk`: Google Agent Development Kit
- `google-genai`: Google Generative AI API
- `fastapi`: Web framework for dashboard
- `pylint`: Python code analysis
- `python-dotenv`: Environment configuration

See [requirements.txt](requirements.txt) and [webapp/requirements.txt](webapp/requirements.txt) for complete dependency lists.

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key_here
GITHUB_TOKEN=your_github_token_here
MODEL_NAME=gemini-2.0-flash-exp
```

### API Keys Setup

1. **Google API Key**: Get from [Google Cloud Console](https://console.cloud.google.com/)
2. **GitHub Token**: Generate at [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)

## 💻 Usage

### Analyze a GitHub Repository

```python
# Using the notebook
repo_url = "https://github.com/username/repository"
# The notebook will analyze and generate a report
```

### Analyze Local Files

```python
file_path = "path/to/your/code.py"
# The notebook will analyze and generate a report
```

### Access Web Dashboard

1. Start the FastAPI server: `python webapp/backend/main.py`
2. Open http://localhost:8000 in your browser
3. Enter a GitHub repository URL
4. View real-time agent processing and results

## 📊 Agent Pipeline Stages

1. **Repository Analysis**: Extract structure, detect frameworks, identify endpoints
2. **Security Analysis**: Scan for vulnerabilities, check dependencies
3. **Architecture Analysis**: Evaluate design patterns, code organization
4. **Quality Analysis**: Assess code standards, complexity, maintainability
5. **Improvement Generation**: AI-powered recommendations for enhancement
6. **Executive Report**: Summary scores and actionable insights

## 📚 Documentation

- [KAGGLE_WRITEUP.md](Docs/KAGGLE_WRITEUP.md) - Comprehensive technical writeup
- [SUBMISSION_SUMMARY.md](Docs/SUBMISSION_SUMMARY.md) - Project overview
- [CHECKLIST.md](Docs/CHECKLIST.md) - Feature and implementation checklist
- [webapp/README.md](webapp/README.md) - Web dashboard documentation

## 🤝 Architecture Overview

The system uses Google's ADK to coordinate multiple specialized agents:

```
┌─────────────────────────────────────────────────────────────┐
│                      Code Broker System                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Input: Repository URL / Local Files / Directory Path         │
│              ↓                                                 │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Repository Agent (Framework Detection, Structure)  │      │
│  └────────────────┬───────────────────────────────────┘      │
│                   ↓                                            │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Parallel Agents:                                   │      │
│  │ • Security Agent (Vulnerability Detection)         │      │
│  │ • Architecture Agent (Design Pattern Analysis)     │      │
│  │ • Quality Agent (Code Quality Metrics)             │      │
│  └────────────────┬───────────────────────────────────┘      │
│                   ↓                                            │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Improvement Agent (AI-Generated Recommendations)   │      │
│  └────────────────┬───────────────────────────────────┘      │
│                   ↓                                            │
│  ┌────────────────────────────────────────────────────┐      │
│  │ Executive Report Agent (Scores & Summary)          │      │
│  └────────────────┬───────────────────────────────────┘      │
│                   ↓                                            │
│  Output: Dashboard / Markdown Report / Scores                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 🎓 Learning Resources

This project demonstrates:
- Multi-agent AI system orchestration with Google ADK
- Real-time WebSocket communication for live updates
- Full-stack web application (FastAPI + Vanilla JS)
- Integration with external APIs (GitHub, Gemini)
- Async Python programming patterns
- Code analysis and metrics collection

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 📧 Support

For issues, questions, or contributions, please open an issue on GitHub or contact the project maintainers.

---

**Created as part of the Agents Intensive Capstone Project**
└── README.md                       # This file
```

## 🏗️ Architecture

Code Broker uses a **hierarchical multi-agent architecture**:

- **Report Generator** (Orchestrator): Coordinates the entire workflow
- **Sequential Pipeline Agent**: Manages assessment flow
- **Parallel Assessment Agent**: Runs 3 agents concurrently:
  - Correctness Assessor
  - Style Assessor  
  - Description Generator
- **Improvement Recommender**: Synthesizes findings into actionable recommendations

## 🖥️ Executive Dashboard (Web App)

Beyond the notebook, `webapp/` contains a FastAPI + browser dashboard that
turns the same multi-agent idea into a live tool: paste a GitHub URL, watch a
six-agent pipeline (Repository → Security → Architecture → Quality →
Improvement → Executive Report) run in real time over a WebSocket, and get an
executive dashboard with security/maintainability/technical-debt/AI-readiness/
deployment-readiness scores, vulnerability & complexity charts, a detected
architecture breakdown, and AI-generated recommendations. See
[`webapp/README.md`](webapp/README.md) for setup.

## 📖 Documentation

For a detailed writeup including architecture, design decisions, and technical details, see:
**[KAGGLE_WRITEUP.md](KAGGLE_WRITEUP.md)**

## 🎓 Competition

This project was created for the **Agents Intensive Capstone Project** on Kaggle:
https://www.kaggle.com/competitions/agents-intensive-capstone-project

## 👨‍💻 Author

**Samer Atra** - [GitHub](https://github.com/Samir-atra)

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Citation

If you use this project in your research, please cite it as follows:

```bibtex
@misc{attrah2026codebrokermultiagentautomated,
      title={Code Broker: A Multi-Agent System for Automated Code Quality Assessment}, 
      author={Samer Attrah},
      year={2026},
      eprint={2604.23088},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2604.23088}, 
}
```
---

⭐ **Star this repo if you find it helpful and donate if you can!** 
