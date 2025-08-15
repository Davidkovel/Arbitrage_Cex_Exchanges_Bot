import json
from pathlib import Path
from typing import Set, Dict

from src.entities.enteties_token_manager import SpreadState


class TokenManager:
    def __init__(self, min_spread_change_percent: float = 0.10):
        self.min_spread_change_percent = min_spread_change_percent
        self.token_states: Dict[str, SpreadState] = {}  # Composite Pattern
        self.ignore_tokens_manager = IgnoreTokensManager()

    def should_notify(self, symbol: str, current_spread: float) -> bool:
        if self.ignore_tokens_manager.is_ignored(symbol):
            return False

        if symbol not in self.token_states:
            self.token_states[symbol] = SpreadState()

        state = self.token_states[symbol]
        state.last_actual_spread = current_spread

        # Если спред изменился на min_spread_change_percent или больше
        spread_change = abs(current_spread - state.last_reported_spread)
        if spread_change >= self.min_spread_change_percent:
            state.last_reported_spread = current_spread
            state.should_notify = True
        else:
            state.should_notify = False

        return state.should_notify


class IgnoreTokensManager:
    def __init__(self, config_path: str = r"C:\Users\David\PycharmProjects\exchanges_arbitrage_bot\src\persistence\ignore_tokens.json"):
        self.config_path = Path(config_path)
        self._ignored_tokens: Set[str] = set()
        self._load_ignored_tokens()

    def _load_ignored_tokens(self):
        """Загружает игнорируемые токены из файла"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self._ignored_tokens = set(data.get("ignoring_tokens", []))
        except json.JSONDecodeError:
            print("Invalid JSON format in config file, using default tokens")
        except Exception as e:
            print(f"Error loading ignored tokens: {e}")
            self._ignored_tokens = set()

    def is_ignored(self, symbol: str) -> bool:
        """Проверяет, нужно ли игнорировать токен"""
        return any(symbol.startswith(token) for token in self._ignored_tokens)

    def _save_ignored_tokens(self):
        """Сохраняет список в файл"""
        try:
            self.config_path.parent.mkdir(exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump({"ignoring_tokens": list(self._ignored_tokens)}, f, indent=2)
        except Exception as e:
            print(f"Error saving ignored tokens: {e}")
