import paramiko
import subprocess
import re
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from dotenv import load_dotenv
import os
import logging
import psycopg2
from psycopg2 import Error
import time
from telegram import Update
from telegram.ext import CallbackContext

load_dotenv()



# Подключаем логирование
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

LOG_FILE_PATH = "/var/log/postgresql/postgresql.log"

SSH_HOST = os.getenv("RM_HOST")
SSH_PORT = os.getenv("RM_PORT")
SSH_USERNAME = os.getenv("RM_USER")
SSH_PASSWORD = os.getenv("RM_PASSWORD")

#Настраиваем ssh соединение и выполнение команд
def ssh_exec_command(command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USERNAME, password=SSH_PASSWORD)
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8')
    ssh.close()
    return output

def connect_to_db():
    try:
        connection = psycopg2.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"), 
            database=os.getenv("DB_DATABASE")
        )
        return connection
    except Error as e:
        logger.error(f"Ошибка подключения к PostgreSQL: {e}")
        return None

#Функционал по сбору данных с удаленного хоста
def get_release(update, context):
    output = ssh_exec_command("cat /etc/*release")
    update.message.reply_text(output)

def get_uname(update, context):
    output = ssh_exec_command("uname -a")
    update.message.reply_text(output)

def get_uptime(update, context):
    output = ssh_exec_command("uptime")
    update.message.reply_text(output)

def get_df(update, context):
    output = ssh_exec_command("df -h")
    update.message.reply_text(output)

def get_free(update, context):
    output = ssh_exec_command("free -m")
    update.message.reply_text(output)

def get_mpstat(update, context):
    output = ssh_exec_command("mpstat")
    update.message.reply_text(output)

def get_w(update, context):
    output = ssh_exec_command("w")
    update.message.reply_text(output)

def get_auths(update, context):
    output = ssh_exec_command("last -n 10")
    update.message.reply_text(output)

def get_critical(update, context):
    output = ssh_exec_command("tail -n 5 /var/log/faillog")
    update.message.reply_text(output)

def get_ps(update, context):
    output = ssh_exec_command("ps")
    update.message.reply_text(output)

def get_ss(update, context):
    output = ssh_exec_command("ss -tuln")
    update.message.reply_text(output)

def get_apt_list(update, context):
    args = context.args
    if args:
        package_name = args[0]
        output = ssh_exec_command(f"apt show {package_name}")
    else:
        output = ssh_exec_command("apt list --installed | head -n 10")
    update.message.reply_text(output)

def get_services(update, context):
    output = ssh_exec_command("systemctl list-units --type=service --state=running")
    update.message.reply_text(output)


#Обработка команды для поиска номеров телефонов
def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'find_phone_number'

#Обработка команды для поиска Email
def findEmailCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска Email-адресов: ')

    return 'find_email'

#Обработка команды для проверки пароля
def verifyPasswordCommand(update: Update, context):
    update.message.reply_text('Введите пароль: ')

    return 'verify_password'

#Поиск номеров телефона
def findPhoneNumbers (update: Update, context):
    user_input = update.message.text 

    phoneNumRegex = re.compile(r'((?:\+7|8)[-\s]?[(]?\d{3}[)]?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})') 

    phoneNumberList = phoneNumRegex.findall(user_input) 

    if not phoneNumberList: 
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END
    
    phoneNumbers = '' 
    for i in range(len(phoneNumberList)):
        phoneNumbers += f'{i+1}. {phoneNumberList[i]}\n' 

    update.message.reply_text(phoneNumbers)
    update.message.reply_text('Хотите добавить в базу данных? (/yes or /no)') 
    context.user_data['phone_list'] = phoneNumberList
    return ConversationHandler.END 

#Поиск Email
def findEmail (update: Update, context):
    user_input = update.message.text 

    emailRegex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b') 

    EmailList = emailRegex.findall(user_input) 

    if not EmailList: 
        update.message.reply_text('Email-адреса не найдены')
        return ConversationHandler.END
    
    Email = '' 
    for i in range(len(EmailList)):
        Email += f'{i+1}. {EmailList[i]}\n' 
        
    update.message.reply_text(Email)
    update.message.reply_text('Хотите добавить в базу данных? (/yes or /no)')
    context.user_data['email_list'] = EmailList
    return ConversationHandler.END 


def email_add (emails):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            for email in emails:
                cursor.execute("INSERT INTO Email (email_address) VALUES (%s)", (email,))
            connection.commit()
            logging.info("Команда успешно выполнена")
            cursor.close()
            connection.close()
            return True
        except Error as error:
            logging.error("Ошибка при добавлении адресов: %s", error)
            connection.close()
            return False
    else:
        return []


def phone_add (phone_numbers):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            for phone in phone_numbers:
                cursor.execute("INSERT INTO Phone (phone_number) VALUES (%s)", (phone,))
            connection.commit()
            logging.info("Команда успешно выполнена")
            cursor.close()
            connection.close()
            return True
        except Error as error:
            logging.error("Ошибка при добавлении номеров: %s", error)
            connection.close()
            return False
    else:
        return []


def yes_command (update, context):
    email_list = context.user_data.get('email_list', [])
    phone_list = context.user_data.get('phone_list', [])
    if email_list:
        data = email_add(email_list)
        if data:
            update.message.reply_text('Электронные адреса успешно сохранены в базе данных!')
        else:
            update.message.reply_text('Ошибка при записи данных!')
    elif phone_list:
        data = phone_add(phone_list)
        if data:
            update.message.reply_text('Номера телефона успешно сохранены в базе данных!')
        else:
            update.message.reply_text('Ошибка при записи данных!')

    context.user_data.clear()

def no_command (update, context):
    update.message.reply_text('Операция отменена.')
    context.user_data.clear()

#Проверка пароля
def VerifyPassword (update: Update, context):
    user_input = update.message.text 

    passwordRegex = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()]).{8,}$') 

    Pass = passwordRegex.findall(user_input) 

    if not Pass: 
        update.message.reply_text('Пароль простой')
        return ConversationHandler.END 
    else:
        update.message.reply_text('Пароль сложный')
        return ConversationHandler.END 
    

def get_email(update, context):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT email_address FROM Email;")
            data = cursor.fetchall()
            for row in data:
                update.message.reply_text(row)
            logging.info("Команда успешно выполнена")
            cursor.close()
            connection.close()
        except Error as error:
            logging.error("Ошибка при получении адресов: %s", error)
            connection.close()
    else:
        return []



def get_phone_number(update, context):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT phone_number FROM Phone;")
            data = cursor.fetchall()
            for row in data:  
                update.message.reply_text(row)
            logging.info("Команда успешно выполнена")
            cursor.close()
            connection.close()
        except Error as error:
            logging.error("Ошибка при получении номеров: %s", error)
        finally:
            if connection is not None:
                cursor.close()
                connection.close()


def get_repl_log(update: Update, context: CallbackContext) -> None:
    try:
        # Выполнение команды для получения логов
        result = subprocess.run(
            ["bash", "-c", f"cat {LOG_FILE_PATH} | grep repl | tail -n 15"],
            capture_output=True,
            text=True,
            check=True  # Проверка наличия ошибок выполнения
        )
        logs = result.stdout
        if logs:
            update.message.reply_text(f"Последние репликационные логи:\n{logs}")
        else:
            update.message.reply_text("Репликационные логи не найдены.")
    except subprocess.CalledProcessError as e:
        update.message.reply_text(f"Ошибка при выполнении команды: {e}")
    except Exception as e:
        update.message.reply_text(f"Ошибка при получении логов: {str(e)}")

        # Создаем обработчик команды /get_repl_logs
repl_logs_handler = CommandHandler('get_repl_log', get_repl_log)


def echo(update: Update, context):
    update.message.reply_text(update.message.text)


def main():
    updater = Updater(os.getenv("TOKEN"), use_context=True)

    
    dp = updater.dispatcher

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            'find_phone_number': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
        },
        fallbacks=[]
    )

    convHandlerFindEmail = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailCommand)],
        states={
            'find_email': [MessageHandler(Filters.text & ~Filters.command, findEmail)],
        },
        fallbacks=[]
    )

    convHandlerVerifyPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verifyPasswordCommand)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, VerifyPassword)],
        },
        fallbacks=[]
    )

	# Регистрируем обработчики команд
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerFindEmail)	
    dp.add_handler(convHandlerVerifyPassword)
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dp.add_handler(CommandHandler("get_services", get_services))
    
    
    dp.add_handler(CommandHandler("get_emails", get_email))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_number))
    dp.add_handler(CommandHandler("yes", yes_command))
    dp.add_handler(CommandHandler("no", no_command))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_log))
	# Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
		
	# Запускаем бота
    updater.start_polling()

	# Останавливаем бота при нажатии Ctrl+C
    updater.idle()


if __name__ == '__main__':
    main()
