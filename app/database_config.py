# from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine#, Session


# Database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
CONNECT_ARGS = {"check_same_thread": False}
# SQLAlchemy settings
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Create engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=CONNECT_ARGS)

# Create SessionLocal
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import all models
# from app.models.models import User, ToolLife, Machine, WorkpieceTool, Tool, ToolOrder, Workpiece, Maintenance
# Initialize database
def init_db():
    SQLModel.metadata.create_all(bind=engine)

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
