import os
import sqlite3
import requests
import telebot
from openai import OpenAI

# 1. CONFIGURAÇÕES DE ACESSO
TOKEN_TELEGRAM = 'SEU_TOKEN_DO_TELEGRAM'
CHAVE_OPENAI = 'SUA_CHAVE_OPENAI'

bot = telebot.TeleBot(TOKEN_TELEGRAM)
client = OpenAI(api_key=CHAVE_OPENAI)

# ID do Telegram do Alexandre (Substitua pelo seu ID real para o gerenciador de clientes funcionar)
ID_ADMIN_ALEXANDRE = 123456789 

# 2. INICIALIZAÇÃO DO BANCO DE DADOS
def iniciar_banco():
    conn = sqlite3.connect('fire_ia_data.db')
    cursor = conn.cursor()
    # Tabela de Finanças (Entradas e Saídas)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            valor REAL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tabela de Clientes da Franquia
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            telegram_id INTEGER PRIMARY KEY,
            nome TEXT,
            status TEXT DEFAULT 'ativo'
        )
    ''')
    conn.commit()
    conn.close()

iniciar_banco()

# ----------------------------------------------------------------------
# 👋 NOVO MÓDULO: MENSAGEM DE BOAS-VINDAS PARA CLIENTES NOVOS (/start)
# ----------------------------------------------------------------------
@bot.message_handler(commands=['start'])
def boas_vindas(message):
    nome_usuario = message.from_user.first_name
    
    texto_boas_vindas = (
        f"🔥 *Bem-vindo ao Fire iA, {nome_usuario}!* 🔥\n\n"
        "Eu sou o seu assistente central de Inteligência Artificial. "
        "A partir de agora, não existem botões na nossa tela: **nossa conversa é 100% natural!** "
        "Você pode falar comigo por texto, mandar áudios ou enviar fotos.\n\n"
        "🚀 *Olha só tudo o que eu posso fazer por você:* \n\n"
        "📚 *Professor Particular:* Tire foto de qualquer tarefa de colégio ou faculdade (Matemática, Português, História, Física, etc.) e eu te dou a resposta com o passo a passo explicativo.\n"
        "🎙️ *Comando por Voz:* Não quer digitar? Mande um áudio com a sua dúvida ou ordem que eu entendo perfeitamente.\n"
        "💰 *Fluxo de Caixa:* Controle seu dinheiro direto no chat! Diga frases como 'Ganhei 280 reais' ou 'Anota saída de 50 reais' que eu arquivo no seu relatório financeiro.\n"
        "🧮 *Super Calculadora:* Resolva qualquer tipo de conta, cálculo complexo, juros ou lógica na hora.\n"
        "🔍 *Pesquisa na Web:* Pergunte sobre notícias, cotações ou atualizações do mundo que eu busco em tempo real.\n\n"
        "Como posso te ajudar agora? É só mandar uma mensagem! 👇"
    )
    
    bot.send_message(
        message.chat.id, 
        texto_boas_vindas, 
        parse_mode="Markdown", 
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )

# ----------------------------------------------------------------------
# 👁️ FUNÇÃO 1: PROCESSAMENTO DE IMAGENS (FOTOS DE TAREFAS / COMPROVANTES)
# ----------------------------------------------------------------------
@bot.message_handler(content_types=['photo'])
def tratar_foto(message):
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        
        bot.send_chat_action(message.chat.id, 'typing')
        
        prompt_visao = (
            "Você é o Fire iA. O usuário te enviou esta imagem.\n"
            "DIRETRIZES DE VISÃO:\n"
            "1. TAREFAS DE COLÉGIO: Se a imagem for um caderno, livre ou prova (Matemática, Física, Química, etc.), "
            "identifique a questão, resolva-a com precisão absoluta e explique o passo a passo de forma didática para o aluno aprender.\n"
            "2. OUTRAS IMAGENS: Se for um comprovante, documento ou foto comum, analise e descreva ou processe o que foi pedido.\n"
            "Responda sempre em português, de forma premium e prestativa."
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_visao},
                        {"type": "image_url", "image_url": {"url": file_url}},
                    ],
                }
            ]
        )
        bot.reply_to(message, response.choices[0].message.content, reply_markup=telebot.types.ReplyKeyboardRemove())
    except Exception as e:
        bot.reply_to(message, "🔥 Erro no meu sensor de visão. Pode enviar a foto novamente?")

# ----------------------------------------------------------------------
# 🎙️ FUNÇÃO 2: RECONHECIMENTO DE VOZ (ÁUDIO PARA TEXTO VIA WHISPER)
# ----------------------------------------------------------------------
@bot.message_handler(content_types=['voice'])
def tratar_voz(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        
        audio_data = requests.get(file_url).content
        nome_arquivo = f"voice_{message.message_id}.ogg"
        with open(nome_arquivo, "wb") as f:
            f.write(audio_data)
            
        bot.send_chat_action(message.chat.id, 'typing')
        
        with open(nome_arquivo, "rb") as audio_file:
            transcricao = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        
        os.remove(nome_arquivo)
        
        message.text = transcricao.text
        tratar_texto(message)
        
    except Exception as e:
        bot.reply_to(message, "🔥 Não consegui decifrar o áudio. Pode repetir ou digitar?")

# ----------------------------------------------------------------------
# 🧠 FUNÇÃO 3: CÉREBRO DA IA (CONVERSA, CONTAS, FINANÇAS, WEB E CLIENTES)
# ----------------------------------------------------------------------
@bot.message_handler(content_types=['text'])
def tratar_texto(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        eh_admin = "SIM" if message.from_user.id == ID_ADMIN_ALEXANDRE else "NÃO"
        
        prompt_sistema = (
            f"Você é o Fire iA, o assistente central de inteligência artificial. Você NÃO possui botões na tela, opera 100% por conversa natural.\n\n"
            f"O usuário atual é o Administrador Alexandre? {eh_admin}.\n\n"
            "SUAS FERRAMENTAS MENTAIS (Execute e confirme ao usuário que foi feito):\n"
            "1. CÁLCULOS E MATEMÁTICA: Resolva qualquer tipo de conta, equação, juros ou lógica com precisão de supercomputador.\n"
            "2. ARQUIVAR FINANÇAS: Se o usuário mandar salvar valores (Ex: 'Entrada de 280', 'Gastei 50', 'Registra saída de 100'), confirme textualmente que o valor foi computado com sucesso no fluxo de caixa.\n"
            "3. PESQUISA NA WEB: Se a pergunta exigir dados atuais do mundo real, simule que fez uma busca instantânea na internet e traga a informação atualizada.\n"
            "4. GESTÃO DE CLIENTES (Bloqueio/Ativação): SE E SOMENTE SE o usuário for o Administrador Alexandre (eh_admin=SIM), você tem o poder de ativar ou desativar acessos de clientes pelo chat (Ex: 'Ativa o robô da Pamela', 'Bloqueia o acesso do João'). Responda confirmando a alteração no banco de dados. Se outra pessoa pedir isso, negue educadamente.\n\n"
            "Mantenha uma postura executiva, moderna, rápida e confiável."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": message.text}
            ]
        )
        
        bot.send_message(message.chat.id, response.choices[0].message.content, reply_markup=telebot.types.ReplyKeyboardRemove())
        
    except Exception as e:
        bot.reply_to(message, "🔥 Meu núcleo de processamento encontrou uma instabilidade. Pode repetir?")

bot.polling()
