from sqlmodel import SQLModel, Session, create_engine
from dotenv import dotenv_values

env = dotenv_values('.env')

# SQLAlchemy settings
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Create engine
engine = create_engine(
    env['DATABASE_URL'],
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
