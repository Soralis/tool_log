"""added tool life measurement boolean to machine model

Revision ID: cfcdb0ba5e02
Revises: c0155276dbf0
Create Date: 2024-11-25 08:25:16.966526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfcdb0ba5e02'
down_revision: Union[str, None] = 'c0155276dbf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the column
    op.add_column('machine', sa.Column('measures_tool_life', sa.Boolean(), nullable=True))
    
    # Update all existing rows to set measures_tool_life to False
    op.execute("UPDATE machine SET measures_tool_life = FALSE")
    
    # Alter the column to make it non-nullable
    op.alter_column('machine', 'measures_tool_life',
        existing_type=sa.BOOLEAN(),
        nullable=False)

def downgrade() -> None:
    # Remove the column in the downgrade method
    op.drop_column('machine', 'measures_tool_life')
