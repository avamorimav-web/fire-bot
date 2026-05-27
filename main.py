import os
import sqlite3
import json
import requests
import telebot
from openai import OpenAI
from datetime import datetime

# ----------------------------------------------------------------------
# 1. CONFIGURAÇÃO DE SEGREDOS E INICIALIZAÇÃO
# ----------------------------------------------------------------------
TOKEN_TELEGRAM = os.environ.get('TELEGRAM_TOKEN')
CHAVE_OPENAI = os.environ.get('GEMINI_API_KEY') 

print("🔥 [SISTEMA] Inicializando Fire iA v4 - Edição Definitiva Ultra-Robusta...")

bot = telebot.TeleBot(TOKEN_TELEGRAM)
client = OpenAI(api_key=CHAVE_OPENAI)

ID_ADMIN_ALEXANDRE = 5435085592 

# ----------------------------------------------------------------------
# 2. ARQUITETURA DO BANCO DE DADOS (PERSISTÊNCIA CONFIÁVEL)
# ----------------------------------------------------------------------
def iniciar_banco():
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        
        # Fluxo de Caixa / Finanças
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
        # Clientes Autorizados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                telegram_id INTEGER PRIMARY KEY,
                nome TEXT,
                status TEXT DEFAULT 'ativo'
            )
        ''')
        # Lembretes Inteligentes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lembretes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                tarefa TEXT,
                data_hora TEXT,
                status TEXT DEFAULT 'pendente'
            )
        ''')
        # Memória Conversacional
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
        print("🔥 [BANCO DE DADOS] Estrutura verificada e pronta para voar alto.")
    except Exception as e:
        print(f"❌ [ERRO BANCO] Falha crítica ao iniciar banco: {e}")

iniciar_banco()

# ----------------------------------------------------------------------
# 3. NÚCLEO DE MEMÓRIA E GESTÃO DE CONTEXTO
# ----------------------------------------------------------------------
def salvar_na_memoria(user_id, papel, texto):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO historico_conversas (telegram_id, role, content) VALUES (?, ?, ?)', (user_id, papel, texto))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ [ERRO MEMÓRIA] Falha ao salvar mensagem: {e}")

def buscar_memoria_usuario(user_id, limite=15):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT role, content FROM historico_conversas WHERE telegram_id = ? ORDER BY data DESC LIMIT ?', (user_id, limite))
        linhas = cursor.fetchall()
        conn.close()
        return [{"role": papel, "content": conteudo} for papel, conteudo in reversed(linhas)]
    except Exception as e:
        print(f"❌ [ERRO MEMÓRIA] Falha ao ler histórico: {e}")
        return []

# ----------------------------------------------------------------------
# 4. DECORADOR: TRAVA DE SEGURANÇA MÁXIMA (BLINDAGEM NATIVA)
# ----------------------------------------------------------------------
def trava_seguranca(funcao):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        # Se for o Admin Alexandre, acesso garantido e imediato
        if user_id == ID_ADMIN_ALEXANDRE:
            return funcao(message, *args, **kwargs)
            
        # Caso contrário, verifica permissão no banco de clientes
        try:
            conn = sqlite3.connect('fire_ia_data.db')
            cursor = conn.cursor()
            cursor.execute('SELECT status FROM clientes WHERE telegram_id=?', (user_id,))
            resultado = cursor.fetchone()
            conn.close()
            
            if resultado and resultado[0] == 'ativo':
                return funcao(message, *args, **kwargs)
        except Exception as e:
            print(f"❌ [ERRO SEGURANÇA] Falha ao checar permissões: {e}")
            
        # Resposta padrão para perfis não autorizados ou bloqueados
        msg_bloqueio = (
            "❌ *Acesso Restrito!*\n\n"
            "Seu perfil não está autorizado a utilizar o sistema do **Fire iA**.\n"
            "Para solicitar a sua liberação, envie o seu número de identificação abaixo para o Administrador:\n\n"
            f"🆔 *Seu ID:* `{user_id}`"
        )
        bot.send_message(message.chat.id, msg_bloqueio, parse_mode="Markdown")
        return
    return wrapper

# ----------------------------------------------------------------------
# 5. MOTORES DE FUNÇÃO (AÇÕES INTERNAS DO SISTEMA)
# ----------------------------------------------------------------------
def pesquisar_internet(termo):
    try:
        url = f"https://html.duckduckgo.com/html/?q={termo}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, 'html.parser')
            snippets = [div.get_text() for div in soup.find_all('div', class_='result__snippet')][:4]
            if snippets:
                return "\n\n".join(snippets)
        return "Nenhum resultado recente foi encontrado em tempo real para esta busca."
    except Exception as e:
        return f"Falha de conexão ao pesquisar na web: {e}"

def gerenciar_financa(user_id, tipo, valor, descricao):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO financas (telegram_id, tipo, valor, descricao, data) VALUES (?, ?, ?, ?, ?)',
                       (user_id, tipo.upper(), float(valor), descricao, data_atual))
        conn.commit()
        conn.close()
        return f"💰 *[Sucesso]* R$ {float(valor):.2f} registrado com sucesso como {tipo.upper()} ({descricao})."
    except Exception as e:
        return f"❌ Erro interno ao salvar movimentação financeira: {e}"

def consultar_extrato(user_id):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT tipo, valor, descricao, data FROM financas WHERE telegram_id=?', (user_id,))
        linhas = cursor.fetchall()
        conn.close()
        
        if not linhas: 
            return "📊 Você ainda não possui movimentações financeiras registradas no sistema."
            
        extrato = "📊 *Seu Extrato Financeiro Atualizado:*\n\n"
        total_entrada = total_saida = 0
        for tipo, valor, desc, data in linhas:
            data_limpa = data.split()[0]
            if tipo == "ENTRADA":
                extrato += f"🟢 + R$ {valor:.2f} | {desc} (_{data_limpa}_)\n"
                total_entrada += valor
            else:
                extrato += f"🔴 - R$ {valor:.2f} | {desc} (_{data_limpa}_)\n"
                total_saida += valor
                
        saldo = total_entrada - total_saida
        extrato += f"\n🔹 *Total Entradas:* R$ {total_entrada:.2f}\n🔸 *Total Saídas:* R$ {total_saida:.2f}\n💰 *Saldo Geral:* R$ {saldo:.2f}"
        return extrato
    except Exception as e:
        return f"❌ Erro interno ao gerar relatório financeiro: {e}"

def agendar_lembrete(user_id, tarefa, data_hora):
    try:
        conn = sqlite3.connect('fire_ia_data.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO lembretes (telegram_id, tarefa, data_hora) VALUES (?, ?, ?)', (user_id, tarefa, data_hora))
        conn.commit()
        conn.close()
        return f"⏰ *[Lembrete Agendado]*\n📝 *Compromisso:* {tarefa}\n📅 *Data/Hora:* {data_hora}"
    except Exception as e:
        return f"❌ Erro ao registrar lembrete no banco: {e}"

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
            msg = f"🟢 *Acesso Liberado!* O usuário *{nome_alvo}* (ID: `{id_alvo}`) agora está ativo."
        elif comando == "BLOQUEAR":
            cursor.execute('UPDATE clientes SET status="bloqueado" WHERE telegram_id=?', (id_alvo,))
            conn.commit()
            msg = f"🔴 *Acesso Revogado!* O ID `{id_alvo}` foi bloqueado e impedido de usar a IA."
        elif comando == "LISTAR":
            cursor.execute('SELECT telegram_id, nome, status FROM clientes')
            linhas = cursor.fetchall()
            if not linhas:
                msg = "📋 Nenhum cliente registrado na base de dados até o momento."
            else:
                msg = "📋 *Painel de Clientes Autorizados (Fire iA):*\n\n"
                for tid, nome, status in linhas:
                    status_icon = "🟢" if status == 'ativo' else "🔴"
                    msg += f"{status_icon} *{nome}* - ID: `{tid}` (_{status}_)\n"
                    
        conn.close()
        return msg
    except Exception as e:
        return f"❌ Erro no painel administrativo: {e}"

# ----------------------------------------------------------------------
# 6. DEFINIÇÃO NATIVA DAS TOOLS DA API DA OPENAI (FUNCTION CALLING)
# ----------------------------------------------------------------------
FERRAMENTAS_FIRE = [
    {
        "type": "function",
        "function": {
            "name": "pesquisar_internet",
            "description": "Busca informações atualizadas em tempo real na internet sobre notícias, cotações, fatos atuais ou dúvidas gerais.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termo": {"type": "string", "description": "O termo ou frase exata a ser pesquisado na internet."}
                },
                "required": ["termo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gerenciar_financa",
            "description": "Registra uma nova movimentação monetária de entrada ou saída no fluxo de caixa pessoal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {"type": "string", "enum": ["entrada", "saida"], "description": "Se o dinheiro está entrando ou saindo."},
                    "valor": {"type": "number", "description": "O valor numérico exato em reais."},
                    "descricao": {"type": "string", "description": "O motivo ou descrição do gasto ou ganho."}
                },
                "required": ["tipo", "valor", "descricao"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_extrato",
            "description": "Exibe o extrato financeiro completo com todas as entradas, saídas e o saldo total atualizado.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "agendar_lembrete",
            "description": "Agenda uma tarefa, aviso ou compromisso para o usuário no banco de dados do sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tarefa": {"type": "string", "description": "Descrição clara do que deve ser lembrado."},
                    "data_hora": {"type": "string", "description": "Data e horário legível para o agendamento."}
                },
                "required": ["tarefa", "data_hora"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gerenciar_painel_adm",
            "description": "Comando exclusivo do Administrador Alexandre para gerenciar clientes (Ativar, Bloquear ou Listar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "comando": {"type": "string", "enum": ["ATIVAR", "BLOQUEAR", "LISTAR"], "description": "Ação administrativa desejada."},
                    "id_alvo": {"type": "integer", "description": "O ID do Telegram do cliente que sofrerá a ação (use 0 se for comando LISTAR)."},
                    "nome_alvo": {"type": "string", "description": "Nome do cliente (obrigatório apenas se comando for ATIVAR)."}
                },
                "required": ["comando", "id_alvo"]
            }
        }
    }
]

# ----------------------------------------------------------------------
# 7. MANIPULADORES DE COMANDOS E ENTRADAS DO TELEGRAM
# ----------------------------------------------------------------------

@bot.message_handler(commands=['start'])
@trava_seguranca
def boas_vindas(message):
    nome = message.from_user.first_name if message.from_user.first_name else "Cliente"
    texto = (
        f"🔥 *Bem-vindo ao Fire iA, {nome}!* 🔥\n\n"
        "Eu sou o seu assistente central de Inteligência Artificial, operando **100% por conversa natural**, sem botões poluindo a tela! Tenho memória de contexto integrada e as seguintes funções prontas:\n\n"
        "📚 *Professor Particular:* Envie fotos de qualquer lição ou conta para ver a resolução passo a passo.\n"
        "🧮 *Super Calculadora:* Execute contas matemáticas complexas e lógicas instantaneamente.\n"
        "🎙️ *Comandos por Voz:* Fale naturalmente por áudio que eu entendo e executo tudo.\n"
        "💰 *Fluxo de Caixa:* Registre seus ganhos e gastos de forma simples e peça seu 'extrato mensal'.\n"
        "⏰ *Lembretes:* Peça para eu agendar lembretes e tarefas importantes.\n"
        "🔍 *Pesquisa na Web:* Consulte notícias, cotações ou fatos atuais em tempo real na internet.\n\n"
        "Como posso te ajudar agora? Pode falar!"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
@trava_seguranca
def tratar_foto(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        
        prompt_visao = "Você é o Fire iA. Analise detalhadamente a imagem recebida. Se for um exercício, resolva com o passo a passo completo. Se for um documento ou objeto, descreva perfeitamente."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt_visao}, {"type": "image_url", "image_url": {"url": file_url}}]}]
        )
        bot.reply_to(message, response.choices[0].message.content)
    except Exception as e:
        print(f"❌ [ERRO VISÃO] {e}")
        bot.reply_to(message, "🔥 Houve um erro temporário ao decodificar os elementos desta imagem.")

@bot.message_handler(content_types=['voice'])
@trava_seguranca
def tratar_voz(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        file_info = bot.get_file(message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        audio_data = requests.get(file_url).content
        
        nome_arquivo = f"voice_{message.message_id}.ogg"
        with open(nome_arquivo, "wb") as f: 
            f.write(audio_data)
            
        with open(nome_arquivo, "rb") as audio_file:
            transcricao = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
            
        os.remove(nome_arquivo)
        
        # Injeta o texto transcrito no fluxo padrão de mensagens do bot
        message.text = transcricao.text
        tratar_texto(message)
    except Exception as e:
        print(f"❌ [ERRO VOZ] {e}")
        bot.reply_to(message, "🔥 Ocorreu uma falha ao processar e compreender o seu áudio.")

@bot.message_handler(content_types=['text'])
@trava_seguranca
def tratar_texto(message):
    user_id = message.from_user.id
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        eh_admin = "SIM" if user_id == ID_ADMIN_ALEXANDRE else "NÃO"
        data_hora_atual = datetime.now().strftime("%A, %d de %B de %Y - %H:%M:%S")
        
        salvar_na_memoria(user_id, "user", message.text)
        historico = buscar_memoria_usuario(user_id, limite=15)
        
        # Sistema de Prompt Base Customizado
        prompt_sistema = {
            "role": "system",
            "content": (
                f"Você é o Fire iA, uma Inteligência Artificial poderosa e refinada.\n"
                f"O usuário atual com quem você fala é o Admin Alexandre? {eh_admin} (ID Telegram: {user_id}).\n"
                f"Sempre que se referir ao Admin Alexandre, saiba que ele é o seu criador, trate-o com respeito de desenvolvedor.\n"
                f"DATA E HORA DO SERVIDOR (Use como referência absoluta de tempo): {data_hora_atual}.\n\n"
                "Instruções Importantes:\n"
                "1. Você opera por conversa e linguagem natural.\n"
                "2. Você possui ferramentas nativas (tools) para pesquisar na web, gerenciar finanças e salvar lembretes. Use-as sempre que necessário.\n"
                "3. Se a ferramenta 'pesquisar_internet' retornar dados, use-os como prioridade absoluta para formular sua resposta e NUNCA diga que sua base de conhecimento está limitada ao passado.\n"
                "4. Se o usuário perguntar se você consegue buscar na internet, execute a ferramenta de busca ou diga que SIM, você tem acesso em tempo real."
            )
        }
        
        mensagens_completas = [prompt_sistema] + historico
        
        # Primeira chamada à API para analisar intenção e acionar as ferramentas
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=mensagens_completas,
            tools=FERRAMENTAS_FIRE,
            tool_choice="auto"
        )
        
        resposta_mensagem = response.choices[0].message
        tool_calls = resposta_mensagem.tool_calls
        
        # Execução dinâmica caso a IA decida usar alguma ferramenta (Tool)
        if tool_calls:
            print(f"📦 [TOOLS] O Fire iA ativou {len(tool_calls)} ferramenta(s) integrada(s).")
            mensagens_completas.append(resposta_mensagem)
            
            for tool_call in tool_calls:
                nome_funcao = tool_call.function.name
                argumentos = json.loads(tool_call.function.arguments)
                resultado_acao = ""
                
                if nome_funcao == "pesquisar_internet":
                    resultado_acao = pesquisar_internet(argumentos.get("termo"))
                elif nome_funcao == "gerenciar_financa":
                    resultado_acao = gerenciar_financa(user_id, argumentos.get("tipo"), argumentos.get("valor"), argumentos.get("descricao"))
                elif nome_funcao == "consultar_extrato":
                    resultado_acao = consultar_extrato(user_id)
                elif nome_funcao == "agendar_lembrete":
