"""Add machine_status notify trigger

Revision ID: add_machine_status_notify
Revises: cb17e33e0bca
Create Date: 2025-04-17 08:45:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'add_machine_status_notify'
down_revision = 'cb17e33e0bca'
branch_labels = None
depends_on = None


def upgrade():
    # Create the trigger function
    op.execute("""
    CREATE OR REPLACE FUNCTION notify_machine_status() RETURNS trigger AS $$
    DECLARE
      payload JSON;
    BEGIN
      IF (TG_OP = 'DELETE') THEN
        payload = json_build_object(
          'op', TG_OP,
          'id', OLD.id
        );
      ELSE
        payload = json_build_object(
          'op', TG_OP,
          'data', row_to_json(NEW)
        );
      END IF;
      PERFORM pg_notify('machine_status', payload::text);
      RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # Attach the trigger to the machine table
    op.execute("""
    DROP TRIGGER IF EXISTS machine_notify_trigger ON machine;
    CREATE TRIGGER machine_notify_trigger
      AFTER INSERT OR UPDATE OR DELETE ON machine
      FOR EACH ROW EXECUTE FUNCTION notify_machine_status();
    """)


def downgrade():
    # Remove trigger and function
    op.execute("DROP TRIGGER IF EXISTS machine_notify_trigger ON machine;")
    op.execute("DROP FUNCTION IF EXISTS notify_machine_status();")
