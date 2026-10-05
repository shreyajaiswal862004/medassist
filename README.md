# MedAssist — AI Medical Assistant

A multimodal, multi-agent AI medical assistant built with FastAPI, LangGraph, React, and free AI APIs.

## Features
- 9 input types: text, voice, image, PDF, prescription, lab values, sensor data, medical reports, X-rays
- 3 user roles: Patient, Doctor, Admin
- Human-in-the-loop (HITL) validation using LangGraph interrupt()
- Safety guardrails: emergency detection, disclaimer injection, no-diagnosis enforcement
- JWT authentication with role-based access control
- PostgreSQL database

## Tech Stack
- Backend: FastAPI + LangGraph + Python
- Frontend: React + Tailwind CSS
- LLM: Groq (LLaMA / Qwen)
- Vision: Google Gemini
- STT: faster-whisper (local)
- Database: PostgreSQL

## Setup

### Backend
```bash
python -m venv medassist_env
medassist_env\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Environment Variables
```
GROQ_API_KEY=your_key
GEMINI_API_KEY=your_key
DATABASE_URL=postgresql://postgres:password@localhost:5432/medassist_db
JWT_SECRET_KEY=your_secret
```