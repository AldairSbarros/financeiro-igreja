from datetime import timedelta
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import crud, models, schemas, security
from models import get_db

models.Base.metadata.create_all(bind=models.engine)

app = FastAPI(
    title="API de Controle Financeiro Eclesiástico",
    description="Sistema multitenant para gestão financeira de congregações e áreas.",
    version="2.1.2"
)

origins = [
    "http://localhost",
    "http://localhost:3000",
]
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
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

@app.post("/token", response_model=schemas.Token, summary="Login do usuário")
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email, "funcao": user.funcao, "congregacao_id": user.congregacao_id, "area_id": user.area_id}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/denominacoes/", response_model=schemas.Denominacao, summary="Cria uma nova denominação (Aberto para setup inicial)")
def create_denominacao(denominacao: schemas.DenominacaoCreate, db: Session = Depends(get_db)):
    return crud.create_denominacao(db, denominacao)

@app.post("/usuarios/", response_model=schemas.Usuario, summary="Cria um novo usuário (Aberto para setup inicial)")
def create_user(user: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_denominacao = db.query(models.Denominacao).filter(models.Denominacao.id == user.denominacao_id).first()
    if not db_denominacao:
        raise HTTPException(status_code=404, detail="Denominação não encontrada. Crie uma primeiro.")
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    return crud.create_user(db=db, user=user)

@app.get("/users/me/", response_model=schemas.Usuario, summary="Verifica o usuário logado (Protegido)")
def read_users_me(current_user: models.Usuario = Depends(get_current_user)):
    return current_user

@app.post("/areas/", response_model=schemas.AreaEclesiastica, summary="Cria uma nova Área Eclesiástica (Admin Only)")
def create_area(area: schemas.AreaEclesiasticaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.funcao != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores podem criar áreas.")
    return crud.create_area(db, area)

@app.post("/congregacoes/", response_model=schemas.Congregacao, summary="Cria uma nova Congregação (Admin ou Pastor de Área)")
def create_congregacao(congregacao: schemas.CongregacaoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.funcao not in ["admin", "pastor_area"]:
        raise HTTPException(status_code=403, detail="Apenas administradores ou pastores de área podem criar congregações.")
    return crud.create_congregacao(db, congregacao)

@app.post("/meses/", response_model=schemas.Mes, summary="Cria um novo mês financeiro (Protegido)")
def criar_mes(mes: schemas.MesCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.funcao == "tesoureiro" and current_user.congregacao_id != mes.congregacao_id:
        raise HTTPException(status_code=403, detail="Você só pode criar meses para a sua própria congregação.")
    if current_user.funcao not in ["admin", "tesoureiro", "pastor_area"]:
        raise HTTPException(status_code=403, detail="Você não tem permissão para criar um mês financeiro.")

    ultimo_mes = db.query(models.Mes).filter(models.Mes.congregacao_id == mes.congregacao_id).order_by(models.Mes.id.desc()).first()
    saldo_inicial = mes.saldo_inicial
    if ultimo_mes and saldo_inicial == 0.0:
        saldo_inicial = ultimo_mes.saldo_final
    
    db_mes = models.Mes(nome=mes.nome, congregacao_id=mes.congregacao_id, saldo_inicial=saldo_inicial, saldo_final=saldo_inicial)
    db.add(db_mes)
    db.commit()
    db.refresh(db_mes)
    return db_mes

@app.post("/meses/{mes_id}/semanas/", response_model=schemas.Semana, summary="Lança os dados de uma semana (Protegido)")
def lancar_dados_semana(mes_id: int, semana: schemas.SemanaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_mes = db.query(models.Mes).filter(models.Mes.id == mes_id).first()
    if not db_mes:
        raise HTTPException(status_code=404, detail="Mês não encontrado.")
    
    if current_user.funcao == "tesoureiro" and current_user.congregacao_id != db_mes.congregacao_id:
        raise HTTPException(status_code=403, detail="Você só pode lançar semanas para a sua própria congregação.")
    if current_user.funcao not in ["admin", "tesoureiro"]:
         raise HTTPException(status_code=403, detail="Você não tem permissão para esta operação.")

    if not (1 <= semana.numero <= 5):
        raise HTTPException(status_code=400, detail="O número da semana deve ser entre 1 e 5.")
    
    saldo_inicial_semana = db_mes.saldo_final
    comissao = semana.renda_semanal * 0.33
    total_despesas = sum(d.valor for d in semana.despesas)
    saldo_final_semana = (saldo_inicial_semana + semana.renda_semanal) - (comissao + total_despesas)
    
    nova_semana = models.Semana(numero=semana.numero, mes_id=mes_id, saldo_inicial_semana=saldo_inicial_semana, renda_semanal=semana.renda_semanal, comissao=comissao, saldo_final_semana=saldo_final_semana)
    db.add(nova_semana)
    db.commit()
    db.refresh(nova_semana)

    for despesa_data in semana.despesas:
        db.add(models.Despesa(**despesa_data.model_dump(), semana_id=nova_semana.id))

    db_mes.saldo_final = saldo_final_semana
    db.commit()
    db.refresh(db_mes)
    return nova_semana

@app.get("/meses/{mes_id}/balancete/", response_model=schemas.BalanceteMensal, summary="Consulta o balancete mensal (Protegido)")
def obter_balancete_mensal(mes_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_mes = db.query(models.Mes).filter(models.Mes.id == mes_id).first()
    if not db_mes:
        raise HTTPException(status_code=404, detail="Mês não encontrado.")

    if current_user.funcao == "tesoureiro" and current_user.congregacao_id != db_mes.congregacao_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    if current_user.funcao == "pastor_area" and current_user.area_id != db_mes.congregacao.area_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    total_entradas = sum(s.renda_semanal for s in db_mes.semanas)
    total_comissao = sum(s.comissao for s in db_mes.semanas)
    total_despesas = sum(d.valor for semana in db_mes.semanas for d in semana.despesas)

    return schemas.BalanceteMensal(nome_mes=db_mes.nome, saldo_inicial_mes=db_mes.saldo_inicial, total_entradas=total_entradas, total_comissao=total_comissao, total_despesas=total_despesas, saldo_final_consolidado=db_mes.saldo_final)