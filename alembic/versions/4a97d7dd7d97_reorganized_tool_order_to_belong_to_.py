"""reorganized tool order to belong to tool not tool life and contain the singular tool price

Revision ID: 4a97d7dd7d97
Revises: 669a6061ef22
Create Date: 2025-02-14 12:12:49.934895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a97d7dd7d97'
down_revision: Union[str, None] = '669a6061ef22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('toollife_tool_order_id_fkey', 'toollife', type_='foreignkey')
    op.drop_column('toollife', 'tool_order_id')
    op.add_column('toolorder', sa.Column('tool_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.alter_column('toolorder', 'gross_price',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('toolorder', 'gross_price',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               nullable=False)
    op.drop_column('toolorder', 'tool_price')
    op.add_column('toollife', sa.Column('tool_order_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('toollife_tool_order_id_fkey', 'toollife', 'toolorder', ['tool_order_id'], ['id'])
    # ### end Alembic commands ###
