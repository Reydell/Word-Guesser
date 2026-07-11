import json
from pathlib import Path
from backend.graph.chatbot import Chatbot


STORAGE_DIR = Path("storage")

class Game:
    def __init__(self):
        self.chat = Chatbot()

    def _game_path(self, game_id: str):
        return STORAGE_DIR / f"{game_id}.json"

    def get_game(self, game_id: str):
        with self._game_path(game_id).open('r', encoding="utf-8") as f:
            return json.load(f)

    def save_game(self, game_id: str, game: dict):
        with self._game_path(game_id).open('w', encoding='utf-8') as f:
            json.dump(game, f, ensure_ascii=False, indent=2)
            f.write("\n")
        
    def handle_message(self, game_id: str, message: str):
        game = self.get_game(game_id)
        response = self.chat.handle_message(
            game_id=game_id,
            message=message,
            secret=game["secret"],
        )

        game["messages"].append({"role": "user", "content": message})
        game["messages"].append({"role": "assistant", "content": response})
        self.save_game(game_id, game)

        return response
        
