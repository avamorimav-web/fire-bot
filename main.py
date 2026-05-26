import os
import sqlite3
import requests
import telebot
from openai import OpenAI
from datetime import datetime

# 1. CONFIGURAÇÃO DE SEGREDOS DA FLY.IO
TOKEN_TELEGRAM = os.environ.get('TELEGRAM_TOKEN')
CHAVE_OPENAI = os.environ.get('GEMINI_API_KEY') 

print("🔥 [SISTEMA] Inicializando Fire iA no MODELO RESTRITO com Saudação Comercial...")

bot = telebot.TeleBot(TOKEN_TELEGRAM)
client = OpenAI(api_key=CHAVE_OPENAI)

ID_ADMIN_ALEXANDRE = 5435085592 

# 2. INICIALIZAÇÃO DO BANCO DE DADOS COMPLETO
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
        # Tabela de Memória (Histórico de Conversa)
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
        print("🔥 [SISTEMA] Banco de dados com Memória e Segurança máxima ativado.")
    except Exception as e:
        print(f"❌ [ERRO BANCO] {e}")

iniciar_banco()

# ----------------------------------------------------------------------
# FUNÇÕES DE GERENCIAMENTO DE MEMÓRIA (NUVEM DO FIRE IA)
# ----------------------------------------------------------------------
def salvar_na_memoria(user_id, papel, texto):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO historico_conversas (telegram_id, role, content) VALUES (?, ?, ?)', (user_id, papel, texto))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao salvar memória: {e}")

def buscar_memoria_usuario(user_id, limite=10):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT role, content FROM historico_conversas WHERE telegram_id = ? ORDER BY data DESC LIMIT ?', (user_id, limite))
        linhas = cursor.fetchall()
        conn.close()
        
        mensagens = []
        for papel, conteudo in reversed(linhas):
            mensagens.append({"role": papel, "content": conteudo})
        return mensagens
    except Exception as e:
        print(f"❌ Erro ao buscar memória: {e}")
        return []

# ----------------------------------------------------------------------
# TRAVA DE SEGURANÇA MÁXIMA (MODELO RESTRITO)
# ----------------------------------------------------------------------
def usuario_autorizado(user_id):
    if user_id == ID_ADMIN_ALEXANDRE:
        return True
        
    conn = sqlite3.connect('fire_ia_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM clientes WHERE telegram_id=?', (user_id,))
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado and resultado[0] == 'ativo':
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
    except Exception as e: return f"❌ Erro ao salvar finança: {e}"

def acao_gerar_extrato(user_id):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT tipo, valor, descricao, data FROM financas WHERE telegram_id=?', (user_id,))
        linhas = cursor.fetchall()
        conn.close()
        if not linhas: return "📊 Você ainda não possui movimentações financeiras registradas."
        
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

def acao_buscar_web(termo):
    try:
        url = f"https://html.duckduckgo.com/html/?q={termo}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, 'html.parser')
            snippets = [div.get_text() for div in soup.find_all('div', class_='result__snippet')][:3]
            return "\n".join(snippets) if snippets else "Sem resultados detalhados."
    except: return "Serviço de busca web instável."

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
    except Exception as e: return f"❌ Erro no gerenciamento de clientes: {e}"

# ----------------------------------------------------------------------
# 👋 MÓDULO: BOAS-VINDAS (/start) - LIMPO E COMERCIAL
# ----------------------------------------------------------------------
@bot.message_handler(commands=['start'])
def boas_vindas(message):
    user_id = message.from_user.id
    
    if not usuario_autorizado(user_id):
        msg_bloqueio = (
            "❌ *Acesso Restrito!*\n\n"
            "Seu perfil não está autorizado a utilizar o sistema do **Fire iA**.\n"
            f"Para solicitar sua liberação, envie o seu número de identificação abaixo para o Administrador:\n\n"
            f"🆔 *Seu ID:* `{user_id}`"
        )
        bot.send_message(message.chat.id, msg_bloqueio, parse_mode="Markdown")
        return

    nome = message.from_user.first_name if message.from_user.first_name else "Cliente"
    texto = (
        f"🔥 *Bem-vindo ao Fire iA, {nome}!* 🔥\n\n"
        "Eu sou a sua Inteligência Artificial central, operando **100% por conversa natural**, sem botões poluindo a tela! E agora tenho memória total para lembrar do contexto de toda a nossa conversa. Olha tudo o que você pode fazer por aqui:\n\n"
        "📚 *Professor Particular:* Tire foto de qualquer lição de escola ou faculdade e eu resolvo explicando o passo a passo de forma didática.\n"
        "🧮 *Super Calculadora:* Mande qualquer tipo de conta matemática complexa ou lógica que eu calculo em tempo real.\n"
        "🎙️ *Comandos por Voz:* Pode falar por áudio que eu entendo e executo tudo o que você mandar.\n"
        "💰 *Fluxo de Caixa:* Fale suas movimentações de dinheiro (Ex: 'Recebi 150 reais da venda' ou 'Gastei 40 com almoço') e peça seu 'extrato mensal' quando quiser.\n"
        "⏰ *Lembretes:* Me peça para te lembrar de coisas relevantes (Ex: 'Me lembre de enviar o relatório amanhã às 14h').\n"
        "🔍 *Pesquisa na Web:* Pergunte sobre notícias do mundo, cotações ou fatos atuais que eu busco na internet na hora.\n\n"
        "Como posso te ajudar agora? Pode falar!"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

# 👁️ FUNÇÃO 1: RECONHECIMENTO DE FOTOS
@bot.message_handler(content_types=['photo'])
def tratar_foto(message):
    if not usuario_autorizado(message.from_user.id):
        bot.reply_to(message, "❌ Seu acesso está bloqueado. Fale com o administrador.")
        return
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        bot.send_chat_action(message.chat.id, 'typing')
        
        prompt_visao = "Você é o Fire iA. Resolva a tarefa escolar desta imagem com o passo a passo ou descreva o documento perfeitamente."
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt_visao}, {"type": "image_url", "image_url": {"url": file_url}}]}]
        )
        bot.reply_to(message, response.choices[0].message.content)
    except: bot.reply_to(message, "🔥 Erro ao processar imagem.")

# 🎙️ FUNÇÃO 2: RECONHECIMENTO DE VOZ
@bot.message_handler(content_types=['voice'])
def tratar_voz(message):
    if not usuario_autorizado(message.from_user.id):
        bot.reply_to(message, "❌ Seu acesso está bloqueado. Fale com o administrador.")
        return
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
    except: bot.reply_to(message, "🔥 Não consegui decifrar o áudio.")

# 🧠 FUNÇÃO 3: CÉREBRO PRINCIPAL COM MEMÓRIA PERSISTENTE E TRAVA DE SEGURANÇA
@bot.message_handler(content_types=['text'])
def tratar_texto(message):
    user_id = message.from_user.id
    if not usuario_autorizado(user_id):
        bot.reply_to(message, f"❌ Seu perfil não está autorizado. Passe seu ID para liberação:\n🆔 ID: `{user_id}`", parse_mode="Markdown")
        return
        
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        eh_admin = "SIM" if user_id == ID_ADMIN_ALEXANDRE else "NÃO"
        
        salvar_na_memoria(user_id, "user", message.text)
        historico_contexto = buscar_memoria_usuario(user_id, limite=12)
        
        prompt_sistema = {
            "role": "system",
            "content": (
                f"Você é o Fire iA, focado em conversa natural e intuitiva. Você possui memória das mensagens anteriores da conversa atual.\n"
                f"O usuário atual é o Admin Alexandre? {eh_admin} (ID: {user_id}).\n\n"
                "DIRETRIZES DE COMANDOS INTERNOS (Responda EXATAMENTE com a tag se detectar a intenção):\n"
                "1. Salvar Entrada: [FINANCAS:ENTRADA:valor:descricao]\n"
                "2. Salvar Saída: [FINANCAS:SAIDA:valor:descricao]\n"
                "3. Ver Extrato: [FINANCAS:EXTRATO]\n"
                "4. Criar Lembrete: [LEMBRETE:descricao:data_e_hora]\n"
                "5. Pesquisa na Web: [BUSCA:termo_para_buscar]\n\n"
                "PAINEL DE CLIENTES (Apenas se Admin Alexandre for SIM):\n"
                "6. Ativar/Cadastrar: [ADMIN:ATIVAR:id:nome]\n"
                "7. Bloquear: [ADMIN:BLOQUEAR:id]\n"
                "8. Lista Clientes: [ADMIN:LISTAR]\n\n"
                "Use o histórico de mensagens fornecido para contextualizar as respostas e não agir como se fosse uma primeira interação."
            )
        }
        
        mensagens_completas = [prompt_sistema] + historico_contexto
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=mensagens_completas
        )
        
        texto_ia = response.choices[0].message.content
        salvar_na_memoria(user_id, "assistant", texto_ia)
        
        # 🔥 EXECUÇÃO DAS AÇÕES REAIS LOGICAMENTE DETECTADAS
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
            
        elif "[BUSCA:" in texto_ia:
            termo = texto_ia.split("[BUSCA:")[1].split("]")[0]
            dados_da_internet = acao_buscar_web(termo)
            resposta_final_web = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Você é o Fire iA. Entregue a resposta baseando-se nestes dados reais obtidos da internet: {dados_da_internet}"},
                    {"role": "user", "content": message.text}
                ]
            )
            bot.send_message(message.chat.id, resposta_final_web.choices[0].message.content, parse_mode="Markdown")
            salvar_na_memoria(user_id, "assistant", resposta_final_web.choices[0].message.content)
            
        elif "[ADMIN:" in texto_ia:
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
        bot.reply_to(message, "🔥 Instabilidade temporária no núcleo de memória.")

print("🔥 [SISTEMA] Escutando o Telegram via Polling Contínuo...")

while True:
    try: bot.polling(none_stop=True, timeout=60)
    except: pass
