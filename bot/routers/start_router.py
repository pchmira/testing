"""
Модуль с роутерами для телеграмма.
"""
import random

import requests
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, Text
from aiogram.types import Message, ReplyKeyboardRemove

from bot.db.postgres import get_user_data, add_stats_for_user
from bot.keyboards.keyboard_for_start import keyboard_for_start
from bot.states.states import MainState


async def cmd_hello(message: Message, state: FSMContext) -> None:
    """
    Метод, отвечающий за приветственное сообщение.
    - Удаляет прошлые состояния.
    - Отправляет сообщение о выборе.
    - Отправляет к сообщению клавиатуру с выбором.
    - Удаляет прошлое сообщение, чтобы не сорить чат.
    - Устанавливает состояние начального меню.

    :param message: Сообщение, в котором была вызвана команда "/start".
    :param state: Состояние, которое было на текущий момент вызова команды.

    :return: None. Отправляем сообщение в чат с начальным меню.
    """
    # Завершаем все прошлые состояния.
    await state.finish()

    if message.text == "/start":
        # Формируем текст ответа, используя f-строку для вставки полного имени из данных сообщения.
        content = f"Выберите что Вам нужно, {message.from_user.full_name}:"

        # Клавиатура для прикрепления к сообщению.
        keyboard = keyboard_for_start

        # Отправляем сообщение и прикрепляем к нему клавиатуру основного меню.
        await message.answer(
            text=content,
            reply_markup=keyboard,
        )

        # Удаляем сообщение с командой "/start".
        await message.delete()

        # Устанавливаем состояние на состояние основного меню.
        await state.set_state(MainState.start_state.state)
    else:
        # Устанавливаем состояние на состояние основного меню.
        await state.set_state(MainState.start_state.state)


async def go_to_test(message: Message, state: FSMContext):
    """
    Метод, который реализует переход от главного меню, к меню выбора тестов, для прохождения.

    :param message: Сообщение == "Пройти тест". Можем взять из него любую информацию.
    :param state: Текущее состояние. Можно сюда попасть только из основного меню.

    :return: None. Сообщение с выбором нужного теста. И клавиатурой.
    """
    # Текст сообщения, которое мы отправим.
    content = "Чтобы выбрать тест напишите и отправьте название теста без пробелов и в нужном регистре.\n\n"

    # Получаем список всех тестов.
    list_all_test = await list_test()

    # Если тест есть.
    if len(list_all_test) != 0:

        # Вызываем класс удаления клавиатуры у сообщения. Поэтому в конце у класса стоит "()".
        keyboard = ReplyKeyboardRemove()

        # Формируем сообщение с названиями тестов.
        for i in range(len(list_all_test)):
            # Называем строку +1 (тк range начинается с 0), дальше название теста.
            content += f"{i + 1}) {list_all_test[i][0]}\n"

        # Отправка сообщения в чат, с выбором тестов.
        await message.answer(
            text=content,
            reply_markup=keyboard,
        )

        # Удаляем пришедшее сообщение, чтобы не засорять чат.
        await message.delete()

        # Устанавливаем состояние выбора тестов.
        await state.set_state(MainState.choose_test.state)
    else:
        # Если тестов нет, высылаем сообщение об этом.
        await message.answer(
            text="Сейчас нет никаких доступных тестов."
        )
        # Вызываем сброс состояний и устанавливаем состояние на меню.
        await cmd_hello(message, state)


async def testing_choose(message: Message, state: FSMContext):
    """
    Метод, который проводит формирование сообщения с выбранным тестом.

    :param message: Объект типа Message.
    :param state: Состояние.

    :return: Сообщение с тестом.
    """
    chosen_test = message.text

    # Отправляем запрос на API в котором хотим получить инфу о тесте, с теекущий именем.
    response = requests.get("http://127.0.0.1:8000/test_info", {"name": chosen_test})

    # Получаем ответ в json формате - формате dict.
    all_good = response.json()

    # Если данные пришли.
    if all_good:

        # Формируем сообщение по тесту и строку с правильными ответами.
        message_test, right_answer = await get_message_for_test(all_good)

        # Отправляем сообщение с тестом.
        await message.answer(text=message_test)

        # Устанавливаем в состояние строку правильных ответов, чтобы в следующем состоянии провести её соответствие
        # с ответом пользователя
        await state.set_data(right_answer.get("data").strip())

        # Устанавливаем состояние в следующее - прохождение теста.
        await state.set_state(MainState.testing_process)
    else:

        # Если с API нам ничего не вернулось.
        await message.answer(
            text="Такого теста не существует, проверьте правильность."
        )

        # Устанавливаем состояние главного меню.
        await state.set_state(MainState.start_state)

        # Возвращаем сообщение и функцию с выбором теста.
        return await go_to_test(message, state)


async def testing_process(message: Message, state: FSMContext):
    """
    Метод, который проводит принятие теста.

    :param message: Сообщение, которое отправил пользователь(тут его ответ на тест)
    :param state: Состояние, в нем есть строка с правильным ответом.

    :return: Сообщение в чат.
    """
    # Получаем данные из состояния - там хранится строка с верными ответами.
    data = await state.get_data()

    # Получаем текст пользователя, с ответами на тест.
    data_text = message.text

    # Сравниваем ответ пользователя с правильным.
    if data_text == data:

        # Если совпал ответ - обновим данные в профиле, если он существует.
        if await add_stats_for_user(user_id=message.from_user.id, is_good=True):
            await message.answer(
                text="Вы успешно прошли тест, ваша статистика обновлена!\nПоздравляем!"
            )

        # Если профиля не существует - результаты не записаны и выдано сообщение о создании профиля.
        else:
            await message.answer(
                text="Вы успешно прошли тест, но у вас отсутствует профиль, ваши данные не сохранились.\nЧтобы создать "
                     "профиль - зайдите в основном меню в раздел 'Профиль'."
            )

        # Сбросим все состояния и вернем главное меню.
        return await cmd_hello(message, state)

    # Если ответ не верный.
    else:

        # Попробуем обновить данные для пользователя, если он есть.
        if await add_stats_for_user(user_id=message.from_user.id, is_good=False):
            await message.answer(
                text="Вы не прошли тест, ваша статистика обновлена.\nПопробуй ещё разок!"
            )

        # Если пользователя нет - результаты не считаются и просим создать профиль.
        else:
            await message.answer(
                text="Вы не прошли тест, и у вас отсутствует профиль, ваши данные не сохранились.\nЧтобы создать "
                     "профиль - зайдите в основном меню в раздел 'Профиль'."
            )

        # Обнуляем состояния и возвращаем главное меню.
        return await cmd_hello(message, state)


async def get_message_for_test(test_info: list) -> tuple[str, dict]:
    """
    Метод, который формирует сообщение для теста.

    :param test_info: Список данных о тесте по его имени.

    :return: Кортеж с сообщением и словарем с ключом "data" в котором правильные ответы.
    """
    # Сообщение с название теста и примером ответа.
    content = "Вы выбрали тест: " + test_info[0][-1] + ("\n\n-----\nПример ответа:\n\n1-ИКСС\n2-М.А.Бонч-Бруевич\n"
                                                       
                                                        "3-1703\n-----\n")
    right_answer = ""

    # Проходим по вопросу в списке.
    for i in range(0, len(test_info)):

        # Добавляем к сообщени номер вопроса и его содержание.
        content += f"{i+1}) {test_info[i][0]}"

        # Формируем сообщение с верным ответом, которое отправим вторым параметром.
        right_answer += f"{i+1}-{test_info[i][-2]}\n"

        # Добавляем отступы в сообщение.
        content += "\n\n"

        # Получаем все варианты ответов, чтобы сделать их случайным образом.
        answers = [test_info[i][1], test_info[i][2], test_info[i][3], test_info[i][4]]

        # С помощью библиотеки random создаем список из 4 значений списка answers в случайном порядке.
        answers_random = random.sample(answers, 4)

        # Добавляем в сообщение варианты ответов.
        content += f"1){answers_random[0]}\n2){answers_random[1]}\n3){answers_random[2]}\n4){answers_random[3]}"

        # Добавляем отступы в сообщение.
        content += "\n\n"
    return content, {"data": right_answer}


async def create_test(message: Message, state: FSMContext):
    """
    Метод, который осуществляет переход от главного меню, к меню создание тестов, сначала спрашивает точно ли мы хотим
    создать тест, или нет.

    :param message: Сообщение вида "Создать тест". Можем получить из него информацию.
    :param state: Состояние на момент вызова этого метода. Вызывается только из основного меню.

    :return: None. Сообщение с текстом.
    """
    # Текст сообщения, которое мы отправим.
    content = "Для создания текста необходимо написать 10 вопросов и ответов к ним в определенном формате, " \
              "описанном ниже.\nОбязательные параметры для корректного теста:\n - КАЖДЫЙ вопрос оканчивается '?'\n" \
              "- Чтобы корректно составить тест необходимо вводить вопрос ответ СТРОГО в заданном формате, учитывая " \
              "пробелы, знаки препинания и т.д\n- КАЖДЫЙ тест должен иметь УНИКАЛЬНОЕ название.\n\n!!! Если хотите " \
              "добавить 10 вопросов к уже существующему тесту - напишите его название, без пробелов(как он записан" \
              " при выборе тестов) и дальше вопросы как в примере\n\n" \
              "Пример:\n\nОбщий тест\n\nНазовите год основания города Санкт-Петербрг?\n1803/1802/1905/1703 (1703)\n\n" \
              "В честь кого назван СПбГУТ?\nМ.А.Бонч-Бруевич/А.С.Пушкин/А.Н.Николаева/Э.Р.Мамедова (М.А.Бонч-Бруевич)" \
              "\n\n...\n\nНа каком вы факультете?\nРТС/ИКСС/СЦТ/ЦЕУБИ (ИКСС)"

    # Вызываем класс удаления клавиатуры у сообщения. Поэтому в конце у класса стоит "()".
    keyboard = ReplyKeyboardRemove()

    # Отправка сообщения в чат.
    await message.answer(
        text=content,
        reply_markup=keyboard,
    )

    # Устанавливаем состояние создания теста.
    await state.set_state(MainState.choose_create_test.state)


async def created_test(message: Message, state: FSMContext):
    """
    Метод, который создает запрос на добавление теста в БД.

    :param message: Текст с новым тестом.
    :param state: Состояние.

    :return: Возвращает сообщение о создании теста.
    """
    # Получаем текст сообщения с тестом.
    message_text = message.text

    # Преобразуем наше сообщение в словарь, который отправим в теле запроса.
    objects = await get_dict_with_test(message_text)

    # Если у нас получилось добавить тест в БД.
    if await create_test_from_db(objects):
        await message.answer(
            text="Вопрос был занесен в базу данных.",
        )

    # Если произошла ошибка при добавлении.
    else:
        await message.answer(
            text="Во время создания теста произошла ошибка.\nПроверьте корректность вопросов или обратитесь в поддержку"
        )

    # Обнуляем состояния и возвращаем главное меню.
    await cmd_hello(message, state)


async def get_dict_with_test(text: str) -> dict:
    """
    Метод, который преобразует строчное выражение с содержанием теста в словарь.

    :param text: Текст теста.

    :return: Возвращаем словарь с ключами.
    """
    # Создаем объект типа словарь.
    objects = {}

    # Разделяем наше сообщение по отступам - получаем список из "Вопрос?1)ответ..".
    result = text.split("\n\n")

    # Получаем название теста.
    test_name = result[0]

    # Обрезаем результат с начала, чтобы убрать 0 элемент массива, в котором находится название теста.
    result = result[1:]

    # Создаем key-value значение в словаре - ключ "test_name"/значение - название теста.
    objects["test_name"] = test_name

    # Создаем счетчик, чтобы задавать ключ в словаре, означающий номер вопроса.
    counter = 1

    # Проходимся по каждому вопросу из списка.
    for answer in result:

        # Создаем словарь, в котором будем записывать данные по текущему вопросу.
        objects_ = {}

        # Разделяем и получаем вопрос и ответы по знаку вопроса - "?".
        question, answers = answer.split("?")

        # Добавляем к вопросу знак вопроса.
        question += "?"

        # Добавляем в словарь вопрос, очищенный от пробелов со всех сторон.
        objects_["question"] = question.strip()

        # Разделяем строку с ответами, на 4 ответа по "/".
        answer_1, answer_2, answer_3, answer_4 = answers.strip().split("/")

        # Отделяем в строке с 4 ответом - ответ и правильный ответ из скобок.
        answer_4, correct_answer = answer_4.split("(")

        # Убираем в правильном ответе скобку справа.
        correct_answer = correct_answer[:-1]

        # В 4 ответе убираем пробел справа.
        answer_4 = answer_4[:-1]

        # Добавляем в словарь 4 значения с ответами + правильный ответ + какой по счету это вопрос.
        objects_["answer_1"] = answer_1.strip()
        objects_["answer_2"] = answer_2.strip()
        objects_["answer_3"] = answer_3.strip()
        objects_["answer_4"] = answer_4.strip()
        objects_["correct_answer"] = correct_answer.strip()
        objects[f"quest_{counter}"] = objects_

        # Увеличиваем счетчик на 1.
        counter += 1

    return objects


async def create_test_from_db(test_dict: dict) -> bool:
    """
    Метод, который отправляет запрос в API на создание теста.

    :param test_dict: Словарь с данными теста.

    :return: True / False - в зависимости от того, выполнился запрос или нет.
    """
    # Отправляем HTTP запрос тип POST, в котором передаем данные по тесту.
    response = requests.post("http://127.0.0.1:8000/create_test", json=test_dict)

    # Получаем текст ответа.
    all_good = response.text

    # Если текст - правда, то отправляем True - запрос выполнился корректно.
    if all_good == "true":
        return True

    # Если что-то другое - ответ не выполнен корректно.
    else:
        return False


async def list_test():
    """
    Метод, который возвращает список всех доступных тестов.

    :return: Список тестов.
    """
    # Отправляем HTTP запрос типа GET, для получения всех уникальных названий тестов.
    response = requests.get("http://127.0.0.1:8000/test_list")

    # Преобразуем ответ API в json - в текущем случае в список.
    answer = response.json()
    return answer


async def show_profile(message: Message, state: FSMContext):
    """
    Метод, который реализует отображение профиля студента/преподавателя.

    :param message: Сообщение вида "Профиль". Можно получить отсюда информацию.
    :param state: Состояние при вызове. Можно вызвать только из основного меню.

    :return: None. Сообщение с информацией профиля.
    """
    # Текст сообщения, которое мы отправим.
    content = ""

    # Если профиля не существует - создаем его
    if not await get_user_data(message.from_user.id, message.from_user.full_name):

        # Получаем данные о пользователе, после того, как создали запись.
        user_id, all_test, good_tests, name = await get_user_data(message.from_user.id,
                                                                  message.from_user.full_name,
                                                                  is_create=True
                                                                  )

    # Если пользователь есть - возвращает данные о нем.
    else:
        user_id, all_test, good_tests, name = await get_user_data(message.from_user.id, message.from_user.full_name)

    # Обновляем сообщние, исходя из полученных данных из БД.
    content += (f"ID пользователя: {user_id}\n\nИмя пользователя: {name}\n\nКоличество пройденных тестов: {all_test}"
                f"\n\nПоложительных тестов: {good_tests}")

    # Вызываем класс удаления клавиатуры у сообщения. Поэтому в конце у класса стоит "()".
    keyboard = ReplyKeyboardRemove()

    # Отправка сообщения в чат с информацией о профиле и удаление клавиатуры.
    await message.answer(
        text=content,
        reply_markup=keyboard,
    )

    # Обнуляем состояния и возвращаем главное меню.
    await cmd_hello(message, state)


async def tech_help(message: Message, state: FSMContext):
    """
    Метод, который дает информацию о Тех. Поддержке.

    :param message: Сообщение вида "Тех. Поддержка". Можно получить отсюда информацию.
    :param state: Состояние при вызове. Можно вызвать только из основного меню.

    :return: None. Сообщение с информацией о Тех. Поддержке.
    """
    # Текст сообщения, которое мы отправим.
    content = "Если возникли проблемы - пишите на почту ..."

    # Вызываем класс удаления клавиатуры у сообщения. Поэтому в конце у класса стоит "()".
    keyboard = ReplyKeyboardRemove()

    # Отправка сообщения в чат с информацией о Тех. Поддержке и удаление клавиатуры.
    await message.answer(
        text=content,
        reply_markup=keyboard,
    )

    # Обнуляем состояния и возвращаем главное меню.
    await cmd_hello(message, state)


# регистрируем хендлер
def register_base_commands(dp: Dispatcher):
    dp.register_message_handler(cmd_hello, Command('start'), state="*")
    dp.register_message_handler(go_to_test, Text(equals="Пройти тест"), state=MainState.start_state)
    dp.register_message_handler(create_test, Text(equals="Создать тест"), state=MainState.start_state)
    dp.register_message_handler(show_profile, Text(equals="Профиль"), state=MainState.start_state)
    dp.register_message_handler(tech_help, Text(equals="Тех. Поддержка"), state=MainState.start_state)
    dp.register_message_handler(created_test, state=MainState.choose_create_test)
    dp.register_message_handler(testing_choose, state=MainState.choose_test)
    dp.register_message_handler(testing_process, state=MainState.testing_process)
