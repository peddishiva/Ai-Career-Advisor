# AI Career Advisor

An intelligent career guidance platform that analyzes resumes and provides personalized career recommendations using AI.

## 🚀 Features

- **Resume Upload & Parsing** - Support for PDF and DOCX formats
- **AI-Powered Analysis** - Intelligent skill assessment and career insights
- **Role Matching** - Find the best career roles based on your profile
- **JDxR Analyser** - Validate a job description, validate a session-specific resume, and compare them locally
- **Job Recommendations** - Browse curated opportunities independently from JDxR comparisons
- **Personalized Recommendations** - Get actionable next steps for career growth
- **Modern UI** - Beautiful, responsive interface with dark/light theme support

## 🛠️ Tech Stack

### Frontend
- Next.js 14
- TypeScript
- TailwindCSS
- shadcn/ui

### Backend
- Python FastAPI
- pdfplumber (PDF parsing)
- python-docx (DOCX parsing)

## 📋 Prerequisites

- Node.js 18+
- Python 3.10+
- npm or yarn

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd Ai-Career-Advisor
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Install Backend Dependencies

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory (see `.env.example` for reference):

```env
# Gemini API Key (optional - for advanced AI features)
GEMINI_API_KEY=your_gemini_api_key_here

# Firebase (optional - for authentication)
FIREBASE_PROJECT_ID=your_project_id
```

**⚠️ IMPORTANT**: Never commit your `.env` file or API keys to Git!

## 🚀 Running the Application

### Start Backend (Terminal 1)

```bash
cd backend
python main.py
```

Backend runs on: `http://localhost:5000`

### Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

Frontend runs on: `http://localhost:3000`

## 📖 Usage

1. Open `http://localhost:3000` in your browser
2. Upload your resume (PDF or DOCX)
3. Wait for the AI analysis to complete
4. View your personalized career insights and recommendations

### Resume Analysis

Upload a resume from the home page to open the independent Resume Analysis workflow. Resume Analysis stores only its own analysis state and does not depend on a job description comparison.

### JDxR Analyser

Open `/jdxr-analyser` or use **Compare Resume with JD** on the home page. Each comparison creates an isolated local session under `uploads/jdxr/<session-id>/`, validates the job description first, validates the resume second, and then runs the deterministic matcher. It does not call an LLM or external job API. Resume and job-description documents are limited to 5 MB each.

JDxR session files use a seven-day retention window and are cleaned deterministically at backend startup; stale temporary upload fragments are also removed. Recently updated sessions and explicitly active sessions are preserved. Session IDs are UUID-shaped and storage paths are root-scoped, but true per-user ownership cannot be guaranteed until authentication/user identity is introduced.

### Job Recommendations

Open `/job-recommendation` to browse the recommendation and discovery experience. It is independent from JDxR session state.

## 🏗️ Project Structure

```
Ai-Career-Advisor/
├── frontend/           # Next.js frontend application
├── backend/           # Python FastAPI backend
│   ├── routes/       # API endpoints
│   ├── services/     # Business logic
│   └── utils/        # Helper functions
└── README.md         # This file
```

## 🚀 Deployment

### Deploy to Vercel (Frontend)

1. Push your code to GitHub
2. Import project to Vercel
3. Set root directory to `frontend`
4. Add environment variable: `NEXT_PUBLIC_API_URL`
5. Deploy!

For detailed instructions, see `DEPLOYMENT_INSTRUCTIONS.txt`

### Deploy Backend

Backend can be deployed to:
- Railway.app
- Render.com
- Heroku
- Any Python hosting service

Required environment variable: `GEMINI_API_KEY`

## 🔐 Security

- All sensitive files are excluded via `.gitignore`
- API keys should be stored in `.env` files (not committed)
- Firebase credentials are gitignored
- Upload directory is excluded from version control
- Unnecessary `.md` files are excluded (except README.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues or questions, please open an issue on GitHub.

---

**Built with ❤️ for career growth**
