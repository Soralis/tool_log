"""Added suffix to toolOrder

Revision ID: bfffcd32703c
Revises: 6f8fc8a7bb20
Create Date: 2025-03-17 13:15:22.025842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'bfffcd32703c'
down_revision: Union[str, None] = '6f8fc8a7bb20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('toolorder', sa.Column('number', sqlmodel.sql.sqltypes.AutoString(), nullable=False))
    op.add_column('toolorder', sa.Column('suffix', sqlmodel.sql.sqltypes.AutoString(), nullable=False))
    op.add_column('toolorder', sa.Column('line', sqlmodel.sql.sqltypes.AutoString(), nullable=False))
    op.drop_index('ix_toolorder_order_number', table_name='toolorder')
    op.drop_constraint('toolorder_order_number_order_line_key', 'toolorder', type_='unique')
    op.create_index(op.f('ix_toolorder_number'), 'toolorder', ['number'], unique=False)
    op.create_unique_constraint(None, 'toolorder', ['number', 'suffix', 'line'])
    op.drop_column('toolorder', 'order_number')
    op.drop_column('toolorder', 'order_line')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('toolorder', sa.Column('order_line', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.add_column('toolorder', sa.Column('order_number', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'toolorder', type_='unique')
    op.drop_index(op.f('ix_toolorder_number'), table_name='toolorder')
    op.create_unique_constraint('toolorder_order_number_order_line_key', 'toolorder', ['order_number', 'order_line'])
    op.create_index('ix_toolorder_order_number', 'toolorder', ['order_number'], unique=False)
    op.drop_column('toolorder', 'line')
    op.drop_column('toolorder', 'suffix')
    op.drop_column('toolorder', 'number')
    # ### end Alembic commands ###
