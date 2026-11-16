# RIT Sync Vision

Vision-based automated attendance and synchronization system.

---

## 📁 Repository Structure

```
rit-sync-vision/
│
├── frontend/                  # Rakesh — React Application
│
├── backend/                   # Vijayalakshmi — Main Backend
│   ├── app/
│   │   ├── core/              # Core configuration and security
│   │   ├── modules/            # All application modules
│   │   │   ├── authentication/
│   │   │   ├── users/
│   │   │   ├── students/
│   │   │   ├── classrooms/
│   │   │   ├── subjects/
│   │   │   ├── face_registration/
│   │   │   ├── camera/
│   │   │   ├── ai_processing/
│   │   │   ├── face_tracking/
│   │   │   ├── attendance/
│   │   │   ├── reports/
│   │   │   ├── synchronization/
│   │   │   └── audit_logs/
│   │   │
│   │   ├── database/
│   │   ├── api/
│   │   ├── middleware/
│   │   └── main.py
│   │
│   └── tests/
│
├── ai_engine/                 # Paul — AI Development
│   ├── detection/
│   ├── recognition/
│   ├── tracking/
│   ├── quality_check/
│   ├── decision_engine/
│   ├── privacy/
│   ├── models/
│   └── tests/
│
├── shared/                    # Shared project contracts
│   ├── schemas/
│   ├── constants/
│   └── types/
│
├── storage/                   # Local application data
│   ├── database/
│   ├── face_templates/
│   └── temporary/
│
├── docs/                      # Project documentation
│   ├── architecture/
│   ├── api/
│   ├── database/
│   └── testing/
│
├── scripts/                   # Development and setup scripts
│
├── tests/                     # Complete system integration tests
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
└── requirements.txt
```

---

## 👥 Team & Responsibilities

- **Frontend**: Rakesh — React Application & UI/UX
- **Backend**: Vijayalakshmi — Core Backend, Database, APIs & Module Integration
- **AI Engine**: Paul — Face Detection, Recognition, Tracking & AI Pipeline

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)
- Docker & Docker Compose (optional)

### 2. Setup Environment
```bash
# Clone the repository
git clone https://github.com/your-org/rit-sync-vision.git
cd rit-sync-vision

# Copy environment variables
cp .env.example .env
```

### 3. Backend Setup
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```
