# Manual de Integração e Uso da API - Controle Financeiro Eclesiástico

Bem-vindo ao manual da API do Sistema de Gestão Financeira Eclesiástica. Este documento tem como objetivo guiar desenvolvedores (Frontend, Mobile, ou integrações de terceiros) no uso correto dos endpoints, fluxos de autenticação e regras de negócio da aplicação.

---

## 1. Acesso Rápido e Documentação Interativa

A API foi construída usando FastAPI, o que significa que a documentação interativa baseada em OpenAPI está disponível nativamente.
Ao rodar o servidor localmente (ex: `uvicorn main:app --reload`), você pode acessar:

*   **Swagger UI (Recomendado para testes):** `http://127.0.0.1:8000/docs`
*   **ReDoc (Recomendado para leitura):** `http://127.0.0.1:8000/redoc`

---

## 2. Autenticação e Autorização (JWT)

A API utiliza tokens JWT (JSON Web Tokens) para segurança. Quase todos os endpoints exigem que o usuário esteja autenticado.

### Como Autenticar (Login)
1. Faça uma requisição `POST` para `/token`.
2. Envie os dados no formato `application/x-www-form-urlencoded` (Padrão OAuth2):
   * `username`: (E-mail do usuário)
   * `password`: (Senha do usuário)
3. A resposta será um JSON contendo o token:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5c...",
     "token_type": "bearer"
   }
   ```

### Como usar o Token
Em todas as requisições subsequentes para endpoints protegidos, envie o token no cabeçalho (Header) da requisição:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5c...
```

### Perfis de Acesso (RBAC)
O sistema bloqueia ações automaticamente dependendo do nível do usuário logado:
*   **`administrador`**: Acesso total ao sistema. Pode reabrir meses fechados.
*   **`supervisor_denominacao`**: Acesso total a todas as áreas e congregações pertencentes à sua Denominação.
*   **`supervisor_area`**: Acesso total a todas as congregações pertencentes à sua Área Eclesiástica.
*   **`tesoureiro`**: Acesso restrito *apenas* à sua própria Congregação. Não consegue ver dados de outras igrejas.

---

## 3. Fluxo de Trabalho Típico (Passo a Passo)

Para entender como a API foi desenhada, siga este fluxo padrão de uso:

### Etapa 1: Setup Estrutural (Apenas Admins/Supervisores)
Antes de lançar valores, a estrutura física da igreja precisa existir.
1.  **Criar Denominação:** `POST /denominacoes/`
2.  **Criar Área:** `POST /areas_eclesiasticas/` (vinculada à denominação)
3.  **Criar Congregação:** `POST /congregacoes/` (vinculada à denominação e opcionalmente à área)
4.  **Criar Usuários:** `POST /usuarios/` (Crie um usuário com função `tesoureiro` e vincule-o ao ID da Congregação criada).

### Etapa 2: Cadastro de Membros
Os tesoureiros devem cadastrar os membros que contribuem.
1.  **Criar Dizimista/Ofertante:** `POST /congregacoes/{id}/dizimistas/`

### Etapa 3: Operação Financeira Mensal
Este é o fluxo que o tesoureiro fará todas as semanas.

1.  **Abrir o Mês:** `POST /meses/` (Informa o nome do mês, ex: "Janeiro/2024", e a congregação).
2.  **Abrir uma Semana:** `POST /meses/{mes_id}/semanas/` (Informa o número da semana (1 a 5) e as datas de início e fim).
3.  **Lançar Rendas (Entradas):** `POST /semanas/{semana_id}/rendas/`
    *   *Regra:* A API validará se a data informada (`data_registro`) está dentro do período da semana aberta.
    *   *Dica:* Pode-se vincular opcionalmente o ID de um dizimista criado na Etapa 2.
4.  **Lançar Despesas (Saídas):** `POST /meses/{mes_id}/semanas/{semana_numero}/despesas/`
    *   *Nota:* O recálculo de saldo é automático. O sistema atualizará o Saldo Final do Mês a cada renda ou despesa inserida.

### Etapa 4: Fechamento e Relatórios
Ao final do mês, o tesoureiro gera o balancete e congela os dados.

1.  **Gerar Balancete PDF:** `GET /meses/{mes_id}/balancete/pdf`
    *   A API processará os dados e retornará um arquivo `.pdf` binário. No frontend, isso deve ser tratado como um download (Blob).
2.  **Ver Dados do Balancete (JSON):** `GET /meses/{mes_id}/balancete/`
    *   Retorna os totais (entradas, saídas, comissão de 33%, saldo final) em formato JSON para montar dashboards no app.
3.  **Fechar o Mês:** `PUT /meses/{mes_id}/fechar`
    *   *Segurança:* Uma vez fechado, a API retornará erro HTTP 400 se alguém tentar adicionar, deletar ou alterar Rendas, Despesas ou Semanas daquele mês.

*(Apenas Administradores podem usar `PUT /meses/{mes_id}/reabrir` caso o tesoureiro tenha errado).*

---

## 4. Tratamento de Erros e Exclusões (Soft-Block)

A API possui mecanismos de defesa robustos:
*   **Erro 404 (Not Found):** Quando você tenta acessar um ID de recurso que não existe.
*   **Erro 403 (Forbidden):** Quando seu usuário não tem o nível hierárquico necessário para ver aquele dado ou não pertence àquela jurisdição.
*   **Erro 400 (Bad Request):** Geralmente acompanhado de uma mensagem clara no `detail`. Ocorre em validações de negócio, por exemplo:
    *   Tentar deletar uma congregação que já possui meses financeiros lançados (a API proíbe para evitar perda de dados).
    *   Tentar inserir uma renda com data incompatível com a semana.
    *   Tentar alterar dados de um Mês já `fechado`.

---

## 5. Endpoints Principais (Resumo)

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| **POST** | `/token` | Autenticação e geração do JWT. |
| **GET** | `/users/me/` | Retorna os dados do usuário atualmente logado. |
| **CRUD** | `/denominacoes/` | Gerenciamento da hierarquia principal. |
| **CRUD** | `/areas_eclesiasticas/` | Gerenciamento de Áreas/Zonas. |
| **CRUD** | `/congregacoes/` | Gerenciamento de Igrejas/Congregações. |
| **CRUD** | `/congregacoes/{id}/dizimistas/` | Gestão de membros/dizimistas de uma congregação. |
| **POST** | `/meses/` | Cria (Abre) um novo mês financeiro. |
| **PUT** | `/meses/{id}/fechar` | Trava o mês para edições (Fechamento). |
| **CRUD** | `/meses/{id}/semanas/` | Gerenciamento das semanas (máximo 5 por mês). |
| **CRUD** | `/semanas/{id}/rendas/` | Lançamento e gestão de Dízimos e Ofertas. |
| **POST** | `/meses/{id}/semanas/{numero}/despesas/`| Lançamento de despesas de uma semana específica. |
| **GET** | `/meses/{id}/balancete/` | Resumo financeiro total do mês em JSON. |
| **GET** | `/meses/{id}/balancete/pdf` | Gera e baixa o relatório em PDF pronto para impressão. |

> **Dica para Desenvolvedores Frontend:** Em requisições de download do PDF (`/balancete/pdf`), configure o seu client HTTP (como Axios) para aceitar `responseType: 'blob'`.