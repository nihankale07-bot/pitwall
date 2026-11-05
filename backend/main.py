
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pitwall.data import load_race
from backend.schemas import OptimizeRequest, OptimizationResponse
from backend.services.simulator import run_strategy_optimization


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = FastAPI(
    title="PITWALL API",
    description="Formula racing strategy optimization and decision support",
    version="0.1.0",
)


# ============================================================
# FRONTEND CONNECTION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT_DIR / "data" / "processed"


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def home():
    return {
        "application": "PITWALL",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "PITWALL API",
    }


# ============================================================
# AVAILABLE SESSIONS
# ============================================================

@app.get("/sessions")
def get_sessions():

    if not DATA_DIR.exists():
        return {"sessions": []}

    sessions = sorted(
        [
            int(folder.name)
            for folder in DATA_DIR.iterdir()
            if folder.is_dir() and folder.name.isdigit()
        ]
    )

    return {
        "sessions": sessions,
        "count": len(sessions),
    }


# ============================================================
# AVAILABLE DRIVERS
# ============================================================

@app.get("/sessions/{session_key}/drivers")
def get_drivers(session_key: int):

    try:
        df = load_race(
            session_key=session_key,
            data_dir=DATA_DIR,
        )

        drivers = sorted(
            int(driver)
            for driver in df["driver_number"].dropna().unique()
        )

        return {
            "session_key": session_key,
            "drivers": drivers,
            "count": len(drivers),
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_key} was not found.",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# STRATEGY OPTIMIZATION
# ============================================================

@app.post(
    "/optimize",
    response_model=OptimizationResponse,
)
def optimize(request: OptimizeRequest):

    try:
        result = run_strategy_optimization(
            session_key=request.session_key,
            target_driver=request.target_driver,
            decision_lap=request.decision_lap,
            race_length=request.race_length,
            track_mode=request.track_mode,
            pit_loss=request.pit_loss,
            max_stops=request.max_stops,
            max_candidates=request.max_candidates,
            data_dir=str(DATA_DIR),
        )

        return result

    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )
