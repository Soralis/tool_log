from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.orm import sessionmaker

# Database configuration
# PostgreSQL connection URL for psycopg (v3)
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost/postgres"

# SQLAlchemy settings
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    future=True
)

# Create session factory
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create SessionLocal
def get_session():
    with Session(engine) as session:
        yield session


# Initialize database
def init_db():
    SQLModel.metadata.create_all(bind=engine)
