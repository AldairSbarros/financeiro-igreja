from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pytest


def test_list_denominacoes(client: TestClient, setup_data: dict):
    token_admin = setup_data["tokens"]["admin"]
    response = client.get(
        "/denominacoes/",
        headers={
            "Authorization": f"Bearer {token_admin}"
        }
    )
    assert response.status_code == 200
    denominacoes = response.json()
    assert len(denominacoes) == 2
    assert denominacoes[0]["nome"] == "Denominacao Alpha"
    assert denominacoes[1]["nome"] == "Denominacao Beta"

def test_list_areas_by_denominacao_authorized(client: TestClient, setup_data: dict):
    denominacao_alpha_id = setup_data["denominacoes"]["denominacao1"].id
    token_denominacao1 = setup_data["tokens"]["denominacao1"]

    response = client.get(
        f"/denominacoes/{denominacao_alpha_id}/areas/",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        }
    )
    assert response.status_code == 200
    areas = response.json()
    assert len(areas) == 2
    assert areas[0]["nome"] == "Area Central Alpha"
    assert areas[1]["nome"] == "Area Norte Alpha"

def test_list_areas_by_denominacao_unauthorized(client: TestClient, setup_data: dict):
    denominacao_alpha_id = setup_data["denominacoes"]["denominacao1"].id
    token_denominacao2 = setup_data["tokens"]["denominacao2"]

    response = client.get(
        f"/denominacoes/{denominacao_alpha_id}/areas/",
        headers={
            "Authorization": f"Bearer {token_denominacao2}"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Você não pertence a esta denominação."

def test_list_congregacoes_by_area_authorized(client: TestClient, setup_data: dict):
    area_central_alpha_id = setup_data["areas"]["area1_denominacao1"].id
    token_area1_denominacao1 = setup_data["tokens"]["area1_denominacao1"]

    response = client.get(
        f"/areas_eclesiasticas/{area_central_alpha_id}/congregacoes/",
        headers={
            "Authorization": f"Bearer {token_area1_denominacao1}"
        }
    )
    assert response.status_code == 200
    congregacoes = response.json()
    assert len(congregacoes) == 2
    assert congregacoes[0]["nome"] == "Congregacao Sede Alpha"
    assert congregacoes[1]["nome"] == "Congregacao Vila Alpha"

def test_list_congregacoes_by_area_unauthorized(client: TestClient, setup_data: dict):
    area_central_alpha_id = setup_data["areas"]["area1_denominacao1"].id
    token_denominacao2 = setup_data["tokens"]["denominacao2"]

    response = client.get(
        f"/areas_eclesiasticas/{area_central_alpha_id}/congregacoes/",
        headers={
            "Authorization": f"Bearer {token_denominacao2}"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Você não pertence à denominação desta área."

def test_list_congregacoes_by_denominacao_authorized(client: TestClient, setup_data: dict):
    denominacao_alpha_id = setup_data["denominacoes"]["denominacao1"].id
    token_denominacao1 = setup_data["tokens"]["denominacao1"]

    response = client.get(
        f"/denominacoes/{denominacao_alpha_id}/congregacoes/",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        }
    )
    assert response.status_code == 200
    congregacoes = response.json()
    # Deve incluir 3 congregações de área e 1 congregação sem área
    assert len(congregacoes) == 4 
    assert any(c["nome"] == "Congregacao Sede Alpha" for c in congregacoes)
    assert any(c["nome"] == "Congregacao Vila Alpha" for c in congregacoes)
    assert any(c["nome"] == "Congregacao Montanha Alpha" for c in congregacoes)
    assert any(c["nome"] == "Congregacao Independente Alpha" for c in congregacoes)

def test_list_congregacoes_by_denominacao_unauthorized(client: TestClient, setup_data: dict):
    denominacao_alpha_id = setup_data["denominacoes"]["denominacao1"].id
    token_denominacao2 = setup_data["tokens"]["denominacao2"]

    response = client.get(
        f"/denominacoes/{denominacao_alpha_id}/congregacoes/",
        headers={
            "Authorization": f"Bearer {token_denominacao2}"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Você não pertence a esta denominação."
