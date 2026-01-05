# 🚀 SDR Agent - Lead Verification & Enrichment System

A full-stack application for lead verification and AI-powered enrichment. Built with **FastAPI** (Python) for the backend and **Next.js** (React) for the frontend.

---

## 📸 Screenshots

### UI Preview
<img width="1255" height="818" alt="SDR Agent UI" src="https://github.com/user-attachments/assets/4a316ed5-33d7-434d-816c-f2b62ed64cf6" />

### Output Excel
<img width="1498" height="515" alt="Output Excel" src="https://github.com/user-attachments/assets/f25170de-3d09-4846-b320-fa7cd46857b3" />

---

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [Clone the Repository](#-clone-the-repository)
3. [Backend Setup](#-backend-setup)
   - [Create Virtual Environment](#step-1-create-virtual-environment)
   - [Activate Virtual Environment](#step-2-activate-virtual-environment)
   - [Install Dependencies](#step-3-install-dependencies)
   - [Configure Environment Variables](#step-4-configure-environment-variables)
   - [Run the Backend Server](#step-5-run-the-backend-server)
4. [Frontend Setup](#-frontend-setup)
   - [Navigate to Client Directory](#step-1-navigate-to-client-directory)
   - [Install Node Dependencies](#step-2-install-node-dependencies)
   - [Configure Frontend Environment](#step-3-configure-frontend-environment-optional)
   - [Run the Frontend Server](#step-4-run-the-frontend-server)
5. [Access the Application](#-access-the-application)
6. [Project Structure](#-project-structure)
7. [Troubleshooting](#-troubleshooting)

---

## 📦 Prerequisites

Before you begin, make sure you have the following installed on your system:

| Software | Version | Download Link |
|----------|---------|---------------|
| **Python** | 3.11 | [Download Python](https://www.python.org/downloads/) |
| **Node.js** | 18+ (LTS recommended) | [Download Node.js](https://nodejs.org/) |
| **Git** | Latest | [Download Git](https://git-scm.com/downloads) |

### Verify Installation

Open your terminal (Git Bash or Command Prompt) and run:

```bash
# Check Python version
python --version
# Should output: Python 3.11.x

# Check Node.js version
node --version
# Should output: v18.x.x or higher

# Check npm version
npm --version
# Should output: 9.x.x or higher

# Check Git version
git --version
# Should output: git version x.x.x
```

---

## 📥 Clone the Repository

### Using Git Bash
```bash
# Navigate to your desired directory
cd /d/your-projects-folder

# Clone the repository
git clone https://github.com/Aiviue-product/sdr-agent.git

# Navigate into the project
cd sdr-agent
```

### Using Windows Command Prompt (CMD)
```cmd
:: Navigate to your desired directory
cd D:\your-projects-folder

:: Clone the repository
git clone https://github.com/Aiviue-product/sdr-agent.git

:: Navigate into the project
cd sdr-agent
```

### Using Windows PowerShell
```powershell
# Navigate to your desired directory
cd D:\your-projects-folder

# Clone the repository
git clone https://github.com/Aiviue-product/sdr-agent.git

# Navigate into the project
cd sdr-agent
```

---

## ⚙️ Backend Setup

The backend is built with **FastAPI** and requires Python 3.11.

### Step 1: Create Virtual Environment

First, navigate to the `backend` directory and create a virtual environment:

#### Using Git Bash
```bash
# Navigate to backend folder
cd backend

# Create virtual environment with Python 3.11
python -m venv venv
```

#### Using Windows Command Prompt (CMD)
```cmd
:: Navigate to backend folder
cd backend

:: Create virtual environment with Python 3.11
python -m venv venv
```

#### Using Windows PowerShell
```powershell
# Navigate to backend folder
cd backend

# Create virtual environment with Python 3.11
python -m venv venv
```

> **Note:** If you have multiple Python versions installed, you might need to specify the Python 3.11 path:
> ```bash
> # Git Bash / PowerShell
> py -3.11 -m venv venv
> 
> # Or specify full path
> "C:\Users\YourUsername\AppData\Local\Programs\Python\Python311\python.exe" -m venv venv
> ```

---

### Step 2: Activate Virtual Environment

#### Using Git Bash
```bash
# Activate the virtual environment
source venv/Scripts/activate
```

#### Using Windows Command Prompt (CMD)
```cmd
:: Activate the virtual environment
venv\Scripts\activate.bat
```

#### Using Windows PowerShell
```powershell
# Activate the virtual environment
.\venv\Scripts\Activate.ps1
```

> **PowerShell Execution Policy Error?** If you get an error about execution policy, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

After activation, you should see `(venv)` at the beginning of your terminal prompt:
```
(venv) user@computer:~/sdr-agent/backend$
```

---

### Step 3: Install Dependencies

With the virtual environment activated, install all required Python packages:

```bash
# Install all dependencies from requirements.txt
pip install -r requirements.txt
```

This will install the following packages:
- `fastapi` - Modern web framework for building APIs
- `uvicorn` - ASGI server to run FastAPI
- `pandas` - Data manipulation library
- `requests` - HTTP library
- `openpyxl` - Excel file handling
- `python-multipart` - File upload support
- `pydantic-settings` - Settings management
- `python-dotenv` - Environment variable management
- `sqlalchemy` - Database ORM
- `asyncpg` - Async PostgreSQL driver
- `psycopg2-binary` - PostgreSQL adapter
- `apify-client` - Apify API client
- `google-genai` - Google Gemini AI integration
- `pytest-asyncio` - Async testing support

---

### Step 4: Configure Environment Variables

You need to set up environment variables for the backend to work properly.

#### 4.1 Create the `.env` file

**Using Git Bash:**
```bash
# Copy the example file
cp .env.example .env
```

**Using Windows Command Prompt (CMD):**
```cmd
:: Copy the example file
copy .env.example .env
```

**Using Windows PowerShell:**
```powershell
# Copy the example file
Copy-Item .env.example .env
```

#### 4.2 Edit the `.env` file

Open the `.env` file with any text editor (VS Code, Notepad++, etc.) and fill in your actual values:

```env
PROJECT_NAME="Lead Verification API"
API_V1_STR="/api/v1"
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# Apify Token - Get from https://console.apify.com/account/integrations
APIFY_TOKEN=your_actual_apify_token_here

# ZeroBounce API Key - Get from https://www.zerobounce.net/
ZEROBOUNCE_API_KEY=your_actual_zerobounce_key_here

# Google Gemini API Key - Get from https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_actual_gemini_api_key_here

# PostgreSQL Database URL
DATABASE_URL=postgresql://username:password@localhost:5432/your_database_name
```

#### Where to Get API Keys:

| Service | Purpose | Get Key From |
|---------|---------|--------------|
| **Apify** | Web scraping & data extraction | [Apify Console](https://console.apify.com/account/integrations) |
| **ZeroBounce** | Email verification | [ZeroBounce Dashboard](https://www.zerobounce.net/) |
| **Google Gemini** | AI-powered enrichment | [Google AI Studio](https://aistudio.google.com/app/apikey) |

> ⚠️ **Security Warning:** Never commit your `.env` file to Git! It's already in `.gitignore` for safety.

---

### Step 5: Run the Backend Server

With everything configured, start the FastAPI backend server:

```bash
# Make sure you're in the backend directory with venv activated
# Run the development server
uvicorn app.main:app --reload
```

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx]
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### Backend URLs:
- **API Base URL:** http://localhost:8000
- **Interactive API Docs (Swagger):** http://localhost:8000/docs
- **Alternative API Docs (ReDoc):** http://localhost:8000/redoc

> 💡 **Tip:** Keep this terminal running while you set up the frontend in a new terminal window!

---

## 🎨 Frontend Setup

The frontend is built with **Next.js 16** and **React 19**.

### Step 1: Navigate to Client Directory

Open a **new terminal window** (keep the backend running!) and navigate to the client folder:

#### Using Git Bash
```bash
# From the project root
cd client/client
```

#### Using Windows Command Prompt (CMD)
```cmd
:: From the project root
cd client\client
```

#### Using Windows PowerShell
```powershell
# From the project root
cd client\client
```

---

### Step 2: Install Node Dependencies

Install all required npm packages:

```bash
# Install dependencies
npm install
```

This will install:
- `next` - React framework
- `react` & `react-dom` - UI library
- `lucide-react` - Icon library
- `tailwindcss` - CSS framework
- And other development dependencies

> ⏳ This might take a few minutes depending on your internet connection.

---

### Step 3: Configure Frontend Environment (Optional)

If you need to customize the backend API URL, create a `.env.local` file:

```bash
# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

Or manually create `.env.local` with:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### Step 4: Run the Frontend Server

Start the Next.js development server:

```bash
# Run the development server
npm run dev
```

You should see output like:
```
   ▲ Next.js 16.0.10
   - Local:        http://localhost:3000
   - Network:      http://192.168.x.x:3000

 ✓ Starting...
 ✓ Ready in xxxms
```

---

## 🌐 Access the Application

Once both servers are running, open your browser and navigate to:

| Service | URL |
|---------|-----|
| **Frontend (Main App)** | [http://localhost:3000](http://localhost:3000) |
| **Backend API** | [http://localhost:8000](http://localhost:8000) |
| **API Documentation** | [http://localhost:8000/docs](http://localhost:8000/docs) |

---

## 📁 Project Structure

```
sdr-agent/
├── backend/                    # FastAPI Backend
│   ├── app/                    # Application code
│   │   ├── api/               # API routes
│   │   │   └── v1/            # API version 1 endpoints
│   │   ├── core/              # Core configurations
│   │   ├── models/            # Database models
│   │   ├── services/          # Business logic
│   │   └── main.py            # App entry point
│   ├── tests/                  # Test files
│   ├── scripts/                # Utility scripts
│   ├── .env                    # Environment variables (create from .env.example)
│   ├── .env.example            # Example environment file
│   ├── requirements.txt        # Python dependencies
│   └── venv/                   # Virtual environment (created by you)
│
├── client/
│   └── client/                 # Next.js Frontend
│       ├── src/               # Source code
│       │   ├── app/           # Next.js app router pages
│       │   └── components/    # React components
│       ├── public/            # Static assets
│       ├── package.json       # Node dependencies
│       └── .env.local         # Frontend environment (optional)
│
└── README.md                   # This file!
```

---

## 🔧 Troubleshooting

### Common Issues & Solutions

#### 1. "python is not recognized as an internal or external command"

**Solution:** Python is not in your PATH. Try these:
```bash
# Use 'py' instead of 'python' on Windows
py -3.11 --version

# Or add Python to PATH during installation
# Re-install Python and check "Add Python to PATH"
```

#### 2. Virtual environment activation fails in Git Bash

**Solution:** Use the correct activation path:
```bash
# Correct path for Git Bash on Windows
source venv/Scripts/activate

# NOT this (Linux/Mac style)
source venv/bin/activate
```

#### 3. PowerShell script execution disabled

**Solution:** Enable script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 4. npm install fails

**Solution:** Clear npm cache and retry:
```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

#### 5. Port 8000 or 3000 already in use

**Solution:** Kill the existing process or use a different port:
```bash
# Run backend on different port
uvicorn app.main:app --reload --port 8001

# Run frontend on different port
npm run dev -- -p 3001
```

#### 6. Database connection error

**Solution:** Make sure your PostgreSQL database is running and the `DATABASE_URL` in `.env` is correct:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

#### 7. CORS errors in browser

**Solution:** Make sure the frontend URL is in the `CORS_ORIGINS` in your backend `.env`:
```env
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

---

## 📞 Need Help?

If you encounter any issues not covered here:

1. Check the existing [Issues](https://github.com/Aiviue-product/sdr-agent/issues) on GitHub
2. Create a new issue with:
   - Your operating system
   - Python and Node.js versions
   - Complete error message
   - Steps to reproduce

---

## 🎉 You're All Set!

Once both servers are running, you can start using the SDR Agent application. Happy coding! 🚀
 