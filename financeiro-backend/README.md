# Financeiro Backend

## Visão Geral

Este é o backend do sistema de controle financeiro eclesiástico, construído com **FastAPI** e **SQLAlchemy**. Ele foi projetado com uma arquitetura **multitenant**, permitindo a gestão financeira de múltiplas denominações, áreas e congregações de forma isolada e segura.

## Funcionalidades Principais

*   **Autenticação e Autorização (JWT):** Gerenciamento de usuários com diferentes níveis de acesso (administrador, supervisor de denominação, supervisor de área, tesoureiro).
*   **Gestão de Hierarquia Eclesiástica (CRUD):**
    *   Criação, leitura, atualização e exclusão de Denominações.
    *   Criação, leitura, atualização e exclusão de Áreas Eclesiásticas.
    *   Criação, leitura, atualização e exclusão de Congregações.
*   **Gestão Financeira:**
    *   Lançamento e acompanhamento de finanças por Mês e Semana.
    *   Registro de despesas detalhadas.
    *   Recálculo automático de saldos com base em receitas e despesas.
*   **Relatórios:** Geração de balancetes financeiros mensais em formato PDF.
*   **Segurança Multitenant:** Controle de acesso rigoroso para garantir que os usuários só possam visualizar e manipular dados pertencentes à sua respectiva denominação, área ou congregação, conforme sua função.

## Estrutura do Projeto

*   `main.py`: O ponto de entrada da aplicação FastAPI, define os endpoints e a lógica de roteamento.
*   `models.py`: Define os modelos de dados (SQLAlchemy) para o banco de dados.
*   `schemas.py`: Define os esquemas de validação e serialização de dados (Pydantic) para a API.
*   `crud.py`: Contém as operações de Create, Read, Update, Delete (CRUD) para interagir com o banco de dados.
*   `database.py`: Configuração da conexão com o banco de dados.
*   `security.py`: Funções para hashing de senhas e manipulação de tokens JWT.
*   `seed.py`: (Opcional) Script para popular o banco de dados com dados iniciais.
*   `tests/`: Contém os testes automatizados para a aplicação.

## Configuração do Ambiente

1.  **Pré-requisitos:** Certifique-se de ter Python 3.8+ e `pip` instalados.
2.  **Clonar o Repositório:**
    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd financeiro-backend
    ```
3.  **Criar e Ativar Ambiente Virtual:**
    ```bash
    python -m venv .venv
    # No Windows:
    .venv\Scripts\activate
    # No Linux/macOS:
    source .venv/bin/activate
    ```
4.  **Instalar Dependências:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Variáveis de Ambiente:** Se o projeto usar variáveis de ambiente (ex: `SECRET_KEY` para JWT), crie um arquivo `.env` na raiz do projeto e configure-as:
    ```
    SECRET_KEY="sua_chave_secreta_aqui"
    # Outras variáveis de ambiente
    ```

## Execução da Aplicação

Para iniciar o servidor FastAPI, use Uvicorn:

```bash
uvicorn main:app --reload
```
A API estará disponível em `http://127.0.0.1:8000`. Você pode acessar a documentação interativa em `http://127.0.0.1:8000/docs`.

## Testes

Para executar os testes automatizados com Pytest:

```bash
pytest tests/
```
Certifique-se de que todas as dependências de teste (como `pytest`, `pytest-cov`, `httpx` ou `httpx2`) estejam instaladas.
