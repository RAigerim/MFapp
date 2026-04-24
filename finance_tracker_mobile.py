import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# --- СИСТЕМА АВТОРИЗАЦИИ ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
 
# Проверка авторизации ПЕРЕД показом интерфейса
if not st.session_state.authenticated:
    # Страница входа
    
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.title("🔐 Finance Tracker")
    st.markdown("### Введите пароль для доступа")
    
    password = st.text_input("Пароль:", type="password", key="password_input")
    
    if st.button("🔓 Войти", type="primary", use_container_width=True):
        # ⚠️ ВАЖНО: Измените этот пароль на свой!
        CORRECT_PASSWORD = "runningman2010"
        
        if password == CORRECT_PASSWORD:
            st.session_state.authenticated = True
            st.success("✅ Вход выполнен успешно!")
            st.rerun()
        else:
            st.error("❌ Неверный пароль")
    
    # st.markdown('</div>', unsafe_allow_html=True)
    # st.info("💡 Для изменения пароля отредактируйте переменную CORRECT_PASSWORD в коде")
    st.stop()
 
# ШАГ 2: Добавьте кнопку выхода в сайдбар
# Этот код добавьте ПОСЛЕ строки st.title("💰 Finance Tracker")
# и ПЕРЕД строкой spreadsheet = connect_gsheet()
 
with st.sidebar:
    st.markdown("### 👤 Аккаунт")
    st.markdown(f"**Статус:** Авторизован ✅")
    
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Навигация")
    st.markdown("• **Аналитика** - просмотр отчетов")
    st.markdown("• **Загрузка** - импорт выписок")
    st.markdown("• **Данные** - редактирование")




# Настройка для мобильных устройств
st.set_page_config(
    page_title="💰 Finance Tracker",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS для мобильной адаптации
st.markdown("""
<style>
    /* Мобильная оптимизация */
    .main {
        padding: 1rem;
    }
    
    .stButton button {
        width: 100%;
        height: 50px;
        font-size: 18px;
        margin: 10px 0;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    
    .upload-section {
        border: 2px dashed #667eea;
        border-radius: 15px;
        padding: 30px;
        text-align: center;
        background: #f8f9fa;
        margin: 20px 0;
    }
    
    /* Увеличенные шрифты для мобильных */
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    
    .medium-font {
        font-size: 18px !important;
    }
    
    /* Адаптивные графики */
    @media (max-width: 768px) {
        .stPlotlyChart {
            height: 300px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- КОНСТАНТЫ ---
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1nXkcUanjzLsq7DTxktQOqXal7AOS0kELnGbygyZt7WY/edit?gid=201416046#gid=201416046"
SHEET_NAME = "Data"

CATEGORY_MAP = {
    "WILDBERRIES": "Одежда",
    "OZON": "Одежда",
    "ARBUZ": "Супермаркет",
    "YANDEX": "Такси",
    "UBER": "Такси",
    "WOLT": "Еда на заказ / Кафе",
    "SPOTIFY": "Телефон/Подписка",
    "AVIATA": "Путешествия",
    "KASPI": "Дом",
    "OLIVE YOU": "Еда на заказ / Кафе",
    "DRUJBA": "Еда на заказ / Кафе",
    "UDACHA": "Еда на заказ / Кафе",
    "FILKA": "Еда на заказ / Кафе",
    "KAMPIT": "Еда на заказ / Кафе",
    "АВТОБУС": "Автобус",
    "BINANCE": "Binance",
    "КОММУНАЛЬНЫЕ": "Комм+интернет",
    "ИНТЕРНЕТ": "Комм+интернет",
    "РАССРОЧКА": "Рассрочка",
    "ТЕЛЕФОН": "Телефон/Подписка"
}

CATEGORIES = [
    "Аренда", 
    "Комм+интернет", 
    "Рассрочка", 
    "Косметика/Здоровье", 
    "Телефон/Подписка", 
    "Binance",
    "Супермаркет", 
    "Еда на заказ / Кафе", 
    "Такси", 
    "Дом", 
    "Автобус", 
    "Подарки", 
    "Развлечение", 
    "Одежда", 
    "Путешествия",
    "Прочее"
]

TYPES = ["Expense", "Income", "Savings"]

# --- ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ---
@st.cache_resource
def connect_gsheet():
    """Подключение к Google Sheets"""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scope
        )
        client = gspread.authorize(creds)
        
        # Открываем таблицу по ID из URL
        sheet_id = "1nXkcUanjzLsq7DTxktQOqXal7AOS0kELnGbygyZt7WY"
        spreadsheet = client.open_by_key(sheet_id)
        
        return spreadsheet
    except Exception as e:
        st.error(f"❌ Ошибка подключения к Google Sheets: {str(e)}")
        return None

def get_or_create_fact_bank_sheet(spreadsheet):
    """Получить или создать лист Fact_bank"""
    try:
        # Пытаемся открыть существующий лист
        sheet = spreadsheet.worksheet("Fact_bank")
    except:
        # Создаем новый лист
        sheet = spreadsheet.add_worksheet(title="Fact_bank", rows=100, cols=5)
        # Добавляем заголовки
        sheet.update('A1', [['Date', 'Bank', 'Summa']], value_input_option='USER_ENTERED')
    
    return sheet

def save_bank_balance(spreadsheet, bank_name, balance):
    """Сохранить фактический остаток банка"""
    try:
        sheet = get_or_create_fact_bank_sheet(spreadsheet)
        
        # Текущая дата
        current_date = datetime.now().strftime('%d.%m.%Y')
        
        # Форматируем сумму
        balance_formatted = f"{balance:.2f}".replace('.', ',')
        
        # Добавляем запись
        sheet.append_row([current_date, bank_name, balance_formatted], value_input_option='USER_ENTERED')
        
        return True
    except Exception as e:
        st.error(f"❌ Ошибка сохранения остатка: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False

def load_bank_balances(spreadsheet):
    """Загрузить последние остатки банков"""
    try:
        sheet = get_or_create_fact_bank_sheet(spreadsheet)
        data = sheet.get_all_values()
        
        if len(data) <= 1:
            return pd.DataFrame(columns=['Date', 'Bank', 'Summa'])
        
        # Создаем DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])
        
        if df.empty:
            return df
        
        # Парсим суммы
        def parse_amount(value):
            if not value or value == '':
                return 0.0
            value_str = str(value).replace(' ', '').replace(',', '.')
            try:
                return float(value_str)
            except:
                return 0.0
        
        df['Summa'] = df['Summa'].apply(parse_amount)
        df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y', errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"❌ Ошибка загрузки остатков: {str(e)}")
        return pd.DataFrame(columns=['Date', 'Bank', 'Summa'])

# --- ФУНКЦИИ ОБРАБОТКИ ---
def detect_category(text):
    """Определение категории по описанию"""
    text = text.upper()
    for keyword, category in CATEGORY_MAP.items():
        if keyword in text:
            return category
    return "Прочее"

def detect_type(amount, details):
    """Определение типа транзакции"""
    details_lower = details.lower()
    
    # Income - положительные суммы
    if amount > 0:
        if "возврат" in details_lower or "пополнение" in details_lower:
            return "Income"
        return "Income"
    
    # Expense - отрицательные суммы
    # Aviata и крупные суммы можно отметить как Savings вручную
    return "Expense"

def is_valid_transaction(details):
    """Проверка валидности транзакции"""
    invalid_keywords = [
        "перевод валюты freedom",
        "сумма в обработке",
        "возврат кешбека",
        "списание кешбэков"
    ]
    details_lower = details.lower()
    return not any(keyword in details_lower for keyword in invalid_keywords)

def parse_bank_balance(file):
    """Извлечение остатков на счетах из PDF выписки"""
    try:
        with pdfplumber.open(file) as pdf:
            first_page = pdf.pages[0].extract_text()
        
        balances = {}
        
        # Определяем банк по тексту
        bank_name = "Unknown"
        if "Фридом Банк" in first_page or "Freedom Bank" in first_page:
            bank_name = "Freedom"
        elif "Kaspi" in first_page or "КАСПИ" in first_page:
            bank_name = "Kaspi"
        
        # Паттерн для поиска остатков
        # Упрощенный: ищем "KZT <число> ₸"
        # Формат в PDF: KZ25551U129110656KZT KZT 1,213,379.71 ₸
        pattern = r'KZT\s+([\d\s,\.]+)\s*₸'
        matches = re.findall(pattern, first_page)
        
        if matches:
            # Берем первое совпадение с большой суммой (остаток на счете)
            # Обычно это первое значение с запятыми (больше 1000)
            for match in matches:
                balance_str = match.strip()
                
                # Пропускаем маленькие суммы (это не остаток)
                if ',' not in balance_str and '.' not in balance_str:
                    continue
                
                # Парсим сумму (запятая = разделитель тысяч, точка = десятичный)
                balance_clean = balance_str.replace(' ', '').replace(',', '')
                
                try:
                    balance = float(balance_clean)
                    
                    # Остаток обычно больше 100 (фильтруем мелкие суммы)
                    if balance > 100:
                        return {
                            'bank': bank_name,
                            'balance': balance,
                            'currency': 'KZT'
                        }
                except Exception as e:
                    continue
        
        st.warning("⚠️ Паттерн остатка не найден в PDF")
        return None
        
    except Exception as e:
        st.warning(f"⚠️ Не удалось извлечь остаток из выписки: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def parse_pdf(file, last_date=None):
    """Парсинг PDF выписки банка с фильтрацией по дате"""
    transactions = []
    debug_info = []
    
    try:
        with pdfplumber.open(file) as pdf:
            debug_info.append(f"Всего страниц: {len(pdf.pages)}")
            
            # Пропускаем первую страницу (сводка)
            for page_num, page in enumerate(pdf.pages):
                if page_num == 0:
                    continue
                
                debug_info.append(f"\n=== Страница {page_num + 1} ===")
                
                # Извлекаем таблицу со страницы
                tables = page.extract_tables()
                
                if not tables:
                    debug_info.append("Нет таблиц")
                    continue
                
                debug_info.append(f"Найдено таблиц: {len(tables)}")
                
                for table_idx, table in enumerate(tables):
                    debug_info.append(f"Таблица {table_idx + 1}: {len(table)} строк")
                    
                    for row_idx, row in enumerate(table):
                        if not row or len(row) < 4:
                            continue
                        
                        # Пропускаем заголовки и служебные строки
                        if row[0] in ['Дата', None, ''] or 'Сумма в обработке' in str(row[0]):
                            continue
                        
                        date_str = str(row[0]).strip() if row[0] else ""
                        
                        # Проверяем формат даты: 22.04.2026
                        if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', date_str):
                            continue
                        
                        debug_info.append(f"  Строка {row_idx}: {date_str}")
                        
                        # Фильтрация по дате
                        if last_date:
                            try:
                                current_date = datetime.strptime(date_str, '%d.%m.%Y')
                                debug_info.append(f"    Проверка: {current_date.date()} > {last_date.date()}?")
                                
                                if current_date <= last_date:
                                    debug_info.append(f"    ❌ Пропущено (дата <= {last_date.date()})")
                                    continue
                                else:
                                    debug_info.append(f"    ✅ Проходит фильтр")
                            except Exception as e:
                                debug_info.append(f"    ⚠️ Ошибка парсинга даты: {e}")
                                pass
                        
                        # Извлекаем данные
                        amount_str = str(row[1]).strip() if len(row) > 1 and row[1] else "0"
                        currency = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                        operation_type = str(row[3]).strip() if len(row) > 3 and row[3] else ""
                        details = str(row[4]).strip() if len(row) > 4 and row[4] else ""
                        
                        debug_info.append(f"    Операция: {operation_type[:30]}")
                        debug_info.append(f"    Детали: {details[:50]}")
                        
                        if not operation_type or not details:
                            debug_info.append(f"    ❌ Пропущено (нет операции или деталей)")
                            continue
                        
                        # Убираем переносы строк для проверки
                        operation_clean = operation_type.replace('\n', ' ').replace('\r', ' ').lower()
                        
                        # Пропускаем суммы в обработке
                        if "обработке" in operation_clean or "обработке" in details.lower():
                            debug_info.append(f"    ❌ Пропущено (в обработке)")
                            continue
                        
                        # Проверка валидности
                        if not is_valid_transaction(details):
                            debug_info.append(f"    ❌ Пропущено (невалидная транзакция)")
                            continue
                        
                        # Парсинг суммы
                        # Формат: +200,000.00 ₸ (запятая = разделитель тысяч, точка = десятичный)
                        # или: -23,210.00 ₸
                        
                        # Убираем все лишнее
                        amount_clean = amount_str.replace(" ", "").replace("₸", "").replace("T", "")
                        
                        # Убираем знаки + и -
                        has_plus = '+' in amount_clean
                        amount_clean = amount_clean.replace("+", "").replace("-", "")
                        
                        # В этом формате PDF:
                        # - запятая (,) = разделитель тысяч → убираем
                        # - точка (.) = десятичный разделитель → оставляем
                        amount_clean = amount_clean.replace(",", "")
                        
                        debug_info.append(f"    Сумма: {amount_str} -> {amount_clean}")
                        
                        try:
                            amount = float(amount_clean)
                            debug_info.append(f"    Парсинг суммы: {amount}")
                        except Exception as e:
                            debug_info.append(f"    ❌ Ошибка парсинга суммы: {e}")
                            continue
                        
                        if amount == 0:
                            debug_info.append(f"    ❌ Пропущено (сумма = 0)")
                            continue
                        
                        debug_info.append(f"    ✅✅ Транзакция успешно добавлена в список!")
                        
                        # Определение типа транзакции
                        trans_type = detect_type(amount if '+' in amount_str else -amount, details)
                        
                        transaction = {
                            "День": date_str,
                            "Расход": amount,
                            "Описание": details.replace('\n', ' ')[:200],
                            "Категория": detect_category(details),
                            "Тип": trans_type
                        }
                        
                        transactions.append(transaction)
                        debug_info.append(f"    Транзакций в списке: {len(transactions)}")
    
    except Exception as e:
        st.error(f"❌ Ошибка при парсинге PDF: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        
        # Показываем отладочную информацию
        if debug_info:
            with st.expander("🔍 Отладочная информация парсинга"):
                st.text("\n".join(debug_info))
        
        return pd.DataFrame()
    
    # Добавляем итоговую информацию
    debug_info.append(f"\n{'='*60}")
    debug_info.append(f"ИТОГО найдено транзакций: {len(transactions)}")
    debug_info.append(f"{'='*60}")
    
    # Показываем отладочную информацию
    if debug_info:
        with st.expander("🔍 Отладочная информация парсинга"):
            st.text("\n".join(debug_info))
    
    df = pd.DataFrame(transactions)
    
    # Убираем дубликаты
    if not df.empty:
        before_dedup = len(df)
        df = df.drop_duplicates(subset=['День', 'Расход', 'Описание'])
        after_dedup = len(df)
        
        if before_dedup != after_dedup:
            st.info(f"🔄 Удалено дубликатов: {before_dedup - after_dedup}")
    
    return df
    """Парсинг PDF выписки банка"""
    transactions = []
    
    try:
        with pdfplumber.open(file) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        
        # Улучшенный паттерн для Freedom Bank
        pattern = r'(\d{2}\.\d{2}\.\d{4})\s+([+-]?[\d\s,\.]+)\s*₸?\s*KZT\s+(Покупка|Платеж|Пополнение|Перевод|Снятие)\s+(.+?)(?=\n\d{2}\.\d{2}\.\d{4}|\n\n|$)'
        
        matches = re.findall(pattern, full_text, re.MULTILINE | re.DOTALL)
        
        for date_str, amount_str, operation_type, details in matches:
            # Очистка деталей
            details = details.strip().replace('\n', ' ')
            
            if not is_valid_transaction(details):
                continue
            
            # Парсинг суммы
            amount_clean = amount_str.replace(" ", "").replace(",", ".")
            try:
                amount = float(amount_clean)
            except:
                continue
            
            # Определение знака для разных типов операций
            if operation_type in ["Покупка", "Платеж", "Перевод", "Снятие"]:
                amount = -abs(amount)
            else:  # Пополнение
                amount = abs(amount)
            
            transaction = {
                "День": date_str,
                "Расход": abs(amount),
                "Описание": details[:100],  # Ограничиваем длину
                "Категория": detect_category(details),
                "Тип": detect_type(amount, details)
            }
            
            transactions.append(transaction)
    
    except Exception as e:
        st.error(f"❌ Ошибка при парсинге PDF: {str(e)}")
        return pd.DataFrame()
    
    return pd.DataFrame(transactions)

def load_data_from_sheets(sheet):
    """Загрузка данных из Google Sheets"""
    try:
        # Получаем сырые данные со всеми форматами
        data = sheet.get_all_values()
        
        if not data or len(data) <= 1:
            return pd.DataFrame(columns=["День", "Расход", "Описание", "Категория", "Тип"])
        
        # Первая строка - заголовки
        headers = data[0]
        rows = data[1:]
        
        # Создаем DataFrame
        df = pd.DataFrame(rows, columns=headers)
        
        # Убираем пустые строки
        df = df[df['День'].str.strip() != '']
        
        if df.empty:
            return df
        
        # Обработка столбца Расход
        if 'Расход' in df.columns:
            def parse_amount(value):
                """Парсинг суммы из разных форматов"""
                if pd.isna(value) or value == '':
                    return 0.0
                
                # Конвертируем в строку
                value_str = str(value).strip()
                
                if value_str == '':
                    return 0.0
                
                # Удаляем пробелы (разделители тысяч)
                value_str = value_str.replace(' ', '')
                
                # Заменяем запятую на точку (десятичный разделитель)
                value_str = value_str.replace(',', '.')
                
                try:
                    return float(value_str)
                except ValueError:
                    return 0.0
            
            df['Расход'] = df['Расход'].apply(parse_amount)
        
        return df
        
    except Exception as e:
        st.error(f"❌ Ошибка загрузки данных: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return pd.DataFrame(columns=["День", "Расход", "Описание", "Категория", "Тип"])

def get_last_date_from_sheets(sheet):
    """Получить последнюю дату из Google Sheets"""
    try:
        df = load_data_from_sheets(sheet)
        
        if df.empty or 'День' not in df.columns:
            return None
        
        # Парсим даты
        df['Дата'] = pd.to_datetime(df['День'], format='%d.%m.%Y', errors='coerce')
        df = df[df['Дата'].notna()]
        
        if df.empty:
            return None
        
        # Находим максимальную дату
        last_date = df['Дата'].max()
        
        return last_date
        
    except Exception as e:
        st.warning(f"⚠️ Не удалось получить последнюю дату: {str(e)}")
        return None

def find_new_transactions(existing_df, new_df):
    """Поиск новых транзакций (избегаем дубликатов)"""
    if existing_df.empty:
        return new_df
    
    # Создаем уникальный ключ для каждой транзакции
    existing_df['key'] = existing_df['День'].astype(str) + "_" + existing_df['Расход'].astype(str) + "_" + existing_df['Описание'].astype(str)
    new_df['key'] = new_df['День'].astype(str) + "_" + new_df['Расход'].astype(str) + "_" + new_df['Описание'].astype(str)
    
    # Фильтруем только новые
    new_transactions = new_df[~new_df['key'].isin(existing_df['key'])]
    new_transactions = new_transactions.drop('key', axis=1)
    
    return new_transactions

def append_to_sheets(sheet, df):
    """Добавление данных в Google Sheets"""
    try:
        # Получаем текущее количество строк
        existing_data = sheet.get_all_values()
        start_row = len(existing_data) + 1
        
        # Подготавливаем данные для записи
        values = []
        for _, row in df.iterrows():
            # Форматируем число с запятой для Google Sheets
            try:
                raskhod_value = float(row['Расход'])
                # Форматируем с 2 знаками после запятой
                raskhod_formatted = f"{raskhod_value:.2f}".replace('.', ',')
            except (ValueError, TypeError):
                raskhod_formatted = '0,00'
            
            values.append([
                str(row['День']),
                raskhod_formatted,
                str(row['Описание']),
                str(row['Категория']),
                str(row['Тип'])
            ])
        
        # Записываем все строки за один раз
        if values:
            sheet.append_rows(values, value_input_option='USER_ENTERED')
        
        return True
    except Exception as e:
        st.error(f"❌ Ошибка при добавлении данных: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False

# --- ИНТЕРФЕЙС ---
st.title("💰 Finance Tracker")

# Кнопка выхода в сайдбаре
with st.sidebar:
    st.markdown("### 👤 Аккаунт")
    st.markdown("**Статус:** ✅ Авторизован")
    
    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Навигация")
    st.markdown("• **Аналитика** - просмотр отчетов")
    st.markdown("• **Загрузка** - импорт выписок")
    st.markdown("• **Данные** - редактирование")

# Подключение к Google Sheets
spreadsheet = connect_gsheet()

if spreadsheet is None:
    st.error("⚠️ Не удалось подключиться к Google Sheets. Проверьте файл авторизации.")
    st.stop()

# Получаем основной лист с данными
try:
    data_sheet = spreadsheet.worksheet(SHEET_NAME)
except Exception as e:
    st.error(f"❌ Не удалось открыть лист {SHEET_NAME}: {str(e)}")
    st.stop()

# Tabs для навигации
tab1, tab2, tab3 = st.tabs(["📊 Аналитика", "📤 Загрузка", "📋 Данные"])

# --- TAB 1: АНАЛИТИКА ---
with tab1:
    # Загружаем данные
    df = load_data_from_sheets(data_sheet)
    
    # Загружаем остатки банков
    bank_balances_df = load_bank_balances(spreadsheet)
    
    # Блок с фактическими остатками банков
    st.markdown("#### 🏦 BANK Balance")
    
    if not bank_balances_df.empty:
        # Получаем последние остатки по каждому банку
        latest_balances = bank_balances_df.sort_values('Date', ascending=False).groupby('Bank').first().reset_index()
        
        total_balance = latest_balances['Summa'].sum()
        
        # Определяем количество банков
        num_banks = len(latest_balances)
        
        # Показываем общий остаток в первой колонке
        if num_banks <= 5:
            # Если банков <= 5, показываем в одной строке (1 + 5 = 6 колонок)
            cols = st.columns(num_banks + 1)
            
            with cols[0]:
                st.metric("💰 Overall bank amount", f"{total_balance:,.0f} ₸")
            
            # Показываем банки
            for idx, (_, row) in enumerate(latest_balances.sort_values('Summa', ascending=False).iterrows()):
                with cols[idx + 1]:
                    bank_icon = "🟢" if row['Bank'] == "Freedom" else "🔵" if row['Bank'] == "Kaspi" else "🏦"
                    date_str = row['Date'].strftime('%d.%m.%Y') if pd.notna(row['Date']) else ''
                    st.metric(
                        f"{bank_icon} {row['Bank']}", 
                        f"{row['Summa']:,.0f} ₸",
                        delta=f"от {date_str}"
                    )
        else:
            # Если банков > 5, показываем в две строки
            # Первая строка - общий баланс
            st.metric("💰 Всего в банках", f"{total_balance:,.0f} ₸")
            
            # Вторая строка - банки (по 6 в ряду)
            cols = st.columns(min(6, num_banks))
            
            for idx, (_, row) in enumerate(latest_balances.iterrows()):
                col_idx = idx % 6
                with cols[col_idx]:
                    bank_icon = "🟢" if row['Bank'] == "Freedom" else "🔵" if row['Bank'] == "Kaspi" else "🏦"
                    date_str = row['Date'].strftime('%d.%m.%Y') if pd.notna(row['Date']) else ''
                    st.metric(
                        f"{bank_icon} {row['Bank']}", 
                        f"{row['Summa']:,.0f} ₸",
                        delta=f"от {date_str}"
                    )
        
        st.markdown("---")
    else:
        st.info("📊 Загрузите выписку для отображения остатков в банках")
        st.markdown("---")
    
    if df.empty:
        st.info("📊 Нет данных для отображения. Загрузите выписку.")
    else:
        # Конвертируем дату и фильтруем некорректные данные
        df['Дата'] = pd.to_datetime(df['День'], format='%d.%m.%Y', errors='coerce')
        df['Расход'] = pd.to_numeric(df['Расход'], errors='coerce').fillna(0)
        
        # Убираем строки с некорректными датами или нулевыми суммами
        df = df[df['Дата'].notna()]
        df = df[df['Расход'] > 0]
        
        if df.empty:
            st.warning("⚠️ Нет корректных данных для анализа. Проверьте формат данных в Google Sheets.")
            st.stop()
        
        df['Месяц'] = df['Дата'].dt.to_period('M')
        df['МесяцДата'] = df['Дата'].dt.to_period('M').dt.to_timestamp()
        
        # 1) БАЛАНС = Все доходы - все расходы (включая Savings)
        st.markdown("#### 💳 Current month")
        current_month = pd.Timestamp.now().to_period('M')
        
        total_income = df[(df['Тип'] == 'Income') & (df['Месяц'] == current_month)]['Расход'].sum()
        total_expenses = df[df['Тип'].isin(['Expense', 'Savings']) & (df['Месяц'] == current_month)]['Расход'].sum()
        balance = total_income - total_expenses
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            delta_color = "normal" if balance >= 0 else "inverse"
            st.metric("💵 Balance", f"{balance:,.0f} ₸")
            # , delta=f"{balance:,.0f} ₸"
            
        with col2:
            st.metric("💸 Expenses", f"{total_expenses:,.0f} ₸")
        with col3:
            st.metric("💰 Income", f"{total_income:,.0f} ₸")
            
        
        st.markdown("---")
        
        # АНАЛИТИКА ПО НАКОПЛЕНИЯМ
        st.markdown("#### 💎 Saving Analysis")
        
        # Группируем по месяцам
        monthly_income = df[df['Тип'] == 'Income'].groupby('МесяцДата')['Расход'].sum()
        monthly_expenses = df[df['Тип'].isin(['Expense', 'Savings'])].groupby('МесяцДата')['Расход'].sum()
        
        # Создаем общий индекс для всех месяцев
        all_months = sorted(set(monthly_income.index) | set(monthly_expenses.index))
        
        savings_data = []
        for month in all_months:
            income = monthly_income.get(month, 0)
            expenses = monthly_expenses.get(month, 0)
            saved = income - expenses
            saved_percent = (saved / income * 100) if income > 0 else 0
            
            savings_data.append({
                'Месяц': month,
                'Доход': income,
                'Расход': expenses,
                'Отложено': saved,
                'Процент': saved_percent
            })
        
        savings_df = pd.DataFrame(savings_data)
        
        if not savings_df.empty:
            # Общая сумма отложенных денег
            total_saved = savings_df['Отложено'].sum()
            avg_saved_percent = savings_df['Процент'].mean()
            
            # Сортируем по дате и берем последние 7 месяцев
            savings_df = savings_df.sort_values('Месяц', ascending=False).head(7)
            savings_df = savings_df.sort_values('Месяц')
            savings_df['МесяцТекст'] = savings_df['Месяц'].dt.strftime('%b %Y')
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("💰 Total Saved", f"{total_saved:,.0f} ₸")
            with col2:
                st.metric("📊 Average Savings %", f"{avg_saved_percent:.1f}%")
            
            # График накоплений
            fig_savings = go.Figure()
            
            fig_savings.add_trace(go.Bar(
                x=savings_df['МесяцТекст'],
                y=savings_df['Доход'],
                name='Доход',
                marker_color='#10b981',
                text=savings_df['Доход'].apply(lambda x: f"{x:,.0f}₸"),
                textposition='outside'
            ))
            
            fig_savings.add_trace(go.Bar(
                x=savings_df['МесяцТекст'],
                y=savings_df['Расход'],
                name='Расход',
                marker_color='#ef4444',
                text=savings_df['Расход'].apply(lambda x: f"{x:,.0f}₸"),
                textposition='outside'
            ))
            
            fig_savings.add_trace(go.Scatter(
                x=savings_df['МесяцТекст'],
                y=savings_df['Отложено'],
                name='Отложено',
                mode='lines+markers+text',
                line=dict(color='#8b5cf6', width=3),
                marker=dict(size=10),
                text=savings_df['Отложено'].apply(lambda x: f"{x:,.0f}₸"),
                textposition='top center',
                yaxis='y2'
            ))
            
            fig_savings.update_layout(
                title='Income vs Expenses vs Savings',
                xaxis_title='Month',
                yaxis_title='Amount (₸)',
                yaxis2=dict(
                    title='Saved (₸)',
                    overlaying='y',
                    side='right'
                ),
                barmode='group',
                height=500,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_savings, use_container_width=True)
            
            # Таблица с процентами
            st.markdown("##### 📋 Detailed Monthly Breakdown:")
            savings_display = savings_df[['МесяцТекст', 'Доход', 'Расход', 'Отложено', 'Процент']].copy()
            savings_display.columns = ['Month', 'Income', 'Expenses', 'Saved', 'Savings %']
            savings_display['Income'] = savings_display['Income'].apply(lambda x: f"{x:,.0f} ₸")
            savings_display['Expenses'] = savings_display['Expenses'].apply(lambda x: f"{x:,.0f} ₸")
            savings_display['Saved'] = savings_display['Saved'].apply(lambda x: f"{x:,.0f} ₸")
            savings_display['Savings %'] = savings_display['Savings %'].apply(lambda x: f"{x:.1f}%")
            
            st.dataframe(savings_display, hide_index=True, use_container_width=True)
        
        st.markdown("---")
        
        # 2) Гистограмма доходов по месяцам за последние 7 месяцев
        # st.markdown("#### 📊 Доходы за последние 7 месяцев")
        
        # income_df = df[df['Тип'] == 'Income'].copy()
        # income_monthly = income_df.groupby('МесяцДата')['Расход'].sum().reset_index()
        # income_monthly = income_monthly.sort_values('МесяцДата', ascending=False).head(7)
        # income_monthly = income_monthly.sort_values('МесяцДата')
        # income_monthly['Месяц'] = income_monthly['МесяцДата'].dt.strftime('%b %Y')
        
        # if not income_monthly.empty:
        #     fig1 = px.bar(
        #         income_monthly,
        #         x='Месяц',
        #         y='Расход',
        #         title='Доходы по месяцам',
        #         text='Расход',
        #         color_discrete_sequence=['#10b981']
        #     )
        #     fig1.update_traces(texttemplate='%{text:,.0f}₸', textposition='outside')
        #     fig1.update_layout(
        #         height=400,
        #         showlegend=False,
        #         xaxis_title="Месяц",
        #         yaxis_title="Сумма (₸)"
        #     )
        #     st.plotly_chart(fig1, use_container_width=True)
        # else:
        #     st.info("Нет данных о доходах")
        
        # 3) Гистограмма расходов за текущий месяц по категориям
        st.markdown("#### 📊 Expenses by Category for Current Month")
        
        
        current_month_df = df[
            (df['Месяц'] == current_month) & 
            (df['Тип'].isin(['Expense', 'Savings']))
        ].copy()
        
        if not current_month_df.empty:
            category_current = current_month_df.groupby('Категория')['Расход'].sum().reset_index()
            category_current = category_current.sort_values('Расход', ascending=False).reset_index()
            
            fig2 = px.bar(
                category_current,
                x='Категория',
                y='Расход',
                title=f'Расходы по категориям ({current_month})',
                text='Расход',
                color='Расход',
                color_continuous_scale='Reds'
            )
            fig2.update_traces(texttemplate='%{text:,.0f}₸', textposition='outside')
            fig2.update_layout(
                height=400,
                showlegend=False,
                xaxis_title="Категория",
                yaxis_title="Сумма (₸)",
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Показываем топ-3 категории
            st.markdown("##### 🏆 Топ-3 категории расходов в этом месяце:")
            for idx, row in category_current.head(3).iterrows():
                total = category_current['Расход'].sum()
                percent = (row['Расход'] / total) * 100 if total > 0 else 0
                st.markdown(f"**{idx+1}. {row['Категория']}**: {row['Расход']:,.0f} ₸ ({percent:.1f}%)")
        else:
            st.info(f"Нет расходов за {current_month}")
        
        # 4) Расходы за последние 7 месяцев по месяцам
        # st.markdown("#### 📊 Расходы за последние 7 месяцев")
        
        # expenses_df = df[df['Тип'].isin(['Expense', 'Savings'])].copy()
        # expenses_monthly = expenses_df.groupby('МесяцДата')['Расход'].sum().reset_index()
        # expenses_monthly = expenses_monthly.sort_values('МесяцДата', ascending=False).head(7)
        # expenses_monthly = expenses_monthly.sort_values('МесяцДата')
        # expenses_monthly['Месяц'] = expenses_monthly['МесяцДата'].dt.strftime('%b %Y')
        
        # if not expenses_monthly.empty:
        #     fig3 = px.bar(
        #         expenses_monthly,
        #         x='Месяц',
        #         y='Расход',
        #         title='Расходы по месяцам',
        #         text='Расход',
        #         color_discrete_sequence=['#ef4444']
        #     )
        #     fig3.update_traces(texttemplate='%{text:,.0f}₸', textposition='outside')
        #     fig3.update_layout(
        #         height=400,
        #         showlegend=False,
        #         xaxis_title="Месяц",
        #         yaxis_title="Сумма (₸)"
        #     )
        #     st.plotly_chart(fig3, use_container_width=True)
            
        #     # Средний расход
        #     avg_expense = expenses_monthly['Расход'].mean()
        #     st.info(f"📊 Средний расход за месяц: **{avg_expense:,.0f} ₸**")
        # else:
        #     st.info("Нет данных о расходах")
        
        # 5) Таблица расходов Savings по категориям за все время
        st.markdown("#### 🏦 Крупные расходы (Savings) по категориям")
        
        savings_df = df[df['Тип'] == 'Savings'].copy()
        
        if not savings_df.empty:
            savings_by_category = savings_df.groupby('Категория').agg({
                'Расход': ['sum', 'count']
            }).reset_index()
            savings_by_category.columns = ['Категория', 'Сумма', 'Количество']
            savings_by_category = savings_by_category.sort_values('Сумма', ascending=False)
            savings_by_category['Процент'] = (savings_by_category['Сумма'] / savings_by_category['Сумма'].sum() * 100).round(1)
            
            # Итоговая статистика (до форматирования)
            total_savings = savings_by_category['Сумма'].sum()
            total_count = savings_by_category['Количество'].sum()
            
            # Форматируем для отображения
            savings_display = savings_by_category.copy()
            savings_display['Сумма'] = savings_display['Сумма'].apply(lambda x: f"{x:,.0f} ₸")
            savings_display['Процент'] = savings_display['Процент'].apply(lambda x: f"{x}%")
            
            st.dataframe(
                savings_display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Категория": st.column_config.TextColumn("Категория", width="medium"),
                    "Сумма": st.column_config.TextColumn("Сумма", width="medium"),
                    "Количество": st.column_config.NumberColumn("Кол-во", width="small"),
                    "Процент": st.column_config.TextColumn("%", width="small"),
                }
            )
            
            st.success(f"💰 Всего крупных расходов: **{total_savings:,.0f} ₸** ({total_count} транзакций)")
            
            # График Savings по категориям
            # fig4 = px.pie(
            #     savings_by_category,
            #     names='Категория',
            #     values='Сумма',
            #     title='Распределение крупных расходов (Savings)',
            #     hole=0.4
            # )
            # fig4.update_traces(textposition='inside', textinfo='percent+label')
            # fig4.update_layout(height=400)
            # st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Нет расходов типа Savings. Отметьте крупные траты в разделе 'Данные'.")

# --- TAB 2: ЗАГРУЗКА PDF ---
with tab2:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown("#### 📄 Загрузите банковскую выписку")
    
    uploaded_file = st.file_uploader(
        "Выберите PDF файл",
        type=["pdf"],
        help="Загрузите выписку из Freedom Bank или Kaspi"
    )
    
    if uploaded_file:
        with st.spinner("🔄 Обработка файла..."):
            # 0. Получаем последнюю дату из таблицы
            last_date = get_last_date_from_sheets(data_sheet)
            
            if last_date:
                st.info(f"📅 Последняя дата в таблице: **{last_date.strftime('%d.%m.%Y')}**. Ищем только новые транзакции.")
            else:
                st.info("📅 Таблица пустая, загружаем все транзакции.")
            
            # 1. Извлекаем остаток банка
            bank_balance_info = parse_bank_balance(uploaded_file)
            
            if bank_balance_info:
                st.info(f"🏦 Обнаружен остаток в {bank_balance_info['bank']}: **{bank_balance_info['balance']:,.2f} ₸**")
            
            # 2. Парсим транзакции (только после last_date)
            new_transactions = parse_pdf(uploaded_file, last_date=last_date)
            
            if not new_transactions.empty:
                st.success(f"✅ Найдено {len(new_transactions)} новых транзакций")
                
                # Показываем превью
                st.markdown("##### Предпросмотр новых транзакций:")
                st.dataframe(new_transactions, use_container_width=True)
                
                # Кнопка добавления
                if st.button("➕ Добавить в Google Sheets", type="primary", key="add_transactions"):
                    success_count = 0
                    
                    # Добавляем транзакции
                    if append_to_sheets(data_sheet, new_transactions):
                        st.success("✅ Транзакции успешно добавлены!")
                        success_count += 1
                    
                    # Сохраняем остаток банка
                    if bank_balance_info:
                        if save_bank_balance(spreadsheet, bank_balance_info['bank'], bank_balance_info['balance']):
                            st.success(f"✅ Остаток {bank_balance_info['bank']} сохранен!")
                            success_count += 1
                    
                    if success_count > 0:
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Ошибка при добавлении данных")
            else:
                st.warning("⚠️ Нет новых транзакций для добавления")
                
                # Все равно можем сохранить остаток
                if bank_balance_info:
                    if st.button("💾 Сохранить только остаток банка", key="save_balance_only"):
                        if save_bank_balance(spreadsheet, bank_balance_info['bank'], bank_balance_info['balance']):
                            st.success(f"✅ Остаток {bank_balance_info['bank']} обновлен!")
                            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


# --- TAB 3: ДАННЫЕ ---
with tab3:
    df = load_data_from_sheets(data_sheet)
    
    if df.empty:
        st.info("📋 Нет данных для отображения")
    else:
        st.markdown("#### 📋 Все транзакции")
        
        # Поиск
        search = st.text_input("🔍 Поиск по описанию:", "")
        
        if search:
            df_display = df[df['Описание'].str.contains(search, case=False, na=False)]
        else:
            df_display = df
        
        st.markdown(f"**Всего записей:** {len(df_display)}")
        
        # Таблица с возможностью редактирования
        edited_df = st.data_editor(
            df_display,
            column_config={
                "Категория": st.column_config.SelectboxColumn(
                    "Категория",
                    options=CATEGORIES,
                    required=True
                ),
                "Тип": st.column_config.SelectboxColumn(
                    "Тип",
                    options=TYPES,
                    required=True
                ),
                "Расход": st.column_config.NumberColumn(
                    "Расход",
                    format="%.2f ₸"
                )
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )
        
        # Кнопка сохранения изменений
        if st.button("💾 Сохранить изменения в Google Sheets", type="primary"):
            try:
                # Очищаем лист (кроме заголовков)
                data_sheet.clear()
                
                # Подготавливаем все данные для записи
                values = [["День", "Расход", "Описание", "Категория", "Тип"]]
                
                # Записываем все данные
                for _, row in edited_df.iterrows():
                    # Безопасное форматирование числа
                    try:
                        raskhod_value = float(row['Расход'])
                        raskhod_formatted = f"{raskhod_value:.2f}".replace('.', ',')
                    except (ValueError, TypeError):
                        raskhod_formatted = '0,00'
                    
                    values.append([
                        str(row['День']),
                        raskhod_formatted,
                        str(row['Описание']),
                        str(row['Категория']),
                        str(row['Тип'])
                    ])
                
                # Записываем все за один раз
                data_sheet.update('A1', values, value_input_option='USER_ENTERED')
                
                st.success("✅ Изменения сохранены!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Ошибка: {str(e)}")
                import traceback
                st.error(traceback.format_exc())

# Footer
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: #666;'>"
    f"💡 <a href='{GOOGLE_SHEET_URL}' target='_blank'>Открыть Google Sheets</a> | "
    f"Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    f"</div>",
    unsafe_allow_html=True
)