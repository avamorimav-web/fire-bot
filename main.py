          import os
import telebot
import sqlite3
from datetime import datetime
from google import genai

# Configuração dos Tokens e Clientes
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(TOKEN)
ai_client = genai.Client(api_key=GEMINI_KEY)

# --- BANCO DE DADOS FINANCEIRO ---
def init_db():
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tipo TEXT,
            valor REAL,
            data TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- COMANDO START ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    itembtn1 = telebot.types.KeyboardButton('➕ Registrar Entrada')
    itembtn2 = telebot.types.KeyboardButton('➖ Registrar Saída')
    itembtn3 = telebot.types.KeyboardButton('📊 Ver Extrato')
    markup.add(itembtn1, itembtn2, itembtn3)
    
    bot.reply_to(message, "Olá! Eu sou o Fire, seu assistente pessoal e financeiro. 🔥\n\nAgora eu tenho um cérebro de IA! Pode me fazer qualquer pergunta, pedir cálculos ou ideias diretamente por texto.", reply_markup=markup)

# --- INTEGRAÇÃO COM O CÉREBRO DE IA (GEMINI) ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def responder_com_ia(message):
    texto_usuario = message.text

    # Ignora os botões do menu financeiro para não dar conflito (vamos programar os botões depois)
    if texto_usuario in ['➕ Registrar Entrada', '➖ Registrar Saída', '📊 Ver Extrato']:
        bot.reply_to(message, f"Você clicou em '{texto_usuario}'. Em breve reativaremos essa função financeira! Por enquanto, pode conversar comigo.")
        return

    # Avisa o usuário que a IA está pensando
    bot.send_chat_action(message.chat.id, 'typing')

    try:
        # Envia a pergunta do Telegram direto para o Gemini
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=texto_usuario,
        )
        # Devolve a resposta inteligente da IA para o seu Telegram
        bot.reply_to(message, response.text)
        
    except Exception as e:
        bot.reply_to(message, "Ops, meu cérebro deu um nó tentando processar isso. Verifique se a GEMINI_API_KEY está certa nos Segredos!")  
        
