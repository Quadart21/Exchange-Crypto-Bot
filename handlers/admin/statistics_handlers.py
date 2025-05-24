from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters import Text
from config import dp, bot
from database.db import create_connection
import matplotlib.pyplot as plt
from fpdf import FPDF
import os

# Функция для получения данных по курьерам
def get_courier_data():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT operator_id, COUNT(*) as operations, SUM(amount) as total_amount
        FROM orders
        GROUP BY operator_id
    """)
    data = cursor.fetchall()
    conn.close()
    return data

# Функция для получения данных по криптовалютам
def get_crypto_data():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT currency, COUNT(*) as operations, SUM(amount) as total_amount
        FROM orders
        GROUP BY currency
    """)
    data = cursor.fetchall()
    conn.close()
    return data

# Функция для получения данных по времени
def get_time_data():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%H', created_at) as hour, COUNT(*) as operations
        FROM orders
        GROUP BY hour
        ORDER BY operations DESC
    """)
    data = cursor.fetchall()
    conn.close()
    return data

# Создание графиков для отчета
def create_graphs(courier_data, crypto_data, time_data):
    # График по курьерам
    couriers = [row[0] for row in courier_data]
    courier_operations = [row[1] for row in courier_data]
    plt.figure(figsize=(8, 6))
    plt.bar(couriers, courier_operations, color='lightgreen')
    plt.title('Количество операций по курьерам')
    plt.xlabel('Курьеры')
    plt.ylabel('Количество операций')
    plt.savefig('courier_graph.png')
    plt.close()

    # График по криптовалютам
    cryptos = [row[0] for row in crypto_data]
    crypto_operations = [row[1] for row in crypto_data]
    plt.figure(figsize=(8, 6))
    plt.bar(cryptos, crypto_operations, color='skyblue')
    plt.title('Количество операций по криптовалютам')
    plt.xlabel('Криптовалюты')
    plt.ylabel('Количество операций')
    plt.savefig('crypto_graph.png')
    plt.close()

    # График по времени
    hours = [row[0] for row in time_data]
    hour_operations = [row[1] for row in time_data]
    plt.figure(figsize=(8, 6))
    plt.bar(hours, hour_operations, color='salmon')
    plt.title('Количество операций по часам')
    plt.xlabel('Часы')
    plt.ylabel('Количество операций')
    plt.savefig('time_graph.png')
    plt.close()

# Создание PDF отчета
class PDF(FPDF):
    def header(self):
        self.set_font('DejaVu', '', 12)
        self.cell(0, 10, 'Финансовый отчет', align='C', ln=True)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        self.cell(0, 10, f'Страница {self.page_no()}', align='C')


def create_detailed_pdf(courier_data, crypto_data, time_data):
    pdf = PDF()
    pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
    pdf.set_font('DejaVu', size=12)
    pdf.add_page()

    # Раздел по курьерам
    pdf.cell(0, 10, 'Детально проведенные операции каждым курьером:', ln=True)
    for row in courier_data:
        pdf.cell(0, 10, f'Курьер ID: {row[0]}, Количество операций: {row[1]}, Сумма: {row[2]:.2f}', ln=True)

    pdf.cell(0, 10, '', ln=True)
    pdf.cell(0, 10, 'График операций по курьерам:', ln=True)
    pdf.image('courier_graph.png', x=10, y=None, w=190)

    # Раздел по криптовалютам
    pdf.add_page()
    pdf.cell(0, 10, 'Отчеты по каждой криптовалюте:', ln=True)
    for row in crypto_data:
        pdf.cell(0, 10, f'Криптовалюта: {row[0]}, Количество операций: {row[1]}, Сумма: {row[2]:.2f}', ln=True)

    pdf.cell(0, 10, '', ln=True)
    pdf.cell(0, 10, 'График операций по криптовалютам:', ln=True)
    pdf.image('crypto_graph.png', x=10, y=None, w=190)

    # Раздел по времени
    pdf.add_page()
    pdf.cell(0, 10, 'Отчеты по времени:', ln=True)
    for row in time_data:
        pdf.cell(0, 10, f'Час: {row[0]}:00, Количество операций: {row[1]}', ln=True)

    pdf.cell(0, 10, '', ln=True)
    pdf.cell(0, 10, 'График операций по времени:', ln=True)
    pdf.image('time_graph.png', x=10, y=None, w=190)

    pdf.output('detailed_report.pdf')

# Обработчик кнопки выгрузки детального отчета
@dp.message_handler(Text(equals="Выгрузить детальный отчет"))
async def handle_detailed_report_request(message: types.Message):
    try:
        # Получение данных и создание отчета
        courier_data = get_courier_data()
        crypto_data = get_crypto_data()
        time_data = get_time_data()

        create_graphs(courier_data, crypto_data, time_data)
        create_detailed_pdf(courier_data, crypto_data, time_data)

        # Отправка PDF пользователю
        with open('detailed_report.pdf', 'rb') as file:
            await message.reply_document(file, caption="Ваш детальный финансовый отчет готов!")

        # Удаление временных файлов
        os.remove('courier_graph.png')
        os.remove('crypto_graph.png')
        os.remove('time_graph.png')
        os.remove('detailed_report.pdf')
    except Exception as e:
        await message.reply(f'Произошла ошибка при генерации отчета: {e}')

# Добавление кнопки в главное меню
async def add_detailed_report_button():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton("Выгрузить детальный отчет"))
    return menu
