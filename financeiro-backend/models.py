from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Date, Boolean # Importado Date e Boolean
from sqlalchemy.orm import relationship, sessionmaker
from database import Base

class Denominacao(Base):
    __tablename__ = 'denominacoes'
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    areas = relationship("AreaEclesiastica", back_populates="denominacao", cascade="all, delete-orphan")
    congregacoes = relationship("Congregacao", back_populates="denominacao", cascade="all, delete-orphan")
    usuarios = relationship("Usuario", back_populates="denominacao", cascade="all, delete-orphan")

class AreaEclesiastica(Base):
    __tablename__ = 'areas_eclesiasticas'
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    denominacao_id = Column(Integer, ForeignKey('denominacoes.id'), nullable=False)
    denominacao = relationship("Denominacao", back_populates="areas")
    congregacoes = relationship("Congregacao", back_populates="area", cascade="all, delete-orphan")
    usuarios_responsavel = relationship("Usuario", back_populates="area_responsavel", cascade="all, delete-orphan")

class Congregacao(Base):
    __tablename__ = 'congregacoes'
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    numero_co = Column(String, nullable=True)
    denominacao_id = Column(Integer, ForeignKey('denominacoes.id'), nullable=False)
    area_id = Column(Integer, ForeignKey('areas_eclesiasticas.id'), nullable=True)
    denominacao = relationship("Denominacao", back_populates="congregacoes")
    area = relationship("AreaEclesiastica", back_populates="congregacoes")
    meses = relationship("Mes", back_populates="congregacao", cascade="all, delete-orphan")
    usuarios = relationship("Usuario", back_populates="congregacao", cascade="all, delete-orphan")
    dizimistas = relationship("DizimistaOfertante", back_populates="congregacao", cascade="all, delete-orphan") # Novo relacionamento
    rendas = relationship("Renda", back_populates="congregacao", cascade="all, delete-orphan") # Novo relacionamento

class DizimistaOfertante(Base): # Novo Modelo
    __tablename__ = 'dizimistas_ofertantes'
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    congregacao_id = Column(Integer, ForeignKey('congregacoes.id'), nullable=False)
    email = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    congregacao = relationship("Congregacao", back_populates="dizimistas")
    rendas = relationship("Renda", back_populates="dizimista_ofertante", cascade="all, delete-orphan") # Novo relacionamento

class Renda(Base): # Novo Modelo
    __tablename__ = 'rendas'
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, nullable=False) # Ex: "Dízimo", "Oferta", "Culto de Oração", "Celebração"
    valor = Column(Float, nullable=False)
    data_registro = Column(Date, nullable=False) # Data em que a renda foi lançada/ocorrida
    numero_recibo = Column(String, nullable=True)
    observacao = Column(String, nullable=True)
    metodo_pagamento = Column(String, nullable=False) # Ex: "Pix", "Espécie", "Transferência", "Cartão"
    congregacao_id = Column(Integer, ForeignKey('congregacoes.id'), nullable=False)
    semana_id = Column(Integer, ForeignKey('semanas.id'), nullable=False)
    dizimista_ofertante_id = Column(Integer, ForeignKey('dizimistas_ofertantes.id'), nullable=True) # Opcional
    congregacao = relationship("Congregacao", back_populates="rendas")
    semana = relationship("Semana", back_populates="rendas")
    dizimista_ofertante = relationship("DizimistaOfertante", back_populates="rendas")

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
    fechado = Column(Boolean, default=False) # Novo campo para indicar se o mês está fechado
    congregacao = relationship("Congregacao", back_populates="meses")
    semanas = relationship("Semana", back_populates="mes", cascade="all, delete-orphan")

class Semana(Base):
    __tablename__ = 'semanas'
    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, nullable=False)
    mes_id = Column(Integer, ForeignKey('meses.id'))
    data_inicio = Column(String, nullable=True)
    data_fim = Column(String, nullable=True)
    saldo_inicial_semana = Column(Float, default=0.0)
    renda_semanal = Column(Float, default=0.0, nullable=True) # Alterado para nullable=True e será calculado
    comissao = Column(Float, default=0.0)
    saldo_final_semana = Column(Float, default=0.0)
    mes = relationship("Mes", back_populates="semanas")
    despesas = relationship("Despesa", back_populates="semana", cascade="all, delete-orphan")
    rendas = relationship("Renda", back_populates="semana", cascade="all, delete-orphan") # Novo relacionamento

class Despesa(Base):
    __tablename__ = 'despesas'
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    data_registro = Column(Date, nullable=True) # Adicionado data_registro na despesa
    # Novo campo: indica se a despesa deve ser gerada automaticamente nas próximas semanas
    recorrente = Column(Boolean, default=False, nullable=False)
    # Periodicidade aceita: "semanal", "quinzenal", "mensal"
    periodicidade = Column(String, nullable=True)
    semana_id = Column(Integer, ForeignKey('semanas.id'))
