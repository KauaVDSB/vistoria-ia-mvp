"""
Rotas Administrativas (Gestão de Vistorias)
Lida com a criação de templates, atribuição e auditoria (aprovação/rejeição).
"""

import uuid
from flask import Blueprint, request, jsonify, g
from models import db, ChecklistTemplate, ChecklistEtapa, Atribuicao, Execucao
from middleware import require_admin

# Cria Blueprint com prefixo padrão /api
admin_bp = Blueprint('admin', __name__, url_prefix='/api')

@admin_bp.route('/checklists', methods=['POST'])
@require_admin
def create_checklist():
    """
    Cria um novo modelo (template) de checklist, suas etapas e já atribui a um Staff.
    """
    data = request.get_json()
    
    titulo = data.get('titulo')
    etapas_data = data.get('etapas', [])
    staff_email = data.get('staff_email')

    if not titulo or not etapas_data or not staff_email:
        return jsonify({"error": "Dados incompletos"}), 400

    try:
        # 1. Cria o Template
        # g.user_id vem do token JWT decodificado no middleware
        novo_template = ChecklistTemplate(
            titulo=titulo,
            criado_por=g.user_id 
        )
        db.session.add(novo_template)
        db.session.flush() # Envia para o banco pegar o ID, mas não commita ainda

        # 2. Cria as Etapas
        for index, etapa in enumerate(etapas_data):
            nova_etapa = ChecklistEtapa(
                id_checklist_template=novo_template.id,
                descricao=etapa.get('descricao'),
                requer_foto=etapa.get('requer_foto', False),
                ordem=index + 1
            )
            db.session.add(nova_etapa)

        # 3. Cria a Atribuição para o Staff
        # TODO: Para fins de MVP, não será feito fetch no Auth do Supabase para pegar o ID
        # real do usuário pelo email, portanto, geramos um UUID determinístico baseado no email.
        # Implementação completa fica para quando o MVP estiver completo.
        id_staff_mock = uuid.uuid5(uuid.NAMESPACE_URL, staff_email) 

        nova_atribuicao = Atribuicao(
            id_checklist_template=novo_template.id,
            id_staff=id_staff_mock,
            status='pendente'
        )
        db.session.add(nova_atribuicao)

        db.session.commit() # Salva tudo na mesma transação (ACID)
        
        return jsonify({
            "message": "Checklist criado e atribuído com sucesso!",
            "id_template": novo_template.id
        }), 201

    except Exception as e:
        db.session.rollback() # Se algo der errado nas etapas, cancela a criação do template
        return jsonify({"error": f"Erro ao criar checklist: {str(e)}"}), 500


@admin_bp.route('/auditoria/feed', methods=['GET'])
@require_admin
def get_auditoria_feed():
    """
    Retorna o feed de vistorias executadas para avaliação do Admin.
    """
    try:
        # Busca todas as execuções, ordenadas da mais recente para a mais antiga
        execucoes = Execucao.query.order_by(Execucao.enviado_em.desc()).all()
        
        feed = []
        for ex in execucoes:
            template = ex.atribuicao.template
            resultados = ex.resultados
            
            # Conta quantas fotos/etapas concluídas e quantos impedimentos (List Comprehension)
            fotos = [r.foto_url for r in resultados if r.foto_url]
            impedimentos = [r.justificativa for r in resultados if r.justificativa]
            
            feed.append({
                "id_execucao": ex.id,
                "staff_nome": "Operador", # TODO: Em um sistema maduro, serai feito um JOIN com a tabela de usuários
                "titulo": template.titulo,
                "fotos": fotos,
                "impedimentos": impedimentos,
                "status": ex.status_auditoria,
                "etapas_concluidas": (len(resultados) - len(impedimentos)),
                "etapas_impedidas": len(impedimentos)
            })
            
        return jsonify(feed), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/auditoria/execucoes/<uuid:id_execucao>', methods=['PATCH'])
@require_admin
def auditar_execucao(id_execucao):
    """
    Aprova ou reprova uma execução de vistoria.
    """
    data = request.get_json()
    novo_status = data.get('status') # O Front-end deve enviar 'aprovado' ou 'rejeitado'
    
    if novo_status not in ['aprovado', 'rejeitado']:
        return jsonify({"error": "Status inválido"}), 400
        
    try:
        execucao = Execucao.query.get(id_execucao)
        if not execucao:
            return jsonify({"error": "Execução não encontrada"}), 404
            
        execucao.status_auditoria = novo_status
        db.session.commit()
        
        return jsonify({"message": f"Vistoria {novo_status} com sucesso!"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500