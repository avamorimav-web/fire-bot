import os
import telebot
import sqlite3
from datetime import datetime
from google import genai

# 1. Configuração dos Tokens
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(TOKEN)
user_state = {}

if GEMINI_KEY:
    ai_client = genai.Client(api_key=GEMINI_KEY)
else:
    ai_client = None

# 2. Criação do Banco de Dados
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
        "• Para falar comigo, **basta digitar qualquer texto, cálculo ou ideia diretamente no chat!** Eu te responderei usando IA."
    )
    bot.reply_to(message, texto_boas_vindas, reply_markup=markup)

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

# 6. PROCESSAMENTO TOTAL LIVRE (IA RESPONDE TUDO DIRETO)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def tratar_texto_direto(message):
    user_id = message.chat.id
    texto = message.text
    estado = user_state.get(user_id)

    # CENÁRIO A: Se você clicou no botão financeiro antes, ele salva o valor número
    if estado in ['esperando_entrada', 'esperando_saida']:
        try:
            valor_final = float(texto.replace(',', '.'))
            tipo_final = "Entrada" if estado == 'esperando_entrada' else "Saída"
            
            salvar_registro(user_id, tipo_final, valor_final)
            user_state[user_id] = None  # Reseta o estado financeiro
            
            bot.reply_to(message, f"✅ R$ {valor_final:.2f} salvos em '{tipo_final}' com sucesso!")
            return
        except ValueError:
            bot.reply_to(message, "⚠️ Digite apenas números para o financeiro. Se quiser conversar com a IA, ignore os botões.")
            return

    # CENÁRIO B: Conversa normal sem comando nenhum (Chama a IA direto)
    if not ai_client:
        bot.reply_to(message, "Estou online, mas a minha chave de IA (GEMINI_API_KEY) não está configurada nos segredos.")
        return

    bot.send_chat_action(user_id, 'typing')

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=texto,
        )
        
        if response.text:
            bot.reply_to(message, response.text)
        else:
            bot.reply_to(message, "🤖 Processei sua mensagem, mas não consegui gerar um texto de resposta.")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro na IA:\n`{str(e)}`", parse_mode="Markdown")

if __name__ == '__main__':
    bot.infinity_polling()
