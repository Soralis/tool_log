from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

# Database configuration
# For SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///../../tool_log.db"

# # For PostgreSQL
# SQLALCHEMY_DATABASE_URL = "postgresql://username:password@localhost/dbname"

# # For SQLite with full path
# SQLALCHEMY_DATABASE_URL = "sqlite:///C:/Users/ckunde/tool_log.db"

CONNECT_ARGS = {"check_same_thread": False}
# SQLAlchemy settings
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=CONNECT_ARGS,
    future=True,
    execution_options={"sqlite_autoincrement": True}  # Add this option
)

# Enable foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create SessionLocal
def get_session():
    with Session(engine) as session:
        yield session

# Database dependency
def get_db():
    db = get_session()
    try:
        yield next(db)
    finally:
        db.close()
        
# Initialize database
def init_db():
    SQLModel.metadata.create_all(bind=engine)
