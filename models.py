"""
Módulo de Modelos de Banco de Dados (ORM)
Mapeia as tabelas do Supabase (PostgreSQL) para classes Python usando a ORM SQLAlchemy.
"""

import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID

# Inicialização desacoplada do SQLAlchemy para evitar importação circular.
# A vinculação com o app Flask será feita no factory (app.py).
db = SQLAlchemy()

class ChecklistTemplate(db.Model):
    """
    Representa o modelo (template) de um checklist criado pelo Admin.
    Tabela: checklists_templates
    """
    __tablename__ = 'checklists_templates'
    
    # UUID nativo do PostgreSQL
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo = db.Column(db.String(255), nullable=False)
    
    # O ID do criador vem do token JWT (auth.users do Supabase)
    criado_por = db.Column(UUID(as_uuid=True), nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relacionamentos para facilitar buscas
    # cascade="all, delete-orphan" garante a integridade referencial caso o template seja apagado
    etapas = db.relationship('ChecklistEtapa', backref='template', lazy=True, cascade="all, delete-orphan")
    atribuicoes = db.relationship('Atribuicao', backref='template', lazy=True, cascade="all, delete-orphan")


class ChecklistEtapa(db.Model):
    """
    Representa uma etapa individual dentro de um template de checklist.
    Tabela: checklist_etapas
    """
    __tablename__ = 'checklist_etapas'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_checklist_template = db.Column(UUID(as_uuid=True), db.ForeignKey('checklists_templates.id', ondelete='CASCADE'), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    requer_foto = db.Column(db.Boolean, default=False)
    ordem = db.Column(db.Integer, nullable=False)


class Atribuicao(db.Model):
    """
    Representa a atribuição de um template a um funcionário (Staff) específico.
    Tabela: atribuicoes
    """
    __tablename__ = 'atribuicoes'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_checklist_template = db.Column(UUID(as_uuid=True), db.ForeignKey('checklists_templates.id', ondelete='CASCADE'), nullable=False)
    
    # ID do funcionário que fará a vistoria (vem do Supabase Auth)
    id_staff = db.Column(UUID(as_uuid=True), nullable=False)
    status = db.Column(db.String(50), default='pendente') # Estados previstos: 'pendente', 'concluido'

    execucoes = db.relationship('Execucao', backref='atribuicao', lazy=True, cascade="all, delete-orphan")


class Execucao(db.Model):
    """
    Representa a execução (resposta) de uma atribuição de checklist feita pelo Staff.
    Tabela: execucoes
    """
    __tablename__ = 'execucoes'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_atribuicao = db.Column(UUID(as_uuid=True), db.ForeignKey('atribuicoes.id', ondelete='CASCADE'), nullable=False)
    enviado_em = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status_auditoria = db.Column(db.String(50), default='pendente_validacao') # 'pendente_validacao', 'aprovado', 'rejeitado'

    resultados = db.relationship('ResultadoEtapa', backref='execucao', lazy=True, cascade="all, delete-orphan")


class ResultadoEtapa(db.Model):
    """
    Representa a resposta específica de uma etapa (a foto capturada ou a justificativa de bloqueio).
    Tabela: resultados_etapas
    """
    __tablename__ = 'resultados_etapas'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_execucao = db.Column(UUID(as_uuid=True), db.ForeignKey('execucoes.id', ondelete='CASCADE'), nullable=False)
    id_etapa = db.Column(UUID(as_uuid=True), db.ForeignKey('checklist_etapas.id', ondelete='CASCADE'), nullable=False)
    
    # A imagem é enviada diretamente do Front-end para o Bucket e é salvo apenas a URL
    foto_url = db.Column(db.Text, nullable=True)
    justificativa = db.Column(db.Text, nullable=True)
    
    # Nota: A validação (foto_url IS NOT NULL OR justificativa IS NOT NULL)
    # para etapas com foto obrigatoria já está garantida no banco de dados via CHECK CONSTRAINT.