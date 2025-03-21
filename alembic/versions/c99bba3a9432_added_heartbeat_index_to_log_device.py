"""Added heartbeat index to log_device

Revision ID: c99bba3a9432
Revises: 0dcec4bfb26f
Create Date: 2025-02-24 08:47:07.699751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c99bba3a9432'
down_revision: Union[str, None] = '0dcec4bfb26f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('heartbeat',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('log_device_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['log_device_id'], ['logdevice.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_heartbeat_log_device_id_timestamp', 'heartbeat', ['log_device_id', 'timestamp'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_heartbeat_log_device_id_timestamp', table_name='heartbeat')
    op.drop_table('heartbeat')
    # ### end Alembic commands ###
