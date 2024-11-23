from app.model import common

from . import lc_model


def register_lc_models() -> None:
    """
    Register langchain models. This is called in main.
    """
    common.register_model(lc_model.Gpt4o_20240513())
    common.register_model(lc_model.Gpt35_Turbo1106())
    common.register_model(lc_model.Gpt4o_mini_20240718())
