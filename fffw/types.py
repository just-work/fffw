try:
    from typing import Literal
except ImportError:  # pragma: no cover
    from typing_extensions import Literal  # type: ignore

__all__ = ['Literal']
