import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class InitialTestingResponseDTO(BaseModel):
    response: str


@app.get("/")
def home():
    return InitialTestingResponseDTO(response="Cozi App")


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
