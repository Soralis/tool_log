"""added erp and cpn number and manufacturer name to tool, sentiment to note and cost center to machine

Revision ID: cef0cfbd1162
Revises: 9ce0cce93384
Create Date: 2025-01-24 11:08:05.914043

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'cef0cfbd1162'
down_revision: Union[str, None] = '9ce0cce93384'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # First add columns as nullable
    op.add_column('machine', sa.Column('cost_center', sa.Integer(), nullable=True))
    op.add_column('note', sa.Column('sentiment', sa.Enum('VERY_BAD', 'BAD', 'NEUTRAL', 'GOOD', 'VERY_GOOD', name='sentiment'), nullable=True))
    op.add_column('tool', sa.Column('manufacturer_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('tool', sa.Column('erp_number', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('tool', sa.Column('cpn_number', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    
    # Create temporary sequence for unique cost centers
    op.execute("CREATE TEMPORARY SEQUENCE temp_cost_center_seq")
    
    # Add default values for mandatory fields
    op.execute("UPDATE machine SET cost_center = nextval('temp_cost_center_seq')")
    op.execute("UPDATE note SET sentiment = 'NEUTRAL'")
    op.execute("UPDATE tool SET manufacturer_name = 'Unknown Manufacturer ' || id")
    
    # Drop temporary sequence
    op.execute("DROP SEQUENCE temp_cost_center_seq")
    
    # Now make fields non-nullable and add constraints
    op.alter_column('machine', 'cost_center', nullable=False)
    op.alter_column('note', 'sentiment', nullable=False)
    op.alter_column('tool', 'manufacturer_name', nullable=False)
    
    # Create unique constraints and indexes
    op.create_unique_constraint(None, 'machine', ['cost_center'])
    op.create_index(op.f('ix_tool_cpn_number'), 'tool', ['cpn_number'], unique=True)
    op.create_index(op.f('ix_tool_erp_number'), 'tool', ['erp_number'], unique=True)
    op.create_unique_constraint(None, 'tool', ['manufacturer_name'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'tool', type_='unique')
    op.drop_index(op.f('ix_tool_erp_number'), table_name='tool')
    op.drop_index(op.f('ix_tool_cpn_number'), table_name='tool')
    op.drop_column('tool', 'cpn_number')
    op.drop_column('tool', 'erp_number')
    op.drop_column('tool', 'manufacturer_name')
    op.drop_column('note', 'sentiment')
    op.drop_constraint(None, 'machine', type_='unique')
    op.drop_column('machine', 'cost_center')
    # ### end Alembic commands ###
