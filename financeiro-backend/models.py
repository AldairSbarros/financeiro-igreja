from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta

Base: DeclarativeMeta = declarative_base()

class Denominacao(Base):
    __tablename__ = 'denominacoes'
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    areas = relationship("AreaEclesiastica", back_populates="denominacao")
    congregacoes = relationship("Congregacao", back_populates="denominacao")
    usuarios = relationship("Usuario", back_populates="denominacao")

class AreaEclesiastica(Base):
    __tablename__ = 'areas_eclesiasticas'
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    denominacao_id = Column(Integer, ForeignKey('denominacoes.id'), nullable=False)
    denominacao = relationship("Denominacao", back_populates="areas")
    congregacoes = relationship("Congregacao", back_populates="area")
    usuarios_responsavel = relationship("Usuario", back_populates="area_responsavel")

class Congregacao(Base):
    __tablename__ = 'congregacoes'
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    numero_co = Column(String, nullable=True)
    denominacao_id = Column(Integer, ForeignKey('denominacoes.id'), nullable=False)
    area_id = Column(Integer, ForeignKey('areas_eclesiasticas.id'), nullable=True)
    denominacao = relationship("Denominacao", back_populates="congregacoes")
    area = relationship("AreaEclesiastica", back_populates="congregacoes")
    meses = relationship("Mes", back_populates="congregacao")
    usuarios = relationship("Usuario", back_populates="congregacao")

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    funcao = Column(String, nullable=False)
    denominacao_id = Column(Integer, ForeignKey('denominacoes.id'), nullable=False)
    area_id = Column(Integer, ForeignKey('areas_eclesiasticas.id'), nullable=True)
    congregacao_id = Column(Integer, ForeignKey('congregacoes.id'), nullable=True)
    denominacao = relationship("Denominacao", back_populates="usuarios")
    area_responsavel = relationship("AreaEclesiastica", back_populates="usuarios_responsavel")
    congregacao = relationship("Congregacao", back_populates="usuarios")

class Mes(Base):
    __tablename__ = 'meses'
    id = Column(Integer, primary_key=True, index=True)
    congregacao_id = Column(Integer, ForeignKey('congregacoes.id'), nullable=False)
    nome = Column(String, index=True, nullable=False)
    saldo_inicial = Column(Float, default=0.0)
    saldo_final = Column(Float, default=0.0)
    congregacao = relationship("Congregacao", back_populates="meses")
    semanas = relationship("Semana", back_populates="mes")

class Semana(Base):
    __tablename__ = 'semanas'
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, nullable=False)
    mes_id = Column(Integer, ForeignKey('meses.id'))
    saldo_inicial_semana = Column(Float, default=0.0)
    renda_semanal = Column(Float, default=0.0)
    comissao = Column(Float, default=0.0)
    saldo_final_semana = Column(Float, default=0.0)
    mes = relationship("Mes", back_populates="semanas")
    despesas = relationship("Despesa", back_populates="semana")

class Despesa(Base):
    __tablename__ = 'despesas'
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    semana_id = Column(Integer, ForeignKey('semanas.id'))
    semana = relationship("Semana", back_populates="despesas")

DATABASE_URL = "sqlite:///./financeiro.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()