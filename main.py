import os
import telebot
import sqlite3
from datetime import datetime
import google.generativeai as genai  # Versão mais estável e compatível

# Configuração dos Tokens
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(TOKEN)

# Configura o Gemini de forma segura
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
else:
    print("AVISO: GEMINI_API_KEY não encontrada nos Segredos!")

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
    
    bot.reply_to(message, "Olá! Eu sou o Fire, seu assistente pessoal e financeiro. 🔥\n\nO cérebro de IA está ativo! Pode me fazer qualquer pergunta diretamente por texto.", reply_markup=markup)

# --- INTEGRAÇÃO COM O CÉREBRO DE IA ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def responder_com_ia(message):
    texto_usuario = message.text

    # Ignora os botões do menu financeiro para não dar conflito
    if texto_usuario in ['➕ Registrar Entrada', '➖ Registrar Saída', '📊 Ver Extrato', '📄 Gerar PDF']:
        bot.reply_to(message, f"Você clicou no botão financeiro '{texto_usuario}'.")
        return

    # Se a chave da IA não existir, avisa logo
    if not GEMINI_KEY:
        bot.reply_to(message, "Erro: A sua chave GEMINI_API_KEY não está configurada nos Segredos do Fly.io!")
        return

    bot.send_chat_action(message.chat.id, 'typing')

    try:
        # Usa o modelo mais leve, rápido e atual do Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(texto_usuario)
        
        # Envia a resposta da IA de volta
        bot.reply_to(message, response.text)
        
    except Exception as e:
        # SE DER ERRO, O BOT VAI TE MANDAR O ERRO REAL NO TELEGRAM!
        bot.reply_to(message, f"Ops! Meu cérebro de IA deu um erro:\n`{str(e)}`")

# Mantém o bot ligado
if __name__ == '__main__':
    print("Bot iniciado com sucesso...")
    bot.infinity_polling()              
