from fastapi import FastAPI

app = FastAPI(title="KPI Weekly Report API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
