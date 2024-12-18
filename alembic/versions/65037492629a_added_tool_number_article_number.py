"""Added Tool Number / article number

Revision ID: 65037492629a
Revises: 0b246048e92f
Create Date: 2024-12-05 07:17:45.231504

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = '65037492629a'
down_revision: Union[str, None] = '0b246048e92f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First add the column as nullable
    op.add_column('tool', sa.Column('number', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    
    # Create a temp table reference
    tool_table = table('tool',
        column('id', sa.Integer),
        column('number', sa.String)
    )
    
    # Get connection
    connection = op.get_bind()
    
    # Get all existing tools
    tools = connection.execute(sa.select(tool_table.c.id)).fetchall()
    
    # Update each tool with a generated number
    for tool in tools:
        tool_id = tool[0]
        # Generate a unique number using the tool ID
        tool_number = f"T{tool_id:06d}"  # Format: T000001, T000002, etc.
        
        # Update the tool
        connection.execute(
            tool_table.update()
            .where(tool_table.c.id == tool_id)
            .values(number=tool_number)
        )
    
    # Now alter the column to be non-nullable
    op.alter_column('tool', 'number',
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=False
    )
    
    # Finally create the unique index
    op.create_index(op.f('ix_tool_number'), 'tool', ['number'], unique=True)


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_tool_number'), table_name='tool')
    op.drop_column('tool', 'number')
    # ### end Alembic commands ###
