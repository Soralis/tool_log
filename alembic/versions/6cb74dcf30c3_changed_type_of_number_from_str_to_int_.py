"""Changed type of number from str to int on toolconsumption

Revision ID: 6cb74dcf30c3
Revises: 6d7c6d3e41ee
Create Date: 2025-03-03 11:50:34.908995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cb74dcf30c3'
down_revision: Union[str, None] = '6d7c6d3e41ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('toolconsumption', 'number',
               existing_type=sa.VARCHAR(),
               type_=sa.Integer(),
               postgresql_using='number::integer',
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('toolconsumption', 'number',
               existing_type=sa.Integer(),
               type_=sa.VARCHAR(),
               existing_nullable=False)
    # ### end Alembic commands ###
