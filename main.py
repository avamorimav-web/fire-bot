import os
import telebot
from openai import OpenAI
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import requests

# =====================================================================
# 👑 ID DO DONO DA FRANQUIA (ALEXANDRE)
# Você tem superpoderes para ativar/desativar qualquer cliente no chat!
# =====================================================================
DONO_DA_FRANQUIA = 5435085592

TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENAI_KEY = os.environ.get('GEMINI_API_KEY') 

bot = telebot.TeleBot(TOKEN)
client = OpenAI(api_key=OPENAI_KEY)

scheduler = BackgroundScheduler()
scheduler.start()

# ======= BANCO DE DADOS AUTOMATIZADO DA FRANQUIA =======
def init_db():
    conn = sqlite3.connect('fire_ia.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tipo TEXT,
            valor REAL,
            categoria TEXT,
            data TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            texto TEXT,
            horario TEXT,
            repeticao TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes_ativos (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ======= FILTRO DE SEGURANÇA DA FRANQUIA =======
def usuario_autorizado(message):
    user_id = message.chat.id
    
    if user_id == DONO_DA_FRANQUIA:
        return True
        
    conn = sqlite3.connect('fire_ia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM clientes_ativos WHERE user_id = ?', (user_id,))
    cliente = cursor.fetchone()
    conn.close()
    
    if cliente:
        return True
    
    mensagem_bloqueio = (
        f"❌ **ACESSO NÃO AUTORIZADO**\n\n"
        f"Olá! Você tentou acessar o **Fire iA**, o assistente pessoal mais avançado do Telegram.\n\n"
        f"🔑 Para adquirir sua licença de uso ou renovar sua assinatura mensal, entre em contato diretamente com o franqueado responsável:\n\n"
        f"🤠 **Alexandre Amorim**\n\n"
        f"ℹ️ _Informe o seu código de identificação ao administrador:_\n"
        f"📌 **Seu ID:** `{user_id}`"
    )
    bot.reply_to(message, mensagem_bloqueio, parse_mode="Markdown")
    return False

def disparar_alarme(user_id, texto_lembrete, tipo_rep):
    try:
        mensagem_alarme = f"🔔 **ALARME ATIVO!**\n\n📌 **Lembrete:** {texto_lembrete}\n🔄 **Repetição:** {tipo_rep}"
        bot.send_message(user_id, mansion_alarme, parse_mode="Markdown")
    except Exception as e:
        print(f"Erro ao disparar alarme: {e}")

def menu_principal():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=False)
    btn_entrada = telebot.types.KeyboardButton('➕ Entrada')
    btn_saida = telebot.types.KeyboardButton('➖ Saída')
    btn_extrato = telebot.types.KeyboardButton('📊 Extrato Mensal')
    btn_lembrete = telebot.types.KeyboardButton('📅 Criar Lembrete')
    
    markup.add(btn_entrada, btn_saida)
    markup.add(btn_extrato, btn_lembrete)
    return markup

# ======= ⚙️ COMANDOS EXCLUSIVOS DE ADMINISTRADOR =======
@bot.message_handler(func=lambda msg: msg.chat.id == DONO_DA_FRANQUIA and (msg.text.startswith('+') or msg.text.startswith('-') or msg.text.lower() == 'clientes'))
def gerenciar_franquia(message):
    texto = message.text.strip()
    
    if texto.startswith('+'):
        try:
            novo_id = int(texto.replace('+', '').strip())
            conn = sqlite3.connect('fire_ia.db')
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO clientes_ativos (user_id) VALUES (?)', (novo_id,))
            conn.commit()
            conn.close()
            bot.reply_to(message, f"✅ **CLIENTE ATIVADO!**\n\nO ID `{novo_id}` foi adicionado à franquia e já pode usar o Fire iA!", parse_mode="Markdown")
            try:
                bot.send_message(novo_id, "🎉 **PARABÉNS!** Sua assinatura do **Fire iA** foi ativada pelo administrador Alexandre! Digite `menu` para começar.", parse_mode="Markdown")
            except:
                pass
        except:
            bot.reply_to(message, "⚠️ Erro! Use o formato: `+ 12345678`")

    elif texto.startswith('-'):
        try:
            remover_id = int(texto.replace('-', '').strip())
            conn = sqlite3.connect('fire_ia.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM clientes_ativos WHERE user_id = ?', (remover_id,))
            conn.commit()
            conn.close()
            bot.reply_to(message, f"⛔ **CLIENTE REMOVIDO!**\n\nO ID `{remover_id}` foi bloqueado no sistema.", parse_mode="Markdown")
            try:
                bot.send_message(remover_id, "⚠️ **ASSINATURA EXPIRADA:** Sua licença do Fire iA venceu. Entre em contato com Alexandre para renovar.", parse_mode="Markdown")
            except:
                pass
        except:
            bot.reply_to(message, "⚠️ Erro! Use o formato: `- 12345678`")

    elif texto.lower() == 'clientes':
        conn = sqlite3.connect('fire_ia.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM clientes_ativos')
        linhas = cursor.fetchall()
        conn.close()
        
        if not linhas:
            bot.reply_to(message, "📊 **Franquia Zerada:** Você ainda não tem nenhum cliente ativo no sistema.")
            return
            
        lista = "👥 **CLIENTES ATIVOS NA FRANQUIA:**\n\n"
        for row in linhas:
            lista += f"• ID: `{row[0]}`\n"
        bot.reply_to(message, lista, parse_mode="Markdown")

# ======= FLUXO DO BOTÃO DE LEMBRETE =======
@bot.message_handler(func=lambda msg: msg.text == '📅 Criar Lembrete')
def iniciar_lembrete(message):
    if not usuario_autorizado(message): return
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Apenas uma vez', 'Todos os dias', 'Toda semana', 'Voltar')
    msg = bot.reply_to(message, "Com que frequência você deseja esse alarme?", reply_markup=markup)
    bot.register_next_step_handler(msg, escolher_horario_lembrete)

def escolher_horario_lembrete(message):
    if message.text == 'Voltar':
        bot.reply_to(message, "Menu principal:", reply_markup=menu_principal())
        return
    tipo_rep = message.text
    msg = bot.reply_to(message, f"Defina o horário e o que lembrar.\n\n⚠️ **Use o formato:** `HH:MM Texto`\n(Ex: `08:00 Tomar remédio`)")
    bot.register_next_step_handler(msg, agendar_lembrete_repetitivo, tipo_rep)

def agendar_lembrete_repetitivo(message, tipo_rep):
    try:
        partes = message.text.split(maxsplit=1)
        hora_str = partes[0]
        texto_lembrete = partes[1]
        
        hora, minuto = map(int, hora_str.split(':'))
        
        conn = sqlite3.connect('fire_ia.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO reminders (user_id, texto, horario, repeticao) VALUES (?, ?, ?, ?)',
                       (message.chat.id, texto_lembrete, hora_str, tipo_rep))
        conn.commit()
        conn.close()
        
        if tipo_rep == 'Todos os dias':
            scheduler.add_job(disparar_alarme, 'cron', hour=hora, minute=minuto, args=[message.chat.id, texto_lembrete, 'Diário'])
        elif tipo_rep == 'Toda semana':
            dia_semana = datetime.now().weekday()
            scheduler.add_job(disparar_alarme, 'cron', day_of_week=dia_semana, hour=hora, minute=minuto, args=[message.chat.id, texto_lembrete, 'Semanal'])
        else:
            agora = datetime.now()
            horario_alarme = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
            if horario_alarme < agora:
                from datetime import timedelta
                horario_alarme += timedelta(days=1)
            scheduler.add_job(disparar_alarme, 'date', run_date=horario_alarme, args=[message.chat.id, texto_lembrete, 'Único'])
            
        bot.reply_to(message, f"⏰ **Alarme Ativado!**\n\n🔔 Horário: **{hora_str}**\n📌 O que: _{texto_lembrete}_\n🔄 Frequência: {tipo_rep}", reply_markup=menu_principal(), parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Erro no formato! Use `HH:MM Texto`", reply_markup=menu_principal())

# ======= 🎙️ TRANSCRITOR DE ÁUDIO =======
@bot.message_handler(content_types=['voice', 'audio'])
def transcrever_audio(message):
    if not usuario_autorizado(message): return
    bot.send_chat_action(message.chat.id, 'typing')
    aviso = bot.reply_to(message, "⏳ **Ouvindo seu áudio no ChatGPT...**")
    
    try:
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = bot.get_file(file_id)
        
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        response_file = requests.get(file_url)
        
        nome_audio = f"audio_{message.chat.id}.ogg"
        with open(nome_audio, 'wb') as f:
            f.write(response_file.content)
            
        with open(nome_audio, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            
        os.remove(nome_audio)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é o Fire iA, um assistente pessoal inteligente de alta performance. Responda de forma direta e muito amigável."},
                {"role": "user", "content": transcription.text}
            ]
        )
        
        bot.delete_message(message.chat.id, aviso.message_id)
        bot.reply_to(message, f"🎙️ **Ouvido:** _{transcription.text}_\n\n🤖 **Resposta:**\n{response.choices[0].message.content}", reply_markup=menu_principal())
        
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao processar áudio: {e}", reply_markup=menu_principal())

# ======= FLUXOS FINANCEIROS INDIVIDUAIS =======
@bot.message_handler(func=lambda msg: msg.text in ['➕ Entrada', '➖ Saída'])
def fluxo_financeiro(message):
    if not usuario_autorizado(message): return
    tipo = 'Entrada' if '➕' in message.text else 'Saída'
    msg = bot.reply_to(message, f"Digite o valor da {tipo} seguido da categoria (Ex: 25.50 Almoço):")
    bot.register_next_step_handler(msg, salvar_financeiro, tipo)

def salvar_financeiro(message, tipo):
    try:
        partes = message.text.split(maxsplit=1)
        valor = float(partes[0].replace(',', '.'))
        categoria = partes[1] if len(partes) > 1 else 'Geral'
        
        conn = sqlite3.connect('fire_ia.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO finance (user_id, tipo, valor, categoria, data) VALUES (?, ?, ?, ?, ?)',
                       (message.chat.id, tipo, valor, categoria, datetime.now().strftime('%Y-%m-%d %H:%M')))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ {tipo} de R$ {valor:.2f} gravada com sucesso!", reply_markup=menu_principal())
    except:
        bot.reply_to(message, "❌ Formato inválido.", reply_markup=menu_principal())

@bot.message_handler(func=lambda msg: msg.text == '📊 Extrato Mensal')
def ver_extrato(message):
    if not usuario_autorizado(message): return
    conn = sqlite3.connect('fire_ia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tipo, valor, categoria FROM finance WHERE user_id = ?', (message.chat.id,))
    linhas = cursor.fetchall()
    conn.close()
    
    if not linhas:
        bot.reply_to(message, "📊 Você ainda não possui nenhum lançamento cadastrado no seu extrato!", reply_markup=menu_principal())
        return
        
    resumo = "📊 **SEU EXTRATO EXCLUSIVO:**\n\n"
    total_entradas = 0
    total_saidas = 0
    for t, v, c in linhas:
        if t == 'Entrada':
            resumo += f"🟢 R$ {v:.2f} - {c}\n"
            total_entradas += v
        else:
            resumo += f"🔴 R$ {v:.2f} - {c}\n"
            total_saidas += v
            
    saldo_final = total_entradas - total_saidas
    resumo += f"\n---------------------\n"
    resumo += f"💰 **Total Entradas:** R$ {total_entradas:.2f}\n"
    resumo += f"📉 **Total Saídas:** R$ {total_saidas:.2f}\n"
    resumo += f"💵 **Saldo Atual:** R$ {saldo_final:.2f}"
    
    bot.reply_to(message, resumo, parse_mode="Markdown", reply_markup=menu_principal())

# ======= 💬 CONVERSA NORMAL POR TEXTO =======
@bot.message_handler(content_types=['text'])
def conversa_ia(message):
    if not usuario_autorizado(message): return
    
    if message.text.lower() in ['/start', '/menu', 'start', 'menu']:
        enviar_menu(message)
        return
        
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é o Fire iA, um assistente pessoal inteligente de alta performance. Responda de forma direta, prestativa e amigável."},
                {"role": "user", "content": message.text}
            ]
        )
        bot.reply_to(message, response.choices[0].message.content, reply_markup=menu_principal())
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro na IA: {e}", reply_markup=menu_principal())

# ======= COMANDO START =======
@bot.message_handler(commands=['start', 'menu'])
def enviar_menu(message):
    if not usuario_autorizado(message): return
    bot.reply_to(message, "🔥 **Bem-vindo ao Fire iA Premium!**\n\nSeu painel de controle pessoal está ativo e pronto. Escolha uma opção nos botões abaixo:", reply_markup=menu_principal(), parse_mode="Markdown")

if __name__ == '__main__':
    bot.infinity_polling()
