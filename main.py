import os
import telebot
import sqlite3
import requests  # Para falar com a fábrica de imagens
from datetime import datetime
from google import genai
import io  # Para lidar com a imagem gerada

# 1. Configuração dos Tokens
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

# Token gratuito para gerar imagens (Hugging Face)
# Crie sua conta em huggingface.co e gere uma 'Access Token' em Settings -> Tokens
HUGGINGFACE_TOKEN = os.environ.get('HUGGINGFACE_TOKEN') 

bot = telebot.TeleBot(TOKEN)
user_state = {}

if GEMINI_KEY:
    ai_client = genai.Client(api_key=GEMINI_KEY)
else:
    ai_client = None

# 2. Criação do Banco de Dados Limpo
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

# --- 4. MÓDULO DE GERAÇÃO DE IMAGEM (GRATUITO) ---
def gerar_imagem_alta_resolucao(prompt):
    # Usando o modelo gratuito "Stable Diffusion" do Hugging Face
    API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}

    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        # Se der certo, a resposta é a própria imagem em bytes
        if response.status_code == 200:
            return response.content
        else:
            return None
    except Exception as e:
        print(f"Erro na geração de imagem: {e}")
        return None

# --- 5. MÓDULO DE INTELIGÊNCIA ARTIFICIAL (GEMINI) ---
def responder_ia(pergunta, contexto=None):
    if not ai_client:
        return "🤖 Minha IA (Gemini) não está configurada nos segredos."

    # Se for um relatório nutricional, usamos um prompt especial
    if contexto == 'nutricao':
        prompt_final = f"Gere uma tabela nutricional estimada e detalhada (calorias, carboidratos, proteínas, gorduras) para: {pergunta}"
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

# --- 6. COMANDO START ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton('➕ Entrada')
    btn2 = telebot.types.KeyboardButton('➖ Saída')
    btn3 = telebot.types.KeyboardButton('📊 Extrato do Mês')
    btn4 = telebot.types.KeyboardButton('🍎 Nutrição')
    markup.add(btn1, btn2, btn3, btn4)
    
    texto_boas_vindas = (
        "Olá, Alexandre! Sou o seu Assistente Pessoal Completo. 🔥\n\n"
        "• Para **Finanças** e **Relatórios**, use os botões.\n"
        "• Para **IA, Cálculos e Sugestões**, basta digitar!\n"
        "• Para **Gerar Imagens**, use `/img` antes da descrição. (Ex: `/img um gato voando no espaço em alta resolução`)"
    )
    bot.reply_to(message, texto_boas_vindas, reply_markup=markup)

# --- 7. MÓDULO FINANCEIRO E RELATÓRIO MENSAL ---
@bot.message_handler(func=lambda message: message.text in ['➕ Entrada', '➖ Saída', '📊 Extrato do Mês', '🍎 Nutrição'])
def escutar_botoes(message):
    user_id = message.chat.id
    texto = message.text

    if texto == '➕ Entrada':
        user_state[user_id] = 'esperando_entrada'
        bot.reply_to(message, "Digite o valor da Entrada (Ex: 50.00):")
    elif texto == '➖ Saída':
        user_state[user_id] = 'esperando_saida'
        bot.reply_to(message, "Digite o valor da Saída (Ex: 22.50):")
    elif texto == '📊 Extrato do Mês':
        historico = pegar_extrato_mensal(user_id)
        if not historico:
            bot.reply_to(message, "Nenhuma transação registrada este mês!")
            return
        
        receitas = sum(valor for tipo, valor in historico if tipo == "Entrada")
        despesas = sum(valor for tipo, valor in historico if tipo == "Saída")
        saldo = receitas - despesas
        
        relatorio = (
            f"📊 **Seu Relatório de {datetime.now().strftime('%B/%Y')}:**\n\n"
            f"🟢 **Entradas totais:** R$ {receitas:.2f}\n"
            f"🔴 **Saídas totais:** R$ {despesas:.2f}\n\n"
            f"💰 **Saldo Final:** R$ {saldo:.2f}"
        )
        bot.reply_to(message, relatorio, parse_mode="Markdown")
    elif texto == '🍎 Nutrição':
        user_state[user_id] = 'esperando_comida'
        bot.reply_to(message, "Digite o nome da comida (ex: 'arroz, feijão e frango') para eu gerar o relatório nutricional.")

# --- 8. COMANDO DE GERAÇÃO DE IMAGEM ---
@bot.message_handler(commands=['img'])
def responder_img_comando(message):
    user_id = message.chat.id
    prompt = message.text.replace('/img', '').strip()
    
    if not prompt:
        bot.reply_to(message, "⚠️ Escreva algo depois do comando! Exemplo: `/img um carro de corrida dourado`")
        return

    if not HUGGINGFACE_TOKEN:
        bot.reply_to(message, "Estou online, mas a minha chave para gerar imagens (HUGGINGFACE_TOKEN) não está configurada.")
        return

    bot.send_chat_action(user_id, 'upload_photo')
    bot.reply_to(message, "Estou gerando sua imagem em alta resolução... Isso pode levar alguns segundos.")

    imagem_bytes = gerar_imagem_alta_resolucao(prompt)
    
    if imagem_bytes:
        # Envia a imagem como um arquivo de foto para o Telegram
        bot.send_photo(user_id, io.BytesIO(imagem_bytes), caption=f"Aqui está sua imagem para: '{prompt}'")
    else:
        bot.reply_to(message, "🤖 Desculpe, a fábrica de imagens está ocupada ou deu erro. Tente novamente mais tarde.")

# --- 9. PROCESSAMENTO TOTAL LIVRE (IA E VALORES) ---
@bot.message_handler(func=lambda message: True, content_types=['text'])
def tratar_texto_direto(message):
    user_id = message.chat.id
    texto = message.text
    estado = user_state.get(user_id)

    # CENÁRIO A: Processamento Financeiro
    if estado in ['esperando_entrada', 'esperando_saida']:
        try:
            valor_final = float(texto.replace(',', '.'))
            tipo_final = "Entrada" if estado == 'esperando_entrada' else "Saída"
            salvar_registro(user_id, tipo_final, valor_final)
            user_state[user_id] = None  # Reseta o estado
            bot.reply_to(message, f"✅ R$ {valor_final:.2f} salvos em '{tipo_final}' com sucesso!")
            return
        except ValueError:
            bot.reply_to(message, "⚠️ Digite apenas números.")
            return

    # CENÁRIO B: Processamento Nutricional
    if estado == 'esperando_comida':
        bot.send_chat_action(user_id, 'typing')
        bot.reply_to(message, "Consultando a base nutricional... Aguarde.")
        relatorio = responder_ia(texto, contexto='nutricao')
        user_state[user_id] = None  # Reseta o estado
        bot.reply_to(message, relatorio, parse_mode="Markdown")
        return

    # CENÁRIO C: Conversa Livre, Cálculos e Sugestões (Chama a IA direto)
    bot.send_chat_action(user_id, 'typing')
    resposta = responder_ia(texto)
    bot.reply_to(message, resposta, parse_mode="Markdown")

if __name__ == '__main__':
    bot.infinity_polling()
