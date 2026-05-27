import os
import telebot
import openai
import requests
import sqlite3

# =====================================================================
# 1. CONFIGURAÇÕES E CHAVES (Puxando do Render)
# =====================================================================
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")
CHAVE_OPENAI = os.environ.get("OPENAI_API_KEY")

bot = telebot.TeleBot(TOKEN_TELEGRAM)
openai.api_key = CHAVE_OPENAI

# 🔴 SEUS DADOS ADM
USUARIOS_PERMITIDOS = [5435085592]  # Seu ID de Administrador
USUARIO_DONO = "@Alexandreav"       # Seu usuário para contato

# Dicionário temporário para controlar as etapas do cadastro
dados_cadastro = {}

# BANCO DE DADOS
def conectar_banco():
    conn = sqlite3.connect("clientes.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            telegram_id INTEGER,
            dias_acesso INTEGER,
            status TEXT DEFAULT 'Ativo'
        )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = conectar_banco()
conn.close()

PROMPT_SISTEMA = (
    "Você é o Robô de Fogo Avançado, uma IA curta e direta. "
    "Responda sempre em português do Brasil de forma muito resumida. "
    "NUNCA use formatação LaTeX."
)

# =====================================================================
# 2. FUNÇÕES DO BANCO DE DADOS
# =====================================================================

def salvar_cliente_no_banco(nome, telegram_id, dias):
    try:
        conn = sqlite3.connect("clientes.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clientes (nome, telegram_id, dias_acesso, status) 
            VALUES (?, ?, ?, 'Ativo')
        """, (nome, telegram_id, dias))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao salvar: {e}")
        return False

def listar_clientes_banco():
    try:
        conn = sqlite3.connect("clientes.db")
        cursor = conn.cursor()
        cursor.execute("SELECT nome, telegram_id, dias_acesso FROM clientes")
        linhas = cursor.fetchall()
        conn.close()
        
        if not linhas:
            return "📊 **Painel de Controle de Clientes**\n\nNenhum cliente cadastrado no momento."
        
        texto = "📊 **Painel de Controle de Clientes**\n\n"
        for i, linha in enumerate(linhas, 1):
            texto += f"{i}. 🟢 **{linha[0]}** | ID: `{linha[1]}` | {linha[2]} dias restantes\n"
        return texto
    except:
        return "Erro ao acessar o painel."

# =====================================================================
# 3. CORE DA IA (Texto, Voz e Visão)
# =====================================================================

def responder_com_chatgpt(texto):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=CHAVE_OPENAI)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": PROMPT_SISTEMA}, {"role": "user", "content": texto}]
        )
        return response.choices[0].message.content
    except:
        return "Tive um probleminha para processar o texto agora."

def analisar_foto_e_tarefa(url_da_foto):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=CHAVE_OPENAI)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": [{"type": "text", "text": "Resolva de forma super resumida e direta."}, {"type": "image_url", "image_url": {"url": url_da_foto}}]}
            ]
        )
        return response.choices[0].message.content
    except:
        return "Não consegui processar a imagem."

# =====================================================================
# 4. CONTROLADORES DO TELEGRAM (Fluxo Passo a Passo)
# =====================================================================

# Comando /start
@bot.message_handler(commands=['start', 'help'])
def enviar_boas_vindas(message):
    user_id = message.from_user.id
    primeiro_nome = message.from_user.first_name
    
    if user_id in USUARIOS_PERMITIDOS:
        texto_adm = (
            f"Olá, {primeiro_nome}! 🔥\n\n"
            f"Você está no modo **Administrador**.\n"
            f"• Para cadastrar um novo cliente, use: /novo\n"
            f"• Para ver a lista de acessos, digite: **Painel**"
        )
        bot.send_message(message.chat.id, texto_adm, parse_mode="Markdown")
        return

    conn = sqlite3.connect("clientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clientes WHERE telegram_id = ?", (user_id,))
    cliente_existe = cursor.fetchone()
    conn.close()

    if cliente_existe:
        bot.send_message(message.chat.id, f"Olá, {primeiro_nome}! 🔥\nO seu Fire iA está ativo e liberado. Pode mandar suas mensagens, fotos ou áudios!")
    else:
        texto_bloqueio = (
            f"Olá, {primeiro_nome}! 🔥\n\n"
            f"⚠️ **SISTEMA PRIVADO** ⚠️\n"
            f"Seu perfil ainda não está liberado no sistema.\n\n"
            f"🆔 **Seu ID do Telegram:** `{user_id}`\n\n"
            f"Copie o seu ID acima e envie para o administrador liberar: {USUARIO_DONO}"
        )
        bot.send_message(message.chat.id, texto_bloqueio, parse_mode="Markdown")

# 🚀 PASSO 1: Iniciar o cadastro com /novo
@bot.message_handler(commands=['novo'])
def iniciar_cadastro(message):
    user_id = message.from_user.id
    if user_id not in USUARIOS_PERMITIDOS: return
    
    bot.send_message(message.chat.id, "👤 **Etapa 1:** Digite o **Nome** do cliente:")
    dados_cadastro[user_id] = {"etapa": "nome"}

# Validador de segurança para funções de mídia
def verificar_acesso(user_id):
    if user_id in USUARIOS_PERMITIDOS: return True
    conn = sqlite3.connect("clientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clientes WHERE telegram_id = ?", (user_id,))
    existe = cursor.fetchone()
    conn.close()
    return True if existe else False

@bot.message_handler(content_types=['photo'])
def tratar_foto(message):
    if not verificar_acesso(message.from_user.id): return
    bot.reply_to(message, "📸 Analisando imagem...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN_TELEGRAM}/{file_info.file_path}"
        bot.reply_to(message, analisar_foto_e_tarefa(file_url))
    except: pass

@bot.message_handler(content_types=['voice'])
def tratar_voz(message):
    user_id = message.from_user.id
    if not verificar_acesso(user_id): return
    
    aviso = bot.reply_to(message, "🎙️ Ouvindo...")
    try:
        file_info = bot.get_file(message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN_TELEGRAM}/{file_info.file_path}"
        audio_data = requests.get(file_url).content
        nome_arquivo = f"voice_{message.message_id}.ogg"
        with open(nome_arquivo, "wb") as f: f.write(audio_data)
        
        from openai import OpenAI
        client = OpenAI(api_key=CHAVE_OPENAI)
        with open(nome_arquivo, "rb") as audio_file:
            transcricao = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        
        texto_audio = transcricao.text
        os.remove(nome_arquivo)
        bot.delete_message(message.chat.id, aviso.message_id)
        
        if (texto_audio.lower() == "painel" or "painel" in texto_audio.lower()) and user_id in USUARIOS_PERMITIDOS:
            bot.reply_to(message, listar_clientes_banco(), parse_mode="Markdown")
        else:
            bot.reply_to(message, f"🤖 *Resposta:* {responder_com_chatgpt(texto_audio)}", parse_mode="Markdown")
    except:
        bot.edit_message_text("Não entendi o áudio.", message.chat.id, aviso.message_id)

# Handler Geral de Texto (Processa as conversas e as etapas do cadastro)
@bot.message_handler(func=lambda message: True)
def tratar_texto_e_cadastro(message):
    user_id = message.from_user.id
    texto = message.text

    # Captura se você estiver no meio de um cadastro (/novo)
    if user_id in dados_cadastro:
        fluxo = dados_cadastro[user_id]
        
        # 🚀 PASSO 2: Recebeu o nome, pede o ID
        if fluxo["etapa"] == "nome":
            fluxo["nome"] = texto
            fluxo["etapa"] = "id"
            bot.send_message(message.chat.id, f"✅ Nome salvo: *{texto}*\n\n🆔 **Etapa 2:** Digite o **ID do Telegram** do cliente:", parse_mode="Markdown")
            return
            
        # 🚀 PASSO 3: Recebeu o ID, pede os Dias
        elif fluxo["etapa"] == "id":
            if not texto.isdigit():
                bot.send_message(message.chat.id, "⚠️ O ID precisa ser apenas números! Digite novamente:")
                return
            fluxo["id"] = int(texto)
            fluxo["etapa"] = "dias"
            bot.send_message(message.chat.id, f"✅ ID salvo: `{texto}`\n\n⏳ **Etapa 3:** Digite a quantidade de **Dias de Acesso** (ex: 30):", parse_mode="Markdown")
            return
            
        # 🚀 PASSO FINAL: Salva tudo no banco de dados
        elif fluxo["etapa"] == "dias":
            if not texto.isdigit():
                bot.send_message(message.chat.id, "⚠️ Os dias precisam ser um número! Digite novamente:")
                return
            dias = int(texto)
            nome = fluxo["nome"]
            telegram_id = fluxo["id"]
            
            # Salva de verdade
            if salvar_cliente_no_banco(nome, telegram_id, dias):
                bot.send_message(
                    message.chat.id, 
                    f"🔥 **CLIENTE LIBERADO COM SUCESSO!**\n\n"
                    f"👤 **Nome:** {nome}\n"
                    f"🆔 **ID:** `{telegram_id}`\n"
                    f"⏳ **Acesso:** {dias} dias\n\n"
                    f"A partir de agora o cliente já pode usar o Fire iA!", 
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(message.chat.id, "❌ Ocorreu um erro ao salvar no banco.")
            
            # Limpa o estado de cadastro para você poder usar o bot normal
            dados_cadastro.pop(user_id)
            return

    # Se não estiver cadastrando, roda as funções normais do ADM ou Cliente
    if not verificar_acesso(user_id):
        return

    if texto.lower() == "painel" and user_id in USUARIOS_PERMITIDOS:
        bot.reply_to(message, listar_clientes_banco(), parse_mode="Markdown")
        return

    bot.reply_to(message, responder_com_chatgpt(texto))

if __name__ == "__main__":
    bot.infinity_polling()
