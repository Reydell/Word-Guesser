from pathlib import Path
import yaml


current_dir = Path(__file__).resolve().parent
yaml_path = current_dir / "config.yaml"
    
with yaml_path.open('r', encoding='utf-8') as f:
    config = yaml.safe_load(f.read())
    bot_config = config.get("bot", {})
    llm_config = config.get("llm", {})

BOT_TOKEN = bot_config.get("token")
BOT_USERNAME = bot_config.get("username")
ALLOWED_USERS = set(bot_config.get("allowed_users") or [])
GROQ_API_KEY = llm_config.get("groq_api_key")
DEBOUNCE_SECONDS = bot_config.get("debounce_seconds")
API_BASE_URL = bot_config.get("api_base_url")
