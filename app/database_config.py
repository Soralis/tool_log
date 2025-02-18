from sqlmodel import SQLModel, Session, create_engine

# Database configuration
# PostgreSQL connection URL for psycopg (v3)
# DEV DB
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost/tool_log_db"

# LIVE DB:
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://postgres:postgres@10.0.36.192/tool_log_db"

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
