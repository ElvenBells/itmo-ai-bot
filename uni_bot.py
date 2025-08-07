import telebot
import camelot
import pandas as pd

# === ТОКЕН БОТА ===
TOKEN = "8496042891:AAFXF6FyVIgY-VAYr84dB0pKOqlu3RuD3tM"
bot = telebot.TeleBot(TOKEN)

# === ПУТИ К PDF-ФАЙЛАМ ===
PDF_AI = "ai_abit.pdf"
PDF_AI_PRODUCT = "ai_product_abit.pdf"

# === Состояния бота ===
user_state = {}  # {chat_id: {stage: ..., program: ...}}
user_background = {}  # {chat_id: словарь с ответами}

# === Клавиатуры ===
def get_main_menu():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Сравнить программы")
    keyboard.add("Показать учебный план")
    keyboard.add("Рекомендации по выбору курсов")
    keyboard.add("О программе «Искусственный интеллект»", "О программе «AI Product»")
    return keyboard

# === Парсинг PDF ===
def parse_curriculum(pdf_path):
    try:
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
        curriculum = []
        for table in tables:
            df: pd.DataFrame = table.df
            if df.shape[1] < 4:
                continue
            for _, row in df.iterrows():
                try:
                    semester = row[0].strip()
                    name = row[1].strip()
                    credits = row[2].strip()
                    hours = row[3].strip()
                    if semester.isdigit() and int(semester) in [1, 2, 3, 4]:
                        curriculum.append({
                            'semester': int(semester),
                            'name': name,
                            'credits': credits,
                            'hours': hours
                        })
                except:
                    continue
        return pd.DataFrame(curriculum)
    except Exception as e:
        print(f"Ошибка при парсинге {pdf_path}: {e}")
        return pd.DataFrame()

# === Загрузка учебных планов ===
df_ai = parse_curriculum(PDF_AI)
df_ai_product = parse_curriculum(PDF_AI_PRODUCT)

print(f"Загружено курсов для 'Искусственный интеллект': {len(df_ai)}")
print(f"Загружено курсов для 'AI Product': {len(df_ai_product)}")

# === Начало опросника для сравнения программ ===
def start_program_questionnaire(chat_id):
    kb = telebot.types.ReplyKeyboardRemove()
    bot.send_message(
        chat_id,
        "🎓 Давай пройдём опрос, чтобы подобрать лучшую программу.\n\n"
        "1️⃣ Какое у тебя образование?\n"
        "Например: бакалавр по IT, магистр экономики, специалист по маркетингу.",
        reply_markup=kb
    )
    user_state[chat_id] = {'stage': 'education'}

# === Начало опросника для рекомендаций по курсам ===
def start_course_questionnaire(chat_id):
    kb = telebot.types.ReplyKeyboardRemove()
    bot.send_message(
        chat_id,
        "🎯 Отлично! Давай подберём тебе подходящие курсы.\n\n"
        "1️⃣ Какие направления тебе интересны?\n"
        "Например: машинное обучение, NLP, Computer Vision, продукт, UX, стартапы.",
        reply_markup=kb
    )
    user_state[chat_id] = {'stage': 'course_interests'}

# === Обработчики ===
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_state[chat_id] = {'stage': 'menu'}
    bot.send_message(
        chat_id,
        "🎓 Привет! Я — бот-помощник по магистерским программам ИТМО в области AI.\n"
        "Я помогу тебе выбрать программу, посмотреть учебный план и подобрать курсы.\n\n"
        "Выбери, что тебя интересует:",
        reply_markup=get_main_menu()
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip().lower()
    state = user_state.get(chat_id, {}).get('stage', 'menu')

    # --- Сравнить программы → широкий опрос ---
    if text == "сравнить программы":
        start_program_questionnaire(chat_id)

    # --- Этапы опросника для выбора программы ---
    elif state == 'education':
        user_background[chat_id] = {'education': text}
        bot.send_message(chat_id, "2️⃣ Какой у тебя опыт работы (если есть)?")
        user_state[chat_id]['stage'] = 'experience'

    elif state == 'experience':
        user_background[chat_id]['experience'] = text
        bot.send_message(chat_id, "3️⃣ Что тебе больше всего нравилось в учёбе или работе?")
        user_state[chat_id]['stage'] = 'interests'

    elif state == 'interests':
        user_background[chat_id]['interests'] = text
        bot.send_message(chat_id, "4️⃣ Какие у тебя сильные стороны?")
        user_state[chat_id]['stage'] = 'strengths'

    elif state == 'strengths':
        user_background[chat_id]['strengths'] = text
        bot.send_message(chat_id, "5️⃣ Какие у тебя цели после магистратуры?")
        user_state[chat_id]['stage'] = 'goals'

    elif state == 'goals':
        user_background[chat_id]['goals'] = text
        all_text = " ".join(user_background[chat_id].values())

        ai_score = sum(1 for kw in [
            'ml', 'machine learning', 'python', 'программирование', 'data', 'математика',
            'информатика', 'инженер', 'наука', 'research', 'алгоритмы', 'статистика', 'deep learning'
        ] if kw in all_text)

        product_score = sum(1 for kw in [
            'продукт', 'product', 'менеджмент', 'бизнес', 'стартап', 'маркетинг',
            'управление', 'инновации', 'лидерство', 'MVP', 'UX', 'UI', 'проект'
        ] if kw in all_text)

        if 'математика' in all_text or 'информатика' in all_text:
            ai_score += 1
        if 'стартап' in all_text or 'предпринимательство' in all_text:
            product_score += 1
        if 'научная работа' in all_text:
            ai_score += 1
        if 'команда' in all_text or 'лидерство' in all_text:
            product_score += 1

        if ai_score > product_score:
            rec = "✅ <b>Рекомендуем: «Искусственный интеллект»</b>\n\nТы технический специалист или исследователь."
        elif product_score > ai_score:
            rec = "✅ <b>Рекомендуем: «AI Product»</b>\n\nТы склонен к продуктовому мышлению и управлению."
        else:
            rec = "💡 <b>Обе программы тебе подходят!</b>\n\nРассмотри учебные планы и выбери по интересам."

        bot.send_message(chat_id, rec, parse_mode='HTML')
        bot.send_message(
            chat_id,
            '🔗 Подробнее:\n• <a href="https://abit.itmo.ru/program/master/ai">Искусственный интеллект</a>\n• <a href="https://abit.itmo.ru/program/master/ai_product">AI Product</a>',
            parse_mode='HTML',
            reply_markup=get_main_menu()
        )
        user_state[chat_id] = {'stage': 'menu'}

    # --- Показать учебный план ---
    elif text == "показать учебный план":
        kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("Искусственный интеллект", "AI Product")
        kb.add("Назад")
        bot.send_message(chat_id, "Выбери программу:", reply_markup=kb)

    # --- Назад в меню ---
    elif text == "назад":
        user_state[chat_id] = {'stage': 'menu'}
        bot.send_message(chat_id, "Что дальше?", reply_markup=get_main_menu())

    # --- Показать план AI ---
    elif text == "искусственный интеллект":
        if df_ai.empty:
            bot.send_message(chat_id, "Не удалось загрузить учебный план.")
        else:
            semesters = df_ai.groupby('semester')
            for sem, group in semesters:
                top_5 = group.head(5)
                courses = "\n".join([f"• {row['name']} ({row['credits']} з.е.)" for _, row in top_5.iterrows()])
                bot.send_message(
                    chat_id,
                    f"📚 <b>Семестр {sem} (Искусственный интеллект)</b>:\n\n{courses}",
                    parse_mode='HTML'
                )
        bot.send_message(chat_id, "Что дальше?", reply_markup=get_main_menu())

    # --- Показать план AI Product ---
    elif text == "ai product":
        if df_ai_product.empty:
            bot.send_message(chat_id, "Не удалось загрузить учебный план.")
        else:
            semesters = df_ai_product.groupby('semester')
            for sem, group in semesters:
                top_5 = group.head(5)
                courses = "\n".join([f"• {row['name']} ({row['credits']} з.е.)" for _, row in top_5.iterrows()])
                bot.send_message(
                    chat_id,
                    f"📚 <b>Семестр {sem} (AI Product)</b>:\n\n{courses}",
                    parse_mode='HTML'
                )
        bot.send_message(chat_id, "Что дальше?", reply_markup=get_main_menu())

    # --- Рекомендации по выбору курсов → узкий опрос ---
    elif text == "рекомендации по выбору курсов":
        start_course_questionnaire(chat_id)

    # --- Этапы узкого опросника по курсам ---
    elif state == 'course_interests':
        user_background[chat_id] = {'interests': text}
        bot.send_message(
            chat_id,
            "2️⃣ Есть ли темы, в которых чувствуешь себя слабо?\n"
            "Например: математика, Python, статистика, менеджмент."
        )
        user_state[chat_id]['stage'] = 'course_weaknesses'

    elif state == 'course_weaknesses':
        user_background[chat_id]['weaknesses'] = text
        bot.send_message(
            chat_id,
            "3️⃣ Какие карьерные цели?\n"
            "Например: стать ML Engineer, запустить стартап, работать в AI Product."
        )
        user_state[chat_id]['stage'] = 'course_goals'

    elif state == 'course_goals':
        user_background[chat_id]['goals'] = text
        bot.send_message(
            chat_id,
            "4️⃣ Предпочитаешь практику, теорию или проекты?"
        )
        user_state[chat_id]['stage'] = 'course_format'

    elif state == 'course_format':
        user_background[chat_id]['format'] = text
        all_text = " ".join(user_background[chat_id].values())
        recs = []

        # Курсы из программ
        ai_courses = df_ai[df_ai['name'].str.contains(
            'Машинное обучение|Глубокое обучение|Python|ML|NLP|Computer Vision|математика|статистика|Data Science', case=False)]
        product_courses = df_ai_product[df_ai_product['name'].str.contains(
            'Продукт|менеджмент|маркетинг|бизнес|стартап|MVP|инновации|UX|UI|аналитика', case=False)]

        # Интересы
        if 'ml' in all_text or 'machine learning' in all_text:
            top_ai = ai_courses[ai_courses['name'].str.contains('Машинное обучение', case=False)]
            if not top_ai.empty:
                recs.append("🎯 <b>Основной курс:</b> " + top_ai.iloc[0]['name'])
        if 'nlp' in all_text:
            nlp = ai_courses[ai_courses['name'].str.contains('NLP', case=False)]
            if not nlp.empty:
                recs.append("💬 <b>Курс по NLP:</b> " + nlp.iloc[0]['name'])
        if 'computer vision' in all_text:
            cv = ai_courses[ai_courses['name'].str.contains('Computer Vision', case=False)]
            if not cv.empty:
                recs.append("👁️ <b>Курс по Computer Vision:</b> " + cv.iloc[0]['name'])

        # Слабые стороны
        if 'математик' in all_text:
            math = df_ai[df_ai['name'].str.contains('Математика для ML', case=False)]
            if not math.empty:
                recs.append("🧮 <b>Укрепи базу:</b> " + math.iloc[0]['name'])
        if 'python' in all_text and 'слаб' in all_text:
            py = df_ai[df_ai['name'].str.contains('Python', case=False)]
            if not py.empty:
                recs.append("💻 <b>Python для анализа данных:</b> " + py.iloc[0]['name'])

        # Цели
        if 'стартап' in all_text:
            startup = df_ai_product[df_ai_product['name'].str.contains('Стартап-трек', case=False)]
            if not startup.empty:
                recs.append("🚀 <b>Дипломный трек:</b> " + startup.iloc[0]['name'])

        # Формат
        if 'практика' in all_text or 'проект' in all_text:
            project = df_ai[df_ai['name'].str.contains('Проект', case=False)].head(1)
            if not project.empty:
                recs.append("🔧 <b>Проектный курс:</b> " + project.iloc[0]['name'])

        if not recs:
            recs.append("📌 Совет: начни с 'Воркшоп по созданию продукта на данных' — он есть в обеих программах.")

        bot.send_message(chat_id, "Рекомендации по курсам:\n\n" + "\n".join(recs), parse_mode='HTML')
        bot.send_message(chat_id, "Что дальше?", reply_markup=get_main_menu())
        user_state[chat_id] = {'stage': 'menu'}

    # --- О программе «Искусственный интеллект» ---
    elif "о программе" in text and ("искусственный интеллект" in text or "ai" in text and "интеллект" in text):
        msg = (
            "🔹 <b>Программа: Искусственный интеллект</b>\n\n"
            "Создавайте AI-продукты и технологии, которые меняют мир.\n"
            "Проектная работа с компаниями: X5 Group, Ozon Банк, МТС, Sber AI, Норникель, Napoleon IT, Genotek, Raft, AIRI, DeepPavlov.\n\n"
            "<b>🎯 Возможные роли:</b>\n"
            "• ML Engineer — создает и внедряет ML-модели в продакшен\n"
            "• Data Engineer — выстраивает процессы сбора, хранения и обработки данных\n"
            "• AI Product Developer — разрабатывает продукты на основе AI\n"
            "• Data Analyst — анализирует массивы данных и помогает бизнесу принимать data-driven решения\n\n"
            "<b>💼 Карьерный уровень:</b> Middle\n"
            "<b>📈 Зарплата:</b> от 170 000 до 300 000 ₽\n\n"
            "<b>🎓 Выпускная работа:</b> проект, статья, стартап, курс или образовательная технология\n\n"
            "<b>🌍 Международные возможности:</b>\n"
            "• Участие в конференциях A*\n"
            "• Научные стажировки за рубежом\n"
            "• Study Abroad at Home\n"
            "• Buddy System\n"
            "• Конкурс стипендий Президента РФ для обучения за рубежом\n\n"
            "<b>📚 Формат:</b> вечерний онлайн — можно совмещать с работой\n\n"
            '<a href="https://abit.itmo.ru/program/master/ai">🔗 Подробнее на сайте</a>'
        )
        bot.send_message(chat_id, msg, parse_mode='HTML', disable_web_page_preview=True)

    # --- О программе «AI Product» ---
    elif "о программе" in text and ("ai product" in text or "ай продукт" in text or "ai продукт" in text):
        msg = (
            "🔹 <b>Программа: AI Product</b>\n\n"
            "Фокус на создании AI-продуктов, управлении проектами и предпринимательстве.\n"
            "Работа с партнёрами: Sber AI, Ozon, X5, Napoleon IT.\n\n"
            "<b>🎯 Возможные роли:</b>\n"
            "• AI Product Manager\n"
            "• Технический менеджер\n\n"
            "<b>🚀 Диплом:</b> можно защитить стартап\n\n"
            "<b>🤝 Партнёры:</b> Sber AI, Ozon, X5, Napoleon IT\n\n"
            "<b>🌍 Международные возможности:</b>\n"
            "• Участие в школах и чемпионатах\n"
            "• Study Abroad at Home\n"
            "• Buddy System\n"
            "• Конкурсы и стажировки\n\n"
            "<b>💡 Особенность:</b> развивай идею продукта и выводи её на рынок\n\n"
            '<a href="https://abit.itmo.ru/program/master/ai_product">🔗 Подробнее на сайте</a>'
        )
        bot.send_message(chat_id, msg, parse_mode='HTML', disable_web_page_preview=True)

    # --- Нерелевантные запросы ---
    else:
        bot.send_message(
            chat_id,
            "Я помогаю по вопросам магистерских программ ИТМО по AI.\n"
            "Выбери тему:",
            reply_markup=get_main_menu()
        )

# === Запуск бота ===
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)