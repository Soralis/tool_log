"""added track_health boolean to log_device

Revision ID: e2ef1da85cb7
Revises: c99bba3a9432
Create Date: 2025-02-24 12:22:18.125181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2ef1da85cb7'
down_revision: Union[str, None] = 'c99bba3a9432'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('logdevice', sa.Column('track_health', sa.Boolean(), nullable=False, server_default='true'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('logdevice', 'track_health')
    # ### end Alembic commands ###
