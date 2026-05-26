import os
import telebot
from google import genai
from google.genai import types
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import requests

# ======= CONFIGURAÇÕES INICIAIS =======
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

scheduler = BackgroundScheduler()
scheduler.start()

# ======= BANCO DE DADOS LOCAL =======
def init_db():
    conn = sqlite3.connect('fire_ia.db')
    cursor = conn.cursor()
    # Tabela Financeira
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
    # Tabela de Lembretes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            texto TEXT,
            horario TEXT,
            repeticao TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ======= FUNÇÃO DE DISPARO DO ALARME =======
def disparar_alarme(user_id, texto_lembrete, tipo_rep):
    try:
        mensagem_alarme = f"🔔 **ALARME ATIVO, ALEXANDRE!**\n\n📌 **Lembrete:** {texto_lembrete}\n🔄 **Repetição:** {tipo_rep}"
        bot.send_message(user_id, mensagem_alarme, parse_mode="Markdown")
    except Exception as e:
        print(f"Erro ao disparar alarme: {e}")

# ======= TECLADO DE BOTÕES (MENU) =======
def menu_principal():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_entrada = telebot.types.KeyboardButton('➕ Entrada')
    btn_saida = telebot.types.KeyboardButton('➖ Saída')
    btn_extrato = telebot.types.KeyboardButton('📊 Extrato Mensal')
    btn_lembrete = telebot.types.KeyboardButton('📅 Criar Lembrete')
    btn_web = telebot.types.KeyboardButton('🌐 Pesquisa Web')
    
    markup.add(btn_entrada, btn_saida)
    markup.add(btn_extrato, btn_lembrete)
    markup.add(btn_web)
    return markup

# ======= FLUXO DO BOTÃO DE LEMBRETE REPETITIVO =======
@bot.message_handler(func=lambda msg: msg.text == '📅 Criar Lembrete')
def iniciar_lembrete(message):
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
        
        # Configura a repetição no APScheduler
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

# ======= 🌐 BUSCADOR WEB (IA NAVEGANDO NA INTERNET) =======
@bot.message_handler(func=lambda msg: msg.text == '🌐 Pesquisa Web')
def iniciar_pesquisa_web(message):
    msg = bot.reply_to(message, "🔍 O que você quer que eu pesquise ao vivo na internet agora?")
    bot.register_next_step_handler(msg, executar_pesquisa_web)

def executar_pesquisa_web(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        bot.reply_to(message, f"🌐 **Resultado da pesquisa ao vivo:**\n\n{response.text}", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro ao buscar na web: {e}")

# ======= 🎙️ TRANSCRITOR DE ÁUDIO =======
@bot.message_handler(content_types=['voice', 'audio'])
def transcrever_audio(message):
    bot.send_chat_action(message.chat.id, 'typing')
    aviso = bot.reply_to(message, "⏳ **Ouvindo seu áudio...** Processando a voz com o Gemini.")
    
    try:
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = bot.get_file(file_id)
        
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        response_file = requests.get(file_url)
        
        nome_audio = f"audio_{message.chat.id}.ogg"
        with open(nome_audio, 'wb') as f:
            f.write(response_file.content)
            
        with open(nome_audio, 'rb') as f:
            bytes_audio = f.read()
            
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=bytes_audio,
                    mime_type='audio/ogg',
                ),
                "Você é o Fire iA. Transcreva exatamente o que foi dito neste áudio pelo Alexandre e, em seguida, responda ao que ele pediu de forma prestativa."
            ]
        )
        
        os.remove(nome_audio)
        bot.delete_message(message.chat.id, aviso.message_id)
        bot.reply_to(message, f"🎙️ **O que eu entendi do seu áudio:**\n\n{response.text}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Não consegui entender o áudio. Detalhe: {e}")

# ======= 📸 OLHOS DO FIRE IA: LEITURA DE FOTOS =======
@bot.message_handler(content_types=['photo'])
def analisar_imagem(message):
    bot.send_chat_action(message.chat.id, 'typing')
    aviso = bot.reply_to(message, "🔔 **Fire iA 'Olhos' Ativados!** Analisando imagem...")
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        nome_arquivo = f"imagem_{message.chat.id}.jpg"
        
        with open(nome_arquivo, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        with open(nome_arquivo, 'rb') as f:
            bytes_imagem = f.read()
            
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=bytes_imagem, mime_type='image/jpeg'),
                "Você é o Professor Particular do Alexandre dentro do Fire iA. Leia atentamente a imagem do caderno, transcreva as perguntas encontradas e resolva cada uma delas passo a passo."
            ]
        )
        os.remove(nome_arquivo)
        bot.delete_message(message.chat.id, aviso.message_id)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao ler foto: {e}")

# ======= FLUXOS DOS BOTÕES FINANCEIROS =======
@bot.message_handler(func=lambda msg: msg.text in ['➕ Entrada', '➖ Saída'])
def fluxo_financeiro(message):
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
        bot.reply_to(message, f"✅ {tipo} de R$ {valor:.2f} gravada!", reply_markup=menu_principal())
    except:
        bot.reply_to(message, "❌ Formato inválido.", reply_markup=menu_principal())

@bot.message_handler(func=lambda msg: msg.text == '📊 Extrato Mensal')
def ver_extrato(message):
    conn = sqlite3.connect('fire_ia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tipo, valor, categoria FROM finance WHERE user_id = ?', (message.chat.id,))
    linhas = cursor.fetchall()
    conn.close()
    if not linhas:
        bot.reply_to(message, "📊 Sem lançamentos!")
        return
    resumo = "📊 **SEU EXTRATO:**\n\n"
    for t, v, c in linhas:
        resumo += f"{'🟢' if t == 'Entrada' else '🔴'} R$ {v:.2f} - {c}\n"
    bot.reply_to(message, resumo, parse_mode="Markdown")

# ======= 💬 CONVERSA NORMAL POR TEXTO =======
@bot.message_handler(content_types=['text'])
def conversa_ia(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Você é o Fire iA, o assistente pessoal inteligente do Alexandre. Responda de forma direta e amigável: {message.text}"
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro na IA: {e}")

# ======= COMANDO START =======
@bot.message_handler(commands=['start', 'menu'])
def enviar_menu(message):
    bot.reply_to(message, "🔥 **Fire iA Atualizado!** Escolha uma opção ou fale diretamente comigo:", reply_markup=menu_principal(), parse_mode="Markdown")

if __name__ == '__main__':
    bot.infinity_polling()
