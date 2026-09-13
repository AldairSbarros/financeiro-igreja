from datetime import timedelta
import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import Response
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from fpdf import FPDF # Importação correta para fpdf2

import crud, models, schemas, security
from database import get_db, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Controle Financeiro Eclesiástico",
    description="Sistema multitenant para gestão financeira de congregações e áreas.",
    version="3.0.0"
)

# --- Configuração de CORS e Autenticação ---
origins = ["http://localhost", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None: raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None: raise credentials_exception
    return user

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos")
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email, "funcao": user.funcao, "congregacao_id": user.congregacao_id},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Endpoints de Setup e Usuários ---
@app.post("/usuarios/", response_model=schemas.Usuario)
def create_user_endpoint(user: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/denominacoes/", response_model=schemas.Denominacao)
def create_denominacao_endpoint(denominacao: schemas.DenominacaoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Apenas administradores podem criar denominações
    if current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem criar denominações.")
    return crud.create_denominacao(db=db, denominacao=denominacao)

@app.get("/denominacoes/{denominacao_id}", response_model=schemas.Denominacao)
def get_denominacao_endpoint(denominacao_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_denominacao = crud.get_denominacao_by_id(db, denominacao_id)
    if not db_denominacao:
        raise HTTPException(status_code=404, detail="Denominação não encontrada.")
    # Qualquer usuário autenticado pode ler uma denominação à qual pertence ou ser administrador
    if current_user.denominacao_id != denominacao_id and current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Você não pertence a esta denominação.")
    return db_denominacao

@app.put("/denominacoes/{denominacao_id}", response_model=schemas.Denominacao)
def update_denominacao_endpoint(
    denominacao_id: int,
    denominacao: schemas.DenominacaoUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Apenas administradores podem atualizar denominações
    if current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem atualizar denominações.")

    db_denominacao = crud.get_denominacao_by_id(db, denominacao_id)
    if not db_denominacao:
        raise HTTPException(status_code=404, detail="Denominação não encontrada.")

    # if current_user.denominacao_id != denominacao_id and current_user.funcao != 'administrador':
    #     raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para atualizar esta denominação.")

    return crud.update_denominacao(db=db, denominacao_id=denominacao_id, denominacao=denominacao)

@app.delete("/denominacoes/{denominacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_denominacao_endpoint(
    denominacao_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Apenas administradores podem deletar denominações
    if current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem deletar denominações.")

    db_denominacao = crud.get_denominacao_by_id(db, denominacao_id)
    if not db_denominacao:
        raise HTTPException(status_code=404, detail="Denominação não encontrada.")

    # TODO: Implementar lógica de verificação se existem áreas/congregações associadas
    # e lidar com a exclusão em cascata ou impedir a exclusão.

    crud.delete_denominacao(db=db, denominacao_id=denominacao_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/areas_eclesiasticas/", response_model=schemas.AreaEclesiastica)
def create_area_endpoint(area: schemas.AreaEclesiasticaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Apenas administradores e supervisores de denominação podem criar áreas
    if current_user.funcao not in ['administrador', 'supervisor_denominacao']:
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores ou supervisores de denominação podem criar áreas.")

    if current_user.funcao == 'supervisor_denominacao' and current_user.denominacao_id != area.denominacao_id:
        raise HTTPException(status_code=403, detail="Acesso negado. Supervisores de denominação só podem criar áreas em sua própria denominação.")

    return crud.create_area(db=db, area=area)

@app.get("/areas_eclesiasticas/{area_id}", response_model=schemas.AreaEclesiastica)
def get_area_eclesiastica_endpoint(area_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_area = crud.get_area_eclesiastica_by_id(db, area_id)
    if not db_area:
        raise HTTPException(status_code=404, detail="Área Eclesiástica não encontrada.")
    # Acesso restrito a usuários da mesma denominação ou administradores
    if current_user.denominacao_id != db_area.denominacao_id and current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Você não pertence à denominação desta área.")
    return db_area

@app.put("/areas_eclesiasticas/{area_id}", response_model=schemas.AreaEclesiastica)
def update_area_eclesiastica_endpoint(
    area_id: int,
    area: schemas.AreaEclesiasticaUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Apenas administradores e supervisores de denominação podem atualizar áreas
    if current_user.funcao not in ['administrador', 'supervisor_denominacao']:
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores ou supervisores de denominação podem atualizar áreas.")

    db_area = crud.get_area_eclesiastica_by_id(db, area_id)
    if not db_area:
        raise HTTPException(status_code=404, detail="Área Eclesiástica não encontrada.")

    # Supervisores de denominação só podem atualizar áreas em sua própria denominação
    if current_user.funcao == 'supervisor_denominacao' and current_user.denominacao_id != db_area.denominacao_id:
        raise HTTPException(status_code=403, detail="Acesso negado. Supervisores de denominação só podem atualizar áreas em sua própria denominação.")

    return crud.update_area_eclesiastica(db=db, area_id=area_id, area=area)

@app.delete("/areas_eclesiasticas/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_area_eclesiastica_endpoint(
    area_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Apenas administradores e supervisores de denominação podem deletar áreas
    if current_user.funcao not in ['administrador', 'supervisor_denominacao']:
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores ou supervisores de denominação podem deletar áreas.")

    db_area = crud.get_area_eclesiastica_by_id(db, area_id)
    if not db_area:
        raise HTTPException(status_code=404, detail="Área Eclesiástica não encontrada.")

    # Supervisores de denominação só podem deletar áreas em sua própria denominação
    if current_user.funcao == 'supervisor_denominacao' and current_user.denominacao_id != db_area.denominacao_id:
        raise HTTPException(status_code=403, detail="Acesso negado. Supervisores de denominação só podem deletar áreas em sua própria denominação.")

    # TODO: Implementar lógica de verificação se existem congregações associadas
    # e lidar com a exclusão em cascata ou impedir a exclusão.

    crud.delete_area_eclesiastica(db=db, area_id=area_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/congregacoes/", response_model=schemas.Congregacao)
def create_congregacao_endpoint(congregacao: schemas.CongregacaoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Apenas administradores, supervisores de denominação ou supervisores de área podem criar congregações
    if current_user.funcao not in ['administrador', 'supervisor_denominacao', 'supervisor_area']:
        raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para criar congregações.")

    # Validar se o usuário tem permissão para criar na denominação/área especificada
    if current_user.funcao == 'supervisor_denominacao' and current_user.denominacao_id != congregacao.denominacao_id:
        raise HTTPException(status_code=403, detail="Acesso negado. Supervisores de denominação só podem criar congregações em sua própria denominação.")

    if current_user.funcao == 'supervisor_area':
        if not congregacao.area_id or current_user.area_id != congregacao.area_id:
            raise HTTPException(status_code=403, detail="Acesso negado. Supervisores de área só podem criar congregações em sua própria área.")
        # Garante que a denominação da congregação corresponde à da área do supervisor
        db_area_supervisor = crud.get_area_eclesiastica_by_id(db, current_user.area_id)
        if not db_area_supervisor or db_area_supervisor.denominacao_id != congregacao.denominacao_id:
            raise HTTPException(status_code=403, detail="Acesso negado. A denominação da congregação não corresponde à denominação da sua área.")

    return crud.create_congregacao(db=db, congregacao=congregacao)

@app.get("/congregacoes/{congregacao_id}", response_model=schemas.Congregacao)
def get_congregacao_endpoint(congregacao_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_congregacao = crud.get_congregacao_by_id(db, congregacao_id)
    if not db_congregacao:
        raise HTTPException(status_code=404, detail="Congregação não encontrada.")

    # Acesso restrito: administrador, ou usuário da mesma denominação/área/congregação
    if current_user.funcao == 'administrador':
        pass # Administrador tem acesso total
    elif current_user.denominacao_id == db_congregacao.denominacao_id:
        pass # Usuário da mesma denominação tem acesso (supervisor de denominação)
    elif current_user.area_id and current_user.area_id == db_congregacao.area_id:
        pass # Usuário da mesma área tem acesso (supervisor de área)
    elif current_user.congregacao_id == db_congregacao.id:
        pass # Tesoureiro da própria congregação tem acesso
    else:
        raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para visualizar esta congregação.")

    return db_congregacao

@app.put("/congregacoes/{congregacao_id}", response_model=schemas.Congregacao)
def update_congregacao_endpoint(
    congregacao_id: int,
    congregacao: schemas.CongregacaoUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Apenas administradores, supervisores de denominação ou supervisores de área podem atualizar congregações
    if current_user.funcao not in ['administrador', 'supervisor_denominacao', 'supervisor_area']:
        raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para atualizar congregações.")

    db_congregacao = crud.get_congregacao_by_id(db, congregacao_id)
    if not db_congregacao:
        raise HTTPException(status_code=404, detail="Congregação não encontrada.")

    # Validar permissões de atualização
    if current_user.funcao == 'supervisor_denominacao' and current_user.denominacao_id != db_congregacao.denominacao_id:
        raise HTTPException(status_code=403, detail="Acesso negado. Supervisores de denominação só podem atualizar congregações em sua própria denominação.")

    if current_user.funcao == 'supervisor_area' and current_user.area_id != db_congregacao.area_id:
        raise HTTPException(status_code=403, detail="Acesso negado. Supervisores de área só podem atualizar congregações em sua própria área.")

    # Se um supervisor tentar mudar a denominação/área pai da congregação
    if current_user.funcao != 'administrador':
        if congregacao.denominacao_id is not None and congregacao.denominacao_id != db_congregacao.denominacao_id:
            raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para alterar a denominação de uma congregação.")
        if congregacao.area_id is not None and congregacao.area_id != db_congregacao.area_id:
            raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para alterar a área de uma congregação.")

    return crud.update_congregacao(db=db, congregacao_id=congregacao_id, congregacao=congregacao)

@app.delete("/congregacoes/{congregacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_congregacao_endpoint(
    congregacao_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Apenas administradores, supervisores de denominação ou supervisores de área podem deletar congregações
    if current_user.funcao not in ['administrador', 'supervisor_denominacao', 'supervisor_area']:
        raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para deletar congregações.")

    db_congregacao = crud.get_congregacao_by_id(db, congregacao_id)
    if not db_congregacao:
        raise HTTPException(status_code=404, detail="Congregação não encontrada.")

    # Validar permissões de exclusão
    if current_user.funcao == 'supervisor_denominacao' and current_user.denominacao_id != db_congregacao.denominacao_id:
        raise HTTPException(status_code=403, detail="Acesso negado. Supervisores de denominação só podem deletar congregações em sua própria denominação.")

    if current_user.funcao == 'supervisor_area' and current_user.area_id != db_congregacao.area_id:
        raise HTTPException(status_code=403, detail="Acesso negado. Supervisores de área só podem deletar congregações em sua própria área.")

    # TODO: Implementar lógica de verificação se existem meses/semanas/despesas associados
    # e lidar com a exclusão em cascata ou impedir a exclusão.

    crud.delete_congregacao(db=db, congregacao_id=congregacao_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/users/me/", response_model=schemas.Usuario)
def read_users_me(current_user: models.Usuario = Depends(get_current_user)):
    return current_user

# --- Endpoints de Listagem ---
@app.get("/denominacoes/", response_model=List[schemas.Denominacao])
def list_denominacoes(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Qualquer usuário autenticado pode listar denominações
    return crud.get_denominacoes(db)

@app.get("/denominacoes/{denominacao_id}/areas/", response_model=List[schemas.AreaEclesiastica])
def list_areas_by_denominacao(
    denominacao_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Acesso restrito a usuários da mesma denominação ou administradores
    if current_user.denominacao_id != denominacao_id and current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Você não pertence a esta denominação.")

    areas = crud.get_areas_eclesiasticas_by_denominacao(db, denominacao_id)
    return areas

@app.get("/areas_eclesiasticas/{area_id}/congregacoes/", response_model=List[schemas.Congregacao])
def list_congregacoes_by_area(
    area_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Verificar se a área pertence à denominação do usuário ou se é administrador
    db_area = db.query(models.AreaEclesiastica).filter(models.AreaEclesiastica.id == area_id).first()
    if not db_area: raise HTTPException(status_code=404, detail="Área Eclesiástica não encontrada.")

    if current_user.denominacao_id != db_area.denominacao_id and current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Você não pertence à denominação desta área.")

    congregacoes = crud.get_congregacoes_by_area(db, area_id)
    return congregacoes

@app.get("/denominacoes/{denominacao_id}/congregacoes/", response_model=List[schemas.Congregacao])
def list_congregacoes_by_denominacao(
    denominacao_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Acesso restrito a usuários da mesma denominação ou administradores
    if current_user.denominacao_id != denominacao_id and current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Você não pertence a esta denominação.")

    congregacoes = crud.get_congregacoes_by_denominacao(db, denominacao_id)
    return congregacoes

# --- LÓGICA DE GERAÇÃO DE PDF ---
class PDF(FPDF):
    def __init__(self, orientation='P', unit='mm', format='A4',
                 denominacao_nome="", area_nome="", congregacao_nome="",
                 usuario_email="", usuario_funcao=""):
        super().__init__(orientation, unit, format)
        self.denominacao_nome = denominacao_nome
        self.area_nome = area_nome
        self.congregacao_nome = congregacao_nome
        self.usuario_email = usuario_email
        self.usuario_funcao = usuario_funcao
        self.data_geracao = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def header(self):
        # Logo (Placeholder de texto)
        self.set_font('Arial', 'B', 10)
        self.set_xy(10, 10)
        self.cell(40, 10, 'LOGO DA IGREJA', 1, 0, 'C') # Placeholder para a logo
        # Para adicionar uma imagem real, você usaria:
        # self.image('caminho/para/sua/logo.png', 10, 8, 33)
        
        # Informações da Denominação, Área e Congregação
        self.set_font('Arial', 'B', 12)
        self.set_xy(55, 10)
        self.cell(0, 5, f"Denominação: {self.denominacao_nome}", 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.set_x(55)
        self.cell(0, 5, f"Área/Zona/Distrito: {self.area_nome}", 0, 1, 'L')
        self.set_x(55)
        self.cell(0, 5, f"Congregação: {self.congregacao_nome}", 0, 1, 'L')
        self.ln(5) # Linha em branco

        # Título do Relatório
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Balancete Financeiro Mensal', 0, 1, 'C')
        self.ln(5)

        # Informações do Usuário e Data de Geração
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f"Gerado por: {self.usuario_email} ({self.usuario_funcao})", 0, 1, 'R')
        self.cell(0, 5, f"Data de Geração: {self.data_geracao}", 0, 1, 'R')
        self.ln(10) # Espaço após o cabeçalho

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@app.get("/meses/{mes_id}/balancete/pdf")
def gerar_balancete_pdf(mes_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_mes = db.query(models.Mes).filter(models.Mes.id == mes_id).first()
    if not db_mes: raise HTTPException(status_code=404, detail="Mês não encontrado.")
    if current_user.congregacao_id != db_mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")

    semanas = db.query(models.Semana).options(joinedload(models.Semana.despesas)).filter(models.Semana.mes_id == mes_id).order_by(models.Semana.numero).all()
    
    total_entradas_brutas = sum(s.renda_semanal for s in semanas)
    total_comissao = sum(s.comissao for s in semanas)
    total_despesas_mes = sum(d.valor for s in semanas for d in s.despesas)
    saldo_final_consolidado = db_mes.saldo_inicial + total_comissao - total_despesas_mes

    # Instanciar PDF com os dados coletados
    pdf = PDF('P', 'mm', 'A4',
              denominacao_nome=denominacao.nome if denominacao else "N/A",
              area_nome=area.nome if area else "N/A",
              congregacao_nome=congregacao.nome if congregacao else "N/A",
              usuario_email=current_user.email,
              usuario_funcao=current_user.funcao)
    
    pdf.add_page()
    pdf.set_font('Arial', '', 12)

    # Tabela de Resumo Financeiro
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Resumo Financeiro do Mês", 0, 1, 'L')
    pdf.ln(2)

    pdf.set_font('Arial', '', 10)
    celula_largura = 95
    celula_altura = 7

    pdf.cell(celula_largura, celula_altura, "Saldo do Mês Anterior:", 1, 0, 'L')
    pdf.cell(celula_largura, celula_altura, formatar_moeda(db_mes.saldo_inicial), 1, 1, 'R')

    pdf.cell(celula_largura, celula_altura, "Total de Entradas Brutas:", 1, 0, 'L')
    pdf.cell(celula_largura, celula_altura, formatar_moeda(total_entradas_brutas), 1, 1, 'R')
    
    pdf.set_text_color(0, 128, 0) # Verde
    pdf.cell(celula_largura, celula_altura, "(+) Comissão p/ Caixa (33%):", 1, 0, 'L')
    pdf.cell(celula_largura, celula_altura, formatar_moeda(total_comissao), 1, 1, 'R')
    pdf.set_text_color(0, 0, 0) # Reseta para preto

    pdf.set_text_color(255, 0, 0) # Vermelho
    pdf.cell(celula_largura, celula_altura, "(-) Total de Despesas:", 1, 0, 'L')
    pdf.cell(celula_largura, celula_altura, f"-{formatar_moeda(total_despesas_mes)}", 1, 1, 'R')
    pdf.set_text_color(0, 0, 0) # Reseta

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(celula_largura, celula_altura, "SALDO FINAL EM CAIXA:", 1, 0, 'L')
    pdf.cell(celula_largura, celula_altura, formatar_moeda(saldo_final_consolidado), 1, 1, 'R')
    pdf.ln(10)

    # Tabela de Despesas Detalhadas
    if total_despesas_mes > 0:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Despesas Detalhadas por Semana", 0, 1, 'L')
        pdf.ln(2)
        
        for semana in semanas:
            if semana.despesas:
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 7, f"Semana {semana.numero} ({semana.data_inicio or 'N/A'} - {semana.data_fim or 'N/A'})", 1, 1, 'L')
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(140, 6, "Descrição", 1, 0, 'C')
                pdf.cell(50, 6, "Valor", 1, 1, 'C')
                pdf.set_font('Arial', '', 9)
                for despesa in semana.despesas:
                    pdf.cell(140, 6, f"  {despesa.descricao}", 1, 0, 'L')
                    pdf.cell(50, 6, formatar_moeda(despesa.valor), 1, 1, 'R')
                pdf.ln(2) # Pequeno espaço entre semanas

    pdf_output = pdf.output(dest='S') # Já é bytearray, não precisa de .encode()
    
    return Response(content=bytes(pdf_output), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="balancete_{db_mes.nome.replace("/", "-")}.pdf"'})

# --- LÓGICA FINANCEIRA PRINCIPAL ---
def recalcular_saldos_mes(db: Session, mes_id: int):
    """
    Função central para recalcular todos os saldos de um mês.
    Deve ser chamada após qualquer alteração em semanas ou despesas.
    """
    db_mes = db.query(models.Mes).options(joinedload(models.Mes.semanas).joinedload(models.Semana.despesas)).filter(models.Mes.id == mes_id).first()
    if not db_mes: return

    semanas_do_mes = sorted(db_mes.semanas, key=lambda s: s.numero) # Garantir ordem das semanas
    
    saldo_acumulado = db_mes.saldo_inicial
    
    for s in semanas_do_mes:
        renda_bruta_semana = s.renda_semanal

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


@app.get("/congregacoes/{congregacao_id}/meses/", response_model=List[schemas.Mes])
def listar_meses_congregacao(congregacao_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.congregacao_id != congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")
    meses = db.query(models.Mes).options(joinedload(models.Mes.semanas).joinedload(models.Semana.despesas)).filter(models.Mes.congregacao_id == congregacao_id).order_by(models.Mes.id.desc()).all()
    return meses

@app.post("/meses/", response_model=schemas.Mes, status_code=status.HTTP_201_CREATED)
def criar_mes_endpoint(mes: schemas.MesCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.congregacao_id != mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")
    return crud.create_mes(db=db, mes=mes)

@app.get("/meses/{mes_id}/semanas/", response_model=List[schemas.Semana])
def listar_semanas(mes_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    semanas = db.query(models.Semana).options(joinedload(models.Semana.despesas)).filter(models.Semana.mes_id == mes_id).order_by(models.Semana.numero).all()
    return semanas

@app.post("/meses/{mes_id}/semanas/", response_model=schemas.Semana, status_code=status.HTTP_201_CREATED)
def adicionar_semana_endpoint(mes_id: int, semana: schemas.SemanaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_mes = db.query(models.Mes).options(joinedload(models.Mes.semanas)).filter(models.Mes.id == mes_id).first()
    if not db_mes: raise HTTPException(status_code=404, detail="Mês não encontrado.")
    if current_user.congregacao_id != db_mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    semana_existente = next((s for s in db_mes.semanas if s.numero == semana.numero), None)
    if semana_existente:
        raise HTTPException(status_code=400, detail=f"A Semana {semana.numero} já foi lançada para este mês.")

    if len(db_mes.semanas) >= 5:
        raise HTTPException(status_code=400, detail="Não é possível adicionar mais de 5 semanas a um mês.")
    
    nova_semana = crud.create_semana(db=db, semana=semana, mes_id=mes_id)
    recalcular_saldos_mes(db, mes_id) # Recalcula o mês após adicionar a semana
    return nova_semana

@app.post("/meses/{mes_id}/semanas/{semana_numero}/despesas/", response_model=schemas.Despesa)
def adicionar_despesa_endpoint(mes_id: int, semana_numero: int, despesa: schemas.DespesaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_semana = db.query(models.Semana).filter_by(mes_id=mes_id, numero=semana_numero).first()
    if not db_semana: raise HTTPException(status_code=404, detail="Semana não encontrada.")
    if current_user.congregacao_id != db_semana.mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")

    nova_despesa = models.Despesa(descricao=despesa.descricao, valor=despesa.valor, semana_id=db_semana.id)
    db.add(nova_despesa)
    db.commit()
    db.refresh(nova_despesa)

    recalcular_saldos_mes(db, mes_id) # CORREÇÃO: Apenas recalcula, não recria a semana
    return nova_despesa

@app.delete("/despesas/{despesa_id}")
def remover_despesa(despesa_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_despesa = db.query(models.Despesa).filter(models.Despesa.id == despesa_id).first()
    if not db_despesa: raise HTTPException(status_code=404, detail="Despesa não encontrada.")
    if current_user.congregacao_id != db_despesa.semana.mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    mes_id = db_despesa.semana.mes_id
    db.delete(db_despesa)
    db.commit()

    recalcular_saldos_mes(db, mes_id)
    return {"detail": "Despesa removida com sucesso."}

@app.get("/meses/{mes_id}/balancete/", response_model=schemas.BalanceteMensal)
def obter_balancete_mensal(mes_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_mes = db.query(models.Mes).filter(models.Mes.id == mes_id).first()
    if not db_mes: raise HTTPException(status_code=404, detail="Mês não encontrado.")
    if current_user.congregacao_id != db_mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    semanas = db.query(models.Semana).options(joinedload(models.Semana.despesas)).filter(models.Semana.mes_id == mes_id).all()
    
    total_entradas_brutas = sum(s.renda_semanal for s in semanas)
    total_comissao = sum(s.comissao for s in semanas)
    total_despesas = sum(d.valor for s in semanas for d in s.despesas)
    
    saldo_final_consolidado = db_mes.saldo_inicial + total_comissao - total_despesas

    return schemas.BalanceteMensal(
        nome_mes=db_mes.nome,
        saldo_inicial_mes=db_mes.saldo_inicial,
        total_entradas=total_entradas_brutas,
        total_comissao=total_comissao,
        total_despesas=total_despesas,
        saldo_final_consolidado=saldo_final_consolidado,
    )