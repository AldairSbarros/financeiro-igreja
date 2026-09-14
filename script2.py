with open('financeiro-backend/MANUAL_API.md', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('| **POST** | `/meses/{id}/semanas/{numero}/despesas/`| Lançamento de despesas de uma semana específica. |', 
'| **POST** | `/meses/{id}/semanas/{numero}/despesas/`| Lançamento de despesas de uma semana específica. |\n| **POST** | `/despesas/recorrentes/duplicar`| Duplica as despesas marcadas como recorrentes para o próximo período. |')

text = text.replace('4.  **Lançar Despesas (Saídas):** `POST /meses/{mes_id}/semanas/{semana_numero}/despesas/`\n    *   *Nota:* O recálculo de saldo é automático. O sistema atualizará o Saldo Final do Mês a cada renda ou despesa inserida.',
'4.  **Lançar Despesas (Saídas):** `POST /meses/{mes_id}/semanas/{semana_numero}/despesas/`\n    *   *Nota:* O recálculo de saldo é automático. O sistema atualizará o Saldo Final do Mês a cada renda ou despesa inserida.\n    *   *Recorrência:* É possível cadastrar despesas com as flags `recorrente=True` e `periodicidade` ("semanal", "quinzenal" ou "mensal"). Use `POST /despesas/recorrentes/duplicar` para gerar as cópias automáticas.')

with open('financeiro-backend/MANUAL_API.md', 'w', encoding='utf-8') as f:
    f.write(text)
