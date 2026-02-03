import streamlit.components.v1 as components
import os

_RELEASE = True
_component_func = components.declare_component(
    "rect_selector",
    path=os.path.join(os.path.dirname(__file__), "frontend")
)

def rect_selector(image_base64: str, width: int, height: int, scale: float, can_go_back: bool, initial_rect: dict = None, key=None):
    """
    矩形選択コンポーネント
    
    Args:
        initial_rect: 初期矩形 {"x", "y", "w", "h"} (元画像座標系)
    
    Returns:
        dict: {"action": "confirm"|"skip"|"back", "rect": {"x", "y", "w", "h"} | None}
    """
    return _component_func(
        image_base64=image_base64,
        width=width,
        height=height,
        scale=scale,
        can_go_back=can_go_back,
        initial_rect=initial_rect,
        key=key,
        default=None
    )
