import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv
from groq import Groq

# Carrega variáveis do arquivo credenciais.env
load_dotenv("credenciais.env")

# Configurações Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    raise Exception("SUPABASE_URL ou SUPABASE_KEY não encontrados. Verifique seu .env")
supabase: Client = create_client(supabase_url, supabase_key)

# Configuração Groq
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise Exception("GROQ_API_KEY não encontrado. Verifique seu .env")
groq_client = Groq(api_key=groq_api_key)

# Inicializa Flask
app = Flask(__name__)

# Guarda estado do usuário ativo
usuarios = {
    "id_usuario": None,
    "gasto_pendente": None  # guarda gasto aguardando confirmação
}

# Função para interpretar mensagem de gasto
def interpretar_gasto(texto):
    prompt = f"""
Você é um assistente financeiro inteligente que interpreta mensagens de gasto em português
e transforma em dados estruturados. Seu papel é identificar a descrição, o valor e a
categoria mais apropriada, mas **só confirmar o gasto se tiver certeza**.

Formato de resposta JSON (apenas JSON):
{{
    "descricao": "<descrição do gasto>",
    "valor": <valor numérico>,
    "categoria": "<categoria: transporte, alimentacao, saude, entretenimento, lazer, moradia ou outros>",
    "resposta_usuario": "<mensagem para o usuário>"
}}

Regras importantes:
1. Se a categoria estiver clara, responda com "Gasto computado ✅" e a categoria correta.
2. Se houver dúvida entre duas categorias (ex: "jantar com amigos" → alimentacao ou lazer),
   pergunte ao usuário qual ele prefere: "Esse gasto se encaixa melhor em alimentação ou lazer?"
3. Se o gasto for muito genérico ("gastei 50", "comprei algo"), defina categoria como "desconhecido"
   e responda: "Não consegui identificar a categoria, você poderia informar?"
4. **Nunca gere um valor ou categoria fictícia.** Se não tiver certeza, pergunte.

Mensagem do usuário: "{texto}"
"""

    try:
        resposta = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        conteudo = resposta.choices[0].message.content.strip()
        gasto_json = json.loads(conteudo)
    except json.JSONDecodeError:
        gasto_json = {"descricao": texto, "valor": 0, "categoria": "desconhecido", "resposta_usuario": "Não consegui processar a mensagem."}
    except Exception as e:
        print("Erro na API Groq:", e)
        gasto_json = {"descricao": texto, "valor": 0, "categoria": "desconhecido", "resposta_usuario": "Erro ao processar gasto."}

    return gasto_json


# Rota principal (frontend)
@app.route("/")
def index():
    return render_template("index.html")


# Rota de envio de mensagem
@app.route("/mensagem", methods=["POST"])
def mensagem():
    data = request.json
    texto = data.get("texto", "").strip()
    if not texto:
        return jsonify({"resposta": "Mensagem vazia."})

    # Se o usuário ainda não enviou seu ID
    if not usuarios["id_usuario"]:
        if len(texto) == 36 and "-" in texto:
            usuarios["id_usuario"] = texto
            return jsonify({"resposta": "✅ ID registrado! Agora envie seu gasto, ex: 'Uber 25 reais'."})
        else:
            return jsonify({"resposta": "Por favor, envie primeiro seu ID de usuário (UUID)."})

    id_usuario = usuarios["id_usuario"]

    # Caso o usuário esteja confirmando um gasto pendente
    if usuarios["gasto_pendente"]:
        gasto = usuarios["gasto_pendente"]
        categoria_escolhida = texto.lower().strip()

        if categoria_escolhida in ["alimentacao", "lazer", "saude", "transporte", "entretenimento", "moradia", "outros"]:
            gasto["categoria"] = categoria_escolhida
            try:
                supabase.table("gastos").insert({
                    "id_usuario": id_usuario,
                    "descricao": gasto["descricao"],
                    "valor": gasto["valor"],
                    "categoria": gasto["categoria"]
                }).execute()
                usuarios["gasto_pendente"] = None
                alerta = verificar_orcamento(id_usuario, gasto["categoria"])
                return jsonify({"resposta": f"Gasto computado ✅ Categoria confirmada: {categoria_escolhida}.{alerta}"})
            except Exception as e:
                print("Erro ao salvar no Supabase:", e)
                return jsonify({"resposta": f"❌ Erro ao salvar gasto: {e}"})
        else:
            return jsonify({"resposta": "Categoria inválida. Tente novamente: alimentação, lazer, saúde, transporte, moradia, entretenimento ou outros."})

    # Interpreta gasto via Groq
    gasto_info = interpretar_gasto(texto)

    # Se IA ficou em dúvida, pede confirmação sem salvar
    if gasto_info["categoria"].lower() == "desconhecido" or "?" in gasto_info["resposta_usuario"]:
        usuarios["gasto_pendente"] = gasto_info
        return jsonify({"resposta": gasto_info["resposta_usuario"]})

    # Caso a IA tenha certeza, grava direto
    try:
        supabase.table("gastos").insert({
            "id_usuario": id_usuario,
            "descricao": gasto_info["descricao"],
            "valor": gasto_info["valor"],
            "categoria": gasto_info["categoria"]
        }).execute()
        alerta = verificar_orcamento(id_usuario, gasto_info["categoria"])
        return jsonify({"resposta": gasto_info.get("resposta_usuario", "Gasto computado ✅") + alerta})
    except Exception as e:
        print("Erro ao salvar no Supabase:", e)
        return jsonify({"resposta": f"❌ Erro ao salvar gasto: {e}"})


# Rota para definir ou atualizar orçamento mensal
@app.route("/definir_orcamento", methods=["POST"])
def definir_orcamento():
    data = request.json
    categoria = data.get("categoria")
    valor = data.get("valor")

    if not usuarios["id_usuario"]:
        return jsonify({"mensagem": "Por favor, envie primeiro seu ID de usuário."})

    id_usuario = usuarios["id_usuario"]
    agora = datetime.now()
    mes_atual, ano_atual = agora.month, agora.year

    try:
        existente = supabase.table("orcamentos") \
            .select("*") \
            .eq("id_usuario", id_usuario) \
            .eq("categoria", categoria) \
            .execute()

        existente_mes = [
            o for o in existente.data
            if datetime.fromisoformat(o["criado_em"]).month == mes_atual
            and datetime.fromisoformat(o["criado_em"]).year == ano_atual
        ]

        if existente_mes:
            id_orc = existente_mes[0]["id_orcamento"]
            supabase.table("orcamentos").update({"limite_mensal": valor}).eq("id_orcamento", id_orc).execute()
            msg = f"✅ Orçamento atualizado: {categoria} → R${valor:.2f}"
        else:
            supabase.table("orcamentos").insert({
                "id_usuario": id_usuario,
                "categoria": categoria,
                "limite_mensal": valor
            }).execute()
            msg = f"💰 Orçamento definido para {categoria}: R${valor:.2f}"

        return jsonify({"mensagem": msg})

    except Exception as e:
        print("Erro ao salvar orçamento:", e)
        return jsonify({"mensagem": f"❌ Erro ao salvar orçamento: {e}"})


# Função que verifica se o gasto atingiu 90% do orçamento
def verificar_orcamento(id_usuario, categoria):
    try:
        agora = datetime.now()
        mes_atual, ano_atual = agora.month, agora.year

        orc = supabase.table("orcamentos") \
            .select("*") \
            .eq("id_usuario", id_usuario) \
            .eq("categoria", categoria) \
            .execute()

        if not orc.data:
            return ""

        limite = float(orc.data[-1]["limite_mensal"])

        # soma dos gastos da categoria no mês atual
        gastos = supabase.table("gastos") \
            .select("valor, criado_em") \
            .eq("id_usuario", id_usuario) \
            .eq("categoria", categoria) \
            .execute()

        total_mes = sum(
            float(g["valor"]) for g in gastos.data
            if datetime.fromisoformat(g["criado_em"]).month == mes_atual
            and datetime.fromisoformat(g["criado_em"]).year == ano_atual
        )

        if total_mes >= 0.9 * limite:
            return f" ⚠️ Atenção: você já gastou {total_mes:.2f} de {limite:.2f} em {categoria} neste mês!"
        return ""

    except Exception as e:
        print("Erro ao verificar orçamento:", e)
        return ""


# Rota para listar gastos (para gráfico)
@app.route("/gastos", methods=["GET"])
def listar_gastos():
    if not usuarios["id_usuario"]:
        return jsonify([])
    id_usuario = usuarios["id_usuario"]
    data = supabase.table("gastos").select("*").eq("id_usuario", id_usuario).execute()
    return jsonify(data.data)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
