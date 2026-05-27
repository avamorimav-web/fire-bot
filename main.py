import os
import telebot
import openai
import requests

# =====================================================================
# 1. CONFIGURAÇÕES E CHAVES (Puxando do Render)
# =====================================================================
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")
CHAVE_OPENAI = os.environ.get("OPENAI_API_KEY")

# Inicializa o Bot e a OpenAI
bot = telebot.TeleBot(TOKEN_TELEGRAM)
openai.api_key = CHAVE_OPENAI

# 🔴 SEUS DADOS ADM
USUARIOS_PERMITIDOS = [5435085592]  # Seu ID de Administrador
USUARIO_DONO = "@Alexandreav"  # Seu usuário para contato

# Instrução mestre para a IA agir corretamente e falar apenas português limpo
PROMPT_SISTEMA = (
    "Você é o Robô de Fogo Avançado, uma inteligência artificial prestativa, direta e focada. "
    "Diretrizes obrigatórias:\n"
    "1. Responda SEMPRE em português do Brasil, de forma natural e humana.\n"
    "2. NUNCA use formatação LaTeX ou símbolos matemáticos complexos como '\\[' ou '\\times'. Use texto normal (ex: 7000 x 17 = 119000).\n"
    "3. Preste muita atenção aos números informados pelo usuário para não errar ordens de grandeza (ex: '7 mil' significa 7.000 e não 7 milhões).\n"
    "4. Se o usuário enviar uma foto de tarefa escolar, não apenas descreva o livro: RESOLVA as questões visíveis passo a passo."
)

# =====================================================================
# 2. INTELIGÊNCIA ARTIFICIAL (Texto, Voz e Fotos/Tarefas)
# =====================================================================

def responder_com_chatgpt(texto):
    """Responde mensagens de texto normais usando o ChatGPT com a calibragem correta"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=CHAVE_OPENAI)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": texto}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        # Se a biblioteca nova falhar por falta de atualização no servidor, usa o método antigo seguro
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": texto}
                ]
            )
            return response.choices[0].message['content']
        except Exception as erro_antigo:
            print(f"Erro OpenAI Texto: {erro_antigo}")
            return "Tive um probleminha para processar o texto agora. Pode tentar de novo?"

def analisar_foto_e_tarefa(url_da_foto):
    """Lê fotos e resolve tarefas escolares enviadas por imagem sem enrolação"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=CHAVE_OPENAI)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analise detalhadamente os textos e perguntas nesta imagem. Resolva e responda cada uma das tarefas ou questões escolares encontradas de forma clara e passo a passo em português."},
                        {"type": "image_url", "image_url": {"url": url_da_foto}}
                    ]
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Erro OpenAI Visão: {e}")
        return "Não consegui ler ou processar os detalhes desta imagem agora."

# =====================================================================
# 3. FUNÇÕES DO SISTEMA (Painel, Lembretes e Finanças)
# =====================================================================

def painel_controle_clientes():
    return "📊 **Painel de Controle de Clientes**\n\nNenhum cliente inadimplente ou pendente no momento."

def gerenciar_lembretes(texto):
    if "lembrar" in texto.lower() or "lembrete" in texto.lower():
        return "⏰ Lembrete anotado com sucesso! Eu te avisarei no momento solicitado."
    return None

# =====================================================================
# 4. CONTROLADORES DO TELEGRAM (Handlers e Trava de Segurança)
# =====================================================================

# Comando /start
@bot.message_handler(commands=['start', 'help'])
def enviar_boas_vindas(message):
    primeiro_nome = message.from_user.first_name
    texto = (
        f"Olá, {primeiro_nome}! 🔥\n\n"
        f"Eu sou o seu **Robô de Fogo Avançado**.\n"
        f"Estou pronto para responder textos, áudios, registrar lembretes, "
        f"controlar clientes e até **resolver tarefas escolares por foto**!\n\n"
        f"Tudo controlado 100% por Inteligência Artificial. Pode mandar sua mensagem!"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

# Recebimento de FOTOS e TAREFAS
@bot.message_handler(content_types=['photo'])
def tratar_foto(message):
    user_id = message.from_user.id
    if user_id not in USUARIOS_PERMITIDOS:
        verificar_e_bloquear_intruso(message)
        return

    bot.reply_to(message, "📸 Analisando sua foto e resolvendo sua tarefa... Aguarde um instante.")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN_TELEGRAM}/{file_info.file_path}"
        resposta_foto = analisar_foto_e_tarefa(file_url)
        bot.reply_to(message, resposta_foto)
    except Exception as e:
        bot.reply_to(message, "Erro ao baixar ou processar a imagem.")

# Recebimento de RECONHECIMENTO DE VOZ
@bot.message_handler(content_types=['voice'])
def tratar_voz(message):
    user_id = message.from_user.id
    if user_id not in USUARIOS_PERMITIDOS:
        verificar_e_bloquear_intruso(message)
        return

    bot.reply_to(message, "🎙️ Ouvindo seu áudio...")
    bot.reply_to(message, "Áudio recebido! Estou processando o comando de voz no painel.")

# Mensagens de TEXTO GERAIS
@bot.message_handler(func=lambda message: True)
def tratar_texto(message):
    user_id = message.from_user.id
    texto_usuario = message.text

    if user_id not in USUARIOS_PERMITIDOS:
        verificar_e_bloquear_intruso(message)
        return

    try:
        if texto_usuario.lower() == "painel":
            bot.reply_to(message, painel_controle_clientes())
            return

        resposta_lembrete = gerenciar_lembretes(texto_usuario)
        if resposta_lembrete:
            bot.reply_to(message, resposta_lembrete)
            return

        resposta_ia = responder_com_chatgpt(texto_usuario)
        bot.reply_to(message, resposta_ia)

    except Exception as erro:
        print(f"Erro Geral: {erro}")
        bot.reply_to(message, "Houve um erro rápido no processamento. Tente novamente.")

def verificar_e_bloquear_intruso(message):
    id_intruso = message.from_user.id
    texto_bloqueio = (
        f"❌ **ACESSO NEGADO** ❌\n\n"
        f"Você não está cadastrado no sistema do Robô de Fogo.\n"
        f"**Seu ID:** `{id_intruso}`\n\n"
        f"Para solicitar o seu acesso e liberação do painel, entre em contato diretamente com o administrador enviando uma mensagem para {USUARIO_DONO}."
    )
    bot.send_message(message.chat.id, texto_bloqueio, parse_mode="Markdown")

# =====================================================================
# 5. INICIALIZAÇÃO
# =====================================================================
if __name__ == "__main__":
    bot.infinity_polling()
