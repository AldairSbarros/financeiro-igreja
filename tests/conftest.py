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
# ... existing code ...