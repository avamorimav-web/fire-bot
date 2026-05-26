import os
import telebot
from google import genai
from google.genai import types
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3

# ======= CONFIGURAÇÕES INICIAIS =======
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

bot = telebot.TeleBot(TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

# Inicializa o Agendador de Alarmes/Lembretes
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
    # Tabela de Lembretes/Alarmes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            texto TEXT,
            horario TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ======= FUNÇÃO DE DISPARO DO ALARME =======
def disparar_alarme(user_id, texto_lembrete):
    try:
        mensagem_alarme = f"🔔 **ALARME ATIVO, ALEXANDRE!**\n\n📌 **Lembrete:** {texto_lembrete}"
        bot.send_message(user_id, message_alarme, parse_mode="Markdown")
    except Exception as e:
        print(f"Erro ao disparar alarme: {e}")

# ======= TECLADO DE BOTÕES (MENU) =======
def menu_principal():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_entrada = telebot.types.KeyboardButton('➕ Entrada')
    btn_saida = telebot.types.KeyboardButton('➖ Saída')
    btn_extrato = telebot.types.KeyboardButton('📊 Extrato Mensal')
    btn_lembrete = telebot.types.KeyboardButton('📅 Criar Lembrete')
    btn_sugestao = telebot.types.KeyboardButton('💡 Pedir Sugestão')
    btn_nutri = telebot.types.KeyboardButton('🍎 Relatório Nutricional')
    
    markup.add(btn_entrada, btn_saida)
    markup.add(btn_extrato, btn_lembrete)
    markup.add(btn_sugestao, btn_nutri)
    return markup

# ======= FLUXOS DOS BOTÕES FINANCEIROS =======
@bot.message_handler(func=lambda msg: msg.text in ['➕ Entrada', '➖ Saída'])
def fluxo_financeiro(message):
    tipo = 'Entrada' if '➕' in message.text else 'Saída'
    msg = bot.reply_to(message, f"Digite o valor da {tipo} (ex: 25.50) seguido da categoria (ex: 25.50 Almoço):")
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
        
        bot.reply_to(message, f"✅ {tipo} de **R$ {valor:.2f}** ({categoria}) gravada com sucesso!", parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Formato inválido. Use: `Número Categoria` (Ex: `10.00 Ônibus`)", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == '📊 Extrato Mensal')
def ver_extrato(message):
    conn = sqlite3.connect('fire_ia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tipo, valor, categoria FROM finance WHERE user_id = ?', (message.chat.id,))
    linhas = cursor.fetchall()
    conn.close()
    
    if not lines:
        bot.reply_to(message, "📊 Você não tem lançamentos este mês!")
        return
        
    resumo = "📊 **SEU EXTRATO ATUAL:**\n\n"
    total_entrada = 0
    total_saida = 0
    for tipo, valor, cat in linhas:
        resumo += f"{'🟢' if tipo == 'Entrada' else '🔴'} R$ {valor:.2f} - {cat}\n"
        if tipo == 'Entrada': total_entrada += valor
        else: total_saida += valor
        
    resumo += f"\n💰 **Total Entradas:** R$ {total_entrada:.2f}"
    resumo += f"\n📉 **Total Saídas:** R$ {total_saida:.2f}"
    resumo += f"\n⚖️ **Saldo:** R$ {(total_entrada - total_saida):.2f}"
    bot.reply_to(message, resumo, parse_mode="Markdown")

# ======= FLUXO DO BOTÃO DE LEMBRETE (AGENDA) =======
@bot.message_handler(func=lambda msg: msg.text == '📅 Criar Lembrete')
def iniciar_lembrete(message):
    msg = bot.reply_to(message, "Digite o que quer lembrar e o horário.\n\n⚠️ **Use o formato:** `HH:MM Texto` (Ex: `22:30 Tomar o remédio`)")
    bot.register_next_step_handler(msg, agendar_lembrete)

def agendar_lembrete(message):
    try:
        partes = message.text.split(maxsplit=1)
        hora_str = partes[0]
        texto_lembrete = partes[1]
        
        # Valida as horas e minutos
        hora, minuto = map(int, hora_str.split(':'))
        agora = datetime.now()
        horario_alarme = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        
        # Se o horário digitado já passou hoje, agenda para amanhã
        if horario_alarme < agora:
            from datetime import timedelta
            horario_alarme += timedelta(days=1)
            
        # Salva no Banco de Dados
        conn = sqlite3.connect('fire_ia.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO reminders (user_id, texto, horario) VALUES (?, ?, ?)',
                       (message.chat.id, texto_lembrete, horario_alarme.strftime('%Y-%m-%d %H:%M')))
        conn.commit()
        conn.close()
        
        # Cria o Alarme Ativo no Relógio do Servidor (APScheduler)
        scheduler.add_job(
            disparar_alarme, 
            'date', 
            run_date=horario_alarme, 
            args=[message.chat.id, texto_lembrete]
        )
        
        bot.reply_to(message, f"⏰ **Alarme Configurado!**\n\n🔔 Vou te chamar às **{hora_str}** para: _{texto_lembrete}_", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "❌ Erro no formato! Certifique-se de usar `HH:MM Texto` (Ex: `08:00 Acordar`)")

# ======= 📸 OLHOS DO FIRE IA: LEITURA DE FOTOS (CADERNO/TAREFA) =======
@bot.message_handler(content_types=['photo'])
def analisar_imagem(message):
    bot.send_chat_action(message.chat.id, 'typing')
    aviso = bot.reply_to(message, "🔔 **Fire iA 'Olhos' Ativados!** Baixando imagem do caderno e analisando as questões... Aguarde.")
    
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
                types.Part.from_bytes(
                    data=bytes_imagem,
                    mime_type='image/jpeg',
                ),
                "Você é o Professor Particular do Alexandre dentro do Fire iA. Leia atentamente a imagem do caderno, transcreva as perguntas encontradas e resolva cada uma delas passo a passo de forma clara e educativa."
            ]
        )
        
        os.remove(nome_arquivo)
        bot.delete_message(message.chat.id, aviso.message_id)
        
        bot.reply_to(message, response.text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Desculpe Alexandre, tive um problema ao tentar ler essa foto. Detalhe: {e}")

# ======= 💬 CONVERSA NORMAL POR TEXTO =======
@bot.message_handler(content_types=['text'])
def conversa_ia(message):
    if message.text in ['💡 Pedir Sugestão', '🍎 Relatório Nutricional']:
        bot.reply_to(message, f"Para usar essa função, basta digitar diretamente por texto o que você precisa! Exemplo: 'Monte meu prato de almoço' ou 'Me dê sugestões de investimentos'.")
        return
        
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Você é o Fire iA, o assistente pessoal inteligente do Alexandre. Responda de forma direta, prestativa e amigável: {message.text}"
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro temporário na IA: {e}")

# ======= COMANDO START =======
@bot.message_handler(commands=['start', 'menu'])
def enviar_menu(message):
    bot.reply_to(message, "🔥 **Fire iA Ativo!** Escolha uma opção nos botões abaixo ou fale diretamente comigo:", reply_markup=menu_principal(), parse_mode="Markdown")

if __name__ == '__main__':
    print("Fire iA rodando com sucesso...")
    bot.infinity_polling()
