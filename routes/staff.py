"""
Rotas Operacionais (Visão do Staff)
Lida com a listagem de tarefas pendentes e a submissão de vistorias executadas.
"""

import uuid
from flask import Blueprint, request, jsonify, g
from models import db, Atribuicao, Execucao, ResultadoEtapa
from middleware import require_auth

staff_bp = Blueprint('staff', __name__, url_prefix='/api')

@staff_bp.route('/atribuicoes', methods=['GET'])
@require_auth
def get_atribuicoes():
    """
    Retorna as vistorias pendentes do staff logado.
    """
    try:
        # Recria o ID determinístico do staff baseado no email extraído do JWT
        id_staff_mock = uuid.uuid5(uuid.NAMESPACE_URL, g.user_email)

        # Busca apenas as atribuições pendentes para este operador específico
        atribuicoes = Atribuicao.query.filter_by(id_staff=id_staff_mock, status='pendente').all()

        lista = []
        for at in atribuicoes:
            template = at.template
            etapas = template.etapas

            lista.append({
                "id": at.id,
                "titulo": template.titulo,
                "status": at.status,
                "total_etapas": len(etapas),
                "criado_em": template.criado_em.isoformat(),
                # O Front-end precisa do array de etapas para renderizar o Wizard/Carrossel de execução
                "etapas": [{
                    "id": e.id,
                    "descricao": e.descricao,
                    "requer_foto": e.requer_foto
                } for e in etapas]
            })

        return jsonify(lista), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@staff_bp.route('/execucoes', methods=['POST'])
@require_auth
def submit_execucao():
    """
    Recebe o payload completo de uma vistoria executada pelo staff e salva os resultados.
    """
    data = request.get_json()

    id_atribuicao = data.get('atribuicao_id')
    resultados_data = data.get('resultados', [])

    if not id_atribuicao or not resultados_data:
        return jsonify({"error": "Dados incompletos (atribuicao_id ou resultados vazios)"}), 400

    try:
        # 1. Valida se a atribuição existe e se já não foi feita
        atribuicao = Atribuicao.query.get(id_atribuicao)
        if not atribuicao:
            return jsonify({"error": "Atribuição não encontrada"}), 404

        if atribuicao.status == 'concluido':
            return jsonify({"error": "Esta vistoria já foi concluída"}), 400

        # 2. Cria o registro de Execução (O cabeçalho da resposta)
        nova_execucao = Execucao(
            id_atribuicao=atribuicao.id,
            status_auditoria='pendente_validacao'
        )
        db.session.add(nova_execucao)
        db.session.flush() # Gera o ID da execução sem commitar a transação

        # 3. Insere os Resultados (As respostas das etapas)
        for res in resultados_data:
            novo_resultado = ResultadoEtapa(
                id_execucao=nova_execucao.id,
                id_etapa=res.get('id_etapa'),
                # A URL da foto já vem do Supabase Storage gerada pelo front-end
                foto_url=res.get('foto_url'), 
                justificativa=res.get('justificativa')
            )
            db.session.add(novo_resultado)

        # 4. Atualiza o status da Atribuição para tirá-la da lista de "Pendentes" do app mobile
        atribuicao.status = 'concluido'

        db.session.commit() # Salva tudo de forma atômica

        return jsonify({"message": "Vistoria enviada com sucesso!", "id_execucao": nova_execucao.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao enviar vistoria: {str(e)}"}), 500