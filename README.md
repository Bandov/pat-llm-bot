## Installation Guide

### Prerequisites

This project must be run on a **Linux environment** with **Mono** installed.

Install Mono and the required libraries:

```bash
sudo apt update
sudo apt install mono-complete
sudo apt install libmono-system-windows-forms4.0-cil
```

### Project Installation

#### Step 1. Install Python Dependencies

Install all required Python packages using the provided `requirements.txt` file.

```bash
pip install -r requirements.txt
```

#### Optional: Use a Python Virtual Environment (Recommended)
It is recommended to use a virtual environment to isolate dependencies.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 2. Create a .env file in the root directory of the project and add your Gemini API key.

Example `.env` file:
```bash
GEMINI_API_KEY=your_api_key_here
```

#### Step 3. Run the Pipeline (Repair Strategy)
Execute the main pipeline with:
```bash
python3 main.py
```
This will start the model pipeline and run the repair process.


