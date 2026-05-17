from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class ProvenanceMixin:
    source_provider: Mapped[str | None] = mapped_column(String(80))
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="seeded")
    ingestion_timestamp: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    source_record_id: Mapped[str | None] = mapped_column(String(255))
