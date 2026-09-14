import re

with open('financeiro-backend/tests/test_crud_endpoints.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1
text = re.sub(
    r'def test_delete_denominacao_admin_authorized.*?assert response\.status_code == 404',
    '''def test_delete_denominacao_admin_authorized(client: TestClient, setup_data: dict):
    token_admin = setup_data["tokens"]["admin"]
    denominacao_beta_id = setup_data["denominacoes"]["denominacao2"].id

    response = client.delete(f"/denominacoes/{denominacao_beta_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 400

    response_create = client.post("/denominacoes/", headers={"Authorization": f"Bearer {token_admin}"}, json={"nome": "Denominacao Vazia para Delete"})
    nova_denom_id = response_create.json()["id"]

    response = client.delete(f"/denominacoes/{nova_denom_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 204
    response = client.get(f"/denominacoes/{nova_denom_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 404''',
    text,
    flags=re.DOTALL
)

# 2
text = re.sub(
    r'def test_delete_area_eclesiastica_admin_authorized.*?assert response\.status_code == 404',
    '''def test_delete_area_eclesiastica_admin_authorized(client: TestClient, setup_data: dict):
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
    assert response.status_code == 404''',
    text,
    flags=re.DOTALL
)

# 3
text = re.sub(
    r'def test_delete_area_eclesiastica_supervisor_denominacao_authorized.*?assert response\.status_code == 404',
    '''def test_delete_area_eclesiastica_supervisor_denominacao_authorized(client: TestClient, setup_data: dict):
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
    assert response.status_code == 404''',
    text,
    flags=re.DOTALL
)

# 4
text = re.sub(
    r'def test_delete_congregacao_supervisor_area_authorized.*?assert response\.status_code == 404',
    '''def test_delete_congregacao_supervisor_area_authorized(client: TestClient, setup_data: dict):
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
    assert response.status_code == 404''',
    text,
    flags=re.DOTALL
)

with open('financeiro-backend/tests/test_crud_endpoints.py', 'w', encoding='utf-8') as f:
    f.write(text)
