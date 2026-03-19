"""lowercase_tag_names

Revision ID: 5dd607e5ebee
Revises: 275e5d081bcd
Create Date: 2026-03-19 20:12:40.271973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dd607e5ebee'
down_revision: Union[str, Sequence[str], None] = '275e5d081bcd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # For each tag that has a lowercase duplicate, remap bookmark_tag references
    # to the lowercase version, then delete the mixed-case original.
    tags = conn.execute(sa.text("SELECT id, name FROM tag")).fetchall()
    seen: dict[str, int] = {}  # lowercase name -> canonical id

    for tag_id, name in tags:
        lower = name.lower()
        if lower in seen:
            canonical_id = seen[lower]
            conn.execute(
                sa.text(
                    "UPDATE OR IGNORE bookmark_tag SET tag_id = :canonical WHERE tag_id = :old"
                ),
                {"canonical": canonical_id, "old": tag_id},
            )
            conn.execute(
                sa.text("DELETE FROM bookmark_tag WHERE tag_id = :old"),
                {"old": tag_id},
            )
            conn.execute(sa.text("DELETE FROM tag WHERE id = :old"), {"old": tag_id})
        else:
            seen[lower] = tag_id

    # Lowercase all remaining tag names
    conn.execute(sa.text("UPDATE tag SET name = LOWER(name)"))


def downgrade() -> None:
    pass
