"""added tool setting to replace tool attribute and recreated tool attribute

Revision ID: 291c5d689a06
Revises: e2ef1da85cb7
Create Date: 2025-02-25 09:00:59.435231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '291c5d689a06'
down_revision: Union[str, None] = 'e2ef1da85cb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('toolsetting',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('unit', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('tool_type_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['tool_type_id'], ['tooltype.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'tool_type_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('toolsetting')
    # ### end Alembic commands ###
