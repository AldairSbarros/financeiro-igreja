from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from datetime import date # Importar date para o campo data_registro

# --- Schemas de Despesa ---
class DespesaBase(BaseModel):
    descricao: str
    valor: float
    data_registro: Optional[date] = None # Adicionado data_registro opcional para despesa
    recorrente: Optional[bool] = False # NOVA FLAG: Despesa Recorrente
    periodicidade: Optional[str] = None # NOVA FLAG: 'semanal', 'quinzenal', 'mensal'

class DespesaCreate(DespesaBase):
    pass

class Despesa(DespesaBase):
    id: int
    semana_id: int
    model_config = ConfigDict(from_attributes=True)
# --- Schemas de Renda (Dízimos e Ofertas) ---
class RendaBase(BaseModel):
    tipo: str # Ex: "Dízimo", "Oferta", "Culto de Oração", "Celebração"
    valor: float
    data_registro: date # Usar o tipo date
    numero_recibo: Optional[str] = None
    observacao: Optional[str] = None
    metodo_pagamento: str # Ex: "Pix", "Espécie", "Transferência", "Cartão"
    # congregacao_id e semana_id virão do path ou do contexto do usuário
    dizimista_ofertante_id: Optional[int] = None

class RendaCreate(RendaBase):
    pass

class RendaUpdate(RendaBase):
    tipo: Optional[str] = None
    valor: Optional[float] = None
    data_registro: Optional[date] = None
    numero_recibo: Optional[str] = None
    observacao: Optional[str] = None
    metodo_pagamento: Optional[str] = None
    dizimista_ofertante_id: Optional[int] = None

class Renda(RendaBase):
    id: int
    congregacao_id: int
    semana_id: int
    model_config = ConfigDict(from_attributes=True)

# --- Schemas de Semana (Lógica Simples) ---
class SemanaBase(BaseModel):
    numero: int
    # renda_semanal não é mais um campo de entrada direto para criação/base
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None

class SemanaCreate(SemanaBase):
    despesas: List[DespesaCreate] = []
    # rendas: List[RendaCreate] = [] # Isso será tratado em um endpoint separado ou modificado

class Semana(SemanaBase):
    id: int
    mes_id: int
    saldo_inicial_semana: float # Adicionado de volta
    renda_semanal: Optional[float] = 0.0 # Agora é um valor calculado, opcional na saída
    comissao: float
    saldo_final_semana: float
    despesas: List[Despesa] = []
    rendas: List[Renda] = [] # Incluir rendas para visualização
    model_config = ConfigDict(from_attributes=True)

# --- Schemas de Mês ---
class MesBase(BaseModel):
    nome: str
    fechado: Optional[bool] = False # Adicionado campo fechado

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

# --- NOVA: Schemas de Análise de Mês ---
class RendaItemResumo(BaseModel):
    tipo: str
    total: float
    quantidade: int

class SemanaResumo(BaseModel):
    numero_semana: int
    label: str
    entradas: float
    saidas: float
    saldo_acumulado: float

class MetodoPagamentoResumo(BaseModel):
    metodo_pagamento: str
    total: float
    quantidade: int

class AnaliseMes(BaseModel):
    mes_id: int
    nome_mes: str
    series_entradas_saida: List[SemanaResumo]
    principais_rendas: List[RendaItemResumo]
    resumo_pagamentos: List[MetodoPagamentoResumo]
    totais: dict

# --- Schema do Balancete (Lógica Simples) ---
class BalanceteMensal(BaseModel):
    nome_mes: str
    saldo_inicial_mes: float
    total_entradas: float # Renda Bruta Total
    total_comissao: float # 33% da Renda Bruta
    total_despesas: float # Despesas Manuais
    saldo_final_consolidado: float

# --- Schemas de Dizimista/Ofertante ---
class DizimistaOfertanteBase(BaseModel):
    nome: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None

class DizimistaOfertanteCreate(DizimistaOfertanteBase):
    pass

class DizimistaOfertanteUpdate(DizimistaOfertanteBase):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None

class DizimistaOfertante(DizimistaOfertanteBase):
    id: int
    congregacao_id: int
    model_config = ConfigDict(from_attributes=True)

# --- Schemas de Hierarquia e Usuários ---
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
    dizimistas: List[DizimistaOfertante] = [] # Novo relacionamento para visualização
    rendas: List[Renda] = [] # Novo relacionamento para visualização
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
    is_active: bool = True

class DenominacaoCreate(DenominacaoBase):
    pass

class DenominacaoUpdate(DenominacaoBase):
    nome: Optional[str] = None # Nome agora é opcional para updates

class Denominacao(DenominacaoBase):
    id: int
    areas: List[AreaEclesiastica] = []
    congregacoes: List[Congregacao] = []
    model_config = ConfigDict(from_attributes=True)

# Novo schema para a atualização de status
class DenominacaoStatusUpdate(BaseModel):
    is_active: bool

class UsuarioBase(BaseModel):
    email: EmailStr

class UsuarioCreate(UsuarioBase):
    password: str
    funcao: str
    is_superuser: bool = False
    denominacao_id: Optional[int] = None
    area_id: Optional[int] = None
    congregacao_id: Optional[int] = None

class UsuarioUpdatePassword(BaseModel):
    senha_atual: str
    nova_senha: str

class Usuario(UsuarioBase):
    id: int
    funcao: str
    is_superuser: bool
    denominacao_id: Optional[int] = None
    denominacao: Optional[DenominacaoBase] = None
    area_id: Optional[int] = None
    area_responsavel: Optional[AreaEclesiasticaBase] = None
    congregacao_id: Optional[int] = None
    congregacao: Optional[CongregacaoBase] = None
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# ... (final do arquivo)
# --- Schemas do Painel Master (Superuser) ---

class InitialTenantCreate(BaseModel):
    """Schema para criar a primeira denominação durante o setup."""
    nome_denominacao: str
    admin_email: EmailStr
    admin_password: str

class SetupPayload(BaseModel):
    """Schema completo para o payload do endpoint de setup."""
    superuser_email: EmailStr
    superuser_password: str
    tenant: InitialTenantCreate

class TenantStats(BaseModel):
    """Estatísticas individuais de um tenant."""
    id: int
    nome: str
    is_active: bool
    data_criacao: date # Assumindo que o modelo terá um campo de data
    total_usuarios: int
    total_transacoes: int # Soma de rendas e despesas

class MasterStats(BaseModel):
    """Schema para o dashboard principal do superuser."""
    total_tenants: int
    tenants_ativos: int
    tenants_suspensos: int
    total_usuarios: int
    volume_financeiro_global: float
    crescimento_tenants_mensal: dict[str, int] # Ex: {"2024-01": 5, "2024-02": 8}
    ranking_tenants_ativos: List[TenantStats]
    tamanho_db_mb: float




