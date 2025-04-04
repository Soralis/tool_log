"""changed date from datetime to date and added time as time

Revision ID: 142d98c7d1fa
Revises: fd4a11a939fb
Create Date: 2025-01-28 12:53:31.712916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '142d98c7d1fa'
down_revision: Union[str, None] = 'fd4a11a939fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ordercompletion', sa.Column('time', sa.Time(), nullable=False))
    op.alter_column('ordercompletion', 'date',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.Date(),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('ordercompletion', 'date',
               existing_type=sa.Date(),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.drop_column('ordercompletion', 'time')
    # ### end Alembic commands ###
