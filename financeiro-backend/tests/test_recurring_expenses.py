"""python financeiro-backend/tests/test_recurring_expenses.py
import pytest
from datetime import date, timedelta

from financeiro.db import crud, models
from financeiro.api import schemas, main, utils

# O conftest já fornece os fixtures: client, db_session, setup_data, mock_get_current_user_factory

def criar_mes_e_semanas(db, congregacao_id):
    """Cria um mês com duas semanas e retorna o objeto Mes."""
    mes = crud.create_mes(
        db,
        schemas.MesCreate(
            nome="Mar/2024",
            congregacao_id=congregacao_id,
            saldo_inicial=1000.0,
        ),
    )
    # Semana 1
    semana1 = crud.create_semana(
        db,
        schemas.SemanaCreate(
            numero=1,
            data_inicio="2024-03-01",
            data_fim="2024-03-07",
            renda_semanal=0,
            despesas=[],
        ),
        mes_id=mes.id,
    )
    # Semana 2 (próxima)
    semana2 = crud.create_semana(
        db,
        schemas.SemanaCreate(
            numero=2,
            data_inicio="2024-03-08",
            data_fim="2024-03-14",
            renda_semanal=0,
            despesas=[],
        ),
        mes_id=mes.id,
    )
    return mes, semana1, semana2

def test_duplicar_despesas_recorrentes(client, db_session, setup_data, mock_get_current_user_factory):
    # -------------------------------------------------------------------------
    # 1️⃣ Preparar dados (congregação, mês, semanas e despesa recorrente)
    # -------------------------------------------------------------------------
    congregacao = setup_data["congregacoes"]["congregacao1_area1"]
    mes, semana1, semana2 = criar_mes_e_semanas(db_session, congregacao.id)

    # Criar uma despesa recorrente na Semana 1
    despesa_recorrente = crud.create_despesa(
        db_session,
        semana_id=semana1.id,
        despesa=schemas.DespesaCreate(
            descricao="Aluguel da Sala",
            valor=200.0,
            data_registro=date(2024, 3, 2),
            recorrente=True,
            periodicidade="semanal",  # pode ser 'semanal', 'quinzenal' ou 'mensal'
        ),
    )
    db_session.commit()

    # -------------------------------------------------------------------------
    # 2️⃣ Mockar o usuário atual (administrador tem permissão)
    # -------------------------------------------------------------------------
    admin_user = setup_data["users"]["admin"]
    main.app.dependency_overrides[utils.get_current_user] = mock_get_current_user_factory(admin_user)

    # -------------------------------------------------------------------------
    # 3️⃣ Chamar o endpoint que duplica as despesas recorrentes
    # -------------------------------------------------------------------------
    response = client.post("/despesas/recorrentes/duplicar")
    assert response.status_code == 200, f"Erro inesperado: {response.text}"
    despesas_geradas = response.json()
    assert isinstance(despesas_geradas, list)
    assert len(despesas_geradas) == 1, "Deveria gerar exatamente 1 despesa duplicada"

    despesa_nova = despesas_geradas[0]

    # -------------------------------------------------------------------------
    # 4️⃣ Validar que a nova despesa está na semana correta (Semana 2)
    # -------------------------------------------------------------------------
    # Busca a despesa no banco para garantir que as relações estão carregadas
    despesa_no_db = db_session.query(models.Despesa).filter(models.Despesa.id == despesa_nova["id"]).first()
    assert despesa_no_db is not None, "Despesa duplicada não encontrada no BD"

    # Deve estar associada à semana 2 (próxima semana)
    assert despesa_no_db.semana_id == semana2.id, "Despesa duplicada não foi atribuída à próxima semana"

    # Os campos recorrentes devem ser preservados
    assert despesa_no_db.recorrente is True
    assert despesa_no_db.periodicidade == "semanal"

    # -------------------------------------------------------------------------
    # 5️⃣ Verificar recalculo de saldos do mês (saldo final deve refletir a nova despesa)
    # -------------------------------------------------------------------------
    # Recarrega o mês para obter o saldo recalculado
    mes_atualizado = db_session.query(models.Mes).filter(models.Mes.id == mes.id).first()
    total_despesas = sum(d.valor for s in mes_atualizado.semanas for d in s.despesas)
    # Saldo final = saldo_inicial + comissão (0) - total_despesas
    esperado = mes_atualizado.saldo_inicial - total_despesas
    assert round(mes_atualizado.saldo_final, 2) == round(esperado, 2)

    # -------------------------------------------------------------------------
    # 6️⃣ Limpar overrides de dependência
    # -------------------------------------------------------------------------
    main.app.dependency_overrides.pop(utils.get_current_user, None)
