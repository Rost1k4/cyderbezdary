"""Налаштування AI (Google Gemini API).

Ключ береться (за пріоритетом) з:
  1) змінної середовища GEMINI_API_KEY (або GOOGLE_API_KEY);
  2) файлу config_local.py поруч із кодом: GEMINI_API_KEY = "ваш_ключ"
     (файл у .gitignore, тож у git не потрапить);
  3) .streamlit/secrets.toml: gemini_api_key = "ваш_ключ" (підхоплює app.py).

Модель можна змінити змінною GEMINI_MODEL. За замовчуванням «gemini-flash-latest»:
це аліас Google на актуальну Flash-модель, тому нічого не доведеться оновлювати,
коли виходять нові версії.
"""
import os

try:  # необов'язковий локальний файл із ключем
    import config_local as _local
except ImportError:
    _local = None


def _clean(value) -> str:
    return (value or "").strip().strip('"').strip("'")


def api_key() -> str:
    """Ключ читається щоразу заново, тому його можна підставити вже після старту."""
    return (_clean(os.environ.get("GEMINI_API_KEY"))
            or _clean(os.environ.get("GOOGLE_API_KEY"))
            or _clean(getattr(_local, "GEMINI_API_KEY", "")))


def model() -> str:
    return (_clean(os.environ.get("GEMINI_MODEL"))
            or _clean(getattr(_local, "GEMINI_MODEL", ""))
            or "gemini-flash-latest")


def fallback_models() -> list:
    """Запасні моделі на випадок, коли основна перевантажена (503) чи вичерпала ліміт (429).
    Перелік через кому можна змінити змінною GEMINI_FALLBACK_MODELS."""
    raw = _clean(os.environ.get("GEMINI_FALLBACK_MODELS")) or "gemini-flash-lite-latest,gemini-2.5-flash"
    return [m.strip() for m in raw.split(",") if m.strip()]
