"""Невеликий Streamlit-компонент для вставлення скріншотів із буфера обміну (Ctrl+V)."""
import os
import streamlit.components.v1 as components

_paste_component = components.declare_component(
    "clipboard_image_paste",
    path=os.path.join(os.path.dirname(__file__), "clipboard_paste_component"),
)


def paste_images(key):
    """Повертає список {name, mime, data}, де data — base64 без data URL."""
    return _paste_component(key=key, default=[])
