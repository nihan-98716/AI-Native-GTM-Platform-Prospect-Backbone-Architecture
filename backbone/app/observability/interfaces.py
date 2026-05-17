from typing import Protocol


class Tracer(Protocol):
    def next_ids(self) -> tuple[str, str]:
        ...


class Meter(Protocol):
    def increment(self, name: str, *, value: int = 1, tags: dict[str, str] | None = None) -> None:
        ...

    def timing(self, name: str, duration_ms: int, *, tags: dict[str, str] | None = None) -> None:
        ...


class Logger(Protocol):
    def info(self, payload: dict) -> None:
        ...

    def error(self, payload: dict) -> None:
        ...

