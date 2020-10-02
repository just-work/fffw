try:
    from typing import Literal, Protocol
except ImportError:  # pragma: no cover
    from typing_extensions import Literal, Protocol  # type: ignore

__all__ = ['Literal', 'Protocol']
