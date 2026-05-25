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
    conn = sqlite3.connect('controle_pessoal.db')
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

# 3. Funções do Banco de Dados e Relatório Mensal
def salvar_registro(user_id, tipo, valor):
    conn = sqlite3.connect('controle_pessoal.db')
    cursor = conn.cursor()
    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO financas (user_id, tipo, valor, data) VALUES (?, ?, ?, ?)',
                   (user_id, tipo, valor, data_atual))
    conn.commit()
    conn.close()

def pegar_extrato_mensal(user_id):
    conn = sqlite3.connect('controle_pessoal.db')
    cursor = conn.cursor()
    mes_atual = datetime.now().strftime('%Y-%m')
    cursor.execute('SELECT tipo, valor FROM financas WHERE user_id = ? AND data LIKE ?', (user_id, f"{mes_atual}%"))
    dados = cursor.fetchall()
    conn.close()
    return dados

# --- 4. MÓDULO DE INTELIGÊNCIA ARTIFICIAL (GEMINI) ---
def responder_ia(pergunta, contexto=None):
    if not ai_client:
        return "🤖 Minha IA (Gemini) não está configurada nos segredos."

    if contexto == 'nutricao':
        prompt_final = f"Gere uma tabela nutricional estimada e detalhada (calorias, carboidratos, proteínas, gorduras) e uma breve análise para: {pergunta}"
    elif contexto == 'sugestao':
        prompt_final = f"Como um assistente pessoal prestativo, dê sugestões criativas, dicas práticas e conselhos sobre o seguinte assunto: {pergunta}"
    else:
        prompt_final = pergunta

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_final,
        )
        return response.text if response.text else "🤖 A IA não conseguiu gerar uma resposta."
    except Exception as e:
        return f"⚠️ Erro na IA:\n`{str(e)}`"

# --- 5. COMANDO START (Interface Visual Atualizada) ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton('➕ Entrada')
    btn2 = telebot.types.KeyboardButton('➖ Saída')
    btn3 = telebot.types.KeyboardButton('📊 Extrato Mensal')
    btn4 = telebot.types.KeyboardButton('🍎 Relatório Nutricional')
    btn5 = telebot.types.KeyboardButton('💡 Pedir Sugestão')
    markup.add(btn1, btn2, btn3, btn4, btn5)
    
    texto_boas_vindas = (
        "Olá, Alexandre! Painel do Assistente Atualizado. 👑🔥\n\n"
        "• Clique nos botões para ativar uma função específica.\n"
        "• Para **Cálculos rápidos ou Conversa livre**, basta digitar direto no chat!"
    )
    bot.reply_to(message, texto_boas_vindas, reply_markup=markup)

# --- 6. ROTEAMENTO DOS BOTÕES ---
@bot.message_handler(func=lambda message: message.text in ['➕ Entrada', '➖ Saída', '📊 Extrato Mensal', '🍎 Relatório Nutricional', '💡 Pedir Sugestão'])
def escutar_botoes(message):
    user_id = message.chat.id
    texto = message.text

    if texto == '➕ Entrada':
        user_state[user_id] = 'esperando_entrada'
        bot.reply_to(message, "💰 Quanto entrou? Digite apenas o valor (Ex: 150.00):")
    elif texto == '➖ Saída':
        user_state[user_id] = 'esperando_saida'
        bot.reply_to(message, "💸 Quanto você gastou? Digite apenas o valor (Ex: 35.50):")
    elif texto == '📊 Extrato Mensal':
        historico = pegar_extrato_mensal(user_id)
        if not historico:
            bot.reply_to(message, "📊 Nenhuma transação financeira registrada este mês ainda!")
            return
        
        receitas = sum(valor for tipo, valor in historico if tipo == "Entrada")
        despesas = sum(valor for tipo, valor in historico if tipo == "Saída")
        saldo = receitas - despesas
        
        relatorio = (
            f"📊 **Seu Fechamento de {datetime.now().strftime('%B/%Y')}:**\n\n"
            f"🟢 **Entradas:** R$ {receitas:.2f}\n"
            f"🔴 **Saídas:** R$ {despesas:.2f}\n\n"
            f"💰 **Saldo em Caixa:** R$ {saldo:.2f}"
        )
        bot.reply_to(message, relatorio, parse_mode="Markdown")
    elif texto == '🍎 Relatório Nutricional':
        user_state[user_id] = 'esperando_comida'
        bot.reply_to(message, "📝 O que você comeu? Descreva a refeição (Ex: '2 fatias de pão integral com queijo e café'):")
    elif texto == '💡 Pedir Sugestão':
        user_state[user_id] = 'esperando_sugestao'
        bot.reply_to(message, "🤔 Sobre o que você quer sugestões ou ideias hoje? (Ex: 'ideias de treino para fazer em casa' ou 'como organizar meu dia produtivo'):")

# --- 7. PROCESSAMENTO DINÂMICO DE RESPOSTAS ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def tratar_texto_direto(message):
    user_id = message.chat.id
    texto = message.text
    estado = user_state.get(user_id)

    # Fluxo Financeiro
    if estado in ['esperando_entrada', 'esperando_saida']:
        try:
            valor_final = float(texto.replace(',', '.'))
            tipo_final = "Entrada" if estado == 'esperando_entrada' else "Saída"
            salvar_registro(user_id, tipo_final, valor_final)
            user_state[user_id] = None  
            bot.reply_to(message, f"✅ R$ {valor_final:.2f} salvos em '{tipo_final}'!")
            return
        except ValueError:
            bot.reply_to(message, "⚠️ Por favor, envie apenas números válidos.")
            return

    # Fluxo Nutricional
    if estado == 'esperando_comida':
        bot.send_chat_action(user_id, 'typing')
        bot.reply_to(message, "🔄 Analisando os componentes nutricionais...")
        relatorio = responder_ia(texto, contexto='nutricao')
        user_state[user_id] = None  
        bot.reply_to(message, relatorio, parse_mode="Markdown")
        return

    # Fluxo de Sugestões Ativas
    if estado == 'esperando_sugestao':
        bot.send_chat_action(user_id, 'typing')
        bot.reply_to(message, "💡 Elaborando ideias para você...")
        sugestao = responder_ia(texto, contexto='sugestao')
        user_state[user_id] = None  
        bot.reply_to(message, sugestao, parse_mode="Markdown")
        return

    # Fluxo Livre: Se não escolheu nenhum botão, cai na IA aberta para conversar ou fazer cálculos!
    bot.send_chat_action(user_id, 'typing')
    resposta = responder_ia(texto)
    bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    bot.infinity_polling()
