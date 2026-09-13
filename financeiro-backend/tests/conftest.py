import sys
import os

# Adiciona o diretório pai (financeiro-backend) ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app  # Isso deve funcionar agora
from database import Base, get_db
import crud, models, security, schemas
from datetime import timedelta

# Configuração do banco de dados de teste em memória
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
# Use check_same_thread=False para SQLite no desenvolvimento/teste se for usar threads
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency for tests
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine) # Cria as tabelas
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine) # Exclui as tabelas após o teste

@pytest.fixture(scope="module")
def client():
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

# Fixtures para criar dados de teste
@pytest.fixture(scope="function")
def setup_data(db_session):
    # Denominacoes
    denominacao1 = crud.create_denominacao(db_session, schemas.DenominacaoCreate(nome="Denominacao Alpha"))
    denominacao2 = crud.create_denominacao(db_session, schemas.DenominacaoCreate(nome="Denominacao Beta"))

    # Areas Eclesiasticas
    area1_denominacao1 = crud.create_area(db_session, schemas.AreaEclesiasticaCreate(nome="Area Central Alpha", denominacao_id=denominacao1.id))
    area2_denominacao1 = crud.create_area(db_session, schemas.AreaEclesiasticaCreate(nome="Area Norte Alpha", denominacao_id=denominacao1.id))
    area3_denominacao2 = crud.create_area(db_session, schemas.AreaEclesiasticaCreate(nome="Area Sul Beta", denominacao_id=denominacao2.id))

    # Congregacoes
    congregacao1_area1 = crud.create_congregacao(db_session, schemas.CongregacaoCreate(nome="Congregacao Sede Alpha", denominacao_id=denominacao1.id, area_id=area1_denominacao1.id))
    congregacao2_area1 = crud.create_congregacao(db_session, schemas.CongregacaoCreate(nome="Congregacao Vila Alpha", denominacao_id=denominacao1.id, area_id=area1_denominacao1.id))
    congregacao3_area2 = crud.create_congregacao(db_session, schemas.CongregacaoCreate(nome="Congregacao Montanha Alpha", denominacao_id=denominacao1.id, area_id=area2_denominacao1.id))
    congregacao4_denominacao1 = crud.create_congregacao(db_session, schemas.CongregacaoCreate(nome="Congregacao Independente Alpha", denominacao_id=denominacao1.id, area_id=None))
    congregacao5_area3 = crud.create_congregacao(db_session, schemas.CongregacaoCreate(nome="Congregacao Centro Beta", denominacao_id=denominacao2.id, area_id=area3_denominacao2.id))

    # Usuarios
    password = "testpassword"
    hashed_password = security.get_password_hash(password)

    user_admin = crud.create_user(db_session, schemas.UsuarioCreate(
        email="admin@example.com", password=password, funcao="administrador", denominacao_id=denominacao1.id, area_id=None, congregacao_id=None
    ))
    user_denominacao1 = crud.create_user(db_session, schemas.UsuarioCreate(
        email="denominacao1@example.com", password=password, funcao="supervisor_denominacao", denominacao_id=denominacao1.id, area_id=None, congregacao_id=None
    ))
    user_area1_denominacao1 = crud.create_user(db_session, schemas.UsuarioCreate(
        email="area1_denominacao1@example.com", password=password, funcao="supervisor_area", denominacao_id=denominacao1.id, area_id=area1_denominacao1.id, congregacao_id=None
    ))
    user_congregacao1_area1 = crud.create_user(db_session, schemas.UsuarioCreate(
        email="congregacao1_area1@example.com", password=password, funcao="tesoureiro", denominacao_id=denominacao1.id, area_id=area1_denominacao1.id, congregacao_id=congregacao1_area1.id
    ))
    user_denominacao2 = crud.create_user(db_session, schemas.UsuarioCreate(
        email="denominacao2@example.com", password=password, funcao="supervisor_denominacao", denominacao_id=denominacao2.id, area_id=None, congregacao_id=None
    ))

    # Gerar tokens para os usuários
    def create_user_token(user_obj: models.Usuario):
        access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
        return security.create_access_token(
            data={"sub": user_obj.email, "funcao": user_obj.funcao, "denominacao_id": user_obj.denominacao_id, "area_id": user_obj.area_id, "congregacao_id": user_obj.congregacao_id},
            expires_delta=access_token_expires
        )

    tokens = {
        "admin": create_user_token(user_admin),
        "denominacao1": create_user_token(user_denominacao1),
        "area1_denominacao1": create_user_token(user_area1_denominacao1),
        "congregacao1_area1": create_user_token(user_congregacao1_area1),
        "denominacao2": create_user_token(user_denominacao2),
    }

    return {
        "denominacoes": {
            "denominacao1": denominacao1,
            "denominacao2": denominacao2,
        },
        "areas": {
            "area1_denominacao1": area1_denominacao1,
            "area2_denominacao1": area2_denominacao1,
            "area3_denominacao2": area3_denominacao2,
        },
        "congregacoes": {
            "congregacao1_area1": congregacao1_area1,
            "congregacao2_area1": congregacao2_area1,
            "congregacao3_area2": congregacao3_area2,
            "congregacao4_denominacao1": congregacao4_denominacao1,
            "congregacao5_area3": congregacao5_area3,
        },
        "users": {
            "admin": user_admin,
            "denominacao1": user_denominacao1,
            "area1_denominacao1": user_area1_denominacao1,
            "congregacao1_area1": user_congregacao1_area1,
            "denominacao2": user_denominacao2,
        },
        "tokens": tokens,
    }

# Mock para security.get_current_user para testes
@pytest.fixture(scope="function")
def mock_get_current_user_factory(db_session):
    def _mock_get_current_user(user_obj: models.Usuario):
        def _get_current_user():
            # Retorna uma instância do modelo de usuário, garantindo que as relações sejam carregáveis
            return db_session.query(models.Usuario).filter(models.Usuario.id == user_obj.id).first()
        return _get_current_user
    return _mock_get_current_user

