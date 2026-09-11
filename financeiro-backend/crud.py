from sqlalchemy.orm import Session
import models, schemas, security

def get_user_by_email(db: Session, email: str):
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def create_user(db: Session, user: schemas.UsuarioCreate):
    hashed_password = security.get_password_hash(user.password)
    db_user = models.Usuario(
        email=user.email,
        hashed_password=hashed_password,
        funcao=user.funcao,
        denominacao_id=user.denominacao_id,
        area_id=user.area_id,
        congregacao_id=user.congregacao_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_denominacao(db: Session, denominacao: schemas.DenominacaoCreate):
    db_denominacao = models.Denominacao(**denominacao.model_dump())
    db.add(db_denominacao)
    db.commit()
    db.refresh(db_denominacao)
    return db_denominacao

def create_area(db: Session, area: schemas.AreaEclesiasticaCreate):
    db_area = models.AreaEclesiastica(**area.model_dump())
    db.add(db_area)
    db.commit()
    db.refresh(db_area)
    return db_area

def create_congregacao(db: Session, congregacao: schemas.CongregacaoCreate):
    db_congregacao = models.Congregacao(**congregacao.model_dump())
    db.add(db_congregacao)
    db.commit()
    db.refresh(db_congregacao)
    return db_congregacao