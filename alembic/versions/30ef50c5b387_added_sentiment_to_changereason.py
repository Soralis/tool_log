"""Added sentiment to changeReason

Revision ID: 30ef50c5b387
Revises: 8b799d3e0abc
Create Date: 2025-01-08 13:59:57.758075

"""
from typing import Sequence, Union
from enum import IntEnum

from alembic import op
import sqlalchemy as sa


class Sentiment(IntEnum):
    VERY_BAD = 1
    BAD = 2
    NEUTRAL = 3
    GOOD = 4
    VERY_GOOD = 5


# revision identifiers, used by Alembic.
revision: str = '30ef50c5b387'
down_revision: Union[str, None] = '8b799d3e0abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type first
    sentiment_enum = sa.Enum(Sentiment, name='sentiment')
    sentiment_enum.create(op.get_bind(), checkfirst=True)
    
    # Add column with default value for existing rows
    op.add_column('changereason', sa.Column('sentiment', sentiment_enum, nullable=False, server_default='NEUTRAL'))


def downgrade() -> None:
    # Drop column first
    op.drop_column('changereason', 'sentiment')
    
    # Then drop the enum type
    sa.Enum(name='sentiment').drop(op.get_bind(), checkfirst=True)
