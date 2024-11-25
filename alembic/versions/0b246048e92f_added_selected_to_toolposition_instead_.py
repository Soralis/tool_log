"""added selected to toolposition instead of active

Revision ID: 0b246048e92f
Revises: cfcdb0ba5e02
Create Date: 2024-11-25 12:33:09.155009

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b246048e92f'
down_revision: Union[str, None] = 'cfcdb0ba5e02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column as nullable first
    op.add_column('toolposition', sa.Column('selected', sa.Boolean(), nullable=True))
    
    # Set default value for existing rows (copying from active column)
    op.execute("UPDATE toolposition SET selected = active")
    
    # Now make it non-nullable
    op.alter_column('toolposition', 'selected',
                    existing_type=sa.Boolean(),
                    nullable=False)
    
    # Update indexes
    op.drop_index('uq_name_recipe_active', table_name='toolposition', postgresql_where='(active = true)')
    op.create_index('uq_name_recipe_selected', 'toolposition', ['name', 'recipe_id'], unique=True, postgresql_where=sa.text('selected = true'))


def downgrade() -> None:
    op.drop_index('uq_name_recipe_selected', table_name='toolposition', postgresql_where=sa.text('selected = true'))
    op.create_index('uq_name_recipe_active', 'toolposition', ['name', 'recipe_id'], unique=True, postgresql_where='(active = true)')
    op.drop_column('toolposition', 'selected')
