from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pytest
from datetime import date

# --- Testes para Dizimistas/Ofertantes ---

def test_create_dizimista_ofertante_authorized(client: TestClient, setup_data: dict):
    token = setup_data["tokens"]["congregacao1_area1"] # Tesoureiro da congregação 1
    congregacao_id = setup_data["congregacoes"]["congregacao1_area1"].id

    response = client.post(
        f"/congregacoes/{congregacao_id}/dizimistas/",
        headers={"Authorization": f"Bearer {token}"},
        json={"nome": "João Dizimista", "email": "joao@example.com"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "João Dizimista"
    assert data["congregacao_id"] == congregacao_id

def test_create_dizimista_ofertante_unauthorized(client: TestClient, setup_data: dict):
    token = setup_data["tokens"]["congregacao1_area1"] # Tesoureiro da congregação 1
    other_congregacao_id = setup_data["congregacoes"]["congregacao5_area3"].id

    response = client.post(
        f"/congregacoes/{other_congregacao_id}/dizimistas/",
        headers={"Authorization": f"Bearer {token}"},
        json={"nome": "João Dizimista", "email": "joao@example.com"}
    )
    assert response.status_code == 403

def test_list_dizimistas_ofertantes_authorized(client: TestClient, setup_data: dict):
    token = setup_data["tokens"]["congregacao1_area1"] # Tesoureiro da congregação 1
    congregacao_id = setup_data["congregacoes"]["congregacao1_area1"].id

    # Criar um dizimista para garantir que a lista não esteja vazia
    client.post(
        f"/congregacoes/{congregacao_id}/dizimistas/",
        headers={"Authorization": f"Bearer {token}"},
        json={"nome": "Maria Ofertante"}
    )

    response = client.get(
        f"/congregacoes/{congregacao_id}/dizimistas/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["nome"] == "Maria Ofertante"

# --- Testes para Rendas (Dízimos e Ofertas) e Recálculo de Saldos ---

def test_create_renda_and_recalculate_saldos(client: TestClient, setup_data: dict):
    token = setup_data["tokens"]["congregacao1_area1"]
    congregacao_id = setup_data["congregacoes"]["congregacao1_area1"].id
    saldo_inicial_mes = 100.0

    # 1. Criar um novo Mês
    mes_response = client.post(
        "/meses/",
        headers={"Authorization": f"Bearer {token}"},
        json={"nome": "2024/01", "congregacao_id": congregacao_id, "saldo_inicial": saldo_inicial_mes}
    )
    assert mes_response.status_code == 201
    mes_data = mes_response.json()
    mes_id = mes_data["id"]
    assert mes_data["saldo_inicial"] == saldo_inicial_mes
    assert mes_data["saldo_final"] == saldo_inicial_mes # Saldo final inicial é igual ao inicial

    # 2. Criar uma nova Semana para o Mês
    semana_response = client.post(
        f"/meses/{mes_id}/semanas/",
        headers={"Authorization": f"Bearer {token}"},
        json={"numero": 1, "data_inicio": "2024-01-01", "data_fim": "2024-01-07"}
    )
    assert semana_response.status_code == 201
    semana_data = semana_response.json()
    semana_id = semana_data["id"]
    assert semana_data["saldo_inicial_semana"] == saldo_inicial_mes
    assert semana_data["renda_semanal"] == 0.0
    assert semana_data["comissao"] == 0.0
    assert semana_data["saldo_final_semana"] == saldo_inicial_mes # Saldo final é igual ao inicial pois não há renda nem despesa

    # 3. Adicionar uma Renda (Dízimo) de 300.0
    renda_valor = 300.0
    renda_response = client.post(
        f"/semanas/{semana_id}/rendas/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "tipo": "Dízimo",
            "valor": renda_valor,
            "data_registro": str(date(2024, 1, 5)),
            "metodo_pagamento": "Pix"
        }
    )
    assert renda_response.status_code == 201

    # 4. Verificar se os saldos foram recalculados corretamente
    mes_recalculado_response = client.get(
        f"/congregacoes/{congregacao_id}/meses/",
        headers={"Authorization": f"Bearer {token}"}
    )
    mes_recalculado_data = mes_recalculado_response.json()[0] # Pega o primeiro e mais recente
    semana_recalculada_data = mes_recalculado_data["semanas"][0]
    
    comissao_esperada = renda_valor * 0.33
    saldo_final_esperado = saldo_inicial_mes + comissao_esperada

    assert semana_recalculada_data["renda_semanal"] == renda_valor
    assert semana_recalculada_data["comissao"] == comissao_esperada
    assert semana_recalculada_data["saldo_final_semana"] == saldo_final_esperado
    assert mes_recalculado_data["saldo_final"] == saldo_final_esperado

def test_delete_renda_and_recalculate_saldos(client: TestClient, setup_data: dict):
    token = setup_data["tokens"]["congregacao1_area1"]
    congregacao_id = setup_data["congregacoes"]["congregacao1_area1"].id

    # 1. Criar Mês, Semana e Renda
    mes_response = client.post("/meses/", headers={"Authorization": f"Bearer {token}"}, json={"nome": "2024/02", "congregacao_id": congregacao_id, "saldo_inicial": 0.0})
    mes_id = mes_response.json()["id"]
    semana_response = client.post(f"/meses/{mes_id}/semanas/", headers={"Authorization": f"Bearer {token}"}, json={"numero": 1})
    semana_id = semana_response.json()["id"]
    renda_response = client.post(
        f"/semanas/{semana_id}/rendas/",
        headers={"Authorization": f"Bearer {token}"},
        json={"tipo": "Oferta", "valor": 100.0, "data_registro": str(date(2024, 2, 3)), "metodo_pagamento": "Espécie"}
    )
    renda_id = renda_response.json()["id"]

    # 2. Verificar o estado inicial
    mes_inicial_response = client.get(f"/congregacoes/{congregacao_id}/meses/", headers={"Authorization": f"Bearer {token}"})
    assert mes_inicial_response.json()[0]["saldo_final"] == 33.0

    # 3. Excluir a Renda
    delete_response = client.delete(f"/rendas/{renda_id}", headers={"Authorization": f"Bearer {token}"})
    assert delete_response.status_code == 204

    # 4. Verificar se os saldos voltaram a 0
    mes_final_response = client.get(f"/congregacoes/{congregacao_id}/meses/", headers={"Authorization": f"Bearer {token}"})
    mes_final_data = mes_final_response.json()[0]
    semana_final_data = mes_final_data["semanas"][0]

    assert semana_final_data["renda_semanal"] == 0.0
    assert semana_final_data["comissao"] == 0.0
    assert semana_final_data["saldo_final_semana"] == 0.0
    assert mes_final_data["saldo_final"] == 0.0
