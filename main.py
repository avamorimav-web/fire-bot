import os
import telebot
import sqlite3
from datetime import datetime
import google.generativeai as genai

# Configuração dos Tokens
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(TOKEN)

# Dicionário temporário para controlar o estado financeiro de cada usuário
user_state = {}

# Configura o Gemini se a chave existir nos segredos
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

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

# --- FUNÇÕES AUXILIARES DO BANCO ---
def salvar_transacao(user_id, tipo, valor):
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO transacoes (user_id, tipo, valor, data) VALUES (?, ?, ?, ?)',
                   (user_id, tipo, valor, data_atual))
    conn.commit()
    conn.close()

def obter_extrato(user_id):
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tipo, valor, data FROM transacoes WHERE user_id = ? ORDER BY id DESC LIMIT 5', (user_id,))
    linhas = cursor.fetchall()
    conn.close()
    return linhas

# --- COMANDO START ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    itembtn1 = telebot.types.KeyboardButton('➕ Registrar Entrada')
    itembtn2 = telebot.types.KeyboardButton('➖ Registrar Saída')
    itembtn3 = telebot.types.KeyboardButton('📊 Ver Extrato')
    markup.add(itembtn1, itembtn2, itembtn3)
    
    bot.reply_to(message, "Olá! Eu sou o Fire, seu assistente pessoal e financeiro. 🔥\n\nUse os botões abaixo para suas contas ou me mande qualquer pergunta por texto para conversar com minha IA!", reply_markup=markup)

# --- LÓGICA DO MENU FINANCEIRO ---
@bot.message_handler(func=lambda message: message.text in ['➕ Registrar Entrada', '➖ Registrar Saída', '📊 Ver Extrato'])
def escutar_botoes(message):
    user_id = message.chat.id
    texto = message.text

    if texto == '➕ Registrar Entrada':
        user_state[user_id] = 'aguardando_entrada'
        bot.reply_to(message, "Digite o valor da Entrada (Ex: 150.50):")
    elif texto == '➖ Registrar Saída':
        user_state[user_id] = 'aguardando_saida'
        bot.reply_to(message, "Digite o valor da Saída (Ex: 50.25):")
    elif texto == '📊 Ver Extrato':
        extrato = obter_extrato(user_id)
        if not extrato:
            bot.reply_to(message, "Nenhum registro encontrado ainda!")
            return
        
        resposta = "📊 **Seu Extrato Recente:**\n\n"
        total = 0.0
        for tipo, valor, data in extrato:
            emoji = "🟢" if tipo == "Entrada" else "🔴"
            resposta += f"{emoji} {tipo}: R$ {valor:.2f} | {data}\n"
            total += valor if tipo == "Entrada" else -valor
            
        resposta += f"\n💰 **Saldo do período:** R$ {total:.2f}"
        bot.reply_to(message, resposta, parse_mode="Markdown")

# --- CAPTURA DE TEXTO GERAL (IA ou Valores) ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def tratar_texto_geral(message):
    user_id = message.chat.id
    texto = message.text
    state = user_state.get(user_id)

    # Se o bot estiver esperando um número para o financeiro
    if state in ['aguardando_entrada', 'aguardando_saida']:
        try:
            # Substitui vírgula por ponto para o Python entender
            valor_limpo = float(texto.replace(',', '.'))
            tipo_transacao = "Entrada" if state == 'aguardando_entrada' else "Saída"
            
            salvar_transacao(user_id, tipo_transacao, valor_limpo)
            
            # Limpa o estado após salvar
            user_state[user_id] = None
            bot.reply_to(message, f"✅ {tipo_transacao} de R$ {valor_limpo:.2f} registrada com sucesso!")
            return
        except ValueError:
            bot.reply_to(message, "⚠️ Valor inválido! Por favor, digite apenas números (Ex: 25.50). Se desistiu, clique em outro botão.")
            return

    # --- SE FOR CONVERSA NORMAL (CHAMA A IA GEMINI) ---
    if not GEMINI_KEY:
        bot.reply_to(message, "⚠️ O sistema financeiro funcionou, mas a chave `GEMINI_API_KEY` não está configurada nos segredos do Fly.io!")
        return

    bot.send_chat_action(message.chat.id, 'typing')

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(texto)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Erro ao acionar a IA:\n`{str(e)}`")

if __name__ == '__main__':
    bot.infinity_polling()
