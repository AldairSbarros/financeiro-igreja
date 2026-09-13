import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def create_user(email, password, funcao, denominacao_id, area_id=None, congregacao_id=None):
    user_data = {
        "email": email,
        "password": password,
        "funcao": funcao,
        "denominacao_id": denominacao_id,
        "area_id": area_id,
        "congregacao_id": congregacao_id
    }
    response = requests.post(f"{BASE_URL}/usuarios/", json=user_data)
    if response.status_code == 200:
        print(f"User {email} created successfully.")
        return response.json()
    else:
        print(f"Error creating user {email}: {response.text}")
        return None

def main():
    # Criar Denominação
    denominacao_data = {"nome": "Assembleia de Deus"}
    response = requests.post(f"{BASE_URL}/denominacoes/", json=denominacao_data)
    if response.status_code == 200:
        denominacao = response.json()
        print(f"Denominação '{denominacao['nome']}' criada com ID: {denominacao['id']}")
        denominacao_id = denominacao['id']

        # Criar Área Eclesiástica
        area_data = {"nome": "Area 1", "denominacao_id": denominacao_id}
        response = requests.post(f"{BASE_URL}/areas_eclesiasticas/", json=area_data)
        if response.status_code == 200:
            area = response.json()
            print(f"Área '{area['nome']}' criada com ID: {area['id']}")
            area_id = area['id']

            # Criar Congregação
            congregacao_data = {"nome": "Congregação Sede", "denominacao_id": denominacao_id, "area_id": area_id}
            response = requests.post(f"{BASE_URL}/congregacoes/", json=congregacao_data)
            if response.status_code == 200:
                congregacao = response.json()
                print(f"Congregação '{congregacao['nome']}' criada com ID: {congregacao['id']}")
                congregacao_id = congregacao['id']

                # Criar Usuários
                create_user("admin@igreja.com", "admin123", "admin", denominacao_id, area_id, congregacao_id)
                create_user("tesoureiro@igreja.com", "tesoureiro123", "tesoureiro", denominacao_id, area_id, congregacao_id)

            else:
                print(f"Erro ao criar congregação: {response.text}")
        else:
            print(f"Erro ao criar área: {response.text}")
    else:
        print(f"Erro ao criar denominação: {response.text}")

if __name__ == "__main__":
    main()