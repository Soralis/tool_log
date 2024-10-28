from sqlmodel import SQLModel, Session, create_engine

# Database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
CONNECT_ARGS = {"check_same_thread": False}
# SQLAlchemy settings
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Create engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=CONNECT_ARGS)

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

# Usage example in a FastAPI route:
# @app.get("/some_route")
# def some_route(db: Session = Depends(get_db)):
#     # Use the db session here
#     pass
