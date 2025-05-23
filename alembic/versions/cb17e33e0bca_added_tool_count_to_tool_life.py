"""added tool_count to tool life

Revision ID: cb17e33e0bca
Revises: cd60ac2ba3ae
Create Date: 2025-04-04 10:19:27.182552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb17e33e0bca'
down_revision: Union[str, None] = 'cd60ac2ba3ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('toollife', sa.Column('tool_count', sa.Integer(), nullable=False, server_default='1'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('toollife', 'tool_count')
    # ### end Alembic commands ###
