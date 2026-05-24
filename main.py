
import os
import telebot
from telebot import types
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Pega o Token direto das configurações seguras do Render
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tipo TEXT, valor REAL, data TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_transacao(user_id, tipo, valor):
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO transacoes (user_id, tipo, valor, data) VALUES (?, ?, ?, ?)', (user_id, tipo, valor, data_atual))
    conn.commit()
    conn.close()

def obter_extrato(user_id):
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tipo, valor, data FROM transacoes WHERE user_id = ? ORDER BY data DESC', (user_id,))
    dados = cursor.fetchall()
    conn.close()
    return dados

# --- MENU PRINCIPAL ---
def abrir_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_entrada = types.KeyboardButton('➕ Registrar Entrada')
    btn_saida = types.KeyboardButton('➖ Registrar Saída')
    btn_extrato = types.KeyboardButton('📊 Ver Extrato')
    btn_pdf = types.KeyboardButton('📄 Gerar PDF')
    markup.row(btn_entrada, btn_saida)
    markup.row(btn_extrato, btn_pdf)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, f"Olá! Eu sou o **Fire**, seu assistente financeiro. 🔥\nVamos organizar suas contas hoje?", parse_mode="Markdown", reply_markup=abrir_menu())

# --- CAPTURA DE ENTRADAS E SAÍDAS ---
user_state = {}

@bot.message_handler(func=lambda message: message.text in ['➕ Registrar Entrada', '➖ Registrar Saída'])
def verificar_opcao(message):
    tipo = 'Entrada' if 'Entrada' in message.text else 'Saída'
    user_state[message.chat.id] = tipo
    bot.reply_to(message, f"Digite o valor da **{tipo}** (Ex: 150.50):", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_state)
def registrar_valor(message):
    chat_id = message.chat.id
    tipo = user_state[chat_id]
    
    try:
        valor = float(message.text.replace(',', '.'))
        salvar_transacao(chat_id, tipo, valor)
        
        bot.reply_to(message, f"✅ {tipo} de R$ {valor:.2f} registrada com sucesso!", reply_markup=abrir_menu())
        
        # Alerta automático de gasto alto
        if tipo == 'Saída' and valor > 500:
            bot.send_message(chat_id, "⚠️ **Alerta do Fire!** Você acabou de registrar uma saída acima de R$ 500,00.")
            
        del user_state[chat_id]
    except ValueError:
        bot.reply_to(message, "❌ Valor inválido. Digite apenas números. Tente clicar no botão novamente.")
        del user_state[chat_id]

# --- EXTRATO NA TELA ---
@bot.message_handler(func=lambda message: message.text == '📊 Ver Extrato')
def exibir_extrato(message):
    historico = obter_extrato(message.chat.id)
    if not historico:
        bot.reply_to(message, "Você ainda não possui transações salvas.")
        return
        
    txt = "📊 **Seu Extrato Recente:**\n\n"
    saldo = 0
    for tipo, valor, data in historico[:10]:
        emoji = "🟢" if tipo == 'Entrada' else "🔴"
        txt += f"{emoji} {tipo}: R$ {valor:.2f} | _{data}_\n"
        saldo += valor if tipo == 'Entrada' else -valor
        
    txt += f"\n💰 **Saldo do período:** R$ {saldo:.2f}"
    bot.reply_to(message, txt, parse_mode="Markdown")

# --- GERADOR DE PDF ---
@bot.message_handler(func=lambda message: message.text == '📄 Gerar PDF')
def enviar_pdf(message):
    chat_id = message.chat.id
    historico = obter_extrato(chat_id)
    if not historico:
        bot.reply_to(message, "Sem dados para gerar relatório.")
        return
        
    bot.reply_to(message, "⏳ Preparando seu PDF...")
    pdf_path = f"extrato_{chat_id}.pdf"
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, f"Relatorio Financeiro - Fire Bot")
    c.setFont("Helvetica", 10)
    c.drawString(100, 735, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.line(100, 725, 500, 725)
    
    y = 700
    saldo_total = 0
    c.setFont("Helvetica", 12)
    for tipo, valor, data in historico:
        sinal = "+" if tipo == "Entrada" else "-"
        c.drawString(100, y, f"{data} - {tipo}: {sinal} R$ {valor:.2f}")
        saldo_total += valor if tipo == 'Entrada' else -valor
        y -= 20
        if y < 50:
            c.showPage()
            y = 750
            
    c.line(100, y, 500, y)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y - 20, f"Saldo Final: R$ {saldo_total:.2f}")
    c.save()
    
    with open(pdf_path, 'rb') as f:
        bot.send_document(chat_id, f, visible_file_name="Extrato_Fire.pdf")
    os.remove(pdf_path)

if __name__ == '__main__':
    init_db()
    print("Fire Bot conectado com sucesso no Render!")
    bot.infinity_polling()
