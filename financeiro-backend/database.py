from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base # Alterado

DATABASE_URL = "sqlite:///./financeiro.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base() # Sem alteração nesta linha

# Adicionando a função que faltava
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
