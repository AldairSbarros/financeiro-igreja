from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func # Importar func para somar
import models, schemas, security

def get_user_by_email(db: Session, email: str):
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def get_denominacao_by_id(db: Session, denominacao_id: int):
    """
    Obtém uma denominação pelo seu ID.
    """
    return db.query(models.Denominacao).filter(models.Denominacao.id == denominacao_id).first()

def get_denominacoes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Denominacao).offset(skip).limit(limit).all()

def update_denominacao(db: Session, denominacao_id: int, denominacao: schemas.DenominacaoUpdate):
    """
    Atualiza uma denominação existente.
    """
    db_denominacao = db.query(models.Denominacao).filter(models.Denominacao.id == denominacao_id).first()
    if db_denominacao:
        update_data = denominacao.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_denominacao, key, value)
        db.add(db_denominacao)
        db.commit()
        db.refresh(db_denominacao)
    return db_denominacao

def delete_denominacao(db: Session, denominacao_id: int):
    """
    Exclui uma denominação pelo seu ID.
    """
    db_denominacao = db.query(models.Denominacao).filter(models.Denominacao.id == denominacao_id).first()
    if db_denominacao:
        db.delete(db_denominacao)
    db.commit()
    return db_denominacao

def get_areas_eclesiasticas_by_denominacao(
    db: Session, denominacao_id: int, skip: int = 0, limit: int = 100
):
    return (
        db.query(models.AreaEclesiastica)
        .filter(models.AreaEclesiastica.denominacao_id == denominacao_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_area_eclesiastica_by_id(db: Session, area_id: int):
    """
    Obtém uma Área Eclesiástica pelo seu ID.
    """
    return db.query(models.AreaEclesiastica).filter(models.AreaEclesiastica.id == area_id).first()

def update_area_eclesiastica(db: Session, area_id: int, area: schemas.AreaEclesiasticaUpdate):
    """
    Atualiza uma Área Eclesiástica existente.
    """
    db_area = db.query(models.AreaEclesiastica).filter(models.AreaEclesiastica.id == area_id).first()
    if db_area:
        update_data = area.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_area, key, value)
        db.add(db_area)
        db.commit()
        db.refresh(db_area)
    return db_area

def delete_area_eclesiastica(db: Session, area_id: int):
    """
    Exclui uma Área Eclesiástica pelo seu ID.
    """
    db_area = db.query(models.AreaEclesiastica).filter(models.AreaEclesiastica.id == area_id).first()
    if db_area:
        db.delete(db_area)
    db.commit()
    return db_area

def get_congregacoes_by_area(db: Session, area_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Congregacao)
        .filter(models.Congregacao.area_id == area_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_congregacoes_by_denominacao(
    db: Session, denominacao_id: int, skip: int = 0, limit: int = 100
):
    return (
        db.query(models.Congregacao)
        .filter(models.Congregacao.denominacao_id == denominacao_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_congregacao_by_id(db: Session, congregacao_id: int):
    """
    Obtém uma Congregação pelo seu ID.
    """
    return db.query(models.Congregacao).filter(models.Congregacao.id == congregacao_id).first()

def update_congregacao(db: Session, congregacao_id: int, congregacao: schemas.CongregacaoUpdate):
    """
    Atualiza uma Congregação existente.
    """
    db_congregacao = db.query(models.Congregacao).filter(models.Congregacao.id == congregacao_id).first()
    if db_congregacao:
        update_data = congregacao.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_congregacao, key, value)
        db.add(db_congregacao)
        db.commit()
        db.refresh(db_congregacao)
    return db_congregacao

def delete_congregacao(db: Session, congregacao_id: int):
    """
    Exclui uma Congregação pelo seu ID.
    """
    db_congregacao = db.query(models.Congregacao).filter(models.Congregacao.id == congregacao_id).first()
    if db_congregacao:
        db.delete(db_congregacao)
    db.commit()
    return db_congregacao

def create_user(db: Session, user: schemas.UsuarioCreate):
    hashed_password = security.get_password_hash(user.password)
    db_user = models.Usuario(
        email=user.email,
        hashed_password=hashed_password,
        funcao=user.funcao,
        denominacao_id=user.denominacao_id,
        area_id=user.area_id,
        congregacao_id=user.congregacao_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_denominacao(db: Session, denominacao: schemas.DenominacaoCreate):
    db_denominacao = models.Denominacao(**denominacao.model_dump())
    db.add(db_denominacao)
    db.commit()
    db.refresh(db_denominacao)
    return db_denominacao

def create_area(db: Session, area: schemas.AreaEclesiasticaCreate):
    db_area = models.AreaEclesiastica(**area.model_dump())
    db.add(db_area)
    db.commit()
    db.refresh(db_area)
    return db_area

def create_congregacao(db: Session, congregacao: schemas.CongregacaoCreate):
    db_congregacao = models.Congregacao(**congregacao.model_dump())
    db.add(db_congregacao)
    db.commit()
    db.refresh(db_congregacao)
    return db_congregacao

# --- Funções CRUD para Dizimistas/Ofertantes ---
def create_dizimista_ofertante(db: Session, dizimista: schemas.DizimistaOfertanteCreate, congregacao_id: int):
    db_dizimista = models.DizimistaOfertante(**dizimista.model_dump(), congregacao_id=congregacao_id)
    db.add(db_dizimista)
    db.commit()
    db.refresh(db_dizimista)
    return db_dizimista

def get_dizimista_ofertante_by_id(db: Session, dizimista_id: int):
    return db.query(models.DizimistaOfertante).filter(models.DizimistaOfertante.id == dizimista_id).first()

def get_dizimistas_ofertantes_by_congregacao(db: Session, congregacao_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(models.DizimistaOfertante)
        .filter(models.DizimistaOfertante.congregacao_id == congregacao_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

def update_dizimista_ofertante(db: Session, dizimista_id: int, dizimista: schemas.DizimistaOfertanteUpdate):
    db_dizimista = db.query(models.DizimistaOfertante).filter(models.DizimistaOfertante.id == dizimista_id).first()
    if db_dizimista:
        update_data = dizimista.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_dizimista, key, value)
        db.add(db_dizimista)
        db.commit()
        db.refresh(db_dizimista)
    return db_dizimista

def delete_dizimista_ofertante(db: Session, dizimista_id: int):
    db_dizimista = db.query(models.DizimistaOfertante).filter(models.DizimistaOfertante.id == dizimista_id).first()
    if db_dizimista:
        db.delete(db_dizimista)
        db.commit()
    return db_dizimista

# --- Funções CRUD para Rendas ---
def create_renda(db: Session, renda: schemas.RendaCreate, congregacao_id: int, semana_id: int):
    db_renda = models.Renda(**renda.model_dump(exclude_unset=True),
                            congregacao_id=congregacao_id,
                            semana_id=semana_id)
    db.add(db_renda)
    db.commit()
    db.refresh(db_renda)
    return db_renda

def get_renda_by_id(db: Session, renda_id: int):
    return db.query(models.Renda).filter(models.Renda.id == renda_id).first()

def get_rendas_by_semana(db: Session, semana_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Renda)
        .filter(models.Renda.semana_id == semana_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

def update_renda(db: Session, renda_id: int, renda: schemas.RendaUpdate):
    db_renda = db.query(models.Renda).filter(models.Renda.id == renda_id).first()
    if db_renda:
        update_data = renda.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_renda, key, value)
        db.add(db_renda)
        db.commit()
        db.refresh(db_renda)
    return db_renda

def delete_renda(db: Session, renda_id: int):
    db_renda = db.query(models.Renda).filter(models.Renda.id == renda_id).first()
    if db_renda:
        db.delete(db_renda)
        db.commit()
    return db_renda

# --- Funções financeiras principais (atualizadas) ---
def create_mes(db: Session, mes: schemas.MesCreate):

    # Encontra o último mês para a congregação
    ultimo_mes = db.query(models.Mes).filter(
        models.Mes.congregacao_id == mes.congregacao_id
    ).order_by(desc(models.Mes.id)).first()

    saldo_inicial = 0.0
    if ultimo_mes:
        # Se JÁ EXISTE um mês, o saldo inicial é OBRIGATORIAMENTE o final do anterior
        saldo_inicial = ultimo_mes.saldo_final
    else:

        # Se é o PRIMEIRO MÊS, usa o valor que veio do formulário
        saldo_inicial = mes.saldo_inicial

    db_mes = models.Mes(
        nome=mes.nome,
        congregacao_id=mes.congregacao_id,
        saldo_inicial=saldo_inicial,
        saldo_final=saldo_inicial  # O saldo final começa igual ao inicial
    )

    db.add(db_mes)
    db.commit()
    db.refresh(db_mes)
    return db_mes

def create_semana(db: Session, semana: schemas.SemanaCreate, mes_id: int):
    # Busca o mês e suas semanas
    mes = db.query(models.Mes).options(joinedload(models.Mes.semanas).joinedload(models.Semana.rendas)).filter(models.Mes.id == mes_id).first() # Modificado para carregar rendas
    if not mes:
        return None # Ou lançar uma exceção

    # Determina o saldo inicial da semana
    if mes.semanas:
        saldo_inicial_semana = mes.semanas[-1].saldo_final_semana
    else:
        saldo_inicial_semana = mes.saldo_inicial

    # A renda_semanal será calculada APÓS a criação das rendas. Começa em 0.0.
    renda_semanal = 0.0
    comissao = renda_semanal * 0.33 # Comissão inicial é 0
    total_despesas = sum(d.valor for d in semana.despesas)
    saldo_final_semana = saldo_inicial_semana + comissao - total_despesas

    # Cria a nova semana
    db_semana = models.Semana(
        numero=semana.numero,
        mes_id=mes_id,
        data_inicio=semana.data_inicio,
        data_fim=semana.data_fim,
        saldo_inicial_semana=saldo_inicial_semana,
        renda_semanal=renda_semanal, # Inicializa com 0.0
        comissao=comissao,
        saldo_final_semana=saldo_final_semana,
    )

    # Adiciona as despesas à semana
    for despesa_data in semana.despesas:
        db_despesa = models.Despesa(
            descricao=despesa_data.descricao,
            valor=despesa_data.valor,
            semana=db_semana
        )
        db.add(db_despesa)

    # As rendas serão adicionadas via endpoint separado, então não as criamos aqui

    # Atualiza o saldo final do mês - isso será recalculado por recalcular_saldos_mes
    # mes.saldo_final = saldo_final_semana # Será movido para recalcular_saldos_mes

    db.add(db_semana)
    db.commit()
    db.refresh(db_semana)
    return db_semana


def recalcular_saldos_mes(db: Session, mes_id: int):
    """
    Função central para recalcular todos os saldos de um mês.
    Deve ser chamada após qualquer alteração em semanas, despesas ou rendas.
    """
    db_mes = (
        db.query(models.Mes)
        .options(joinedload(models.Mes.semanas).joinedload(models.Semana.despesas))
        .options(joinedload(models.Mes.semanas).joinedload(models.Semana.rendas)) # Carrega as rendas
        .filter(models.Mes.id == mes_id)
        .first()
    )
    if not db_mes: return

    semanas_do_mes = sorted(db_mes.semanas, key=lambda s: s.numero) # Garantir ordem das semanas

    saldo_acumulado = db_mes.saldo_inicial

    for s in semanas_do_mes:
        # CALCULA A RENDA SEMANAL A PARTIR DAS RENDAS DETALHADAS
        renda_bruta_semana = sum(r.valor for r in s.rendas) # SOMA TODAS AS RENDAS DA SEMANA
        s.renda_semanal = renda_bruta_semana # Atualiza o campo da semana

        comissao = renda_bruta_semana * 0.33
        s.comissao = comissao

        total_despesas_semana = sum(d.valor for d in s.despesas) # Sum over s.despesas directly

        s.saldo_inicial_semana = saldo_acumulado
        s.saldo_final_semana = (saldo_acumulado + comissao) - total_despesas_semana

        saldo_acumulado = s.saldo_final_semana
        db.add(s)

    db_mes.saldo_final = saldo_acumulado
    db.add(db_mes)
    db.commit()

