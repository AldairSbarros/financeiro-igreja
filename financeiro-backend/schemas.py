from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional

# --- Schemas de Despesa ---
class DespesaBase(BaseModel):
    descricao: str
    valor: float

class DespesaCreate(DespesaBase):
    pass

class Despesa(DespesaBase):
    id: int
    semana_id: int
    model_config = ConfigDict(from_attributes=True)
# --- Schemas de Semana (Lógica Simples) ---
class SemanaBase(BaseModel):
    numero: int
    renda_semanal: float
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None

class SemanaCreate(SemanaBase):
    despesas: List[DespesaCreate] = []

class Semana(SemanaBase):
    id: int
    mes_id: int
    comissao: float
    saldo_final_semana: float
    despesas: List[Despesa] = []
    model_config = ConfigDict(from_attributes=True)
# --- Schemas de Mês ---
class MesBase(BaseModel):
    nome: str

class MesCreate(MesBase):
    congregacao_id: int
    saldo_inicial: Optional[float] = 0.0

class Mes(MesBase):
    id: int
    congregacao_id: int
    saldo_inicial: float
    saldo_final: float
    semanas: List[Semana] = []
    model_config = ConfigDict(from_attributes=True)
# --- Schema do Balancete (Lógica Simples) ---
class BalanceteMensal(BaseModel):
    nome_mes: str
    saldo_inicial_mes: float
    total_entradas: float # Renda Bruta Total
    total_comissao: float # 33% da Renda Bruta
    total_despesas: float # Despesas Manuais
    saldo_final_consolidado: float

# --- Schemas de Hierarquia e Usuários (Sem alterações) ---
class CongregacaoBase(BaseModel):
    nome: str
    numero_co: Optional[str] = None
    area_id: Optional[int] = None

class CongregacaoCreate(CongregacaoBase):
    denominacao_id: int

class CongregacaoUpdate(CongregacaoBase):
    nome: Optional[str] = None
    numero_co: Optional[str] = None
    area_id: Optional[int] = None
    denominacao_id: Optional[int] = None # Pode ser alterada a denominação pai

class Congregacao(CongregacaoBase):
    id: int
    denominacao_id: int
    area_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)
class AreaEclesiasticaBase(BaseModel):
    nome: str

class AreaEclesiasticaCreate(AreaEclesiasticaBase):
    denominacao_id: int

class AreaEclesiasticaUpdate(AreaEclesiasticaBase):
    nome: Optional[str] = None # Nome agora é opcional para updates
    denominacao_id: Optional[int] = None # Pode ser alterada a denominação pai

class AreaEclesiastica(AreaEclesiasticaBase):
    id: int
    denominacao_id: int
    congregacoes: List[Congregacao] = []
    model_config = ConfigDict(from_attributes=True)
class DenominacaoBase(BaseModel):
    nome: str

class DenominacaoCreate(DenominacaoBase):
    pass

class DenominacaoUpdate(DenominacaoBase):
    nome: Optional[str] = None # Nome agora é opcional para updates

class Denominacao(DenominacaoBase):
    id: int
    areas: List[AreaEclesiastica] = []
    congregacoes: List[Congregacao] = []
    model_config = ConfigDict(from_attributes=True)
class UsuarioBase(BaseModel):
    email: EmailStr

class UsuarioCreate(UsuarioBase):
    password: str
    funcao: str
    denominacao_id: int
    area_id: Optional[int] = None
    congregacao_id: Optional[int] = None

class Usuario(UsuarioBase):
    id: int
    funcao: str
    denominacao_id: int
    denominacao: DenominacaoBase # Adicionado
    area_id: Optional[int] = None
    area_responsavel: Optional[AreaEclesiasticaBase] = None # Adicionado
    congregacao_id: Optional[int] = None
    congregacao: Optional[CongregacaoBase] = None # Adicionado
    model_config = ConfigDict(from_attributes=True)
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

