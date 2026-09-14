from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pytest

# --- Testes para Denominações ---

def test_update_denominacao_admin_authorized(client: TestClient, setup_data: dict):
    token_admin = setup_data["tokens"]["admin"]
    denominacao_alpha_id = setup_data["denominacoes"]["denominacao1"].id
    updated_name = "Denominacao Alpha Updated"

    response = client.put(
        f"/denominacoes/{denominacao_alpha_id}",
        headers={
            "Authorization": f"Bearer {token_admin}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 200
    assert response.json()["nome"] == updated_name

def test_update_denominacao_unauthorized(client: TestClient, setup_data: dict):
    token_denominacao1 = setup_data["tokens"]["denominacao1"]
    denominacao_alpha_id = setup_data["denominacoes"]["denominacao1"].id
    updated_name = "Denominacao Alpha Unauthorized Update"

    response = client.put(
        f"/denominacoes/{denominacao_alpha_id}",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Apenas administradores podem atualizar denominações."

def test_delete_denominacao_admin_authorized(client: TestClient, setup_data: dict):
    token_admin = setup_data["tokens"]["admin"]
    denominacao_beta_id = setup_data["denominacoes"]["denominacao2"].id

    response = client.delete(f"/denominacoes/{denominacao_beta_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 400

    response_create = client.post("/denominacoes/", headers={"Authorization": f"Bearer {token_admin}"}, json={"nome": "Denominacao Vazia para Delete"})
    nova_denom_id = response_create.json()["id"]

    response = client.delete(f"/denominacoes/{nova_denom_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 204
    response = client.get(f"/denominacoes/{nova_denom_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 404

def test_delete_denominacao_unauthorized(client: TestClient, setup_data: dict):
    token_denominacao1 = setup_data["tokens"]["denominacao1"]
    denominacao_alpha_id = setup_data["denominacoes"]["denominacao1"].id

    response = client.delete(
        f"/denominacoes/{denominacao_alpha_id}",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Apenas administradores podem deletar denominações."

# --- Testes para Áreas Eclesiásticas ---

def test_update_area_eclesiastica_admin_authorized(client: TestClient, setup_data: dict):
    token_admin = setup_data["tokens"]["admin"]
    area_id = setup_data["areas"]["area1_denominacao1"].id
    updated_name = "Area Central Alpha Updated Admin"

    response = client.put(
        f"/areas_eclesiasticas/{area_id}",
        headers={
            "Authorization": f"Bearer {token_admin}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 200
    assert response.json()["nome"] == updated_name

def test_update_area_eclesiastica_supervisor_denominacao_authorized(client: TestClient, setup_data: dict):
    token_denominacao1 = setup_data["tokens"]["denominacao1"]
    area_id = setup_data["areas"]["area2_denominacao1"].id
    updated_name = "Area Norte Alpha Updated Supervisor"

    response = client.put(
        f"/areas_eclesiasticas/{area_id}",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 200
    assert response.json()["nome"] == updated_name

def test_update_area_eclesiastica_supervisor_denominacao_unauthorized_other_denominacao(client: TestClient, setup_data: dict):
    token_denominacao1 = setup_data["tokens"]["denominacao1"]
    area_id_denominacao2 = setup_data["areas"]["area3_denominacao2"].id
    updated_name = "Area Sul Beta Unauthorized Update"

    response = client.put(
        f"/areas_eclesiasticas/{area_id_denominacao2}",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Supervisores de denominação só podem atualizar áreas em sua própria denominação."

def test_update_area_eclesiastica_unauthorized(client: TestClient, setup_data: dict):
    token_congregacao1_area1 = setup_data["tokens"]["congregacao1_area1"]
    area_id = setup_data["areas"]["area1_denominacao1"].id
    updated_name = "Area Central Alpha Unauthorized User Update"

    response = client.put(
        f"/areas_eclesiasticas/{area_id}",
        headers={
            "Authorization": f"Bearer {token_congregacao1_area1}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Apenas administradores ou supervisores de denominação podem atualizar áreas."

def test_delete_area_eclesiastica_admin_authorized(client: TestClient, setup_data: dict):
    token_admin = setup_data["tokens"]["admin"]
    area_id = setup_data["areas"]["area3_denominacao2"].id

    response = client.delete(f"/areas_eclesiasticas/{area_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 400

    denominacao_id = setup_data["denominacoes"]["denominacao1"].id
    response_create = client.post("/areas_eclesiasticas/", headers={"Authorization": f"Bearer {token_admin}"}, json={"nome": "Area Vazia", "denominacao_id": denominacao_id})
    nova_area_id = response_create.json()["id"]

    response = client.delete(f"/areas_eclesiasticas/{nova_area_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 204
    response = client.get(f"/areas_eclesiasticas/{nova_area_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 404

def test_delete_area_eclesiastica_supervisor_denominacao_authorized(client: TestClient, setup_data: dict):
    token_denominacao1 = setup_data["tokens"]["denominacao1"]
    area_id = setup_data["areas"]["area2_denominacao1"].id

    response = client.delete(f"/areas_eclesiasticas/{area_id}", headers={"Authorization": f"Bearer {token_denominacao1}"})
    assert response.status_code == 400

    denominacao_id = setup_data["denominacoes"]["denominacao1"].id
    response_create = client.post("/areas_eclesiasticas/", headers={"Authorization": f"Bearer {token_denominacao1}"}, json={"nome": "Area Vazia Sup", "denominacao_id": denominacao_id})
    nova_area_id = response_create.json()["id"]

    response = client.delete(f"/areas_eclesiasticas/{nova_area_id}", headers={"Authorization": f"Bearer {token_denominacao1}"})
    assert response.status_code == 204
    response = client.get(f"/areas_eclesiasticas/{nova_area_id}", headers={"Authorization": f"Bearer {token_denominacao1}"})
    assert response.status_code == 404

def test_delete_area_eclesiastica_supervisor_denominacao_unauthorized_other_denominacao(client: TestClient, setup_data: dict):
    token_denominacao1 = setup_data["tokens"]["denominacao1"]
    area_id_denominacao2 = setup_data["areas"]["area3_denominacao2"].id

    response = client.delete(
        f"/areas_eclesiasticas/{area_id_denominacao2}",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Supervisores de denominação só podem deletar áreas em sua própria denominação."

def test_delete_area_eclesiastica_unauthorized(client: TestClient, setup_data: dict):
    token_congregacao1_area1 = setup_data["tokens"]["congregacao1_area1"]
    area_id = setup_data["areas"]["area1_denominacao1"].id

    response = client.delete(
        f"/areas_eclesiasticas/{area_id}",
        headers={
            "Authorization": f"Bearer {token_congregacao1_area1}"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Apenas administradores ou supervisores de denominação podem deletar áreas."

# --- Testes para Congregações ---

def test_update_congregacao_admin_authorized(client: TestClient, setup_data: dict):
    token_admin = setup_data["tokens"]["admin"]
    congregacao_id = setup_data["congregacoes"]["congregacao1_area1"].id
    updated_name = "Congregacao Sede Alpha Updated Admin"

    response = client.put(
        f"/congregacoes/{congregacao_id}",
        headers={
            "Authorization": f"Bearer {token_admin}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 200
    assert response.json()["nome"] == updated_name

def test_update_congregacao_supervisor_denominacao_authorized(client: TestClient, setup_data: dict):
    token_denominacao1 = setup_data["tokens"]["denominacao1"]
    congregacao_id = setup_data["congregacoes"]["congregacao3_area2"].id
    updated_name = "Congregacao Montanha Alpha Updated Supervisor Denominacao"

    response = client.put(
        f"/congregacoes/{congregacao_id}",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 200
    assert response.json()["nome"] == updated_name

def test_update_congregacao_supervisor_denominacao_unauthorized_other_denominacao(client: TestClient, setup_data: dict):
    token_denominacao1 = setup_data["tokens"]["denominacao1"]
    congregacao_id_denominacao2 = setup_data["congregacoes"]["congregacao5_area3"].id
    updated_name = "Congregacao Centro Beta Unauthorized Update"

    response = client.put(
        f"/congregacoes/{congregacao_id_denominacao2}",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Supervisores de denominação só podem atualizar congregações em sua própria denominação."

def test_update_congregacao_supervisor_area_authorized(client: TestClient, setup_data: dict):
    token_area1_denominacao1 = setup_data["tokens"]["area1_denominacao1"]
    congregacao_id = setup_data["congregacoes"]["congregacao2_area1"].id
    updated_name = "Congregacao Vila Alpha Updated Supervisor Area"

    response = client.put(
        f"/congregacoes/{congregacao_id}",
        headers={
            "Authorization": f"Bearer {token_area1_denominacao1}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 200
    assert response.json()["nome"] == updated_name

def test_update_congregacao_supervisor_area_unauthorized_other_area(client: TestClient, setup_data: dict):
    token_area1_denominacao1 = setup_data["tokens"]["area1_denominacao1"]
    congregacao_id_area2 = setup_data["congregacoes"]["congregacao3_area2"].id
    updated_name = "Congregacao Montanha Alpha Unauthorized Update"

    response = client.put(
        f"/congregacoes/{congregacao_id_area2}",
        headers={
            "Authorization": f"Bearer {token_area1_denominacao1}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Supervisores de área só podem atualizar congregações em sua própria área."

def test_update_congregacao_unauthorized(client: TestClient, setup_data: dict):
    token_congregacao1_area1 = setup_data["tokens"]["congregacao1_area1"]
    congregacao_id = setup_data["congregacoes"]["congregacao1_area1"].id
    updated_name = "Congregacao Sede Alpha Unauthorized User Update"

    response = client.put(
        f"/congregacoes/{congregacao_id}",
        headers={
            "Authorization": f"Bearer {token_congregacao1_area1}"
        },
        json={
            "nome": updated_name
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Você não tem permissão para atualizar congregações."

def test_delete_congregacao_admin_authorized(client: TestClient, setup_data: dict):
    token_admin = setup_data["tokens"]["admin"]
    congregacao_id_to_delete = setup_data["congregacoes"]["congregacao4_denominacao1"].id

    response = client.delete(
        f"/congregacoes/{congregacao_id_to_delete}",
        headers={
            "Authorization": f"Bearer {token_admin}"
        }
    )
    assert response.status_code == 204

    # Tentar buscar a congregação excluída
    response = client.get(
        f"/congregacoes/{congregacao_id_to_delete}",
        headers={
            "Authorization": f"Bearer {token_admin}"
        }
    )
    assert response.status_code == 404

def test_delete_congregacao_supervisor_denominacao_authorized(client: TestClient, setup_data: dict):
    token_denominacao1 = setup_data["tokens"]["denominacao1"]
    # Usar uma congregação que não está em área para simplificar, mas ainda pertence à denominação
    congregacao_id_to_delete = setup_data["congregacoes"]["congregacao3_area2"].id 

    response = client.delete(
        f"/congregacoes/{congregacao_id_to_delete}",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        }
    )
    assert response.status_code == 204

    # Tentar buscar a congregação excluída
    response = client.get(
        f"/congregacoes/{congregacao_id_to_delete}",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        }
    )
    assert response.status_code == 404

def test_delete_congregacao_supervisor_denominacao_unauthorized_other_denominacao(client: TestClient, setup_data: dict):
    token_denominacao1 = setup_data["tokens"]["denominacao1"]
    congregacao_id_denominacao2 = setup_data["congregacoes"]["congregacao5_area3"].id

    response = client.delete(
        f"/congregacoes/{congregacao_id_denominacao2}",
        headers={
            "Authorization": f"Bearer {token_denominacao1}"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Supervisores de denominação só podem deletar congregações em sua própria denominação."

def test_delete_congregacao_supervisor_area_authorized(client: TestClient, setup_data: dict):
    token_area1_denominacao1 = setup_data["tokens"]["area1_denominacao1"]
    congregacao_id_to_delete = setup_data["congregacoes"]["congregacao1_area1"].id

    response = client.delete(f"/congregacoes/{congregacao_id_to_delete}", headers={"Authorization": f"Bearer {token_area1_denominacao1}"})
    assert response.status_code == 400

    denominacao_id = setup_data["denominacoes"]["denominacao1"].id
    area_id = setup_data["areas"]["area1_denominacao1"].id
    response_create = client.post("/congregacoes/", headers={"Authorization": f"Bearer {token_area1_denominacao1}"}, json={"nome": "Cong Vazia Sup Area", "denominacao_id": denominacao_id, "area_id": area_id})
    nova_cong_id = response_create.json()["id"]

    response = client.delete(f"/congregacoes/{nova_cong_id}", headers={"Authorization": f"Bearer {token_area1_denominacao1}"})
    assert response.status_code == 204
    response = client.get(f"/congregacoes/{nova_cong_id}", headers={"Authorization": f"Bearer {token_area1_denominacao1}"})
    assert response.status_code == 404

def test_delete_congregacao_supervisor_area_unauthorized_other_area(client: TestClient, setup_data: dict):
    token_area1_denominacao1 = setup_data["tokens"]["area1_denominacao1"]
    congregacao_id_area2 = setup_data["congregacoes"]["congregacao3_area2"].id

    response = client.delete(
        f"/congregacoes/{congregacao_id_area2}",
        headers={
            "Authorization": f"Bearer {token_area1_denominacao1}"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Supervisores de área só podem deletar congregações em sua própria área."

def test_delete_congregacao_unauthorized(client: TestClient, setup_data: dict):
    token_congregacao1_area1 = setup_data["tokens"]["congregacao1_area1"]
    congregacao_id = setup_data["congregacoes"]["congregacao1_area1"].id

    response = client.delete(
        f"/congregacoes/{congregacao_id}",
        headers={
            "Authorization": f"Bearer {token_congregacao1_area1}"
        }
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Você não tem permissão para deletar congregações."
