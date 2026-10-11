from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class JobHandler:
    execute: Callable[[int], None]
    recover: Callable[[Session, int, bool], bool]
    queued_ids: Callable[[Session], list[int]]
    running_ids: Callable[[Session], list[int]]
