"""Added ToolConsumption

Revision ID: a968d09cc3b8
Revises: c07bdfe1f6b6
Create Date: 2025-01-28 16:15:02.880746

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a968d09cc3b8'
down_revision: Union[str, None] = 'c07bdfe1f6b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('toolconsumption',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.DateTime(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.Column('number', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('consumption_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('value', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=False),
    sa.Column('tool_id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('tool_position_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('workpiece_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['machine_id'], ['machine.id'], ),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
    sa.ForeignKeyConstraint(['tool_id'], ['tool.id'], ),
    sa.ForeignKeyConstraint(['tool_position_id'], ['toolposition.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['workpiece_id'], ['workpiece.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_toolconsumption_consumption_type'), 'toolconsumption', ['consumption_type'], unique=False)
    op.create_index(op.f('ix_toolconsumption_date'), 'toolconsumption', ['date'], unique=False)
    op.create_index(op.f('ix_toolconsumption_number'), 'toolconsumption', ['number'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_toolconsumption_number'), table_name='toolconsumption')
    op.drop_index(op.f('ix_toolconsumption_date'), table_name='toolconsumption')
    op.drop_index(op.f('ix_toolconsumption_consumption_type'), table_name='toolconsumption')
    op.drop_table('toolconsumption')
    # ### end Alembic commands ###
