"""Added PO line to toolOrder

Revision ID: 6f8fc8a7bb20
Revises: 0c6aed9f25ee
Create Date: 2025-03-17 12:38:00.847467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '6f8fc8a7bb20'
down_revision: Union[str, None] = '0c6aed9f25ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_changeover_timestamps'), 'changeover', ['timestamps'], unique=False)
    op.add_column('toolorder', sa.Column('order_line', sqlmodel.sql.sqltypes.AutoString(), nullable=False))
    op.drop_index('ix_toolorder_order_number', table_name='toolorder')
    op.create_index(op.f('ix_toolorder_order_number'), 'toolorder', ['order_number'], unique=False)
    op.create_unique_constraint(None, 'toolorder', ['order_number', 'order_line'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'toolorder', type_='unique')
    op.drop_index(op.f('ix_toolorder_order_number'), table_name='toolorder')
    op.create_index('ix_toolorder_order_number', 'toolorder', ['order_number'], unique=True)
    op.drop_column('toolorder', 'order_line')
    op.drop_index(op.f('ix_changeover_timestamps'), table_name='changeover')
    # ### end Alembic commands ###
