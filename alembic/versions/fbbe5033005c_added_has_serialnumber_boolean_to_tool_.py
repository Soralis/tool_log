"""Added has serialnumber boolean to tool model

Revision ID: fbbe5033005c
Revises: 59b9fa487567
Create Date: 2025-01-15 11:35:31.597087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbbe5033005c'
down_revision: Union[str, None] = '59b9fa487567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tool', sa.Column('has_serialnumber', sa.Boolean(), nullable=False, server_default='false'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tool', 'has_serialnumber')
    # ### end Alembic commands ###
