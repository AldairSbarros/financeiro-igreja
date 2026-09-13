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
import os
import shutil
from fastapi import UploadFile, File

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

    # Verificação de segurança: impedir exclusão se houver áreas ou congregações vinculadas
    if db_denominacao.areas or db_denominacao.congregacoes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir a denominação pois existem áreas eclesiásticas ou congregações vinculadas a ela."
        )

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

    # Verificação de segurança: impedir exclusão se houver congregações vinculadas
    if db_area.congregacoes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir a área eclesiástica pois existem congregações vinculadas a ela."
        )

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

    # Verificação de segurança: impedir exclusão se houver dados financeiros, usuários ou dizimistas vinculados
    if db_congregacao.meses or db_congregacao.rendas or db_congregacao.usuarios or db_congregacao.dizimistas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir a congregação pois existem dados financeiros (meses, rendas), usuários ou dizimistas vinculados a ela."
        )

    crud.delete_congregacao(db=db, congregacao_id=congregacao_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/users/me/", response_model=schemas.Usuario)
def read_users_me(current_user: models.Usuario = Depends(get_current_user)):
    return current_user

@app.put("/users/me/password")
def update_user_password(
    password_data: schemas.UsuarioUpdatePassword,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if not security.verify_password(password_data.senha_atual, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
        
    current_user.hashed_password = security.get_password_hash(password_data.nova_senha)
    db.commit()
    return {"detail": "Senha atualizada com sucesso"}

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

# --- Endpoints para Dizimistas/Ofertantes ---
@app.post("/congregacoes/{congregacao_id}/dizimistas/", response_model=schemas.DizimistaOfertante, status_code=status.HTTP_201_CREATED)
def create_dizimista_ofertante_endpoint(
    congregacao_id: int,
    dizimista: schemas.DizimistaOfertanteCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_congregacao = crud.get_congregacao_by_id(db, congregacao_id)
    if not db_congregacao:
        raise HTTPException(status_code=404, detail="Congregação não encontrada.")

    # Apenas usuários da congregação (ou superiores) podem criar dizimistas
    if current_user.funcao not in ['administrador', 'supervisor_denominacao', 'supervisor_area', 'tesoureiro']:
        raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para criar dizimistas.")
    if current_user.funcao == 'tesoureiro' and current_user.congregacao_id != congregacao_id:
        raise HTTPException(status_code=403, detail="Tesoureiros só podem criar dizimistas em sua própria congregação.")

    return crud.create_dizimista_ofertante(db=db, dizimista=dizimista, congregacao_id=congregacao_id)

@app.get("/congregacoes/{congregacao_id}/dizimistas/", response_model=List[schemas.DizimistaOfertante])
def list_dizimistas_by_congregacao_endpoint(
    congregacao_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Apenas usuários da congregação (ou superiores) podem listar dizimistas
    if current_user.funcao == 'tesoureiro' and current_user.congregacao_id != congregacao_id:
        raise HTTPException(status_code=403, detail="Tesoureiros só podem listar dizimistas de sua própria congregação.")
    
    return crud.get_dizimistas_ofertantes_by_congregacao(db=db, congregacao_id=congregacao_id)

@app.put("/dizimistas/{dizimista_id}", response_model=schemas.DizimistaOfertante)
def update_dizimista_ofertante_endpoint(
    dizimista_id: int,
    dizimista: schemas.DizimistaOfertanteUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_dizimista = crud.get_dizimista_ofertante_by_id(db, dizimista_id)
    if not db_dizimista:
        raise HTTPException(status_code=404, detail="Dizimista/Ofertante não encontrado.")

    # Lógica de autorização para atualização
    if current_user.funcao == 'administrador':
        pass # Administrador tem acesso total
    elif current_user.funcao == 'supervisor_denominacao' and db_dizimista.congregacao.area.denominacao_id == current_user.denominacao_id:
        pass # Supervisor de denominação pode atualizar dizimistas da sua denominação
    elif current_user.funcao == 'supervisor_area' and db_dizimista.congregacao.area_id == current_user.area_id:
        pass # Supervisor de área pode atualizar dizimistas da sua área
    elif current_user.funcao == 'tesoureiro' and db_dizimista.congregacao_id == current_user.congregacao_id:
        pass # Tesoureiro pode atualizar dizimistas da sua congregação
    else:
        raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para atualizar este dizimista/ofertante.")

    return crud.update_dizimista_ofertante(db=db, dizimista_id=dizimista_id, dizimista=dizimista)

@app.delete("/dizimistas/{dizimista_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dizimista_ofertante_endpoint(
    dizimista_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_dizimista = crud.get_dizimista_ofertante_by_id(db, dizimista_id)
    if not db_dizimista:
        raise HTTPException(status_code=404, detail="Dizimista/Ofertante não encontrado.")

    # Lógica de autorização para exclusão
    if current_user.funcao == 'administrador':
        pass # Administrador tem acesso total
    elif current_user.funcao == 'supervisor_denominacao' and db_dizimista.congregacao.area.denominacao_id == current_user.denominacao_id:
        pass # Supervisor de denominação pode deletar dizimistas da sua denominação
    elif current_user.funcao == 'supervisor_area' and db_dizimista.congregacao.area_id == current_user.area_id:
        pass # Supervisor de área pode deletar dizimistas da sua área
    elif current_user.funcao == 'tesoureiro' and db_dizimista.congregacao_id == current_user.congregacao_id:
        pass # Tesoureiro pode deletar dizimistas da sua congregação
    else:
        raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para deletar este dizimista/ofertante.")
    
    crud.delete_dizimista_ofertante(db=db, dizimista_id=dizimista_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# (Endpoints para GET, PUT, DELETE de um dizimista específico podem ser adicionados aqui se necessário)
@app.get("/dizimistas/{dizimista_id}", response_model=schemas.DizimistaOfertante)
def get_dizimista_ofertante_endpoint(
    dizimista_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_dizimista = crud.get_dizimista_ofertante_by_id(db, dizimista_id)
    if not db_dizimista:
        raise HTTPException(status_code=404, detail="Dizimista/Ofertante não encontrado.")

    # Lógica de autorização
    if current_user.funcao == 'administrador':
        pass # Administrador tem acesso total
    elif current_user.funcao == 'supervisor_denominacao' and db_dizimista.congregacao.area.denominacao_id == current_user.denominacao_id:
        pass # Supervisor de denominação pode ver dizimistas da sua denominação
    elif current_user.funcao == 'supervisor_area' and db_dizimista.congregacao.area_id == current_user.area_id:
        pass # Supervisor de área pode ver dizimistas da sua área
    elif current_user.funcao == 'tesoureiro' and db_dizimista.congregacao_id == current_user.congregacao_id:
        pass # Tesoureiro pode ver dizimistas da sua congregação
    else:
        raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para visualizar este dizimista/ofertante.")

    return db_dizimista

# --- Endpoints para Rendas (Dízimos e Ofertas) ---
@app.post("/semanas/{semana_id}/rendas/", response_model=schemas.Renda, status_code=status.HTTP_201_CREATED)
def create_renda_endpoint(
    semana_id: int,
    renda: schemas.RendaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_semana = db.query(models.Semana).filter(models.Semana.id == semana_id).first()
    if not db_semana:
        raise HTTPException(status_code=404, detail="Semana não encontrada.")

    # Apenas usuários da congregação (ou superiores) podem criar rendas
    if current_user.funcao == 'tesoureiro' and current_user.congregacao_id != db_semana.mes.congregacao_id:
        raise HTTPException(status_code=403, detail="Tesoureiros só podem criar rendas em sua própria congregação.")
        
    if db_semana.mes.fechado:
        raise HTTPException(status_code=400, detail="Não é possível adicionar rendas a um mês fechado.")

    # Validação da data da renda dentro do período da semana
    if db_semana.data_inicio and db_semana.data_fim:
        try:
            semana_data_inicio = datetime.datetime.strptime(db_semana.data_inicio, "%Y-%m-%d").date()
            semana_data_fim = datetime.datetime.strptime(db_semana.data_fim, "%Y-%m-%d").date()
            if not (semana_data_inicio <= renda.data_registro <= semana_data_fim):
                raise HTTPException(
                    status_code=400,
                    detail=f"A data da renda ({renda.data_registro}) deve estar dentro do período da semana ({db_semana.data_inicio} a {db_semana.data_fim})."
                )
        except ValueError:
            pass # Ignora se o formato da data da semana estiver incorreto no DB (já deve ser evitado na criação da semana)

    nova_renda = crud.create_renda(db=db, renda=renda, congregacao_id=db_semana.mes.congregacao_id, semana_id=semana_id)
    crud.recalcular_saldos_mes(db, db_semana.mes_id)
    return nova_renda

@app.get("/semanas/{semana_id}/rendas/", response_model=List[schemas.Renda])
def list_rendas_by_semana_endpoint(
    semana_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_semana = db.query(models.Semana).filter(models.Semana.id == semana_id).first()
    if not db_semana:
        raise HTTPException(status_code=404, detail="Semana não encontrada.")

    # Apenas usuários da congregação (ou superiores) podem listar rendas
    if current_user.funcao == 'tesoureiro' and current_user.congregacao_id != db_semana.mes.congregacao_id:
        raise HTTPException(status_code=403, detail="Tesoureiros só podem listar rendas de sua própria congregação.")

    return crud.get_rendas_by_semana(db=db, semana_id=semana_id)

@app.delete("/rendas/{renda_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_renda_endpoint(
    renda_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_renda = crud.get_renda_by_id(db, renda_id)
    if not db_renda:
        raise HTTPException(status_code=404, detail="Renda não encontrada.")

    # Apenas usuários da congregação (ou superiores) podem deletar rendas
    if current_user.funcao == 'tesoureiro' and current_user.congregacao_id != db_renda.congregacao_id:
        raise HTTPException(status_code=403, detail="Tesoureiros só podem deletar rendas de sua própria congregação.")
        
    if db_renda.semana.mes.fechado:
        raise HTTPException(status_code=400, detail="Não é possível deletar rendas de um mês fechado.")

    mes_id = db_renda.semana.mes_id
    crud.delete_renda(db=db, renda_id=renda_id)
    crud.recalcular_saldos_mes(db, mes_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/rendas/{renda_id}", response_model=schemas.Renda)
def get_renda_endpoint(
    renda_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_renda = crud.get_renda_by_id(db, renda_id)
    if not db_renda:
        raise HTTPException(status_code=404, detail="Renda não encontrada.")

    # Lógica de autorização
    if current_user.funcao == 'administrador':
        pass # Administrador tem acesso total
    elif current_user.funcao == 'supervisor_denominacao' and db_renda.congregacao.area.denominacao_id == current_user.denominacao_id:
        pass # Supervisor de denominação pode ver rendas da sua denominação
    elif current_user.funcao == 'supervisor_area' and db_renda.congregacao.area_id == current_user.area_id:
        pass # Supervisor de área pode ver rendas da sua área
    elif current_user.funcao == 'tesoureiro' and db_renda.congregacao_id == current_user.congregacao_id:
        pass # Tesoureiro pode ver rendas da sua congregação
    else:
        raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para visualizar esta renda.")

    return db_renda

@app.put("/rendas/{renda_id}", response_model=schemas.Renda)
def update_renda_endpoint(
    renda_id: int,
    renda: schemas.RendaUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_renda = crud.get_renda_by_id(db, renda_id)
    if not db_renda:
        raise HTTPException(status_code=404, detail="Renda não encontrada.")

    # Lógica de autorização para atualização
    if current_user.funcao == 'administrador':
        pass # Administrador tem acesso total
    elif current_user.funcao == 'supervisor_denominacao' and db_renda.congregacao.area.denominacao_id == current_user.denominacao_id:
        pass # Supervisor de denominação pode atualizar rendas da sua denominação
    elif current_user.funcao == 'supervisor_area' and db_renda.congregacao.area_id == current_user.area_id:
        pass # Supervisor de área pode atualizar rendas da sua área
    elif current_user.funcao == 'tesoureiro' and db_renda.congregacao_id == current_user.congregacao_id:
        pass # Tesoureiro pode atualizar rendas da sua congregação
    else:
        raise HTTPException(status_code=403, detail="Acesso negado. Você não tem permissão para atualizar esta renda.")
        
    if db_renda.semana.mes.fechado:
        raise HTTPException(status_code=400, detail="Não é possível modificar rendas de um mês fechado.")

    # Validação da data da renda (se for atualizada) dentro do período da semana
    if renda.data_registro and db_renda.semana.data_inicio and db_renda.semana.data_fim:
        try:
            semana_data_inicio = datetime.datetime.strptime(db_renda.semana.data_inicio, "%Y-%m-%d").date()
            semana_data_fim = datetime.datetime.strptime(db_renda.semana.data_fim, "%Y-%m-%d").date()
            if not (semana_data_inicio <= renda.data_registro <= semana_data_fim):
                raise HTTPException(
                    status_code=400,
                    detail=f"A nova data da renda ({renda.data_registro}) deve estar dentro do período da semana ({db_renda.semana.data_inicio} a {db_renda.semana.data_fim})."
                )
        except ValueError:
            pass

    updated_renda = crud.update_renda(db=db, renda_id=renda_id, renda=renda)
    crud.recalcular_saldos_mes(db, updated_renda.semana.mes_id) # Recalcula o mês após a atualização da renda
    return updated_renda

# (Endpoints para GET e PUT de uma renda específica podem ser adicionados aqui se necessário)

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
    db_mes = db.query(models.Mes).options(joinedload(models.Mes.congregacao).joinedload(models.Congregacao.area).joinedload(models.AreaEclesiastica.denominacao)).filter(models.Mes.id == mes_id).first()
    if not db_mes: raise HTTPException(status_code=404, detail="Mês não encontrado.")
    if current_user.congregacao_id != db_mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    congregacao = db_mes.congregacao
    area = congregacao.area if congregacao else None
    denominacao = area.denominacao if area else None

    semanas = (
        db.query(models.Semana)
        .options(joinedload(models.Semana.despesas), joinedload(models.Semana.rendas).joinedload(models.Renda.dizimista_ofertante)) # Adicionado joinedload para DizimistaOfertante
        .filter(models.Semana.mes_id == mes_id)
        .order_by(models.Semana.numero)
        .all()
    )

    total_entradas_brutas = sum(r.valor for s in semanas for r in s.rendas)
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

    # Tabela de Rendas Detalhadas (Dízimos e Ofertas)
    if total_entradas_brutas > 0:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Rendas Detalhadas por Semana", 0, 1, 'L')
        pdf.ln(2)

        for semana in semanas:
            if semana.rendas:
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 7, f"Semana {semana.numero} ({semana.data_inicio or 'N/A'} - {semana.data_fim or 'N/A'})", 1, 1, 'L')
                pdf.set_font('Arial', 'B', 9)
                pdf.cell(60, 6, "Tipo", 1, 0, 'C')
                pdf.cell(80, 6, "Dizimista/Ofertante", 1, 0, 'C')
                pdf.cell(50, 6, "Valor", 1, 1, 'C')
                pdf.set_font('Arial', '', 9)
                for renda in semana.rendas:
                    dizimista_nome = renda.dizimista_ofertante.nome if renda.dizimista_ofertante else "Não Identificado"
                    pdf.cell(60, 6, f"  {renda.tipo}", 1, 0, 'L')
                    pdf.cell(80, 6, f"  {dizimista_nome}", 1, 0, 'L')
                    pdf.cell(50, 6, formatar_moeda(renda.valor), 1, 1, 'R')
                pdf.ln(2) # Pequeno espaço entre semanas

    pdf_output = pdf.output(dest='S') # Já é bytearray, não precisa de .encode()

    return Response(content=bytes(pdf_output), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="balancete_{db_mes.nome.replace("/", "-")}.pdf"'})

@app.post("/backup/")
def gerar_backup(current_user: models.Usuario = Depends(get_current_user)):
    # Apenas administradores podem fazer backup
    if current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem gerar backups.")
    
    db_path = "./financeiro.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Banco de dados não encontrado.")
    
    backup_filename = f"financeiro_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    with open(db_path, "rb") as db_file:
        content = db_file.read()

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{backup_filename}"'}
    )

@app.post("/restore/")
async def restaurar_backup(file: UploadFile = File(...), current_user: models.Usuario = Depends(get_current_user)):
    # Apenas administradores podem restaurar backup
    if current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem restaurar backups.")
    
    if not file.filename.endswith('.db'):
        raise HTTPException(status_code=400, detail="Arquivo inválido. O backup deve ser um arquivo .db")

    db_path = "./financeiro.db"
    temp_path = "./financeiro_temp.db"
    
    try:
        # Salva o arquivo enviado temporariamente
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Substitui o banco atual pelo temporário
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rename(temp_path, db_path)
        
        return {"detail": "Backup restaurado com sucesso. Recomendado reiniciar a aplicação (API) para evitar travamentos de cache do SQLAlchemy."}
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Erro ao restaurar backup: {str(e)}")

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

@app.put("/meses/{mes_id}/fechar", response_model=schemas.Mes)
def fechar_mes_endpoint(mes_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_mes = db.query(models.Mes).filter(models.Mes.id == mes_id).first()
    if not db_mes:
        raise HTTPException(status_code=404, detail="Mês não encontrado.")
    if current_user.congregacao_id != db_mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    db_mes.fechado = True
    db.commit()
    db.refresh(db_mes)
    return db_mes

@app.put("/meses/{mes_id}/reabrir", response_model=schemas.Mes)
def reabrir_mes_endpoint(mes_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_mes = db.query(models.Mes).filter(models.Mes.id == mes_id).first()
    if not db_mes:
        raise HTTPException(status_code=404, detail="Mês não encontrado.")
    
    # Apenas administradores podem reabrir um mês
    if current_user.funcao != 'administrador':
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores podem reabrir meses.")
    
    db_mes.fechado = False
    db.commit()
    db.refresh(db_mes)
    return db_mes

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
    
    if db_mes.fechado:
        raise HTTPException(status_code=400, detail="Não é possível adicionar semanas a um mês fechado.")

    semana_existente = next((s for s in db_mes.semanas if s.numero == semana.numero), None)
    if semana_existente:
        raise HTTPException(status_code=400, detail=f"A Semana {semana.numero} já foi lançada para este mês.")

    if len(db_mes.semanas) >= 5:
        raise HTTPException(status_code=400, detail="Não é possível adicionar mais de 5 semanas a um mês.")

    nova_semana = crud.create_semana(db=db, semana=semana, mes_id=mes_id)
    crud.recalcular_saldos_mes(db, mes_id) # Recalcula o mês após adicionar a semana
    return nova_semana

@app.post("/meses/{mes_id}/semanas/{semana_numero}/despesas/", response_model=schemas.Despesa)
def adicionar_despesa_endpoint(mes_id: int, semana_numero: int, despesa: schemas.DespesaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_semana = db.query(models.Semana).filter_by(mes_id=mes_id, numero=semana_numero).first()
    if not db_semana: raise HTTPException(status_code=404, detail="Semana não encontrada.")
    if current_user.congregacao_id != db_semana.mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")
        
    if db_semana.mes.fechado:
        raise HTTPException(status_code=400, detail="Não é possível adicionar despesas a um mês fechado.")

    # Validação da data da despesa (se fornecida) dentro do período da semana
    if despesa.data_registro and db_semana.data_inicio and db_semana.data_fim:
        try:
            semana_data_inicio = datetime.datetime.strptime(db_semana.data_inicio, "%Y-%m-%d").date()
            semana_data_fim = datetime.datetime.strptime(db_semana.data_fim, "%Y-%m-%d").date()
            if not (semana_data_inicio <= despesa.data_registro <= semana_data_fim):
                raise HTTPException(
                    status_code=400,
                    detail=f"A data da despesa ({despesa.data_registro}) deve estar dentro do período da semana ({db_semana.data_inicio} a {db_semana.data_fim})."
                )
        except ValueError:
            pass

    nova_despesa = models.Despesa(descricao=despesa.descricao, valor=despesa.valor, data_registro=despesa.data_registro, semana_id=db_semana.id)
    db.add(nova_despesa)
    db.commit()
    db.refresh(nova_despesa)

    crud.recalcular_saldos_mes(db, mes_id) # CORREÇÃO: Apenas recalcula, não recria a semana
    return nova_despesa

@app.delete("/despesas/{despesa_id}")
def remover_despesa(despesa_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_despesa = db.query(models.Despesa).filter(models.Despesa.id == despesa_id).first()
    if not db_despesa: raise HTTPException(status_code=404, detail="Despesa não encontrada.")
    if current_user.congregacao_id != db_despesa.semana.mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")
        
    if db_despesa.semana.mes.fechado:
        raise HTTPException(status_code=400, detail="Não é possível remover despesas de um mês fechado.")

    mes_id = db_despesa.semana.mes_id
    db.delete(db_despesa)
    db.commit()

    crud.recalcular_saldos_mes(db, mes_id)
    return {"detail": "Despesa removida com sucesso."}

@app.get("/meses/{mes_id}/analises", response_model=schemas.AnaliseMes)
def get_analises_mes(mes_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    """
    Retorna dados agregados para gráficos e análises de um mês específico.
    """
    db_mes = db.query(models.Mes).filter(models.Mes.id == mes_id).first()
    if not db_mes: raise HTTPException(status_code=404, detail="Mês não encontrado.")

    # Permissão: apenas admins ou o tesoureiro da congregação
    if current_user.funcao == 'tesoureiro' and current_user.congregacao_id != db_mes.congregacao_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    # Buscar semanas com rendas e despesas
    semanas = db.query(models.Semana).options(
        joinedload(models.Semana.rendas),
        joinedload(models.Semana.despesas)
    ).filter(models.Semana.mes_id == mes_id).order_by(models.Semana.numero).all()
    # 1. Calcular séries Entradas x Saídas com saldo acumulado
    series = []
    saldo_acumulado = db_mes.saldo_inicial
    for semana in semanas:
        entradas = sum(r.valor for r in semana.rendas)
        saidas = sum(d.valor for d in semana.despesas)
        comissao = semana.comissao
        saldo_acumulado = saldo_acumulado + comissao - saidas
        series.append(schemas.SemanaResumo(
            numero_semana=semana.numero,
            label=f"S{semana.numero}",
            entradas=entradas,
            saidas=saidas,
            saldo_acumulado=saldo_acumulado
        ))

    # 2. Calcular principais rendas por tipo
    tipos = {}
    for semana in semanas:
        for renda in semana.rendas:
            chave = renda.tipo
            if chave not in tipos:
                tipos[chave] = {"total": 0, "quantidade": 0, "tipo": chave}
            tipos[chave]["total"] += renda.valor
            tipos[chave]["quantidade"] += 1

    principais_rendas = [
        schemas.RendaItemResumo(**item)
        for item in sorted(tipos.values(), key=lambda x: x["total"], reverse=True)
    ]

    # 3. Resumo por método de pagamento
    metodos = {}
    for semana in semanas:
        for renda in semana.rendas:
            chave = renda.metodo_pagamento
            if chave not in metodos:
                metodos[chave] = {"metodo_pagamento": chave, "total": 0, "quantidade": 0}
            metodos[chave]["total"] += renda.valor
            metodos[chave]["quantidade"] += 1

    resumo_pagamentos = [
        schemas.MetodoPagamentoResumo(**item)
        for item in sorted(metodos.values(), key=lambda x: x["total"], reverse=True)
    ]

    # 4. Totais gerais
    total_entradas_brutas = sum(r.valor for s in semanas for r in s.rendas)
    total_comissao = sum(s.comissao for s in semanas)
    total_despesas = sum(d.valor for s in semanas for d in s.despesas)

    totais = {
        "saldo_inicial": db_mes.saldo_inicial,
        "entradas_brutas": total_entradas_brutas,
        "comissao": total_comissao,
        "despesas": total_despesas,
        "saldo_final": db_mes.saldo_final,
        "taxa_comissao": 0.33,
        "semanas_lancadas": len(semanas),
        "rendas_total": sum(1 for s in semanas for r in s.rendas),
        "despesas_total": sum(1 for s in semanas for d in s.despesas)
    }

    return schemas.AnaliseMes(
        mes_id=mes_id,
        nome_mes=db_mes.nome,
        series_entradas_saida=series,
        principais_rendas=principais_rendas,
        resumo_pagamentos=resumo_pagamentos,
        totais=totais
    )

@app.get("/meses/{mes_id}/balancete/", response_model=schemas.BalanceteMensal)
def obter_balancete_mensal(mes_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    db_mes = db.query(models.Mes).filter(models.Mes.id == mes_id).first()
    if not db_mes: raise HTTPException(status_code=404, detail="Mês não encontrado.")
    if current_user.congregacao_id != db_mes.congregacao_id and current_user.funcao == 'tesoureiro':
        raise HTTPException(status_code=403, detail="Acesso negado.")

    semanas = db.query(models.Semana).options(joinedload(models.Semana.despesas), joinedload(models.Semana.rendas)).filter(models.Semana.mes_id == mes_id).all()

    total_entradas_brutas = sum(r.valor for s in semanas for r in s.rendas)
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

@app.post("/despesas/recorrentes/duplicar", response_model=List[schemas.Despesa])
def duplicar_despesas_recorrentes_endpoint(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Apenas administradores ou tesoureiros podem acionar a duplicação
    if current_user.funcao not in ['administrador', 'tesoureiro']:
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores ou tesoureiros podem duplicar despesas recorrentes.")
    # Executa a lógica de duplicação no CRUD
    despesas_criadas = crud.duplicar_despesas_recorrentes(db)
    # Recalcula saldos dos meses afetados
    meses_afetados = set()
    for d in despesas_criadas:
        semana = db.query(models.Semana).filter(models.Semana.id == d.semana_id).first()
        if semana:
            meses_afetados.add(semana.mes_id)
    for mes_id in meses_afetados:
        crud.recalcular_saldos_mes(db, mes_id)
    return despesas_criadas

