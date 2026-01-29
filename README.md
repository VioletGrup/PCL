# PCL
 run to lint
 ruff check . --fix && ruff format .
 
BACKEND
python3 -m uvicorn backend.api.main:app --reload --port 8000
 
FRONTEND 
npm run dev -- --host 127.0.0.1 --port 5173
