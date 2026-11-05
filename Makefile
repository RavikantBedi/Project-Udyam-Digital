dev:
	@echo "Starting backend and frontend..."
	@cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@cd frontend && npm run dev &
	@wait

seed:
	cd backend && python scripts/seed.py
