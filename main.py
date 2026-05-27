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
USUARIO_DONO = "@Alexandreav"

# BANCO DE DADOS ATUALIZADO
def conectar_banco():
    conn = sqlite3.connect("clientes.db")
    cursor = conn.cursor()
    # Cria a tabela com os novos campos que você pediu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            telefone TEXT,
            telegram_id INTEGER,
            dias_acesso INTEGER,
            status TEXT DEFAULT 'Pendente'
        )
    """)
    conn.commit()
    return conn, cursor

# Inicializa o banco
conn, cursor = conectar_banco()
conn.close()

PROMPT_SISTEMA = (
    "Você é o Robô de Fogo Avançado, uma IA curta e direta. "
    "Diretrizes obrigatórias:\n"
    "1. Responda SEMPRE em português do Brasil.\n"
    "2. Seja o mais resumido possível.\n"
    "3. NUNCA use formatação LaTeX como '\\[' ou '\\times'.\n"
    "4. Se o usuário quiser cadastrar, oriente a usar o padrão: Cadastrar Nome - Telefone - ID - Dias"
)

# =====================================================================
# 2. FUNÇÕES DE GERENCIAMENTO DE CLIENTES
# =====================================================================

def cadastrar_cliente_completo(nome, telefone, telegram_id, dias):
    try:
        conn = sqlite3.connect("clientes.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clientes (nome, telefone, telegram_id, dias_acesso, status) 
            VALUES (?, ?, ?, ?, 'Pendente')
        """, (nome, telefone, telegram_id, dias))
        conn.commit()
        conn.close()
        
        return (
            f"✅ **Cliente Liberado e Cadastrado!**\n\n"
            f"👤 **Nome:** {nome}\n"
            f"📱 **Zap:** {telefone}\n"
            f"🆔 **ID Telegram:** `{telegram_id}`\n"
            f"⏳ **Acesso:** {dias} dias\n"
            f"📊 **Status:** Pendente"
        )
    except Exception as e:
        return f"Erro ao salvar cliente: {e}"

def listar_clientes_banco():
    try:
        conn = sqlite3.connect("clientes.db")
        cursor = conn.cursor()
        cursor.execute("SELECT nome, telegram_id, dias_acesso, status FROM clientes")
        linhas = cursor.fetchall()
        conn.close()
        
        if not linhas:
            return "📊 **Painel de Controle de Clientes**\n\nNenhum cliente cadastrado no momento."
        
        texto = "📊 **Painel de Controle de Clientes**\n\n"
        for i, linha in enumerate(linhas, 1):
            emoji = "🟢" if linha[3] == "Pago" else "🔴"
            texto += f"{i}. {emoji} **{linha[0]}** | ID: `{linha[1]}` | {linha[2]} dias ({linha[3]})\n"
        return texto
    except Exception as e:
        return f"Erro ao listar clientes: {e}"

# =====================================================================
# 3. INTELIGÊNCIA ARTIFICIAL (Texto, Voz e Visão)
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
                {"role": "user", "content": [{"type": "text", "text": "Resolva a imagem direto ao ponto, sem enrolação."}, {"type": "image_url", "image_url": {"url": url_da_foto}}]}
            ]
        )
        return response.choices[0].message.content
    except:
        return "Não consegui ler a imagem agora."

# =====================================================================
# 4. CONTROLADORES DO TELEGRAM
# =====================================================================

@bot.message_handler(commands=['start', 'help'])
def enviar_boas_vindas(message):
    texto = (
        f"Olá, {message.from_user.first_name}! 🔥\n\n"
        f"Para cadastrar um cliente completo, digite exatamente assim:\n"
        f"`Cadastrar Nome - Telefone - ID - Dias`\n\n"
        f"Exemplo:\n"
        f"`Cadastrar João Silva - 11999999999 - 123456789 - 30`\n\n"
        f"Toque em **Painel** para ver a lista."
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def tratar_foto(message):
    # Verifica se quem mandou a foto é você (Administrador) ou um cliente cadastrado no banco
    user_id = message.from_user.id
    
    conn = sqlite3.connect("clientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clientes WHERE telegram_id = ?", (user_id,))
    cliente_existe = cursor.fetchone()
    conn.close()

    if user_id not in USUARIOS_PERMITIDOS and not cliente_existe:
        verificar_e_bloquear_intruso(message)
        return

    bot.reply_to(message, "📸 Analisando imagem...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN_TELEGRAM}/{file_info.file_path}"
        bot.reply_to(message, analisar_foto_e_tarefa(file_url))
    except:
        bot.reply_to(message, "Erro na imagem.")

@bot.message_handler(content_types=['voice'])
def tratar_voz(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect("clientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clientes WHERE telegram_id = ?", (user_id,))
    cliente_existe = cursor.fetchone()
    conn.close()

    if user_id not in USUARIOS_PERMITIDOS and not cliente_existe:
        verificar_e_bloquear_intruso(message)
        return

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

@bot.message_handler(func=lambda message: True)
def tratar_texto(message):
    user_id = message.from_user.id
    texto_usuario = message.text

    # Verifica se é cliente autorizado no banco
    conn = sqlite3.connect("clientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clientes WHERE telegram_id = ?", (user_id,))
    cliente_existe = cursor.fetchone()
    conn.close()

    if user_id not in USUARIOS_PERMITIDOS and not cliente_existe:
        verificar_e_bloquear_intruso(message)
        return

    # Comando apenas para você (ADM) ver a lista de clientes
    if texto_usuario.lower() == "painel" and user_id in USUARIOS_PERMITIDOS:
        bot.reply_to(message, listar_clientes_banco(), parse_mode="Markdown")
        return

    # Comando de texto para você (ADM) cadastrar o cliente completo
    if texto_usuario.lower().startswith("cadastrar") and user_id in USUARIOS_PERMITIDOS:
        try:
            # Separa os dados pelos traços (-)
            dados = texto_usuario.replace("Cadastrar", "").replace("cadastrar", "").strip()
            partes = dados.split("-")
            
            nome = partes[0].strip()
            telefone = partes[1].strip()
            telegram_id = int(partes[2].strip())
            dias = int(partes[3].strip())
            
            resposta = cadastrar_cliente_completo(nome, telefone, telegram_id, dias)
            bot.reply_to(message, resposta, parse_mode="Markdown")
            return
        except:
            bot.reply_to(message, "⚠️ **Erro no formato!** Use exatamente assim:\n`Cadastrar Nome - Telefone - ID - Dias`")
            return

    bot.reply_to(message, responder_com_chatgpt(texto_usuario))

def verificar_e_bloquear_intruso(message):
    id_intruso = message.from_user.id
    texto_bloqueio = (
        f"❌ **ACESSO NEGADO** ❌\n\n"
        f"Você não está cadastrado no sistema do Robô de Fogo.\n"
        f"**Seu ID:** `{id_intruso}`\n\n"
        f"Para solicitar o seu acesso envie uma mensagem para {USUARIO_DONO}."
    )
    bot.send_message(message.chat.id, texto_bloqueio, parse_mode="Markdown")

if __name__ == "__main__":
    bot.infinity_polling()
