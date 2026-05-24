# 📞 Trilingual Telecom Customer Service Voice Bot (PoC)

A complete Proof of Concept (PoC) for an AI-driven, trilingual customer service voice assistant tailored for a telecom provider. The system handles raw microphone input in **English, Sinhala, or Tamil**, converts speech to text, manages conversational state across multi-turn dialogues, handles dynamic Text-to-SQL tool execution against an SQLite relational database, and synthesizes localized natural neural voice responses.

---

# 🏛️ System Architecture

The pipeline uses a decoupled, modular AI architecture to achieve fast processing times and high translation fidelity:

- **The Ears (STT):** Microsoft Azure Cognitive Services Speech SDK (hardcoded to active listening locales `en-US`, `si-LK`, or `ta-LK`).
- **The Brain (Orchestration & LLM):** LangChain Agent Framework powered by Google Gemini (`gemini-3.5-flash`).
- **The Memory:** In-memory stateful conversation tracking (Stateless Cloud API wrapper pattern).
- **The Data (Knowledge Base):** Local SQLite relational schema with parameterized inputs to protect against SQL injection.
- **The Mouth (TTS):** Azure Neural Text-to-Speech voices (`en-US-AvaNeural`, `si-LK-ThiliniNeural`, and `ta-LK-PallaviNeural`).

---

# 🌟 Key Features

## Continuous Voice Interaction

Utilizes a continuous execution loop (`while True`) that keeps the microphone active until the user explicitly exits the conversation by saying commands such as:

- Goodbye
- ස්තූතියි
- நன்றி

## Cross-Thread Database Operations

Database connectivity utilizes:

```python
sqlite3.connect("telecom.db", check_same_thread=False)
```

This allows safe asynchronous database execution from LangChain background worker threads.

## Context-Aware Memory Handling

The system preserves conversation history across multiple turns and injects prior messages into the LLM request context, enabling understanding of references such as:

> Which of those is cheaper?

> Show me the first one again.

## Dynamic Parameter Validation

The LLM evaluates tool descriptions and function docstrings before execution.

Examples:

- Missing phone number → ask user for phone number.
- Missing issue description → ask user to describe the fault.
- Missing package filters → request budget or data requirements.

This ensures tool execution occurs only after all required parameters are collected.

---

# 🧠 Memory Management

## Why Memory Is Needed

LLMs accessed through APIs are inherently stateless.

Without memory:

**User:**

> Show broadband packages below Rs.3000

**Assistant:**

> Package A, Package B, Package C

**User:**

> Which one has more data?

The model would not know what “one” refers to unless previous conversation context is supplied.

## Implementation Strategy

Conversation history is maintained in memory and appended to each request.

Example:

```python
conversation_history = [
    HumanMessage(content="Show broadband packages below Rs.3000"),
    AIMessage(content="Package A and Package B are available"),
    HumanMessage(content="Which one has more data?")
]
```

This list is injected into Gemini during every invocation.

Benefits:

- Multi-turn dialogue support
- Reference resolution
- Natural conversation flow
- Context-aware recommendations

---

# 🗄️ Database Schema & Tools

The agent uses structured function calling to interact with a local SQLite database.

---

## Table 1: `packages`

Stores broadband package information.

### Schema

| Column | Type |
|----------|----------|
| id | INTEGER |
| package_name | TEXT |
| monthly_price | REAL |
| data_allowance_gb | INTEGER |
| speed_mbps | INTEGER |

### Tool

```python
get_broadband_packages(max_price, min_data)
```

### Example Query

```sql
SELECT *
FROM packages
WHERE monthly_price <= ?
AND data_allowance_gb >= ?
```

---

## Table 2: `customers`

Stores customer account information.

### Schema

| Column | Type |
|----------|----------|
| phone_number | TEXT |
| customer_name | TEXT |
| remaining_data_gb | REAL |
| outstanding_bill | REAL |

### Tool

```python
check_account_balance(phone_number)
```

### Example Query

```sql
SELECT remaining_data_gb,
       outstanding_bill
FROM customers
WHERE phone_number = ?
```

---

## Table 3: `fault_tickets`

Stores reported network issues.

### Schema

| Column | Type |
|----------|----------|
| ticket_id | INTEGER |
| phone_number | TEXT |
| issue_description | TEXT |
| created_at | TIMESTAMP |

### Tool

```python
report_network_fault(
    phone_number,
    issue_description
)
```

### Example Insert

```sql
INSERT INTO fault_tickets(
    phone_number,
    issue_description
)
VALUES (?, ?)
```

---

# 🔄 End-to-End Processing Flow

```text
User Speech
      │
      ▼
Azure Speech-to-Text
      │
      ▼
Detected Language Text
      │
      ▼
Conversation Memory
      │
      ▼
LangChain Agent
      │
      ├──────────────┐
      │              │
      ▼              ▼
Gemini LLM      Database Tools
      │              │
      └──────┬───────┘
             ▼
      Final Response Text
             ▼
Azure Neural TTS
             ▼
      Spoken Reply
```

---

# ⚙️ Installation & Environment Setup

Before running the application, obtain the following credentials:

## Required Cloud Credentials

### Google Gemini API Key

Generated from Google AI Studio.

### Azure Speech Services

Obtain:

- Speech Key
- Speech Region

from the Azure Portal.

---

# 🍏 macOS Setup Instructions

On macOS, microphone access must be explicitly granted to terminal applications.

## 1. Install UV Package Manager

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 2. Clone or Open Project

```bash
cd voice-bot-poc
```

---

## 3. Install Dependencies

```bash
uv sync
```

This command:

- Creates a virtual environment
- Installs all dependencies
- Synchronizes lockfile packages

---

## 4. Configure Environment Variables

```bash
export GOOGLE_API_KEY="your-gemini-api-key"
export SPEECH_KEY="your-azure-speech-key"
export SPEECH_REGION="your-azure-region"
```

To verify:

```bash
echo $GOOGLE_API_KEY
```

---

## 5. Grant Microphone Permissions

Open:

```text
System Settings
  └── Privacy & Security
       └── Microphone
```

Enable microphone access for:

- Terminal
- iTerm2
- Visual Studio Code

### Important

If using VS Code integrated terminal:

1. Grant permission
2. Close VS Code completely
3. Re-open VS Code

Otherwise microphone access may remain blocked.

---

## 6. Initialize Database

```bash
uv run upgrade_db.py
```

Expected result:

- Creates tables
- Seeds sample data
- Applies schema migrations

---

## 7. Run Application

```bash
uv run main.py
```

---

# 🪟 Windows Setup Instructions

Windows uses different installation and environment variable syntax.

---

## 1. Install UV Package Manager

Open PowerShell:

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify:

```powershell
uv --version
```

---

## 2. Open Project

```powershell
cd voice-bot-poc
```

---

## 3. Install Dependencies

```powershell
uv sync
```

---

## 4. Configure Environment Variables

### Command Prompt (CMD)

```cmd
set GOOGLE_API_KEY=your-gemini-api-key
set SPEECH_KEY=your-azure-speech-key
set SPEECH_REGION=your-azure-region
```

### PowerShell

```powershell
$env:GOOGLE_API_KEY="your-gemini-api-key"
$env:SPEECH_KEY="your-azure-speech-key"
$env:SPEECH_REGION="your-azure-region"
```

Verify:

```powershell
echo $env:GOOGLE_API_KEY
```

---

## 5. Verify Audio Devices

Open:

```text
Settings
  └── System
       └── Sound
```

Confirm:

### Input Device

- Microphone enabled
- Default recording device selected

### Output Device

- Speakers enabled
- Headphones enabled
- Headset enabled

---

## 6. Initialize Database

```powershell
uv run upgrade_db.py
```

---

## 7. Start Application

```powershell
uv run main.py
```

---

# 🚀 Running the Voice Bot

After startup:

1. Microphone begins listening.
2. User speaks in English, Sinhala, or Tamil.
3. Speech is transcribed.
4. Agent determines whether a tool is required.
5. Tool executes if necessary.
6. Response generated.
7. Azure TTS speaks reply.
8. Conversation continues until exit command.

---

# 🔒 Security Considerations

## SQL Injection Protection

Parameterized queries are used throughout:

```python
cursor.execute(
    "SELECT * FROM customers WHERE phone_number = ?",
    (phone_number,)
)
```

No direct string interpolation is performed.

---

## Credential Security

Secrets are stored in environment variables:

```bash
GOOGLE_API_KEY
SPEECH_KEY
SPEECH_REGION
```

Never hardcode production credentials.

---

## Controlled Tool Execution

The LLM cannot execute arbitrary SQL.

Instead, it can invoke only approved functions:

- `get_broadband_packages()`
- `check_account_balance()`
- `report_network_fault()`

This limits access to authorized operations only.

---

# 📈 Future Enhancements

Potential production-grade improvements include:

## AI Improvements

- Automatic language detection
- Sentiment analysis
- Customer intent classification
- Enhanced telecom domain prompting

## Memory Improvements

- Redis conversation memory
- PostgreSQL persistence
- Long-term customer profile memory

## Knowledge Base Enhancements

- Retrieval-Augmented Generation (RAG)
- Telecom policy documents
- Product manuals
- Internal troubleshooting guides

## Enterprise Integrations

- CRM integration
- Billing platform integration
- Customer profile systems
- Ticketing systems

## Deployment Enhancements

- Docker containers
- Kubernetes orchestration
- Azure App Services deployment
- CI/CD pipelines

## Human Escalation

- Transfer to live support agent
- Supervisor intervention
- Priority customer routing

## Multi-Channel Support

- Web Chat
- WhatsApp
- Mobile App
- SMS
- Microsoft Teams

---

# 📊 Technology Stack

| Layer | Technology |
|---------|------------|
| Programming Language | Python |
| Speech Recognition | Azure Cognitive Services Speech SDK |
| LLM Framework | LangChain |
| Large Language Model | Google Gemini 3.5 Flash |
| Database | SQLite |
| Tool Calling | LangChain Tools |
| Memory | In-Memory Conversation State |
| Text-to-Speech | Azure Neural Voices |
| Dependency Management | uv |
| Operating Systems | macOS, Windows |

---

# 🚀 Git Commands for Updating README

After saving this file as `README.md`:

```bash
git add README.md
git commit -m "Docs: Final production-ready README with architecture and cross-platform setup details"
git push
```

---

# 📄 License

This repository is provided as a Proof of Concept (PoC) for educational, research, and demonstration purposes.

You are free to modify, extend, and adapt the implementation for production environments according to your organization's security, scalability, and compliance requirements.