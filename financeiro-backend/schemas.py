from pydantic import BaseModel, EmailStr
from typing import List, Optional

class DespesaBase(BaseModel):
    descricao: str
    valor: float

class DespesaCreate(DespesaBase):
    pass

class Despesa(DespesaBase):
    id: int
    semana_id: int
    class Config:
        from_attributes = True

class SemanaBase(BaseModel):
    numero: int
    renda_semanal: float
    despesas: List[DespesaCreate] = []

class SemanaCreate(SemanaBase):
    pass

class Semana(SemanaBase):
    id: int
    mes_id: int
    saldo_inicial_semana: float
    comissao: float
    saldo_final_semana: float
    despesas: List[Despesa] = []
    class Config:
        from_attributes = True

class MesBase(BaseModel):
    nome: str
    saldo_inicial: Optional[float] = 0.0

class MesCreate(MesBase):
    congregacao_id: int

class Mes(MesBase):
    id: int
    congregacao_id: int
    saldo_final: float
    semanas: List[Semana] = []
    class Config:
        from_attributes = True

class BalanceteMensal(BaseModel):
    nome_mes: str
    saldo_inicial_mes: float
    total_entradas: float
    total_comissao: float
    total_despesas: float
    saldo_final_consolidado: float

class CongregacaoBase(BaseModel):
    nome: str
    numero_co: Optional[str] = None
    area_id: Optional[int] = None

class CongregacaoCreate(CongregacaoBase):
    denominacao_id: int

class Congregacao(CongregacaoBase):
    id: int
    class Config:
        from_attributes = True

class AreaEclesiasticaBase(BaseModel):
    nome: str

class AreaEclesiasticaCreate(AreaEclesiasticaBase):
    denominacao_id: int

class AreaEclesiastica(AreaEclesiasticaBase):
    id: int
    congregacoes: List[Congregacao] = []
    class Config:
        from_attributes = True

class DenominacaoBase(BaseModel):
    nome: str

class DenominacaoCreate(DenominacaoBase):
    pass

class Denominacao(DenominacaoBase):
    id: int
    areas: List[AreaEclesiastica] = []
    congregacoes: List[Congregacao] = []
    class Config:
        from_attributes = True

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
    area_id: Optional[int] = None
    congregacao_id: Optional[int] = None
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None