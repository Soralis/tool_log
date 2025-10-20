"""add workpiece groups and many-to-many line relationships

Revision ID: add_workpiece_groups
Revises: b316b5ef6a65
Create Date: 2025-10-20 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_workpiece_groups'
down_revision: Union[str, None] = 'b316b5ef6a65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create WorkpieceGroup table
    op.create_table(
        'workpiecegroup',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_workpiecegroup_name')
    )

    # Create junction tables for many-to-many relationships
    op.create_table(
        'workpiecegroupmembership',
        sa.Column('workpiece_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['workpiece_id'], ['workpiece.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['workpiecegroup.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workpiece_id', 'group_id')
    )

    op.create_table(
        'workpieceline',
        sa.Column('workpiece_id', sa.Integer(), nullable=False),
        sa.Column('line_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['workpiece_id'], ['workpiece.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['line_id'], ['line.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workpiece_id', 'line_id')
    )

    op.create_table(
        'workpiecegroupline',
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('line_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['workpiecegroup.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['line_id'], ['line.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('group_id', 'line_id')
    )

    # Migrate existing line_id data from workpiece to WorkpieceLine junction table
    # First, get all workpieces with non-null line_id and insert them into WorkpieceLine
    op.execute("""
        INSERT INTO workpieceline (workpiece_id, line_id)
        SELECT id, line_id FROM workpiece WHERE line_id IS NOT NULL
    """)

    # Remove line_id from Workpiece
    op.drop_constraint('workpiece_line_id_fkey', 'workpiece', type_='foreignkey')
    op.drop_column('workpiece', 'line_id')

    # Add workpiece_group_id to Recipe and make workpiece_id optional
    op.add_column('recipe', sa.Column('workpiece_group_id', sa.Integer(), nullable=True))
    op.alter_column('recipe', 'workpiece_id', existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        'recipe_workpiece_group_id_fkey',
        'recipe', 'workpiecegroup',
        ['workpiece_group_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add check constraint to Recipe for XOR between workpiece_id and workpiece_group_id
    op.create_check_constraint(
        'check_workpiece_xor_group',
        'recipe',
        "(workpiece_id IS NOT NULL)::int + (workpiece_group_id IS NOT NULL)::int = 1"
    )

    # Add unique constraints for Recipe
    op.create_unique_constraint('uq_workpiece_machine', 'recipe', ['workpiece_id', 'machine_id'])
    op.create_unique_constraint('uq_group_machine', 'recipe', ['workpiece_group_id', 'machine_id'])

    # Add workpiece_id and workpiece_group_id to ToolLife
    op.add_column('toollife', sa.Column('workpiece_id', sa.Integer(), nullable=True))
    op.add_column('toollife', sa.Column('workpiece_group_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'toollife_workpiece_id_fkey',
        'toollife', 'workpiece',
        ['workpiece_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'toollife_workpiece_group_id_fkey',
        'toollife', 'workpiecegroup',
        ['workpiece_group_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add check constraint to ToolLife
    op.create_check_constraint(
        'check_toollife_workpiece_xor_group',
        'toollife',
        "(workpiece_id IS NOT NULL)::int + (workpiece_group_id IS NOT NULL)::int <= 1"
    )

    # Add workpiece_group_id to ToolConsumption
    op.add_column('toolconsumption', sa.Column('workpiece_group_id', sa.Integer(), nullable=True))
    op.alter_column('toolconsumption', 'workpiece_id', existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        'toolconsumption_workpiece_group_id_fkey',
        'toolconsumption', 'workpiecegroup',
        ['workpiece_group_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add check constraint to ToolConsumption
    op.create_check_constraint(
        'check_consumption_workpiece_xor_group',
        'toolconsumption',
        "(workpiece_id IS NOT NULL)::int + (workpiece_group_id IS NOT NULL)::int <= 1"
    )


def downgrade() -> None:
    # Drop check constraints
    op.drop_constraint('check_consumption_workpiece_xor_group', 'toolconsumption', type_='check')
    op.drop_constraint('check_toollife_workpiece_xor_group', 'toollife', type_='check')
    op.drop_constraint('check_workpiece_xor_group', 'recipe', type_='check')

    # Remove columns from ToolConsumption
    op.drop_constraint('toolconsumption_workpiece_group_id_fkey', 'toolconsumption', type_='foreignkey')
    op.drop_column('toolconsumption', 'workpiece_group_id')
    op.alter_column('toolconsumption', 'workpiece_id', existing_type=sa.Integer(), nullable=False)

    # Remove columns from ToolLife
    op.drop_constraint('toollife_workpiece_group_id_fkey', 'toollife', type_='foreignkey')
    op.drop_constraint('toollife_workpiece_id_fkey', 'toollife', type_='foreignkey')
    op.drop_column('toollife', 'workpiece_group_id')
    op.drop_column('toollife', 'workpiece_id')

    # Remove unique constraints from Recipe
    op.drop_constraint('uq_group_machine', 'recipe', type_='unique')
    op.drop_constraint('uq_workpiece_machine', 'recipe', type_='unique')

    # Remove workpiece_group_id from Recipe
    op.drop_constraint('recipe_workpiece_group_id_fkey', 'recipe', type_='foreignkey')
    op.drop_column('recipe', 'workpiece_group_id')
    op.alter_column('recipe', 'workpiece_id', existing_type=sa.Integer(), nullable=False)

    # Restore line_id to Workpiece from WorkpieceLine junction table
    op.add_column('workpiece', sa.Column('line_id', sa.Integer(), nullable=True))
    op.execute("""
        UPDATE workpiece 
        SET line_id = (SELECT line_id FROM workpieceline WHERE workpieceline.workpiece_id = workpiece.id LIMIT 1)
        WHERE id IN (SELECT workpiece_id FROM workpieceline)
    """)
    op.create_foreign_key(
        'workpiece_line_id_fkey',
        'workpiece', 'line',
        ['line_id'], ['id'],
        ondelete='SET NULL'
    )

    # Drop junction tables
    op.drop_table('workpiecegroupline')
    op.drop_table('workpieceline')
    op.drop_table('workpiecegroupmembership')
    op.drop_table('workpiecegroup')
