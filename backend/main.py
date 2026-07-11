from fastapi import FastAPI
from random import randint
from pydantic import BaseModel
from backend.services.game_service import Game
from backend.services.word_provider import stub_generate_word
import uuid

class SendMessageRequest(BaseModel):
    message: str

OPENING_MESSAGE = "Guess the word!"


app = FastAPI()
game_engine = Game()


@app.post("/games/")
def create_game():
    game_id: str = "game-" + str(uuid.uuid4())
    game_engine.save_game(game_id, {
        "secret": stub_generate_word(),
        "messages": [
            {"role": "assistant", "content": OPENING_MESSAGE},
        ],
    })

    return {
        "game_id": game_id,
        "message": OPENING_MESSAGE,
    }
@app.post("/games/{game_id}/messages")
async def send_message(game_id: str, request: SendMessageRequest):
    response = await game_engine.handle_message(game_id, request.message)
    return {
        "message": response, 
    }


@app.post("/games/{game_id}/logs")
def stub(game_id: str):
    game_engine.chat._print_history(game_id=game_id)
    return {"message": "ok"}
