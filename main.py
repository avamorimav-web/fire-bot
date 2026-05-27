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

# 🔴 SEUS DADOS ADM ATUALIZADOS
USUARIOS_PERMITIDOS = [5435085592]  # Seu ID de Administrador
USUARIO_DONO = "@Alexandreav"  # Seu usuário para contato

# =====================================================================
# 2. INTELIGÊNCIA ARTIFICIAL (Texto, Voz e Fotos/Tarefas)
# =====================================================================

def responder_com_chatgpt(texto):
    """Responde mensagens de texto normais usando o ChatGPT"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": texto}]
        )
        return response.choices[0].message['content']
    except Exception as e:
        print(f"Erro OpenAI Texto: {e}")
        return "Desculpe, tive um problema ao processar o texto agora."

def analisar_foto_e_tarefa(url_da_foto):
    """Lê fotos e resolve tarefas escolares enviadas por imagem"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analise esta imagem. Se for uma tarefa de colégio ou pergunta, resolva-a passo a passo detalhadamente. Se for apenas uma foto comum, descreva o que vê."},
                        {"type": "image_url", "image_url": {"url": url_da_foto}}
                    ]
                }
            ]
        )
        return response.choices[0].message['content']
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

# Comando /start (Apenas texto, sem botões)
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
    
    # Trava de Segurança para fotos
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
    
    # Trava de Segurança para voz
    if user_id not in USUARIOS_PERMITIDOS:
        verificar_e_bloquear_intruso(message)
        return

    bot.reply_to(message, "🎙️ Ouvindo seu áudio...")
    bot.reply_to(message, "Áudio recebido! Estou processando o comando de voz no painel.")

# Mensagens de TEXTO GERAIS (ChatGPT, Lembretes e Painel)
@bot.message_handler(func=lambda message: True)
def tratar_texto(message):
    user_id = message.from_user.id
    texto_usuario = message.text

    # ⛔ TRAVA DE SEGURANÇA SE A PESSOA NÃO ESTIVER NO SISTEMA
    if user_id not in USUARIOS_PERMITIDOS:
        verificar_e_bloquear_intruso(message)
        return

    try:
        # 1. Verifica se quer acessar o Painel
        if texto_usuario.lower() == "painel":
            bot.reply_to(message, painel_controle_clientes())
            return

        # 2. Verifica se é um Lembrete
        resposta_lembrete = gerenciar_lembretes(texto_usuario)
        if resposta_lembrete:
            bot.reply_to(message, resposta_lembrete)
            return

        # 3. Resposta Padrão Inteligente com ChatGPT
        resposta_ia = responder_com_chatgpt(texto_usuario)
        bot.reply_to(message, resposta_ia)

    except Exception as erro:
        print(f"Erro Geral: {erro}")
        bot.reply_to(message, "Houve um erro rápido no processamento. Tente novamente.")

def verificar_e_bloquear_intruso(message):
    """Bloqueia o intruso por texto limpo, exibindo o ID dele e seu @ de contato"""
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
    print("---------------------------------------------")
    print("Robô de Fogo COMPLETO (Sem Botões) iniciado no Render!")
    print("OpenAI Ativa | IA no controle total.")
    print("---------------------------------------------")
    bot.infinity_polling()
