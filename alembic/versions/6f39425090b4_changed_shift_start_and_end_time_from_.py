"""changed shift start and end time from datetime to time

Revision ID: 6f39425090b4
Revises: 265a24829e8f
Create Date: 2025-05-02 09:35:17.841320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6f39425090b4'
down_revision: Union[str, None] = '265a24829e8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('shift', 'start_time',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.Time(),
               existing_nullable=False)
    op.alter_column('shift', 'end_time',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.Time(),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('shift', 'end_time',
               existing_type=sa.Time(),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.alter_column('shift', 'start_time',
               existing_type=sa.Time(),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    # ### end Alembic commands ###
