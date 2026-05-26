import os
import sqlite3
import requests
import telebot
from openai import OpenAI
from datetime import datetime

# 1. CONFIGURAÇÃO DE SEGREDOS DA FLY.IO
TOKEN_TELEGRAM = os.environ.get('TELEGRAM_TOKEN')
CHAVE_OPENAI = os.environ.get('GEMINI_API_KEY') # Sua chave OpenAI salva como GEMINI_API_KEY

print("🔥 [SISTEMA] Inicializando Fire iA com todas as funções ativas...")

bot = telebot.TeleBot(TOKEN_TELEGRAM)
client = OpenAI(api_key=CHAVE_OPENAI)

ID_ADMIN_ALEXANDRE = 5435085592 

# 2. INICIALIZAÇÃO COMPLETA DO BANCO DE DADOS (Finanças, Clientes e Lembretes)
def iniciar_banco():
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        # Tabela de Finanças
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
        # Tabela de Clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                telegram_id INTEGER PRIMARY KEY,
                nome TEXT,
                status TEXT DEFAULT 'ativo'
            )
        ''')
        # Tabela de Lembretes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lembretes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                tarefa TEXT,
                data_hora TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("🔥 [SISTEMA] Banco de dados SQLite 100% operacional.")
    except Exception as e:
        print(f"❌ [ERRO BANCO] {e}")

iniciar_banco()

# ----------------------------------------------------------------------
# INTERCEPTOR DE SEGURANÇA (Verifica se o usuário está bloqueado)
# ----------------------------------------------------------------------
def usuario_bloqueado(user_id):
    if user_id == ID_ADMIN_ALEXANDRE:
        return False
    conn = sqlite3.connect('fire_ia_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM clientes WHERE telegram_id=?', (user_id,))
    resultado = cursor.fetchone()
    conn.close()
    if resultado and resultado[0] == 'bloqueado':
        return True
    return False

# ----------------------------------------------------------------------
# FERRAMENTAS DO SISTEMA (Ações reais disparadas pela IA)
# ----------------------------------------------------------------------
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
    except Exception as e:
        return f"❌ Erro ao salvar finança: {e}"

def acao_gerar_extrato(user_id):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT tipo, valor, descricao, data FROM financas WHERE telegram_id=?', (user_id,))
        linhas = cursor.fetchall()
        conn.close()
        if not linhas: return "📊 Você ainda não possui movimentações financeiras registradas."
        
        extrato = "📊 *Seu Extrato Mensal Atualizado:*\n\n"
        total_entrada = 0
        total_saida = 0
        for tipo, valor, desc, data in linhas:
            if tipo == "ENTRADA":
                extrato += f"🟢 + R$ {valor:.2f} | {desc} (_{data.split()[0]}_)\n"
                total_entrada += valor
            else:
                extrato += f"🔴 - R$ {valor:.2f} | {desc} (_{data.split()[0]}_)\n"
                total_saida += valor
        saldo = total_entrada - total_saida
        extrato += f"\n🔹 *Total Entradas:* R$ {total_entrada:.2f}\n🔸 *Total Saídas:* R$ {total_saida:.2f}\n💰 *Saldo Atual:* R$ {saldo:.2f}"
        return extrato
    except Exception as e:
        return f"❌ Erro ao gerar extrato: {e}"

def acao_salvar_lembrete(user_id, tarefa, data_hora):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO lembretes (telegram_id, tarefa, data_hora) VALUES (?, ?, ?)', (user_id, tarefa, data_hora))
        conn.commit()
        conn.close()
        return f"⏰ [Lembrete Agendado] Eu vou te lembrar de: '{tarefa}' na data/hora: {data_hora}."
    except Exception as e:
        return f"❌ Erro ao salvar lembrete: {e}"

def acao_buscar_web(termo):
    try:
        url = f"https://html.duckduckgo.com/html/?q={termo}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, 'html.parser')
            snippets = [div.get_text() for div in soup.find_all('div', class_='result__snippet')][:3]
            return "\n".join(snippets) if snippets else "Sem resultados detalhados encontrados."
    except:
        return "O serviço de pesquisa web está instável no momento."

# 👑 FUNÇÕES DA IA PARA GERENCIAMENTO DE CLIENTES (Via conversa natural)
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
            msg = f"🟢 Cliente com ID `{id_alvo}` foi Ativado/Cadastrado com sucesso."
        elif comando == "BLOQUEAR":
            cursor.execute('UPDATE clientes SET status="bloqueado" WHERE telegram_id=?', (id_alvo,))
            conn.commit()
            msg = f"🔴 Cliente com ID `{id_alvo}` foi Bloqueado com sucesso."
        elif comando == "LISTAR":
            cursor.execute('SELECT telegram_id, nome, status FROM clientes')
            linhas = cursor.fetchall()
            if not linhas: msg = "📋 Nenhum cliente registrado no sistema."
            else:
                msg = "📋 *Painel de Clientes Fire iA:*\n\n"
                for tid, nome, status in linhas:
                    status_icon = "🟢" if status == 'ativo' else "🔴"
                    msg += f"{status_icon} *{nome}* - ID: `{tid}` ({status})\n"
        conn.close()
        return msg
    except Exception as e:
        return f"❌ Erro no gerenciamento de clientes: {e}"

# ----------------------------------------------------------------------
# 👋 MÓDULO: BOAS-VINDAS (/start)
# ----------------------------------------------------------------------
@bot.message_handler(commands=['start'])
def boas_vindas(message):
    if usuario_bloqueado(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Seu acesso está suspenso.")
        return
    
    nome = message.from_user.first_name if message.from_user.first_name else "Cliente"
    texto = (
        f"🔥 *Bem-vindo ao Fire iA, {nome}!* 🔥\n\n"
        "Eu sou a sua Inteligência Artificial central, operando **100% por conversa natural**, sem botões poluindo a tela! Olha tudo o que você pode fazer por aqui:\n\n"
        "📚 *Professor Particular:* Tire foto de qualquer lição de escola ou faculdade e eu resolvo explicando o passo a passo.\n"
        "🧮 *Super Calculadora:* Mande qualquer tipo de conta matemática complexa ou simples.\n"
        "🎙️ *Comandos por Voz:* Pode falar por áudio que eu entendo e executo tudo.\n"
        "💰 *Fluxo de Caixa:* Fale suas movimentações de dinheiro (Ex: 'Recebi 150 reais da venda' ou 'Gastei 40 com almoço') e peça seu 'extrato mensal' quando quiser.\n"
        "⏰ *Lembretes:* Me peça para te lembrar de coisas relevantes (Ex: 'Me lembre de pagar a conta amanhã às 14h').\n"
        "🔍 *Pesquisa na Web:* Pergunte sobre notícias do mundo ou fatos em tempo real.\n\n"
        "👑 *Para o Admin Alexandre:* Você pode gerenciar seus clientes mandando mensagens naturais como 'Ative o cliente 12345 nome Pedro' ou 'Me mostre a lista de clientes'.\n\n"
        "Como posso te ajudar agora? Pode falar!"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

# 👁️ FUNÇÃO 1: RECONHECIMENTO DE FOTOS (TAREFAS ESCOLARES / DOCUMENTOS)
@bot.message_handler(content_types=['photo'])
def tratar_foto(message):
    if usuario_bloqueado(message.from_user.id): return
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        bot.send_chat_action(message.chat.id, 'typing')
        
        prompt_visao = (
            "Você é o Fire iA. Se a imagem contiver uma tarefa escolar, conta, exercício ou prova, "
            "resolva tudo perfeitamente fornecendo o passo a passo didático explicativo para o estudante aprender. "
            "Se for outro tipo de foto ou documento, analise e descreva com altíssima qualidade."
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt_visao}, {"type": "image_url", "image_url": {"url": file_url}}]}]
        )
        bot.reply_to(message, response.choices[0].message.content)
    except Exception as e:
        bot.reply_to(message, "🔥 Erro ao processar a imagem. Envie novamente.")

# 🎙️ FUNÇÃO 2: RECONHECIMENTO DE VOZ (WHISPER)
@bot.message_handler(content_types=['voice'])
def tratar_voz(message):
    if usuario_bloqueado(message.from_user.id): return
    try:
        file_info = bot.get_file(message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        audio_data = requests.get(file_url).content
        nome_arquivo = f"voice_{message.message_id}.ogg"
        with open(nome_arquivo, "wb") as f: f.write(audio_data)
            
        bot.send_chat_action(message.chat.id, 'typing')
        with open(nome_arquivo, "rb") as audio_file:
            transcricao = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        os.remove(nome_arquivo)
        
        message.text = transcricao.text
        tratar_texto(message)
    except:
        bot.reply_to(message, "🔥 Não consegui decifrar seu áudio.")

# 🧠 FUNÇÃO 3: CÉREBRO DA IA 100% NATURAL (CONVERSA, CONTAS, EXTRATOS, BUSCA E ADMIN)
@bot.message_handler(content_types=['text'])
def tratar_texto(message):
    if usuario_bloqueado(message.from_user.id): return
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        user_id = message.from_user.id
        eh_admin = "SIM" if user_id == ID_ADMIN_ALEXANDRE else "NÃO"
        
        prompt_sistema = (
            f"Você é o Fire iA, focado em conversa natural e intuitiva. Nunca use botões.\n"
            f"O usuário atual é o Admin Alexandre? {eh_admin} (ID: {user_id}).\n\n"
            "DIRETRIZES DE COMANDOS INTERNOS (Se identificar uma dessas intenções no texto do usuário, responda EXATAMENTE com a tag estruturada correspondente):\n"
            "1. Salvar Entrada: [FINANCAS:ENTRADA:valor:descricao]\n"
            "2. Salvar Saída: [FINANCAS:SAIDA:valor:descricao]\n"
            "3. Ver Extrato Financeiro: [FINANCAS:EXTRATO]\n"
            "4. Criar Lembrete: [LEMBRETE:descricao_da_tarefa:data_e_hora]\n"
            "5. Pesquisa na Web: [BUSCA:termo_para_buscar_na_internet]\n\n"
            "PAINEL DE CLIENTES (Apenas se Admin Alexandre for SIM):\n"
            "6. Ativar/Cadastrar Cliente: [ADMIN:ATIVAR:id_do_cliente:nome_do_cliente]\n"
            "7. Bloquear/Cortar Acesso: [ADMIN:BLOQUEAR:id_do_cliente]\n"
            "8. Ver Lista de Clientes: [ADMIN:LISTAR]\n\n"
            "Se o usuário estiver apenas conversando ou pedindo contas matemáticas, resolva diretamente de forma clara e profissional."
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt_sistema}, {"role": "user", "content": message.text}]
        )
        
        texto_ia = response.choices[0].message.content
        
        if "[FINANCAS:" in texto_ia:
            if "EXTRATO" in texto_ia:
                res_financa = acao_gerar_extrato(user_id)
            else:
                partes = texto_ia.replace("[", "").replace("]", "").split(":")
                res_financa = acao_salvar_financa(user_id, partes[1], partes[2], partes[3])
            bot.send_message(message.chat.id, res_financa, parse_mode="Markdown")
            
        elif "[LEMBRETE:" in texto_ia:
            partes = texto_ia.replace("[", "").replace("]", "").split(":")
            res_lembrete = acao_salvar_lembrete(user_id, partes[1], partes[2])
            bot.send_message(message.chat.id, res_lembrete)
            
        elif "[BUSCA:" in texto_ia:
            termo = texto_ia.split("[BUSCA:")[1].split("]")[0]
            dados_da_internet = acao_buscar_web(termo)
            resposta_final_web = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Você é o Fire iA. Formate e explique essa informação extraída em tempo real da internet: {dados_da_internet}"},
                    {"role": "user", "content": message.text}
                ]
            )
            bot.send_message(message.chat.id, resposta_final_web.choices[0].message.content, parse_mode="Markdown")
            
        elif "[ADMIN:" in texto_ia:
            partes = texto_ia.replace("[", "").replace("]", "").split(":")
            comando_adm = partes[1]
            if comando_adm == "LISTAR":
                res_adm = acao_admin_clientes("LISTAR", 0)
            elif comando_adm == "BLOQUEAR":
                res_adm = acao_admin_clientes("BLOQUEAR", int(partes[2]))
            else:
                res_adm = acao_admin_clientes("ATIVAR", int(partes[2]), partes[3])
            bot.send_message(message.chat.id, res_adm, parse_mode="Markdown")
            
        else:
            bot.send_message(message.chat.id, texto_ia, parse_mode="Markdown")
            
    except Exception as e:
        bot.reply_to(message, "🔥 Meu processamento encontrou uma instabilidade temporária.")

print("🔥 [SISTEMA] Escutando o Telegram via Polling Contínuo...")

while True:
    try:
        bot.polling(none_stop=True, timeout=60)
    except:
        pass
