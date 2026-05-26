import os
import sqlite3
import requests
import telebot
from openai import OpenAI
from datetime import datetime

# 1. CONFIGURAÇÃO DE SEGREDOS DA FLY.IO
TOKEN_TELEGRAM = os.environ.get('TELEGRAM_TOKEN')
CHAVE_OPENAI = os.environ.get('GEMINI_API_KEY') 

print("🔥 [SISTEMA] Inicializando Fire iA com Busca na Web Forçada...")

bot = telebot.TeleBot(TOKEN_TELEGRAM)
client = OpenAI(api_key=CHAVE_OPENAI)

ID_ADMIN_ALEXANDRE = 5435085592 

# 2. INICIALIZAÇÃO DO BANCO DE DADOS
def iniciar_banco():
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                tipo TEXT,
                valor REAL,
                descricao TEXT,
                data TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                telegram_id INTEGER PRIMARY KEY,
                nome TEXT,
                status TEXT DEFAULT 'ativo'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lembretes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                tarefa TEXT,
                data_hora TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_conversas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                role TEXT,
                content TEXT,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ [ERRO BANCO] {e}")

iniciar_banco()

def salvar_na_memoria(user_id, papel, texto):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO historico_conversas (telegram_id, role, content) VALUES (?, ?, ?)', (user_id, papel, texto))
        conn.commit()
        conn.close()
    except: pass

def buscar_memoria_usuario(user_id, limite=10):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT role, content FROM historico_conversas WHERE telegram_id = ? ORDER BY data DESC LIMIT ?', (user_id, limite))
        linhas = cursor.fetchall()
        conn.close()
        return [{"role": papel, "content": conteudo} for papel, conteudo in reversed(linhas)]
    except: return []

def usuario_autorizado(user_id):
    if user_id == ID_ADMIN_ALEXANDRE: return True
    conn = sqlite3.connect('fire_ia_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM clientes WHERE telegram_id=?', (user_id,))
    resultado = cursor.fetchone()
    conn.close()
    return True if resultado and resultado[0] == 'ativo' else False

def acao_salvar_financa(user_id, tipo, valor, descricao):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO financas (telegram_id, tipo, valor, descricao, data) VALUES (?, ?, ?, ?, ?)',
                       (user_id, tipo.upper(), float(valor), descricao, data_atual))
        conn.commit()
        conn.close()
        return f"💰 [Sucesso] R$ {valor:.2f} registrado como {tipo} ({descricao})."
    except Exception as e: return f"❌ Erro ao salvar finança: {e}"

def acao_gerar_extrato(user_id):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT tipo, valor, descricao, data FROM financas WHERE telegram_id=?', (user_id,))
        linhas = cursor.fetchall()
        conn.close()
        if not lines: return "📊 Você ainda não possui movimentações financeiras registradas."
        extrato = "📊 *Seu Extrato Mensal Atualizado:*\n\n"
        total_entrada = total_saida = 0
        for tipo, valor, desc, data in linhas:
            if tipo == "ENTRADA":
                extrato += f"🟢 + R$ {valor:.2f} | {desc} (_{data.split()[0]}_)\n"
                total_entrada += valor
            else:
                extrato += f"🔴 - R$ {valor:.2f} | {desc} (_{data.split()[0]}_)\n"
                total_saida += valor
        extrato += f"\n🔹 *Total Entradas:* R$ {total_entrada:.2f}\n🔸 *Total Saídas:* R$ {total_saida:.2f}\n💰 *Saldo Atual:* R$ {total_entrada - total_saida:.2f}"
        return extrato
    except Exception as e: return f"❌ Erro ao gerar extrato: {e}"

def acao_salvar_lembrete(user_id, tarefa, data_hora):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO lembretes (telegram_id, tarefa, data_hora) VALUES (?, ?, ?)', (user_id, tarefa, data_hora))
        conn.commit()
        conn.close()
        return f"⏰ [Lembrete Agendado] Eu vou te lembrar de: '{tarefa}' em: {data_hora}."
    except Exception as e: return f"❌ Erro ao salvar lembrete: {e}"

# 🌐 BUSCA ROBUSTA NA WEB
def acao_buscar_web(termo):
    try:
        url = f"https://html.duckduckgo.com/html/?q={termo}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, 'html.parser')
            snippets = [div.get_text() for div in soup.find_all('div', class_='result__snippet')][:4]
            if snippets:
                return "\n\n".join(snippets)
        return "Nenhum resultado em tempo real pôde ser parseado no momento."
    except Exception as e: 
        return f"Erro de conexão com o motor de busca: {e}"

def acao_admin_clientes(comando, id_alvo, nome_alvo=None):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        if comando == "ATIVAR":
            cursor.execute('''
                INSERT INTO clientes (telegram_id, nome, status) VALUES (?, ?, 'ativo')
                ON CONFLICT(telegram_id) DO UPDATE SET status='ativo', nome=COALESCE(?, nome)
            ''', (id_alvo, nome_alvo, nome_alvo))
            conn.commit()
            msg = f"🟢 *Cliente Ativado com Sucesso!*\n👤 *Nome:* {nome_alvo}\n🆔 *ID:* `{id_alvo}`"
        elif comando == "BLOQUEAR":
            cursor.execute('UPDATE clientes SET status="bloqueado" WHERE telegram_id=?', (id_alvo,))
            conn.commit()
            msg = f"🔴 *Acesso Bloqueado!*\n🆔 O ID `{id_alvo}` foi removido da lista de autorizados."
        elif comando == "LISTAR":
            cursor.execute('SELECT telegram_id, nome, status FROM clientes')
            linhas = cursor.fetchall()
            if not linhas: msg = "📋 Nenhum cliente cadastrado no sistema ainda."
            else:
                msg = "📋 *Painel de Clientes Fire iA:*\n\n"
                for tid, nome, status in linhas:
                    icone = "🟢" if status == 'ativo' else "🔴"
                    msg += f"{icone} *{nome}* - ID: `{tid}` (_{status}_)\n"
        conn.close()
        return msg
    except Exception as e: return f"❌ Erro adm: {e}"

@bot.message_handler(commands=['start'])
def boas_vindas(message):
    user_id = message.from_user.id
    if not usuario_autorizado(user_id):
        bot.send_message(message.chat.id, f"❌ *Acesso Restrito!*\n\nEnvie seu ID ao admin:\n🆔 *Seu ID:* `{user_id}`", parse_mode="Markdown")
        return
    nome = message.from_user.first_name if message.from_user.first_name else "Cliente"
    texto = (
        f"🔥 *Bem-vindo ao Fire iA, {nome}!* 🔥\n\n"
        "Eu sou o seu assistente central de Inteligência Artificial, operando **100% por conversa natural**, sem botões! Tenho memória de contexto e as seguintes funções:\n\n"
        "📚 *Professor Particular:* Resolução didática de fotos de tarefas escolares.\n"
        "🧮 *Super Calculadora:* Contas complexas ou lógicas na hora.\n"
        "🎙️ *Comandos por Voz:* Entendo perfeitamente áudios.\n"
        "💰 *Fluxo de Caixa:* Fale suas movimentações de dinheiro e peça seu 'extrato mensal'.\n"
        "⏰ *Lembretes:* Agende avisos e tarefas.\n"
        "🔍 *Pesquisa na Web:* Busco fatos atuais, notícias e resultados na internet em tempo real.\n\n"
        "Como posso te ajudar agora? Pode falar!"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def tratar_foto(message):
    if not usuario_autorizado(message.from_user.id): return
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        bot.send_chat_action(message.chat.id, 'typing')
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": [{"type": "text", "text": "Resolva a imagem."}, {"type": "image_url", "image_url": {"url": file_url}}]}]
        )
        bot.reply_to(message, response.choices[0].message.content)
    except: bot.reply_to(message, "🔥 Erro ao processar imagem.")

@bot.message_handler(content_types=['voice'])
def tratar_voz(message):
    if not usuario_autorizado(message.from_user.id): return
    try:
        file_info = bot.get_file(message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        audio_data = requests.get(file_url).content
        nome_arquivo = f"voice_{message.message_id}.ogg"
        with open(nome_arquivo, "wb") as f: f.write(audio_data)
        with open(nome_arquivo, "rb") as audio_file:
            transcricao = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        os.remove(nome_arquivo)
        message.text = transcricao.text
        tratar_texto(message)
    except: bot.reply_to(message, "🔥 Não consegui processar o áudio.")

@bot.message_handler(content_types=['text'])
def tratar_texto(message):
    user_id = message.from_user.id
    if not usuario_autorizado(user_id): return
        
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        eh_admin = "SIM" if user_id == ID_ADMIN_ALEXANDRE else "NÃO"
        texto_usuario = message.text.lower()
        
        # 🔥 INTERCEPTADOR MANUAl DE BUSCA WEB
        palavras_busca = ["pesquisa", "busque", "procure", "quem ganhou", "noticia", "na internet", "no google", "sobre o", "sobre a"]
        precisa_buscar = any(p in texto_usuario for p in palavras_busca)
        
        dados_da_internet = ""
        if precisa_buscar:
            print(f"🌐 [BUSCA INTERNA] Executando pesquisa para: {message.text}")
            dados_da_internet = acao_buscar_web(message.text)
        
        salvar_na_memoria(user_id, "user", message.text)
        historico_contexto = buscar_memoria_usuario(user_id, limite=12)
        
        prompt_sistema = {
            "role": "system",
            "content": (
                f"Você é o Fire iA, focado em conversa natural e intuitiva.\n"
                f"O usuário atual é o Admin Alexandre? {eh_admin} (ID: {user_id}).\n"
                f"ANO ATUAL: 2026. Responda tudo com base nisso.\n\n"
                f"DADOS EXTRAÍDOS EM TEMPO REAL DA INTERNET (Use isto se o usuário pediu uma busca ou fato atual recente): {dados_da_internet}\n\n"
                "DIRETRIZES DE COMANDOS INTERNOS (Use se identificar a intenção exata):\n"
                "1. Salvar Entrada: [FINANCAS:ENTRADA:valor:descricao]\n"
                "2. Salvar Saída: [FINANCAS:SAIDA:valor:descricao]\n"
                "3. Ver Extrato: [FINANCAS:EXTRATO]\n"
                "4. Criar Lembrete: [LEMBRETE:descricao:data_e_hora]\n\n"
                "PAINEL DE CLIENTES (Apenas se Admin Alexandre for SIM):\n"
                "5. Ativar/Cadastrar: [ADMIN:ATIVAR:id:nome]\n"
                "6. Bloquear: [ADMIN:BLOQUEAR:id]\n"
                "7. Lista Clientes: [ADMIN:LISTAR]"
            )
        }
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[prompt_sistema] + historico_contexto
        )
        
        texto_ia = response.choices[0].message.content
        salvar_na_memoria(user_id, "assistant", texto_ia)
        
        if "[FINANCAS:" in texto_ia:
            if "EXTRATO" in texto_ia: res = acao_gerar_extrato(user_id)
            else:
                partes = texto_ia.replace("[", "").replace("]", "").split(":")
                res = acao_salvar_financa(user_id, partes[1], partes[2], partes[3])
            bot.send_message(message.chat.id, res, parse_mode="Markdown")
        elif "[LEMBRETE:" in texto_ia:
            partes = texto_ia.replace("[", "").replace("]", "").split(":")
            res = acao_salvar_lembrete(user_id, partes[1], partes[2])
            bot.send_message(message.chat.id, res)
        elif "[ADMIN:" in texto_ia and eh_admin == "SIM":
            partes = texto_ia.replace("[", "").replace("]", "").split(":")
            comando_adm = partes[1]
            if comando_adm == "LISTAR": res_adm = acao_admin_clientes("LISTAR", 0)
            elif comando_adm == "BLOQUEAR": res_adm = acao_admin_clientes("BLOQUEAR", int(partes[2]))
            else: res_adm = acao_admin_clientes("ATIVAR", int(partes[2]), partes[3])
            bot.send_message(message.chat.id, res_adm, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, texto_ia, parse_mode="Markdown")
            
    except Exception as e:
        print(e)
        bot.reply_to(message, "🔥 Instabilidade temporária.")

print("🔥 [SISTEMA] Escutando o Telegram...")
while True:
    try: bot.polling(none_stop=True, timeout=60)
    except: pass
