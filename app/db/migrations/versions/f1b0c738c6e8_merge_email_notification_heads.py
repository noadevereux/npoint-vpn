"""merge heads before email notifications

Revision ID: f1b0c738c6e8
Revises: 2b231de97dc3, e3f0e888a563, ece13c4c6f65
Create Date: 2025-02-14 00:00:00.000000

"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision = "f1b0c738c6e8"
down_revision = ("2b231de97dc3", "e3f0e888a563", "ece13c4c6f65")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
