
# 🧠 CLAUDE.md - Missão Vistoria IA (App Checklist Fotográfico)
**Versão:** 1.0 (Refatorada) | **Data:** [16/03/2026-11:20] | **Autores:** Kauã e Leon

## 1. Topologia do Sistema e Stack
* **Front-end UI:** React, TypeScript, Tailwind CSS, shadcn/ui (Gerado via v0). SPA estrita.
* **Back-end API:** Python 3 + Flask + SQLAlchemy. Atua exclusivamente como Fachada e Camada de Regras de Negócio.
* **BaaS:** Supabase. Utilizaremos o PostgreSQL (com RLS ativado), Supabase Auth (JWT) e Supabase Storage (Buckets).
* **Arquitetura de Rede e Upload (Obrigatório):** * O Front-end consome a API Flask trafegando EXCLUSIVAMENTE dados JSON.
  * O arquivo físico da imagem NUNCA passa pelo Flask. O Front-end faz o upload direto para o Supabase Storage usando o Supabase-js Client, obtém a URL pública e envia apenas a string da URL para o Flask no payload de conclusão da etapa.

## 2. Modelagem de Dados e Índices (PostgreSQL)
Todos os comandos DDL abaixo devem ser executados no SQL Editor do Supabase. O RLS é obrigatório.

```sql
-- 1. Tabelas Base
CREATE TABLE checklists_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    titulo VARCHAR(255) NOT NULL,
    criado_por UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE checklist_etapas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_checklist_template UUID REFERENCES checklists_templates(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    requer_foto BOOLEAN DEFAULT FALSE,
    ordem INTEGER NOT NULL
);

CREATE TABLE atribuicoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_checklist_template UUID REFERENCES checklists_templates(id) ON DELETE CASCADE,
    id_staff UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pendente' -- pendente, concluido
);

CREATE TABLE execucoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_atribuicao UUID REFERENCES atribuicoes(id) ON DELETE CASCADE,
    enviado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status_auditoria VARCHAR(50) DEFAULT 'pendente_validacao' -- pendente_validacao, aprovado, rejeitado
);

CREATE TABLE resultados_etapas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_execucao UUID REFERENCES execucoes(id) ON DELETE CASCADE,
    id_etapa UUID REFERENCES checklist_etapas(id) ON DELETE CASCADE,
    foto_url TEXT NULL,
    justificativa TEXT NULL,
    CONSTRAINT valida_submissao CHECK (foto_url IS NOT NULL OR justificativa IS NOT NULL)
);

-- 2. Índices Críticos de Performance
CREATE INDEX idx_atribuicoes_staff ON atribuicoes(id_staff);
CREATE INDEX idx_execucoes_auditoria ON execucoes(status_auditoria);

-- 3. Row Level Security (RLS) - OBRIGATÓRIO
ALTER TABLE checklists_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE atribuicoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE execucoes ENABLE ROW LEVEL SECURITY;

-- Exemplo de Policy (Aplicar lógica similar a todas): 
-- Staff só vê suas próprias atribuições.
CREATE POLICY "Staff_Select_Own_Atribuicoes" ON atribuicoes 
    FOR SELECT USING (auth.uid() = id_staff);
-- Admin vê tudo (Assumindo que uma claim ou tabela de roles gerencie isso).
```

## 3. Segurança e Autenticação (Fluxo JWT)
* **Client-Side:** O v0 deve implementar o login usando `@supabase/supabase-js`. O token JWT recebido no login deve ser armazenado (localStorage/sessionStorage) e injetado no header `Authorization: Bearer <token>` em TODAS as requisições `fetch()` para a API Flask.
* **Server-Side (Flask):** O Flask possuirá um middleware/decorator (`@token_required`) que intercepta o header, decodifica o JWT usando a chave JWT Secret do Supabase e valida a Role do usuário antes de processar a rota.
* **Database-Side:** RLS garante que, mesmo se a API falhar, uma query maliciosa não retorne dados de outros usuários.

## 4. Contratos de API (REST Flask) - [STRICT JSON]
*A UI não deve esperar HTML, apenas JSON. A UI não deve enviar Form-Data com arquivos, apenas JSON.*

* `POST /api/checklists` (Criação pelo Admin)
  * **Req:** `{ "titulo": "Vistoria Patio A", "etapas": [{"descricao": "Foto do Portão", "requer_foto": true, "ordem": 1}], "id_staff": "uuid-do-staff" }`
  * **Res:** `201 Created`

* `GET /api/atribuicoes` (Listagem para o Staff)
  * **Req:** `Header: Bearer <token>`
  * **Res:** `200 OK` `[{ "atribuicao_id": "...", "titulo": "...", "status": "pendente", "etapas": [...] }]`

* `POST /api/execucoes` (Submissão pelo Staff)
  * **Req:** `{ "atribuicao_id": "uuid", "resultados": [ {"id_etapa": "uuid", "foto_url": "https://...", "justificativa": null} ] }`
  * **Res:** `201 Created`

* `GET /api/auditoria/feed` (Feed do Admin)
  * **Req:** `Header: Bearer <token>`
  * **Res:** `200 OK` Array de execuções concluídas com os dados do staff, horário e array de fotos/justificativas.

## 5. Regras de Domínio e Estado (Validação Frontend e Backend)
* **Máquina de Estado da Etapa:**
  * Se `requer_foto == true`: O botão "Confirmar Etapa" só é habilitado se a variável de estado `foto_url` estiver preenchida OU a variável `justificativa` estiver preenchida. Nunca as duas vazias.
  * Se `requer_foto == false`: Requer apenas a ação de clique no botão "Confirmar".
* O Backend Flask retornará HTTP 400 se o payload violar essa máquina de estado ou a Constraint `valida_submissao` do DB.

## 6. Diretrizes de Interface (UI/UX) para o v0
**Atenção v0:** Gere os componentes React utilizando Tailwind CSS e `shadcn/ui`. O design deve ser estritamente Mobile-First.
* **Paleta:** Fundo cinza claro (`bg-slate-50`), Cards brancos, Botões de ação principal em Azul (`bg-blue-600`), Avisos/Bloqueios em Vermelho (`bg-red-500`) ou Amarelo.
* **Visão Admin (Gestão e Auditoria):**
  * *Feed de Auditoria:* Estilo Instagram. Cards verticais. O cabeçalho do card tem o nome do Staff e a hora. Abaixo deverá constar o título da checklist criada. O corpo do card **deve** usar um componente de Carrossel (`Carousel` do shadcn) para deslizar entre as fotos enviadas daquela execução. Abaixo deverá constar quantas etapas foram concluídas, quantas foram impedidas e abaixo caixa com justificativas de bloqueio. Abaixo, um botão verde "Validar Vistoria".
* **Visão Staff (Operação Mobile):**
  * *Layout da Execução:* Exibir uma Barra de Progresso (`Progress` do shadcn) fixada no topo mostrando `(Etapas Concluídas / Total de Etapas)`.
  * *Captura de Foto:* O botão de envio de imagem deve usar estritamente `<input type="file" accept="image/*" capture="environment" />` para forçar a abertura da câmera nativa do celular.
  * *Ação de Bloqueio:* Um botão "Relatar Impedimento" que abre um Modal ou Drawer inferior (`Sheet` ou `Dialog` do shadcn) com um `<Textarea>` para a justificativa. Ao salvar, a etapa é marcada como concluída (com justificativa, sem foto).

## 7. Governança, Anti-Vibe Coding e Prompts
* **Regras do One-Shot Visual:** O prompt gerador de UI no v0 deve conter uma cópia estrita da Seção 6 e os JSONs de mock da Seção 4 para o v0 não "alucinar" dados.
* **Padrões:** Clean Code, separação de arquivos lógicos no React (hooks separados de views) e no Flask (Routes separadas de Services/Models).