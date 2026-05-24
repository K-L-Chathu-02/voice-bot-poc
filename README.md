# Trilingual Telecom Voice Bot (PoC)

A Proof of Concept (PoC) for a customer service voice assistant tailored for a Sri Lankan telecom network. The system processes voice input in English, Sinhala, and Tamil, executes Text-to-SQL tool calls against a relational database, and replies natively via localized Neural Text-to-Speech.

## Architecture
* **The Ears (STT):** Azure Cognitive Services (Speech-to-Text)
* **The Brain (Agent):** LangChain + Google Gemini (3.5-Flash)
* **The Data (Knowledge Base):** Local SQLite DB (Function Calling / Text-to-SQL)
* **The Mouth (TTS):** Azure Neural Voices (`si-LK-ThiliniNeural`, `ta-LK-PallaviNeural`, `en-US-AvaNeural`)

## Features
* **Continuous Audio Loop:** Maintains an open, stateful voice connection until the user says "bye".
* **Stateless Memory Management:** Injects full conversation history into the LLM context window on every turn.
* **Dynamic Tool Calling:** Analyzes intent to trigger specific backend Python functions (`get_broadband_packages`, `check_account_balance`, `report_network_fault`).
* **Multi-turn Logic:** Automatically requests missing parameters (e.g., asking for a phone number before checking a balance) before executing a database query.

## Setup Instructions

1. Initialize the environment using `uv`: