from __future__ import annotations

from app.models import CheckRecord
from app.nicegui_app.models.ui_events import HistoryDisplayRow
from app.scoring import SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1, compute_internal_total


class HistoryService:
    def resolve_scores(self, record: CheckRecord) -> tuple[float, float]:
        if record.score_model == SCORE_MODEL_INTERNAL20_GRADEBOOK10_V1:
            internal_score = record.internal_score
            if internal_score <= 0 and (
                record.agenda_score > 0 or record.notebook_score > 0 or record.comment_deduction > 0
            ):
                internal_score = compute_internal_total(
                    agenda_score=record.agenda_score,
                    notebook_score=record.notebook_score,
                    deduction=record.comment_deduction,
                )
            return round(internal_score, 2), round(record.gradebook_score, 2)

        legacy_gradebook = round(record.gradebook_score, 2)
        if legacy_gradebook > 10:
            return legacy_gradebook, round(legacy_gradebook / 2, 2)
        return round(legacy_gradebook * 2, 2), legacy_gradebook

    def to_display_rows(self, records: list[CheckRecord], limit: int = 50) -> list[HistoryDisplayRow]:
        rows: list[HistoryDisplayRow] = []
        for record in records[-limit:]:
            internal_score, gradebook_score = self.resolve_scores(record)
            has_comment = bool(record.comments.strip()) or bool(record.comment_tags.strip())
            rows.append(
                HistoryDisplayRow(
                    student_name=record.student_name,
                    date=record.date,
                    check_mode=record.check_mode,
                    agenda_score=record.agenda_score,
                    notebook_score=record.notebook_score,
                    internal_score=internal_score,
                    gradebook_score=gradebook_score,
                    comment_deduction=record.comment_deduction,
                    has_comment=has_comment,
                    comments=record.comments if has_comment else "",
                )
            )
        return rows
