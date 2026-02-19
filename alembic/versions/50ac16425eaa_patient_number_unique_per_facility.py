# ruff: noqa: E501
# mypy: ignore-errors
"""patient_number unique per facility

Revision ID: 50ac16425eaa
Revises: df797b3361f4
Create Date: 2026-02-18 20:24:42.611102

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "50ac16425eaa"
down_revision: str | Sequence[str] | None = "df797b3361f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("patients_patient_number_key", "patients", type_="unique")
    op.create_unique_constraint(
        "uq_patients_facility_number", "patients", ["facility_id", "patient_number"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_patients_facility_number", "patients", type_="unique")
    op.create_unique_constraint("patients_patient_number_key", "patients", ["patient_number"])
