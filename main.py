import os
import telebot
import sqlite3
from datetime import datetime
import google.generativeai as genai

# 1. Configuração dos Tokens
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(TOKEN)
user_state = {}

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# 2. Criação do Banco de Dados Limpo
def init_db():
    conn = sqlite3.connect('controleporia.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financas (
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

# 3. Funções do Banco de Dados
def salvar_registro(user_id, tipo, valor):
    conn = sqlite3.connect('controleporia.db')
    cursor = conn.cursor()
    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO financas (user_id, tipo, valor, data) VALUES (?, ?, ?, ?)',
                   (user_id, tipo, valor, data_atual))
    conn.commit()
    conn.close()

def pegar_extrato(user_id):
    conn = sqlite3.connect('controleporia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tipo, valor, data FROM financas WHERE user_id = ? ORDER BY id DESC LIMIT 5', (user_id,))
    dados = cursor.fetchall()
    conn.close()
    return dados

# 4. Comando de Boas-Vindas (/start)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton('➕ Entrada')
    btn2 = telebot.types.KeyboardButton('➖ Saída')
    btn3 = telebot.types.KeyboardButton('📊 Meu Extrato')
    markup.add(btn1, btn2, btn3)
    
    texto_boas_vindas = (
        "Olá! Eu sou o Controleporia Bot. 🤖🔥\n\n"
        "• Para usar as **Finanças**, clique nos botões abaixo.\n"
        "• Para usar a **IA**, use o comando **/ia** seguido da sua pergunta!\n"
        "  _Exemplo:_ `/ia Me dê ideias de jantar saudável`"
    )
    bot.reply_to(message, texto_boas_vindas, reply_markup=markup, parse_mode="Markdown")

# 5. Monitoramento dos Botões Financeiros
@bot.message_handler(func=lambda message: message.text in ['➕ Entrada', '➖ Saída', '📊 Meu Extrato'])
def escutar_botoes(message):
    user_id = message.chat.id
    texto = message.text

    if texto == '➕ Entrada':
        user_state[user_id] = 'esperando_entrada'
        bot.reply_to(message, "Quanto entrou? Digite apenas o número (Ex: 50.00):")
    elif texto == '➖ Saída':
        user_state[user_id] = 'esperando_saida'
        bot.reply_to(message, "Quanto você gastou? Digite apenas o número (Ex: 22.50):")
    elif texto == '📊 Meu Extrato':
        historico = pegar_extrato(user_id)
        if not historico:
            bot.reply_to(message, "Você ainda não tem gastos ou entradas registrados!")
            return
        
        relatorio = "📊 **Extrato Recente:**\n\n"
        saldo = 0.0
        for tipo, valor, data in historico:
            emoji = "🟢" if tipo == "Entrada" else "🔴"
            relatorio += f"{emoji} {tipo}: R$ {valor:.2f} \n"
            saldo += valor if tipo == "Entrada" else -valor
            
        relatorio += f"\n💰 **Saldo Atual:** R$ {saldo:.2f}"
        bot.reply_to(message, relatorio, parse_mode="Markdown")

# 6. COMANDO EXCLUSIVO DA IA (Garante que o Telegram não confunda)
@bot.message_handler(commands=['ia'])
def responder_ia_comando(message):
    user_id = message.chat.id
    
    # Remove o "/ia " do início para pegar só a pergunta do usuário
    pergunta = message.text.replace('/ia', '').strip()
    
    if not pergunta:
        bot.reply_to(message, "⚠️ Escreva algo depois do comando! Exemplo: `/ia qual a capital do Brasil?`", parse_mode="Markdown")
        return

    if not GEMINI_KEY:
        bot.reply_to(message, "Estou online, mas a minha chave de IA (GEMINI_API_KEY) não está configurada nos segredos.")
        return

    bot.send_chat_action(user_id, 'typing')

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(pergunta)
        
        if response.text:
            bot.reply_to(message, response.text)
        else:
            bot.reply_to(message, "🤖 A IA processou, mas devolveu uma resposta vazia.")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro na IA:\n`{str(e)}`", parse_mode="Markdown")

# 7. Captura de Valores Financeiros (Quando não for comando)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def processar_valores(message):
    user_id = message.chat.id
    texto = message.text
    estado = user_state.get(user_id)

    if estado in ['esperando_entrada', 'esperando_saida']:
        try:
            valor_final = float(texto.replace(',', '.'))
            tipo_final = "Entrada" if estado == 'esperando_entrada' else "Saída"
            
            salvar_registro(user_id, tipo_final, valor_final)
            user_state[user_id] = None  
            
            bot.reply_to(message, f"✅ R$ {valor_final:.2f} salvos em '{tipo_final}' com sucesso!")
        except ValueError:
            bot.reply_to(message, "⚠️ Digite apenas números. Se quiser cancelar, clique em outro botão.")

if __name__ == '__main__':
    bot.infinity_polling()
