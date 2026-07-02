from fastapi import FastAPI

app = FastAPI(title="TechDocKnowledgeAgent")


@app.get("/")
def read_root():
    return {"status": "ok", "message": "TechDocKnowledgeAgent backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
