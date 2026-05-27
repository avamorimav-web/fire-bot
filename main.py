import os
import sqlite3
import json
import requests
import telebot
from openai import OpenAI
from datetime import datetime

# ======================================================================
# 1. CONFIGURAÇÕES INICIAIS E ENV
# ======================================================================
TOKEN_TELEGRAM = os.environ.get('TELEGRAM_TOKEN')
CHAVE_OPENAI = os.environ.get('GEMINI_API_KEY')

print("🔥 [SISTEMA] Iniciando Fire iA v4 - Versão de Recuperação...")

bot = telebot.TeleBot(TOKEN_TELEGRAM)
client = OpenAI(api_key=CHAVE_OPENAI)

ID_ADMIN_ALEXANDRE = 5435085592

# ======================================================================
# 2. BANCO DE DADOS (SQLITE)
# ======================================================================
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
                data_hora TEXT,
                status TEXT DEFAULT 'pendente'
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
        print("🔥 [BANCO DE DADOS] Base inicializada com sucesso.")
    except Exception as e:
        print(f"❌ [ERRO BANCO] Falha ao iniciar: {e}")

iniciar_banco()

# ======================================================================
# 3. GESTÃO DE MEMÓRIA DO CHAT
# ======================================================================
def salvar_na_memoria(user_id, papel, texto):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO historico_conversas (telegram_id, role, content) VALUES (?, ?, ?)', (user_id, papel, texto))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ [ERRO MEMÓRIA] {e}")

def buscar_memoria_usuario(user_id, limite=15):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT role, content FROM historico_conversas WHERE telegram_id = ? ORDER BY data DESC LIMIT ?', (user_id, limite))
        linhas = cursor.fetchall()
        conn.close()
        return [{"role": p, "content": c} for p, c in reversed(linhas)]
    except Exception as e:
        print(f"❌ [ERRO MEMÓRIA CHAT] {e}")
        return []

# ======================================================================
# 4. CONTROLE DE ACESSO (SEGURANÇA)
# ======================================================================
def trava_seguranca(funcao):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        if user_id == ID_ADMIN_ALEXANDRE:
            return funcao(message, *args, **kwargs)
            
        try:
            conn = sqlite3.connect('fire_ia_data.db')
            cursor = conn.cursor()
            cursor.execute('SELECT status FROM clientes WHERE telegram_id=?', (user_id,))
            resultado = cursor.fetchone()
            conn.close()
            
            if resultado and resultado[0] == 'ativo':
                return funcao(message, *args, **kwargs)
        except Exception as e:
            print(f"❌ [ERRO TRAVA] {e}")
            
        msg = f"❌ *Acesso Restrito!*\n\nSeu perfil não está autorizado.\n🆔 *Seu ID:* `{user_id}`"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        return
    return wrapper

# ======================================================================
# 5. EXECUÇÃO DE FUNÇÕES INTERNAS (NÚCLEO)
# ======================================================================
def pesquisar_internet(termo):
    try:
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(termo)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, 'lxml')
            
            resultados = []
            for item in soup.find_all('div', class_='result__body'):
                snippet = item.find('a', class_='result__snippet')
                if snippet:
                    resultados.append(snippet.get_text().strip())
            
            if resultados:
                return "\n\n".join(resultados[:4])
                
        wiki_url = f"https://pt.wikipedia.org/w/api.php?action=query&list=search&srsearch={requests.utils.quote(termo)}&format=json"
        wiki_res = requests.get(wiki_url, timeout=10).json()
        if "query" in wiki_res and wiki_res["query"]["search"]:
            snippets = [item["snippet"].replace('<span class="searchmatch">', '').replace('</span>', '') for item in wiki_res["query"]["search"]]
            return "Resultados alternativos (Wiki/Web):\n\n" + "\n\n".join(snippets[:3])
            
        return f"Não foi possível extrair dados em tempo real para: '{termo}'. Use seu conhecimento prévio para responder da melhor forma possível."
    except Exception as e:
        return f"Erro ao acessar a rede: {e}. Responda com base no seu conhecimento operacional."

def gerenciar_financa(user_id, tipo, valor, descricao):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO financas (telegram_id, tipo, valor, descricao, data) VALUES (?, ?, ?, ?, ?)',
                       (user_id, tipo.upper(), float(valor), descricao, data_atual))
        conn.commit()
        conn.close()
        return f"💰 *[Sucesso]* R$ {float(valor):.2f} em {tipo.upper()} ({descricao})."
    except Exception as e:
        return f"❌ Erro nas finanças: {e}"

def consultar_extrato(user_id):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT tipo, valor, descricao, data FROM financas WHERE telegram_id=?', (user_id,))
        linhas = cursor.fetchall()
        conn.close()
        
        if not linhas:
            return "📊 Nenhuma movimentação registrada."
            
        extrato = "📊 *Seu Extrato:* \n\n"
        ent = sai = 0
        for t, v, d, dt in linhas:
            limpa = dt.split()[0]
            if t == "ENTRADA":
                extrato += f"🟢 + R$ {v:.2f} | {d} ({limpa})\n"
                ent += v
            else:
                extrato += f"🔴 - R$ {v:.2f} | {d} ({limpa})\n"
                sai += v
        extrato += f"\n🔹 Entradas: R$ {ent:.2f}\n🔸 Saídas: R$ {sai:.2f}\n💰 Saldo: R$ {ent-sai:.2f}"
        return extrato
    except Exception as e:
        return f"❌ Erro no extrato: {e}"

def agendar_lembrete(user_id, tarefa, data_hora):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO lembretes (telegram_id, tarefa, data_hora) VALUES (?, ?, ?)', (user_id, tarefa, data_hora))
        conn.commit()
        conn.close()
        return f"⏰ *[Lembrete Agendado]*\n📝 Tarefa: {tarefa}\n📅 Data: {data_hora}"
    except Exception as e:
        return f"❌ Erro no lembrete: {e}"

def gerenciar_painel_adm(comando, id_alvo, nome_alvo=None):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        msg = ""
        
        if comando == "ATIVAR":
            cursor.execute('''
                INSERT INTO clientes (telegram_id, nome, status) VALUES (?, ?, 'ativo')
                ON CONFLICT(telegram_id) DO UPDATE SET status='ativo', nome=COALESCE(?, nome)
            ''', (id_alvo, nome_alvo, nome_alvo))
            conn.commit()
            msg = f"🟢 *Acesso Ativado:* {nome_alvo} (ID: `{id_alvo}`)"
        elif comando == "BLOQUEAR":
            cursor.execute('UPDATE clientes SET status="bloqueado" WHERE telegram_id=?', (id_alvo,))
            conn.commit()
            msg = f"🔴 *Acesso Bloqueado:* ID `{id_alvo}`"
        elif comando == "LISTAR":
            cursor.execute('SELECT telegram_id, nome, status FROM clientes')
            linhas = cursor.fetchall()
            if not linhas:
                msg = "📋 Nenhum cliente registrado."
            else:
                msg = "📋 *Clientes Cadastrados:*\n\n"
                for tid, nome, status in linhas:
                    icon = "🟢" if status == 'ativo' else "🔴"
                    msg += f"{icon} *{nome}* - ID: `{tid}` ({status})\n"
        conn.close()
        return msg
    except Exception as e:
        return f"❌ Erro no painel adm: {e}"

# ======================================================================
# 6. ARQUITETURA DE MODELOS (TOOLS)
# ======================================================================
FERRAMENTAS_FIRE = [
    {
        "type": "function",
        "function": {
            "name": "pesquisar_internet",
            "description": "Busca informações atualizadas e em tempo real na internet.",
            "parameters": {
                "type": "object",
                "properties": {"termo": {"type": "string"}},
                "required": ["termo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gerenciar_financa",
            "description": "Registra uma nova movimentação de entrada ou saída financeira.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {"type": "string", "enum": ["entrada", "saida"]},
                    "valor": {"type": "number"},
                    "descricao": {"type": "string"}
                },
                "required": ["tipo", "valor", "descricao"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_extrato",
            "description": "Exibe o saldo e movimentações financeiras.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "agendar_lembrete",
            "description": "Agenda uma tarefa ou aviso para o usuário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tarefa": {"type": "string"},
                    "data_hora": {"type": "string"}
                },
                "required": ["tarefa", "data_hora"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gerenciar_painel_adm",
            "description": "Painel de controle de clientes (Exclusivo Admin Alexandre).",
            "parameters": {
                "type": "object",
                "properties": {
                    "comando": {"type": "string", "enum": ["ATIVAR", "BLOQUEAR", "LISTAR"]},
                    "id_alvo": {"type": "integer"},
                    "nome_alvo": {"type": "string"}
                },
                "required": ["comando", "id_alvo"]
            }
        }
    }
]

# ======================================================================
# 7. EVENTOS TELEGRAM
# ======================================================================
@bot.message_handler(commands=['start'])
@trava_seguranca
def boas_vindas(message):
    nome = message.from_user.first_name if message.from_user.first_name else "Cliente"
    texto = (
        f"🔥 *Bem-vindo ao Fire iA, {nome}!* 🔥\n\n"
        "Estou pronto e operando por linguagem natural. Funções disponíveis:\n"
        "📚 Envio de fotos com visão computacional para responder tarefas.\n"
        "🎙️ Comandos diretos por áudio.\n"
        "💰 Fluxo de caixa completo e gerenciamento de lembretes.\n"
        "🔍 Consultas em tempo real na internet."
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
@trava_seguranca
def tratar_foto(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        f_id = message.photo[-1].file_id
        f_info = bot.get_file(f_id)
        f_url = f"https://api.telegram.org/file/bot{bot.token}/{f_info.file_path}"
        
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": [{"type": "text", "text": "Analise a imagem a seguir:"}, {"type": "image_url", "image_url": {"url": f_url}}]}]
        )
        bot.reply_to(message, res.choices[0].message.content)
    except Exception as e:
        print(f"❌ [ERRO IMAGEM] {e}")
        bot.reply_to(message, "🔥 Falha ao processar arquivo de imagem.")

@bot.message_handler(content_types=['voice'])
@trava_seguranca
def tratar_voz(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        f_info = bot.get_file(message.voice.file_id)
        f_url = f"https://api.telegram.org/file/bot{bot.token}/{f_info.file_path}"
        audio = requests.get(f_url).content
        
        nome = f"v_{message.message_id}.ogg"
        with open(nome, "wb") as f:
            f.write(audio)
            
        with open(nome, "rb") as af:
            trans = client.audio.transcriptions.create(model="whisper-1", file=af)
            
        os.remove(nome)
        message.text = trans.text
        tratar_texto(message)
    except Exception as e:
        print(f"❌ [ERRO VOZ] {e}")
        bot.reply_to(message, "🔥 Falha ao ler arquivo de áudio.")

@bot.message_handler(content_types=['text'])
@trava_seguranca
def tratar_texto(message):
    user_id = message.from_user.id
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        eh_admin = "SIM" if user_id == ID_ADMIN_ALEXANDRE else "NÃO"
        dt_atual = datetime.now().strftime("%A, %d de %B de %Y - %H:%M:%S")
        
        salvar_na_memoria(user_id, "user", message.text)
        hist = buscar_memoria_usuario(user_id, limite=15)
        
        sys_prompt = {
            "role": "system",
            "content": (
                f"Você é o Fire iA, assistente inteligente criado pelo Admin Alexandre.\n"
                f"O usuário atual é o Admin Alexandre? {eh_admin} (ID: {user_id}).\n"
                f"DATA DO SERVIDOR: {dt_atual}.\n\n"
                "Regras:\n"
                "1. Sempre acione a ferramenta 'pesquisar_internet' quando o usuário pedir fatos recentes, notícias do dia ou buscas externas.\n"
                "2. 'gerenciar_painel_adm' é estritamente restrito ao criador Alexandre.\n"
                "3. Responda em Markdown estruturado e de forma natural."
            )
        }
        
        ctx = [sys_prompt] + hist
        
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=ctx,
            tools=FERRAMENTAS_FIRE,
            tool_choice="auto"
        )
        
        msg_obj = res.choices[0].message
        calls = msg_obj.tool_calls
        
        if calls:
            ctx.append(msg_obj)
            for call in calls:
                f_name = call.function.name
                args = json.loads(call.function.arguments)
                ret = ""
                
                if f_name == "pesquisar_internet":
                    ret = pesquisar_internet(args.get("termo"))
                elif f_name == "gerenciar_financa":
                    ret = gerenciar_financa(user_id, args.get("tipo"), args.get("valor"), args.get("descricao"))
                elif f_name == "consultar_extrato":
                    ret = consultar_extrato(user_id)
                elif f_name == "agendar_lembrete":
                    ret = agendar_lembrete(user_id, args.get("tarefa"), args.get("data_hora"))
                elif f_name == "gerenciar_painel_adm":
                    if eh_admin == "SIM":
                        ret = gerenciar_painel_adm(args.get("comando"), args.get("id_alvo"), args.get("nome_alvo"))
                    else:
                        ret = "❌ Erro: Função restrita ao administrador."
                        
                ctx.append({
                    "tool_call_id": call.id,
                    "role": "tool",
                    "name": f_name,
                    "content": ret
                })
                
            final_res = client.chat.completions.create(model="gpt-4o-mini", messages=ctx)
            txt = final_res.choices[0].message.content
            bot.send_message(message.chat.id, txt, parse_mode="Markdown")
            salvar_na_memoria(user_id, "assistant", txt)
        else:
            txt = msg_obj.content
            bot.send_message(message.chat.id, txt, parse_mode="Markdown")
            salvar_na_memoria(user_id, "assistant", txt)
            
    except Exception as e:
        print(f"❌ [ERRO FLUXO CORE] {e}")
        bot.reply_to(message, "🔥 Instabilidade interna encontrada.")

# ======================================================================
# 8. POLLING
# ======================================================================
print("🔥 [SISTEMA] Escutando requisições do Telegram...")
while True:
    try:
        bot.polling(none_stop=True, timeout=60, long_polling_timeout=30)
    except Exception as ep:
        print(f"⚠️ [REBOOT] Reiniciando loop: {ep}")
