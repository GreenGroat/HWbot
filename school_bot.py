# -*- coding: utf-8 -*-
"""
### WATERMARK ###

# Dev: Pavel Krupenko #
# Git: greengroat #
# VK: @greengroat
# Telegram: @greengroat #
# Discord: '3EJLEHblN 4EJLOBEK#3374'

### WATERMARK ###


Main скрипт бота. Используется vkbottle.
"""

import datetime
import itertools
import json
import os
import sys
import time
import traceback
import zipfile
from asyncio import sleep
from datetime import timedelta

import loguru
import requests
from vkbottle import Callback, GroupEventType, GroupTypes
from vkbottle import Keyboard, KeyboardButtonColor, Text, CtxStorage, BaseStateGroup
from vkbottle import PhotoMessageUploader, DocMessagesUploader
from vkbottle.bot import Bot, Message, MessageEvent
from vkbottle_types.objects import WallPostType

from modules.botdb import BotDB
from modules.config import *
from modules.creating_images import create_img, create_report, generation_total_report
from modules.parse_site import post_to_site
from modules.paths import *
from netschoolapi import NetSchoolAPI

# Debug
loguru.logger.add(full_path_to_errors_txt, level="ERROR")
loguru.logger.add(path_to_informations_txt, level="INFO", encoding='cp866')

# Creating DataBase
db = BotDB(os.getcwd() + path_to_school_db_db)
db.making_table()

# preparatory stage
bot = Bot(vk_acces_token)
ctx = CtxStorage()


class States(BaseStateGroup):
    wall_news_header = 'wall_news_header'
    login = 'login'
    password = 'password'
    output_type = 'output_type'
    right_week = 'right_week'
    id_login = 1
    id_pass = 2
    report = 'report'
    id_answ = 3
    day = 'day'
    site = ''
    school = 'school'
    question = 'question'


# Write to file peoples`s online
async def write_online(user_id):
    global online_data
    if datetime.date.today().strftime('%d.%m.%y') in online_data.keys():
        if user_id not in online_data[datetime.date.today().strftime('%d.%m.%y')]:
            online_data[datetime.date.today().strftime('%d.%m.%y')].append(user_id)
    else:
        online_data[datetime.date.today().strftime('%d.%m.%y')] = [user_id]

    with open(path_to_online_json, 'a', encoding='utf-8') as file:
        file.truncate(0)
        json.dump(online_data, file)


async def writing_to_file(name_function):
    with open(path_to_logs_functions_txt, 'a', encoding='utf-8') as f:
        f.write(name_function + ' ')


async def get_log(user_id):
    user = (await db.get(user_id))[0]
    sgo_login, sgo_password, output_type, site, school = user[2], user[3], user[4], user[7], user[8]
    ns = NetSchoolAPI(site)
    log = await ns.login(sgo_login, sgo_password, school)
    return log


async def islogged(id_user):
    if await db.get(id_user):
        user = (await db.get(id_user))[0]
        is_auth = user[-1]
        if is_auth == 'Yes':
            return True
        else:
            return False
    else:
        return False


async def beauty_text(list_lessons):
    res, result = "", []
    for lesson in list_lessons[1:]:
        if lesson != "":
            n_patterns = ['\n\n📕 ', '\n\u2800\u2800📚 ', '\n\u2800\u2800📝 ']

            lesson = lesson.strip()
            subject = lesson[:lesson.find(':')]
            if len(subject) > 17:
                subject = subject[:18] + '...'
            if lesson[-8:] != 'Оценка: ':
                mark = lesson[lesson.rfind(':') + 1:]
            else:
                mark = ''
            homework = lesson[lesson.find(':') + 2:lesson.find(' Оценка: ')].replace('Оценка', '')
            n_patterns[0] += subject
            n_patterns[1] += homework
            n_patterns[2] += mark
            for i in n_patterns:
                res += i
    return res


async def debugging(type_func, printed):
    with open(path_to_finction_debug_txt, 'a') as debug_file:
        debug_file.write(
            f"Data: {datetime.datetime.today().strftime('%d-%m-%Y %H:%M:%S')}\n"
            f"Type: {type_func}\n\n"
            f"Printed: {printed}"
        )
        debug_file.close()


async def detection_days(msg):
    monday, monday_another_w = '', ''
    if not msg[:1].isnumeric():
        if msg.count("| Сегодня") > 0:
            real_day = datetime.date.today()
        elif msg.count("| Завтра") > 0:
            real_day = datetime.date.today() + timedelta(days=1)
        elif msg.count("| Послезавтра") > 0:
            real_day = datetime.date.today() + timedelta(days=2)
        else:
            monday = datetime.date.today() - timedelta(days=datetime.date.today().weekday())
            real_day = monday + timedelta(days=daya[msg[msg.rfind(' ') + 1:]])
    else:
        another_w_day = msg.split(' ')[0] + '.' + str(datetime.datetime.today().year)
        another_w_day = datetime.datetime.strptime(another_w_day, "%d.%m.%Y").date()
        monday_another_w = another_w_day - timedelta(days=another_w_day.weekday())
        real_day = another_w_day

    return monday_another_w, real_day, monday


@bot.on.private_message(payload={'logged': 'menu'})
async def logged_menu(message: Message):
    user = (await db.get(message.from_id))[0][-2]
    try:
        await bot.state_dispenser.delete(message.peer_id)
    except:
        pass
    if user == 'МОУ гимназия № 10':
        paylo = {'logged': 'schedule'}
    else:
        paylo = {'schedule': 'week'}
    keyboard = (
        Keyboard(inline=False, one_time=False)
        .add(Text('Boпpосы пo РДШ/Группе', {'menu': 'question'}), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text('📚 Дневник на текущую неделю', {'schedule': 'full_week'}), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(Text('📖 Дневник', {'logged': 'diary'}), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(Text('📅 Расписание', payload=paylo), color=KeyboardButtonColor.PRIMARY)
        .add(Text('📝 Отчет', {'menu': 'reports'}), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text('⚙ Настройки', {'logged': 'settings'}), color=KeyboardButtonColor.SECONDARY)
    )
    if not await islogged(message.from_id):
        text = '👋 Добро пожаловать в тестовый режим!\n\nВ нем вы можете протестировать функции, кнопочки и всё необходимое.\n' \
               'Будет показываться выдуманное расписание с выдуманными предметами, заданиями и оценками.\n\n' \
               'Для входа в свой дневник воспользуйтесь соответствующей кнопкой ниже = )'
        keyboard.row().add(Text('🔑 Войти в свой дневник', {'variant': 'login'}),
                           color=KeyboardButtonColor.POSITIVE)
    else:
        text = 'Меню...'

    if message.from_id == developer_id:
        keyboard.row().add(Text('Отчет', {'admin_report_week': 'global_admin_report'}),
                           color=KeyboardButtonColor.SECONDARY)
    await message.answer(
        message=text, keyboard=keyboard
    )


@bot.on.message(payload={'homework': 'day'})
async def homework_day(message: Message):
    first = time.time()
    res = '💤 Нет уроков, отдыхай = )'
    detected = await detection_days(message.text)
    monday_another_w, real_day, monday = detected[0], detected[1], detected[2]
    data = {}
    msg = ''
    mark = ' Оценка: '

    user = (await db.get(message.from_id))[0]
    sgo_login, sgo_password, output_type, site, school = user[2], user[3], user[4], user[7], user[8]
    if await islogged(message.from_id):
        try:
            ns = NetSchoolAPI(site)
            await message.answer('Авторизация в СГО...')
            # Logging at NetSchoolAPI with Users Login And Password and getting result
            await ns.login(sgo_login,
                           sgo_password,
                           school)
            if not message.text[:1].isnumeric():

                # NOT Other days at this week
                if message.text[:2] != 'ДЗ':

                    # Not Sunday or Saturday -> Simple Diary
                    if datetime.datetime.today().strftime("%A") not in ['Sunday', 'Saturday']:
                        result = await ns.diary()
                    else:
                        if datetime.datetime.today().strftime("%A") == 'Sunday':
                            day_x = (datetime.date.today() + timedelta(days=1))
                            result = await ns.diary(start=day_x)
                            date = day_x

                        else:
                            if message.text.count('| Сегодня') > 0:
                                result = await ns.diary()
                            else:
                                day_x = (datetime.date.today() + timedelta(days=2))
                                result = await ns.diary(start=day_x)
                else:
                    result = await ns.diary()
            else:
                result = await ns.diary(start=monday_another_w)

            await ns.logout()
            await message.answer('Генерация дневника...')

            # Creating week as list
            for days in result.schedule:
                data[str(days.day)] = []
                msg += '\n\n' + str(days.day) + 'koli'
                for lesson in days.lessons:
                    if len(lesson.assignments) > 0:
                        for i in range(len(lesson.assignments)):
                            if lesson.assignments[i].mark:
                                mark += str(lesson.assignments[i].mark)
                            else:
                                mark += ''
                        msg += '\n' + lesson.subject + ': ' + lesson.assignments[0].content + mark + 'koli'
                    else:
                        msg += '\n' + lesson.subject + ': Не задано' + mark + 'koli'
                    mark = ' Оценка: '
                data[str(days.day)] = msg.split("koli")
                msg = ''
            res = data[str(real_day)]
        except:
            await logged_menu(message)
    else:
        real_day = await detection_days(message.text)
        res = test_week[real_day[1].strftime("%A")]
        if real_day[1].strftime("%A") == 'Sunday':
            res = '💤 Нет уроков, отдыхай = )'

    # Sending list of lessons to func, creating image
    if res != '💤 Нет уроков, отдыхай = )':
        if await islogged(message.from_id):
            keyboard = (Keyboard(one_time=False, inline=False))\
                .add(Callback('ℹ Подробности', {'homework': 'details', 'day': real_day.strftime('%d-%m-%y')}),
                     color=KeyboardButtonColor.PRIMARY)\
                .row()\
                .add(Text('Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.SECONDARY)
        else:
            keyboard = (Keyboard(one_time=False,
                                 inline=False)).add(Text('🏡 Назад в меню', {'logged': 'menu'}),
                                                    color=KeyboardButtonColor.SECONDARY)

        if output_type == 'Изображение':
            msg = 'Подробный текст домашнего задания:\n\n'
            await message.answer('Генерируем изображение...')
            total_data = create_img(res, message.from_id)
            image = total_data[0]
            if total_data[1]:
                for lesson in total_data[1]:
                    msg += f'{list(lesson[0].items())[0][0]}: {list(lesson[0].items())[0][1]}\n\n'
            doc = await PhotoMessageUploader(bot.api).upload(
                title='image.jpg', file_source=image, peer_id=message.peer_id
            )
            if msg == 'Подробный текст домашнего задания:\n\n':
                msg = '\xa0'
            await message.answer(message=msg, attachment=doc, keyboard=keyboard)
            os.remove(image)

        elif output_type == 'Текст':
            await message.answer('Генерируем текстовое сообщение...')
            date = datetime.datetime.strptime(res[0].strip(), "%Y-%m-%d").date()
            weekday = w_daya[date.weekday()]
            res = '\n\n\n✅ ' + weekday + await beauty_text(res)
            await message.answer(message=res, keyboard=keyboard)
    else:
        await message.answer(res)
    await write_online(message.from_id)
    await writing_to_file('homework_day')


@bot.on.message(text=['Начать'])
@bot.on.message(command='start')
async def start(message: Message):
    user = await db.get(message.from_id)
    if not user:
        user_info = await bot.api.users.get(message.from_id)
        first = user_info[0].first_name
        sec = user_info[0].last_name

        await db.adding_user(message.from_id, first, sec)
        await bot.api.messages.send(peer_id=feedback_chat, random_id=0, message=f'Added @id{message.from_id}')
        await message.answer('👋 Приветствую в системе!\n'
                             'Выбери дальнейший вариант развития событий:\n\n\n'
                             'P.S. в данный момент проводится Бета-Тест, в случае каких-то неполадок воспользуйтесь '
                             'пунктом "Жалоба/Предложение" в настройках = )',
                             keyboard=(Keyboard(inline=False, one_time=False)
                                       .add(Text('🚪 Тестовый Вариант (Без входа в дневник)', {'logged': 'menu'}),
                                            color=KeyboardButtonColor.PRIMARY)
                                       .add(Text('🔐 Войти в свой дневник', {'variant': 'login'}),
                                            color=KeyboardButtonColor.PRIMARY)
                                       )
                             )
        await message.answer('При наличии вопросов по использованию бота и его функциям: ⬇',
                             keyboard=Keyboard(one_time=False, inline=True)
                             .add(Text('Помощь', {'menu': 'help'}), color=KeyboardButtonColor.NEGATIVE))
    else:
        await logged_menu(message)


@bot.on.private_message(lev='Вoйти в систему')
@bot.on.private_message(payload={'variant': 'login'})
async def login(message: Message):
    await db.set_site_and_school(message.from_id, 'МОУ гимназия № 10')
    await bot.state_dispenser.set(message.peer_id, States.login)
    await message.answer('❓ Чтобы получать Ваше домашнее задание из ВК нужно авторизоваться в системе.\n'
                         '\n\n\n'
                         '❗❗❗ ВНИМАНИЕ ❗❗❗\n'
                         'Вводя свои данные данные Вы соглашаетесь с Пользовательским соглашением, доступным по ссылке:\n'
                         'vk.com/@gymnasium_10_vlg-politika-v-otnoshenii-obrabotki-personalnyh-dannyh\n\n'
                         '🔒 Введите Ваш логин, как при входе в "Сетевой Город.Образование" (Госуслуги не работают): ',
                         keyboard=Keyboard(one_time=True, inline=False)
                         .add(Callback('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.NEGATIVE)
                         )


@bot.on.private_message(state=States.login)
async def password(message: Message):
    ctx.set('login', message.text)
    await bot.state_dispenser.set(message.peer_id, States.password)
    await message.answer('🔑 Введите Ваш пароль, как при входе в "Сетевой Город.Образование":',
                         keyboard=Keyboard(one_time=True, inline=False)
                         .add(Callback('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.NEGATIVE))


@bot.on.private_message(state=States.password)
async def result_login(message: Message):
    try:
        name = ctx.get('login')
        ctx.set('password', message.text)
        await bot.state_dispenser.delete(message.peer_id)
        id_ans = await message.answer(f'❗ Проверьте Ваши данные: \n\n'
                                      f'🔒 Логин: {name}\n'
                                      f'🔑 Пароль: {message.text}\n\n'
                                      f'В случае, если вы из другой школы, воспользуйтесь кнопкой "Другие настройки"\n',
                                      keyboard=(Keyboard(inline=False, one_time=True)
                                                .add(Text('✅ Все верно!', {'choose': 'output'}),
                                                     color=KeyboardButtonColor.POSITIVE)
                                                .add(Text('🔄 Заполнить заново', {'variant': 'login'}),
                                                     color=KeyboardButtonColor.PRIMARY)
                                                .row()
                                                .add(Text('⚙ Дрyгие нaстpойки', {'logged': 'other_settings'}),
                                                     color=KeyboardButtonColor.SECONDARY))
                                      )
        ctx.set('id_answ', id_ans.message_id)
    except Exception as e:
        await message.answer('❗ Произошла ошибка! Разработчики уже оповещены о проблеме. Приносим свои извинения.')
        await bot.api.messages.send(developer_id, random_id=0, message=f'Error with {message.from_id}!\n {e}')
        await logged_menu(message)


@bot.on.private_message(lev='Дрyгие нaстpойки')
@bot.on.private_message(payload={'logged': 'other_settings'})
async def site_settings(message: Message):
    await bot.state_dispenser.set(message.peer_id, States.school)
    await message.answer(message='✍ Введите название своей школы (Точь-в-точь, как при выборе школы): \n\n'
                                 'Пример: "МОУ гимназия №10", "МОУ СОШ №57"',
                         keyboard=Keyboard(one_time=True, inline=False)
                         .add(Callback('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.NEGATIVE))
    await writing_to_file('site_settings')


@bot.on.private_message(state=States.school)
async def school_settings(message: Message):
    await bot.state_dispenser.delete(message.peer_id)
    name = ctx.get('login')
    password = ctx.get('password')
    await db.set_site_and_school(message.from_id, message.text)
    res = await message.answer(message='❗ Проверьте данные: \n'
                                       f'🔒 Имя: {name}\n'
                                       f'🔑 Пароль: {password}\n'
                                       f'🏫 Школа: {message.text}',
                               keyboard=(Keyboard(inline=False, one_time=True)
                                         .add(Text('✅ Все верно!', {'choose': 'output'}),
                                              color=KeyboardButtonColor.POSITIVE)
                                         .add(Text('🔄 Заполнить заново', {'logged': 'other_settings'}),
                                              color=KeyboardButtonColor.PRIMARY)
                                         )
                               )
    await sleep(30)
    await bot.api.messages.delete(res.message_id, peer_id=message.peer_id, delete_for_all=True)
    await writing_to_file('school_settings')


@bot.on.private_message(payload={'choose': 'output'})
async def choose_output(message: Message):
    await message.answer('🔄 Пытаемся авторизироваться с Вашими данными...')
    name = ctx.get('login')
    password = ctx.get('password')
    man = (await db.get(message.from_id))[0]
    site, school = man[-3], man[-2]
    id_n = ctx.get('id_answ')

    try:
        ns = NetSchoolAPI(site)
        await ns.login(name, password, school)
        await ns.diary()
    except Exception as e:
        id_ans = await message.answer(f'❗ Произошла ошибка! Проверьте свои данные!\n\n'
                                      f'🔒 Логин: {name}\n'
                                      f'🔑 Пароль: {password}\n'
                                      f'🏫 Школа: {school}\n'
                                      f'🕸 Сайт: {site}',
                                      keyboard=Keyboard(inline=False, one_time=True)
                                      .add(Text('🔄 Заполнить заново', {'variant': 'login'}),
                                           color=KeyboardButtonColor.PRIMARY))
        await sleep(30)
        await bot.api.messages.delete(peer_id=message.from_id,
                                      message_ids=id_ans.message_id,
                                      delete_for_all=True)
        await bot.api.messages.delete(peer_id=message.from_id,
                                      message_ids=id_n,
                                      delete_for_all=True)
    else:
        await db.update(message.from_id, name, password)
        await db.set_authorize(message.from_id, 'Yes')
        await message.answer('✅ Успешно!')
        await message.answer(message='Выберите способ отображения домашнего задания:',
                             keyboard=(Keyboard(one_time=True, inline=False)
                                       .add(Text('💬 Текст', {'choose_output': 'Done'}), color=KeyboardButtonColor.PRIMARY)
                                       .add(Text('🖼 Изображение', {'choose_output': 'Done'}),
                                            color=KeyboardButtonColor.PRIMARY)
                                       )
                             )
        await bot.api.messages.delete(peer_id=message.from_id,
                                      message_ids=id_n,
                                      delete_for_all=True)


@bot.on.private_message(payload={'choose': 'output_l'})
async def choose_output_l(message: Message):
    await message.answer(message='Выберите способ отображения домашнего задания:',
                         keyboard=(
                             Keyboard(one_time=True, inline=False)
                             .add(Text('💬 Текст', {'choose_output': 'Done'}), color=KeyboardButtonColor.PRIMARY)
                             .add(Text('🖼 Изображение', {'choose_output': 'Done'}),
                                  color=KeyboardButtonColor.PRIMARY)
                         )
                         )


@bot.on.private_message(payload={'choose_output': 'Done'})
async def go_to_menu(message: Message):
    await db.set_output_type(message.from_id, message.text.split()[1])
    await message.answer(message=f'✅ Принято! Вы будете видеть домашнее задание как {message.text}.\n'
                                 f'Выбор можно изменить в любой момент в настройках = )',
                         keyboard=(Keyboard(one_time=True, inline=False)
                                   .add(Text('🏡 В меню', {'logged': 'menu'}))
                                   )
                         )


@bot.on.private_message(payload={'schedule': 'full_week'})
async def full_week(message: Message):
    data = {}
    msg = ''
    mark = ' Оценка: '
    user = (await db.get(message.from_id))[0]
    sgo_login, sgo_password, output_type, site, school = user[2], user[3], user[4], user[7], user[8]
    if await islogged(message.from_id):
        ns = NetSchoolAPI(site)
        await ns.login(sgo_login, sgo_password, school)
        schedule = await ns.diary()
        for days in schedule.schedule:
            data[str(days.day)] = []
            msg += '\n\n' + str(days.day) + 'koli'
            for lesson in days.lessons:
                if len(lesson.assignments) > 0:
                    for i in range(len(lesson.assignments)):
                        if lesson.assignments[i].mark:
                            mark += str(lesson.assignments[i].mark)
                        else:
                            mark += ''
                    msg += '\n' + lesson.subject + ': ' + lesson.assignments[0].content + mark + 'koli'
                else:
                    msg += '\n' + lesson.subject + ': Не задано' + mark + 'koli'
                mark = ' Оценка: '
            data[str(days.day)] = msg.split("koli")
            msg = ''
        result = data
    else:
        result = dict(itertools.islice(test_week.items(), 6))

    if output_type == 'Изображение':
        num = 0
        path_list = []
        pic_list = []
        await message.answer('Генерируем изображения...')
        for day in result.keys():
            day = result[day]
            image = create_img(day, str(message.from_id) + f'_{num}')[0]
            pic_list.append(image)
            path_list += image + ', '
            num += 1
            doc = await PhotoMessageUploader(bot.api).upload(
                title='image.jpg', file_source=image, peer_id=message.peer_id
            )
            path_list.append(doc)
        await message.answer(message='\xa0', attachment=path_list)
        for pic in pic_list:
            os.remove(pic)

    elif output_type == 'Текст':
        res = ''
        for day in result.keys():
            day = result[day]
            date = datetime.datetime.strptime(day[0].strip(), "%Y-%m-%d").date()
            weekday = w_daya[date.weekday()]
            res += '\n\n\n✅ ' + weekday + await beauty_text(day) + '\n'
        await message.answer(res)

    await write_online(message.from_id)
    await writing_to_file('full_week')


async def homework_details(user_id, date_str):
    user = (await db.get(user_id))[0]
    sgo_login, sgo_password, output_type, site, school = user[2], user[3], user[4], user[7], user[8]

    try:
        ns = NetSchoolAPI(site)

        # Logging at NetSchoolAPI with Users Login And Password and getting result
        await ns.login(sgo_login,
                       sgo_password,
                       school)
        date = datetime.datetime.strptime(date_str, '%d-%m-%y')
        result = await ns.diary(start=date, end=date)
        date_local = date.strftime('%d.%m.%Y')[:date.strftime('%d.%m.%Y').rfind('.')]
        lessons_list, result_list = [], []
        for days in result.schedule:
            for lesson in days.lessons:
                if lesson.assignments:
                    family = await ns.details(lesson.assignments[0].id)
                    if family['description']:
                        description = family['description']
                    else:
                        description = None

                    if family['attachments']:
                        attachments = await ns.download_attachment(family['attachments'])
                    else:
                        attachments = None

                    if lesson.subject.count('Элективный курс') > 0:
                        if len(lesson.subject.strip('Элективный курс ')) > 30:
                            scopes = lesson.subject[lesson.subject.find('"'):lesson.subject.rfind(""'') + 1].split(' ')
                            subject = 'Эл.курс' + scopes[0] + '..' + scopes[-1]
                        else:
                            subject = lesson.subject.strip('Элективный курс ')
                    else:

                        if len(f'{date_local} | {lesson.subject}') < 39:
                            subject = lesson.subject
                        else:
                            subject = f'{lesson.subject.split()[0]}...{lesson.subject.split()[-1]}'
                    if subject in lessons_list:
                        pos_les = 0
                        for work in range(len(lessons_list)):
                            if lessons_list[work].count(subject) > 0:
                                pos_les = work

                        if lessons_list[pos_les][-1] == ')' and lessons_list[pos_les][-2].isnumeric():
                            subject = subject + str(int(lessons_list[pos_les][-2]) + 1)
                        else:
                            subject += '(1)'

                    lessons_list.append(subject)
                    if attachments or description:
                        result_list.append(subject)
        keyboard = Keyboard(one_time=True, inline=False)
        if result_list:
            for attach in range(len(result_list)):
                if attach != len(result_list) - 1:
                    keyboard.add(Text(f'{date_local} | {result_list[attach]}', {'lessons': 'attachments'}),
                                 color=KeyboardButtonColor.POSITIVE)
                    keyboard.row()
                else:
                    keyboard.add(Text(f'{date_local} | {result_list[attach]}', {'lessons': 'attachments'}),
                                 color=KeyboardButtonColor.POSITIVE)
            return ('Показаны только те дни, у которых есть подробности\n\n'
                    'Выберите день, у которого хотите узнать подробности:\n',
                    keyboard)
        else:
            return 'Нет подробностей...', []
    except Exception as e:
        return ('❗ Произошла ошибка! Разработчики уже оповещены о проблеме.\n'
                '❗ Приносим свои извинения, попробуйте еще раз', traceback.format_exc())


@bot.on.private_message(payload={'lessons': 'attachments'})
async def lessons_attachment(message: Message):
    await message.answer('🔄 Загрузка подробностей...')
    subject = message.text[message.text.find('| ') + 2:]
    result_dict, total_lesson = {}, ''

    date = message.text[:message.text.find(' ')] + '.' + str(datetime.date.today().year)
    real_date = datetime.datetime.strptime(date, '%d.%m.%Y')
    user = (await db.get(message.from_id))[0]
    sgo_login, sgo_password, output_type, site, school = user[2], user[3], user[4], user[7], user[8]

    ns = NetSchoolAPI(site)
    await ns.login(sgo_login, sgo_password, school)
    result = await ns.diary(start=real_date, end=real_date)
    for lesson in result.schedule[0].lessons:
        if lesson.assignments:
            data[lesson.subject] = lesson.assignments[0].id

    if subject[-2].isnumeric() and subject[-1] == ')':
        for work in data.keys():
            if subject[:-3] in work or (subject[:-3].split('...')[0] in work and subject[:-3].split('...')[1]):
                result_dict[work] = data[work]
        key = int(subject[-2]) - 1
        total_lesson = list(result_dict.keys())[key]
    else:
        for work in data.keys():
            if subject in work or subject.split('...')[0] in work and subject.split('...')[1]:
                total_lesson = data[work]

    family = await ns.details(total_lesson)
    loguru.logger.info(f'{family} {message.from_id}')
    if family['description']:
        description = '🖹 Подробности от учителя: \n' + family['description'] + '\n'
    else:
        description = '🤷 Нет подробностей от учителя...\n'

    if family['attachments']:
        doc_list = []
        attachments = await ns.download_attachment_as_bytes(family['attachments'])
        for file in attachments:
            doc = await DocMessagesUploader(bot.api).upload(
                title=file['name'],
                file_source=file['file'],
                peer_id=message.from_id
            )
            doc_list.append(doc)

        files = '\n📎 Прикрепленные файлы:'
    else:
        doc_list = []
        files = '\n🤷 Нет прикрепленных файлов = ('
    await message.answer(message=description + files, attachment=doc_list)
    await logged_menu(message)
    await writing_to_file('lessons_attachment')


@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def on_settings(event: MessageEvent):
    if event.object.payload != {'bot_news': 'True'}:
        try:
            await bot.state_dispenser.delete(event.peer_id)
        except:
            pass
        if list(event.payload.keys())[0] != 'homework' and list(event.payload.values())[0] != 'details':
            if (await db.get(event.user_id))[0][-2] == 'МОУ гимназия № 10':
                paylo = {'logged': 'schedule'}
            else:
                paylo = {'schedule': 'week'}

            keyboard = (
                Keyboard(inline=False, one_time=False)
                .add(Text('Boпpосы пo РДШ/Группе', {'menu': 'question'}), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(Text('📚 Дневник на текущую неделю', {'schedule': 'full_week'}), color=KeyboardButtonColor.POSITIVE)
                .row()
                .add(Text('📖 Дневник', {'logged': 'diary'}), color=KeyboardButtonColor.POSITIVE)
                .row()
                .add(Text('📅 Расписание', payload=paylo), color=KeyboardButtonColor.PRIMARY)
                .add(Text('📝 Отчет', {'menu': 'reports'}), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(Text('⚙ Настройки', {'logged': 'settings'}), color=KeyboardButtonColor.SECONDARY)
            )
            if not await islogged(event.peer_id):
                text = '👋 Добро пожаловать в тестовый режим!\nВы можете протестировать функции, кнопочки и всё необходимое.\n' \
                       '👋 Будет показываться выдуманное расписание с выдуманными предметами, заданиями и оценками.\n\n' \
                       '👋 Для входа в свой дневник воспользуйтесь соответствующей кнопкой ниже = )'
                keyboard.row().add(Text('Войти в свой дневник', {'variant': 'login'}),
                                   color=KeyboardButtonColor.POSITIVE)
            else:
                text = '...'

            if event.user_id == developer_id:
                keyboard.row().add(Text('Отчет', {'admin_report_week': 'global_admin_report'}), color=KeyboardButtonColor.SECONDARY)
            await event.send_message(
                message=text, keyboard=str(keyboard)
            )
        else:
            if await islogged(event.user_id):
                result = await homework_details(event.user_id, list(event.payload.values())[1])
                setattr(event.object, 'payload', {})
                if result[0] == '❗ Произошла ошибка! Разработчики уже оповещены о проблеме.\n❗ Приносим свои извинения, попробуйте еще раз':
                    await bot.api.messages.send(peer_ids=feedback_chat, random_id=0,
                                                message=f'Ошибка у пользователя {event.user_id}:\n\n'
                                                        f'{result[1]}')
                    await event.send_message(message=result[0], random_id=0)
                    await on_settings(event)

                elif result[0] == 'Показаны только те дни, у которых есть подробности\n\nВыберите день, у которого хотите узнать подробности:\n':
                    await event.send_message(message=result[0], keyboard=result[1], random_id=0)

                else:
                    await event.send_message(message=result[0], random_id=0)

            else:
                await event.send_message(message='В тестовом режиме недоступны подробности', random_id=0,)
                await on_settings(event)
        await event.show_snackbar(text='Выполнено!')
    else:
        ctx.set('cms', event.object.conversation_message_id)
        await event.show_snackbar('Секунду...')
        await bot.state_dispenser.set(peer_id=event.peer_id, state=States.wall_news_header)
        await bot.api.messages.send(user_id=site_manager_id, random_id=0, message='Введите заголовок: ')


@bot.on.message(payload={'homework': 'chooseday_l'})
async def choose_day(message: Message):
    await message.answer(
        'Выберите день:',
        keyboard=(
            Keyboard(inline=False, one_time=False)
            .row()
            .add(Text('ДЗ | Пн', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .add(Text('ДЗ | Вт', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .add(Text('ДЗ | Ср', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .row()
            .add(Text('ДЗ | Чт', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .add(Text('ДЗ | Пт', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .add(Text('ДЗ | Сб', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .row()
            .add(Text('Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.PRIMARY)
        )
    )
    await writing_to_file('choose_day')


@bot.on.private_message(payload={'logged': 'diary'})
async def diary(message: Message):
    await message.answer(message='...',
                         keyboard=(
                             Keyboard(inline=False, one_time=False)
                             .add(Text(
                                 f'{list(daya.keys())[list(daya.values()).index(datetime.date.today().weekday())]} | Сегодня',
                                 {'homework': 'day'}), color=KeyboardButtonColor.POSITIVE)
                             .add(Text(
                                 f'{list(daya.keys())[list(daya.values()).index((datetime.date.today() + timedelta(days=1)).weekday())]} | Завтра',
                                 {'homework': 'day'}), color=KeyboardButtonColor.POSITIVE)
                             .add(Text(
                                 f'{list(daya.keys())[list(daya.values()).index((datetime.date.today() + timedelta(days=2)).weekday())]} | Послезавтра',
                                 {'homework': 'day'}), color=KeyboardButtonColor.POSITIVE)
                             .row()
                             .add(Text('📅 Другие дни', {'homework': 'chooseday_l'}), color=KeyboardButtonColor.PRIMARY)
                             .add(Text('📅 Дрyгaя недeля', {'homework': 'another_week'}),
                                  color=KeyboardButtonColor.PRIMARY))
                         .row()
                         .add(Text('🧐 Посмотреть долги по предметам', {'menu': 'dept'}), color=KeyboardButtonColor.NEGATIVE)
                         .row()
                         .add(Text('🏡 В меню', {'logged': 'menu'}))
                         )
    await writing_to_file('diary')


@bot.on.private_message(payload={'homework': 'another_week'})
async def another_week(message: Message):
    monday = datetime.date.today() - timedelta(days=datetime.date.today().weekday())
    list_mondays = [((monday + timedelta(days=7) - timedelta(days=(i - 1) * 7)).strftime("%d-%m-%Y"),
                     (monday + timedelta(days=7) - timedelta(days=(i - 1) * 7) + timedelta(days=6)).strftime(
                         "%d-%m-%Y")) for i in range(5)]
    list_mondays = list(reversed(list_mondays))

    keyboard = Keyboard(inline=False, one_time=False)
    for i in range(len(list_mondays)):

        if i == 2:
            condition = 'Текущ.'
            color = KeyboardButtonColor.POSITIVE
        elif i == 1:
            condition = 'Прошл'
            color = KeyboardButtonColor.SECONDARY
        elif i == 0:
            condition = 'Позапрошл.'
            color = KeyboardButtonColor.SECONDARY
        elif i == 3:
            condition = 'След.'
            color = KeyboardButtonColor.SECONDARY
        else:
            condition = 'Последующ.'
            color = KeyboardButtonColor.SECONDARY

        keyboard.add(
            Text(list_mondays[i][0].replace('-', '.') + '-' + list_mondays[i][1].replace('-', '.') + f' ({condition})',
                 {'another_week': 'day'}), color=color).row()
    await message.answer(message='...',
                         keyboard=keyboard.add(Text('🏡 В меню', {'logged': 'menu'}), color=KeyboardButtonColor.PRIMARY
                                               )
                         )
    await writing_to_file('another_week')


@bot.on.private_message(payload={'another_week': "day"})
async def another_week_day(message: Message):
    right_monday = message.text.split('-')[0]
    date_monday = datetime.datetime.strptime(right_monday, '%d.%m.%Y').date()
    list_days = [date_monday + timedelta(days=i) for i in range(6)]
    list_days = [i.strftime('%d.%m.%Y').replace('-', '.')[:i.strftime('%d.%m.%Y').replace('-', '.').rfind('.')] for i in
                 list_days]
    await message.answer(
        'Выберите день:',
        keyboard=(
            Keyboard(inline=False, one_time=False)
            .row()
            .add(Text(f'{str(list_days[0])} ДЗ | Пн', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .add(Text(f'{str(list_days[1])} ДЗ | Вт', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .add(Text(f'{str(list_days[2])} ДЗ | Ср', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .row()
            .add(Text(f'{str(list_days[3])} ДЗ | Чт', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .add(Text(f'{str(list_days[4])} ДЗ | Пт', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .add(Text(f'{str(list_days[5])} ДЗ | Сб', {'homework': 'day'}), color=KeyboardButtonColor.SECONDARY)
            .row()
            .add(Text('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.PRIMARY)
        )
    )
    await writing_to_file('another_week_day')


@bot.on.private_message(payload={'logged': 'schedule'})
async def schedule(message: Message):
    if await islogged(message.from_id):
        await message.answer(message='Выберите расписание: ', keyboard=Keyboard(one_time=True, inline=False)
                             .add(Text('🎒 Уроков', {'schedule': 'week'}), color=KeyboardButtonColor.PRIMARY)
                             .add(Text('🔔 Звонков', {'schedule': 'rings'}), color=KeyboardButtonColor.PRIMARY)
                             .row()
                             .add(Text('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.SECONDARY))
    else:
        await schedule_week(message)


@bot.on.private_message(payload={'schedule': 'rings'})
async def schedule_rings(message: Message):
    if datetime.date.today().weekday() == 0:
        doc = await PhotoMessageUploader(bot.api).upload(
            title='image.jpg', file_source=os.getcwd() + path_to_monday_jpg, peer_id=message.peer_id
        )
        now_day = 'на понедельник'
    else:
        doc = await PhotoMessageUploader(bot.api).upload(
            title='image.jpg', file_source=os.getcwd() + path_to_other_days_jpg, peer_id=message.peer_id
        )
        now_day = ''

    await message.answer(message=f'🔔 Расписание звонков{now_day}',
                         keyboard=Keyboard(one_time=True, inline=False)
                         .add(Text('🔄 Другой день', {'rings': 'day'}), color=KeyboardButtonColor.PRIMARY)
                         .row()
                         .add(Text('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.SECONDARY), attachment=doc)
    await writing_to_file('rings_day')


@bot.on.private_message(payload={'rings': 'day'})
async def rings_day(message: Message):
    if datetime.date.today().weekday() != 0:
        doc = await PhotoMessageUploader(bot.api).upload(
            title='image.jpg', file_source=os.getcwd() + path_to_monday_jpg, peer_id=message.peer_id
        )
        now_day = ' на понедельник'
    else:
        doc = await PhotoMessageUploader(bot.api).upload(
            title='image.jpg', file_source=os.getcwd() + path_to_other_days_jpg, peer_id=message.peer_id
        )
        now_day = ''
    await message.answer(message=f'🔔 Расписание звонков {now_day}', attachment=doc)
    await logged_menu(message)
    await writing_to_file('rings_another_day')


@bot.on.private_message(payload={'schedule': 'week'})
async def schedule_week(message: Message):
    res = ''
    data = {}
    if await islogged(message.from_id):
        user = (await db.get(message.from_id))[0]
        sgo_login, sgo_password, output_type, site, school = user[2], user[3], user[4], user[7], user[8]
        ns = NetSchoolAPI(site)
        await ns.login(sgo_login, sgo_password, school)
        result = await ns.diary()

        # Generating dict of diary
        for days in result.schedule:
            day = w_daya[days.day.weekday()]
            data[day] = ''
            lessons = days.lessons
            for lesson in lessons:
                subject = lesson.subject
                data[day] += '\u2800' + subject + '\n81679am'

    else:
        for i in test_week.keys():
            if i != 'Sunday':
                data[eng_daya[i]] = ''
                for lesson in test_week[i][1:-1]:
                    subject = lesson[:lesson.find(":")]
                    data[eng_daya[i]] += '\u2800' + subject.strip() + '\n81679am'

    # Generating answer
    if data != {}:
        for i in data.keys():
            data[i] = data[i].split('81679am')

        for i in data.keys():
            res += '\n📅  ' + i + '\n'

            for num in range(len(data[i]) - 1):
                res += str(num + 1) + ') ' + data[i][num]

        await message.answer(res)
    else:
        await message.answer('💤 Нет уроков, отдыхай = )')
    await logged_menu(message)
    await writing_to_file('schedule_week')


@bot.on.private_message(payload={'report': 'parent'})
async def parent_report(message: Message):
    user = (await db.get(message.from_id))[0]
    sgo_login, sgo_password, output_type, site, school = user[2], user[3], user[4], user[7], user[8]
    ns = NetSchoolAPI(site)
    if await islogged(message.from_id):
        term = int(message.text)
        await ns.login(sgo_login, sgo_password, school)
        report = await ns.parentReport(term=term)
        await ns.logout()
    else:
        report = test_report

    # Generating answer
    if output_type == 'Изображение':
        await message.answer(' 🖼 Генерируем отчет...')
        path = create_report(report, message.from_id)
        doc = await PhotoMessageUploader(bot.api).upload(
            title='image.jpg', file_source=path, peer_id=message.peer_id
        )
        await message.answer(message='...', attachment=doc, keyboard=Keyboard(one_time=False, inline=False)
                             .add(Text('🧐 Посмотреть долги по предметам', {'menu': 'dept'}),
                                  color=KeyboardButtonColor.NEGATIVE)
                             .row()
                             .add(Text('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.PRIMARY))

        os.remove(path)
    elif output_type == 'Текст':
        result = f"🔘Общие:\n5️⃣: {report['total']['5']}\n4️⃣: {report['total']['4']}\n3️⃣: {report['total']['3']}\n2️⃣: " \
                 f"{report['total']['2']}\n〰️Средняя: {report['total']['average']}\n" \
                 f"🗒Средняя за четверть: {report['total']['average_term']}\n\n"
        for subject in report['subjects'].keys():
            result += f"🔶{subject}:\nОценка 5: {report['subjects'][subject]['5']} Оценка 4: " \
                      f"{report['subjects'][subject]['4']}\nОценка 3: " \
                      f"{report['subjects'][subject]['3']} Оценка 2: {report['subjects'][subject]['2']}\n〰️" \
                      f"Средняя: {report['subjects'][subject]['average']}\n🗒За четверть: " \
                      f"{report['subjects'][subject]['term']}\n\n"
        await message.answer(result, keyboard=Keyboard(one_time=False, inline=False)
                             .add(Text('🧐 Посмотреть долги по предметам', {'menu': 'dept'}),
                                  color=KeyboardButtonColor.NEGATIVE)
                             .row()
                             .add(Text('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.PRIMARY))
    await writing_to_file('parent_report')


@bot.on.private_message(payload={'logged': 'settings'})
async def settings(message: Message):
    user = (await db.get(message.from_id))[0]
    sgo_login, sgo_password, output_type = user[2], user[3], user[4]
    if await islogged(message.from_id):
        res = await message.answer(message=f'🤭Ваши данные:\n\n'
                                           f'🔒 Логин: {sgo_login[:2] + "**" + sgo_login[-2:]}\n'
                                           f'🔑 Пароль: {sgo_password[:2] + "**" + sgo_password[-2:]}\n'
                                           f'🖼 Тип отображения: {output_type}',
                                   keyboard=Keyboard(one_time=True, inline=False)
                                   .add(Text('🧐 Посмотреть данные', {'show': 'userdata'}),
                                        color=KeyboardButtonColor.PRIMARY)
                                   .row()
                                   .add(Text('🔄 Сменить пользователя', {'variant': 'login'}),
                                        color=KeyboardButtonColor.PRIMARY)
                                   .add(Text('📺 Тип представления', {'choose': 'output_l'}),
                                        color=KeyboardButtonColor.PRIMARY)
                                   .row()
                                   .add(Text('📢 Жaлобa/Пpедлoжениe', {'settings': 'info'}),
                                        color=KeyboardButtonColor.NEGATIVE)
                                   .add(Text('Помощь', {'menu': 'help'}), color=KeyboardButtonColor.NEGATIVE)
                                   .row()
                                   .add(Text('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.SECONDARY)
                                   )
    else:
        await message.answer(message='🤭 Ваши данные:\n\n🔒 Логин: ПупкинВ2\n🔑 Пароль: Гимназия_10_love\n'
                                     f'🖼 Тип отображения: {output_type}',
                             keyboard=Keyboard(one_time=True, inline=False)
                             .add(Text('🔄 Тип отображения',
                                       {'choose': 'output_l'}), color=KeyboardButtonColor.PRIMARY)
                             .row()
                             .add(Text('📢 Жaлобa/Пpедлoжениe', {'settings': 'info'}), color=KeyboardButtonColor.NEGATIVE)
                             .add(Text('Помощь', {'menu': 'help'}), color=KeyboardButtonColor.NEGATIVE)
                             .row()
                             .add(Text('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.SECONDARY)
                             )
    await writing_to_file('settings')


@bot.on.private_message(payload={'show': 'userdata'})
async def show_userdata(message: Message):
    login, password = (await db.get(message.from_id))[0][2], (await db.get(message.from_id))[0][3]
    res = await message.answer(message=f'🤭 Ваши данные:\n\n🔒 Логин: {login}\n🔑 Пароль: {password}\n')

    await logged_menu(message)
    await sleep(30)
    await bot.api.messages.delete(peer_id=message.from_id,
                                  message_ids=res.message_id,
                                  delete_for_all=True)
    await writing_to_file('show_userdata')


@bot.on.private_message(lev='Жaлобa/Пpедлoжениe')
@bot.on.private_message(payload={'settings': 'info'})
async def report_to_admin(message: Message):
    await bot.state_dispenser.set(message.from_id, States.report)
    await message.answer(message='✍ Введите текст Вашей жалобы/предложения, и он тут же будет доставлен разработчику:',
                         keyboard=Keyboard(one_time=True, inline=False)
                         .add(Callback('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.NEGATIVE)

                         )
    await writing_to_file('report_to_admin')


@bot.on.private_message(state=States.report)
async def report_to_dev(message: Message):
    user = (await db.get(message.from_id))[0]
    user_id, vk_id = user[0], user[1]
    msg = f'New Feedback from ' \
          f'| {user_id} | @id{vk_id} |\n' \
          f'Text: \n{message.text}'
    await bot.api.messages.send(peer_id=feedback_chat, random_id=0, message=msg)
    await message.answer(
        message='✅ Успешно отправлено!\n\nПримерное время ожидания: 1 рабочий день\nСпасибо за Фидбэк = )')
    await bot.state_dispenser.delete(message.from_id)
    await logged_menu(message)
    await writing_to_file('report_to_dev')


@bot.on.private_message(lev='Boпpосы пo РДШ/Группе')
@bot.on.private_message(payload={'menu': 'question'})
async def questions(message: Message):
    await bot.state_dispenser.set(message.from_id, States.question)
    await message.answer(message='✍ Введите свой вопрос для группы, и он тут же будет доставлен администраторам:',
                         keyboard=Keyboard(one_time=True, inline=False)
                         .add(Callback('🏡 Назад в меню', {'logged': 'menu'}), color=KeyboardButtonColor.NEGATIVE)

                         )
    await writing_to_file('question_group')


@bot.on.private_message(state=States.question)
async def question_group(message: Message):
    user = (await db.get(message.from_id))[0]
    msg = f'Новый вопрос от ' \
          f'[id{user[1]}|{user[5]} {user[6]}] \n\n' \
          f'Ответьте на это сообoение для ответа на вопрос\n\n' \
          f'Текст вопроса: {message.text}'
    await bot.api.messages.send(message=msg, peer_id=question_chat,
                                forward_messages=message.id, random_id=0)
    await message.answer(
        message='✅ Успешно отправлено!')
    await bot.state_dispenser.delete(message.from_id)
    await logged_menu(message)


@bot.on.private_message(payload={'report': 'total'})
async def total_marks(message: Message):
    report = base_total
    student_class = '55555'
    user = (await db.get(message.from_id))[0]
    sgo_login, sgo_password, output_type, site, school = user[2], user[3], user[4], user[7], user[8]
    if await islogged(message.from_id):
        ns = NetSchoolAPI(site)

        await message.answer('Подключение к дневнику...')
        await ns.login(sgo_login, sgo_password, school)

        try:
            report = await ns.reportTotal()
            student_class = int((await ns.get_period())['filterSources'][1]['items'][0]['title'][:-1])
            await ns.logout()

        except:
            await message.answer('Нет данных...')
            await logged_menu(message)
        else:
            report = report
        await message.answer('Получение отметок...')

    await message.answer('Генерация итоговых отметок...')

    if output_type == 'Изображение':
        photo = generation_total_report(message.from_id, report, student_class)
        pic = await PhotoMessageUploader(bot.api).upload(file_source=photo, title='total.jpg', peer_id=message.from_id)
        await message.answer('Ваши итоговые отметки:', attachment=pic)
        os.remove(photo)
    else:
        result = '❇️Итоги четвертей:'
        result += '\n1️⃣:\n'
        for subject in report['1']:
            result += f"	{subject}: {report['1'][subject]}\n"
        result += '\n2️⃣:\n'
        for subject in report['2']:
            result += f"	{subject}: {report['2'][subject]}\n"
        if int(student_class[:-1]) not in [10, 11]:
            result += '\n3️⃣:\n'
            for subject in report['3']:
                result += f"	{subject}: {report['3'][subject]}\n"
            result += '\n4️⃣:\n'
            for subject in report['4']:
                result += f"	{subject}: {report['4'][subject]}\n"
        result += '\n🗓Годовые:\n'
        for subject in report['year']:
            result += f"	{subject}: {report['year'][subject]}\n"
        await message.answer(result)

    await logged_menu(message)
    await writing_to_file('total_report')


@bot.on.private_message(payload={'parent': 'choose_term'})
async def term(message: Message):
    user = (await db.get(message.from_id))[0]
    sgo_login, sgo_password, output_type, site, school = user[2], user[3], user[4], user[7], user[8]
    ns = NetSchoolAPI(site)
    await ns.login(sgo_login, sgo_password, school)
    terms = await ns.getTermId()
    if len(terms) == 4:
        await message.answer('Выберите нужную четверть:',
                             keyboard=Keyboard(one_time=True, inline=False)
                             .add(Text('1', {'report': 'parent'}), color=KeyboardButtonColor.PRIMARY)
                             .add(Text('2', {'report': 'parent'}), color=KeyboardButtonColor.PRIMARY)
                             .add(Text('3', {'report': 'parent'}), color=KeyboardButtonColor.PRIMARY)
                             .add(Text('4', {'report': 'parent'}), color=KeyboardButtonColor.PRIMARY))
    elif len(terms) == 2:
        await message.answer('Выберите нужное полугодие:',
                             keyboard=Keyboard(one_time=True, inline=False)
                             .add(Text('1', {'report': 'parent'}), color=KeyboardButtonColor.PRIMARY)
                             .add(Text('2', {'report': 'parent'}), color=KeyboardButtonColor.PRIMARY))


@bot.on.private_message(payload={'menu': 'reports'})
async def reports(message: Message):
    if not await islogged(message.from_id):
        await message.answer('Выберите нужный отчет:',
                             keyboard=Keyboard(one_time=False, inline=False)
                             .add(Text('Информационное письмо для родителей', {'report': 'parent'}), color=KeyboardButtonColor.PRIMARY)
                             .row()
                             .add(Text('Итоговые отметки', {'report': 'total'}), color=KeyboardButtonColor.PRIMARY))
    else:
        await message.answer('Выберите нужный отчет:',
                             keyboard=Keyboard(one_time=False, inline=False)
                             .add(Text('Информационное письмо для родителей', {'parent': 'choose_term'}),
                                  color=KeyboardButtonColor.PRIMARY)
                             .row()
                             .add(Text('Итоговые отметки', {'report': 'total'}), color=KeyboardButtonColor.PRIMARY))


@bot.on.private_message(payload={'menu': 'help'})
async def helpin(message: Message):
    await message.answer(helping)
    await logged_menu(message)
    await writing_to_file('helping')


@bot.on.private_message(payload={'menu': 'dept'})
async def dept(message: Message):
    msg = 'Задолженности по предметам:\n\n'
    user = (await db.get(message.from_id))[0]
    sgo_login, sgo_password, output_type, site, school = user[2], user[3], user[4], user[7], user[8]
    if await islogged(message.from_id):
        ns = NetSchoolAPI(site)
        await ns.login(sgo_login, sgo_password, school)
        over = await ns.overdue()
        await ns.logout()
        if over:
            for dept_rep in over:
                day = dept_rep["dueDate"][:dept_rep["dueDate"].find('T')].split('-')
                msg += f'Дата: {day[2]}.{day[1]}.{day[0]}\n' \
                       f'Предмет: {dept_rep["subjectName"]}\n' \
                       f'Задание: {dept_rep["assignmentName"]}\n\n'
            await message.answer(msg)
        else:
            await message.answer('😇 Задолженности отсутствуют ')
    else:
        await message.answer('Дата: 09.01.2023\n'
                             'Предмет: Русский язык\n'
                             'Задание: Выучить словарные слова\n')
    await logged_menu(message)
    await writing_to_file('dept')


# ADMIN COMANDS
@bot.on.message(text=['.удалить <id_first_del> <id_last_del>', '.удалить <id_first_del>'])
async def deleting_user(message: Message):
    if message.from_id == developer_id:
        not_sended = 'Не удалось удалить: \n'
        if len(message.text.split()) == 3:
            id_first_del = int(message.text.split()[1])
            id_last_del = int(message.text.split()[2])
        else:
            id_first_del = int(message.text.split()[1])
            id_last_del = int(message.text.split()[1])
        for num in range(id_first_del, id_last_del + 1):
            try:
                await db.del_user(num)
            except:
                not_sended += f'{num}, '
            else:
                await db.del_user(num)
        await message.answer(not_sended)


@bot.on.message(text=['.все'])
async def all_users(message: Message):
    if message.from_id == developer_id:
        answers = f''
        everyone = await db.get_all()
        for user in everyone:
            answers += f'{user[0]} | {user[5]} {user[6]} | [id{user[1]}|{user[5]}] | {user[-1]}\n'
        await message.answer(answers)


@bot.on.message(text='.изменить <user> <param> <value>')
async def changing_params(message: Message, user, param, value):
    if message.from_id == developer_id:

        await message.answer(message=(await db.change_user(user, param, value)))


@bot.on.message(text='.хелп')
async def help_command(message: Message):
    if message.from_id == developer_id:
        await message.answer(message="Dev-commands:\n\n"
                                     "Список пользователей: .все\n"
                                     "Изменить параметры пользователя: .изменить <id> <param> <value>\n"
                                     "Получить параметр пользователя: .гет <id> <param>\n"
                                     "Названия параметров пользователя: .парам\n"
                                     "Получение логов ошибок: .ошибки\n"
                                     "Удаление пользователя: .удалить")
        await message.answer(message.peer_id)


@bot.on.message(text='.гет <user> <param>')
async def changing_params(message: Message, user, param):
    if message.from_id == developer_id:
        result = db.get_value_param(user, param)
        if result != '':
            await message.answer(message=result)
        else:
            await message.answer(f'No one of: {param}')


@bot.on.message(text='.парам')
async def sending_params(message: Message):
    if message.from_id == developer_id:
        await message.answer("""id integer primary key autoincrement,
                    userid INT,
                    sgo_login TEXT,
                    sgo_password TEXT,
                    output_type TEXT,
                    name TEXT,
                    sec_name TEXT,
                    site_sgo TEXT,
                    school TEXT,
                    is_auth Text""")


@bot.on.message(text='.килл')
async def killing(message: Message) -> None:
    if message.from_id == developer_id:
        await message.answer('Пока = (')
        sys.exit()


@bot.on.chat_message(text='.рестарт')
async def restarting(message: Message) -> None:
    if message.from_id == developer_id:
        await message.answer('Запуск новой копии...')
        os.system(f'python {path_to_school_bot_file} &')
        await message.answer('Завершение старой копии...')
        sys.exit()


@bot.on.message(text='.обновить')
async def updating_project(message: Message):
    if message.from_id == developer_id:
        await message.answer('Скачивание файла...')
        doc = requests.get(message.attachments[0].doc.url).content
        open('github.zip', 'wb').write(doc)
        await message.answer('Замена файлов...')

        try:
            with zipfile.ZipFile('github.zip', 'r') as ref:
                ref.extractall(os.getcwd() + os.sep + 'mlok')
        except:
            await message.answer(f'Произошла ошибка! {traceback.format_exc()}')

        else:
            os.remove('github.zip')
            await message.answer('Перезагрузка...')
            os.system(f'python {path_to_school_bot_file} &')
            sys.exit()


@bot.on.private_message(text='.ошибки')
async def logging_send(message: Message):
    if message.from_id == developer_id:
        doc = await DocMessagesUploader(bot.api).upload(
            title='text.txt',
            file_source=full_path_to_errors_txt,
            peer_id=message.from_id)
        await message.answer('Логи:', attachment=doc)


@bot.on.message(text='.логин_<login>_<password>_<site>_<school>')
async def detail_lesson(message: Message, login, password, site, school):
    if message.from_id == developer_id:
        ns = NetSchoolAPI(site)
        await ns.login(login, password, school)
        await message.answer(str(await ns.diary()))


@bot.on.message(text='.очистить логи')
async def remove_report(message: Message):
    if message.from_id == developer_id:
        try:
            os.remove(os.getcwd() + os.sep + path_to_logs_functions_txt)
        except:
            await message.answer(str(traceback.format_exc()))
        else:
            await message.answer('Done!')


@bot.on.private_message(payload={'admin_report_week': 'global_admin_report'})
async def report_admin(message: Message):
    if message.from_id == developer_id:
        everyone = await db.get_all()
        authed = 0
        for user in everyone:
            if user[-1] == 'Yes':
                authed += 1
        msg = f'Отчет:\n\n' \
              f'Время непрерывной работы бота:{int((time.time() - start_time) // 3600 // 24)} дн. {int((time.time() - start_time) // 3600 % 24)} ч. ' \
              f'{int((time.time() - start_time) // 60 % 60)} мин. {int((time.time() - start_time) % 60)} с.\n' \
              f'Количество пользователей: {len(everyone)}\n\n' \
              f'Авторизованных: {authed}\n\n'

        await message.answer(msg, keyboard=Keyboard(one_time=True, inline=False)
                             .add(Text('Онлайн неделя', {'admin_report': 'online'}), color=KeyboardButtonColor.POSITIVE)
                             .add(Text('Онлайн месяц', {'admin_report': 'online'}), color=KeyboardButtonColor.PRIMARY)
                             .add(Text('Топ используемых функций', {'admin_report': 'online'}), color=KeyboardButtonColor.SECONDARY)
                             )


@bot.on.private_message(payload={'admin_report': 'online'})
async def global_report_admin(message: Message):
    msg = ''
    if message.text == 'Топ используемых функций':
        msg = 'Список используемых функций:\n\n'
        num_functions = {}
        with open(path_to_logs_functions_txt, 'r', encoding='utf-8') as filer:
            file = filer.readlines()
            for function in file[0].split(' ')[:-1]:
                num_functions[function] = num_functions.get(function, 0) + 1
            filer.close()

        num_functions = dict(reversed(sorted(num_functions.items(), key=lambda item: item[1])))
        for function in num_functions.keys():
            msg += f'{function}: {num_functions[function]} шт.\n'

    elif message.text == 'Онлайн неделя':
        msg = 'Статистика онлайна за неделю: \n'
        if len(online_data.keys()) > 6:
            for i in range(len(online_data.keys()) - 1, len(online_data.keys()) - 8, -1):
                msg += f'{list(online_data.keys())[i]}: {len(online_data[list(online_data.keys())[i]])} чел.\n'
        else:
            for day in online_data.keys():
                msg += f'{day}: {len(online_data[day])} чел.\n'

    elif message.text == 'Онлайн месяц':
        msg = 'Статистика онлайна за месяц: \n'
        if len(online_data.keys()) > 30:
            for i in range(len(online_data.keys()) - 1, len(online_data.keys()) - 31, -1):
                msg += f'{list(online_data.keys())[i]}: {len(online_data[list(online_data.keys())[i]])} чел.\n'
        else:
            for day in online_data.keys():
                msg += f'{day}: {len(online_data[day])} чел.\n'

    await message.answer(msg)
    await logged_menu(message)


@bot.on.raw_event(GroupEventType.WALL_POST_NEW, dataclass=GroupTypes.WallPostNew)
async def aboba(event: GroupTypes.WallPostNew):
    if event.object.post_type == WallPostType.POST:
        try:
            keyboard = Keyboard(inline=True, one_time=False).add(Callback('Oпубликoвaть!', {'bot_news': 'True'}), color=KeyboardButtonColor.POSITIVE)

            await bot.api.messages.send(user_id=site_manager_id,
                                        random_id=0,
                                        message='Новый пост!',
                                        attachment=f'wall{event.object.owner_id}_{event.object.id}',
                                        keyboard=keyboard)
            await bot.api.messages.send(user_id=developer_id, random_id=0, message=f'Новый пост:\n\nwall{event.object.owner_id}_{event.object.id}')
        except Exception as e:
            msg = 'Возникла ошибка при получении поста с группы:\n\n' + traceback.format_exc()
            await bot.api.messages.send(user_id=developer_id, random_id=0, message=msg)
            await bot.api.messages.send(user_id=site_manager_id, random_id=0, message='Произошла ошибка, разработчик уже оповещен')


@bot.on.private_message(text='.отзыв <text>')
async def review(message: Message, text):
    if message.from_id == developer_id:
        sender = 0
        keyboard = Keyboard(one_time=True, inline=False)
        for num in range(10):
            if num % 3 != 0:
                keyboard.add(Text(str(num + 1), {'review': 'mark'}), color=KeyboardButtonColor.PRIMARY)
            else:
                if num != 9:
                    keyboard.add(Text(str(num + 1), {'review': 'mark'}), color=KeyboardButtonColor.PRIMARY).row()
                else:
                    keyboard.add(Text(str(num + 1), {'review': 'mark'}), color=KeyboardButtonColor.PRIMARY)
        everyone = await db.get_all()
        alist = []
        for user in everyone:
            if user[-1] == 'Yes':
                alist.append(int(user[1]))

        for human in alist:
            try:
                await bot.api.messages.send(user_id=human, message=text, keyboard=keyboard, random_id=0)
                sender += 1
            except Exception as e:
                pass
            finally:
                await sleep(2)
        await message.answer(f'Готово!\nОтправлено {sender} сообщений')


@bot.on.private_message(payload={'review': 'mark'})
async def payload_review(message: Message):
    try:
        await message.answer('Спасибо за ответ!')
        await bot.api.messages.send(peer_id=feedback_chat, message=f'Новый отзыв о боте!\nОценка: {message.text}\nПользователь: @{message.from_id}', random_id=0)
        await logged_menu(message)
    except:
        pass


@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def photos_private(event: MessageEvent):
    ctx.set('cms', event.object.conversation_message_id)
    await event.show_snackbar('Секунду...')
    await bot.state_dispenser.set(peer_id=event.peer_id, state=States.wall_news_header)
    await bot.api.messages.send(user_id=site_manager_id, random_id=0, message='Введите заголовок: ')


@bot.on.private_message(state=States.wall_news_header)
async def set_heades_post(message: Message):
    await bot.state_dispenser.delete(peer_id=message.peer_id)
    ctx.set('header', message.text)
    await message.answer('Выберите действие:', keyboard=Keyboard(one_time=True, inline=False)
                         .add(Text('Опубликовать без категории', {'push_to_site': 'no_cat'}), color=KeyboardButtonColor.SECONDARY)
                         .row()
                         .add(Text('Мероприятия', {'push_to_site': 'no_cat'}))
                         .add(Text('Всемирный день', {'push_to_site': 'no_cat'}))
                         .row()
                         .add(Text('Конкурсы', {'push_to_site': 'no_cat'}))
                         .add(Text('Последний звонок 2020г.', {'push_to_site': 'no_cat'}))
                         .row()
                         .add(Text('Вести образования', {'push_to_site': 'no_cat'}))
                         .add(Text('День знаний', {'push_to_site': 'no_cat'}))
                         .row()
                         .add(Text('Соревнования', {'push_to_site': 'no_cat'}))
                         .add(Text('День воинской славы', {'push_to_site': 'no_cat'}))
                         .row()
                         .add(Text('COVID', {'push_to_site': 'no_cat'}))
                         .add(Text('Проект "Современная траектория..."', {'push_to_site': 'no_cat'})))


@bot.on.private_message(payload={'push_to_site': 'no_cat'})
async def choose_cat(message: Message):
    cms_id = ctx.get('cms')
    header = ctx.get('header')

    categories = {
        'Проект "Современная траектория..."': 10,
        'COVID': 9,
        'День воинской славы': 8,
        'Соревнования': 7,
        'День знаний': 6,
        'Вести образования': 5,
        'Последний звонок 2020г.': 4,
        'Конкурсы': 3,
        'Всемирный день': 2,
        'Мероприятия': 1
    }
    if message.text == 'Опубликовать без категории':
        cat = 0
    else:
        cat = categories[message.text]

    pictures_dict = []
    msg = (await bot.api.messages.get_by_conversation_message_id(site_manager_id, cms_id)).items[0].attachments[0].wall
    attachments = msg.attachments
    if attachments:
        for attach in attachments:
            if attach.photo:
                for photo in attach.photo.sizes:
                    if photo.width == 320:
                        pictures_dict.append(photo.url)

    short_text = msg.text
    try:
        post_to_site(cat, header, pictures_dict, short_text)
        await message.answer('Успешно опубликовано для всех пользователей!')
    except:
        msg = 'Возникла ошибка при публикации поста на сайт:\n\n' + traceback.format_exc()
        await bot.api.messages.send(user_id=developer_id, random_id=0, message=msg)
        await bot.api.messages.send(user_id=site_manager_id, random_id=0,
                                    message='Произошла ошибка, разработчик уже оповещен')


@bot.on.private_message(text=['кот', 'Кот', 'коты', "котик"])
async def cats(message: Message):
    if len(message.text.split()) == 1:
        cat_url = 'https://aws.random.cat/meow'
        cat_link = requests.get(cat_url).json()['file']
        pic_cat = requests.get(cat_link).content
        pic = await PhotoMessageUploader(bot.api).upload(file_source=pic_cat, title='cat.jpg', peer_id=message.from_id)
        await message.answer('Лови котенка!', attachment=pic)
        await logged_menu(message)


@bot.on.chat_message()
async def answering(message: Message):
    if message.reply_message:
        id_user = message.reply_message.text.split()
        id_user = id_user[3][id_user[3].find('[') + 3:id_user[3].rfind('|')]
        msg = f'Ответ от администратора группы на ваш вопрос:\n' \
              f'"{message.reply_message.text[message.reply_message.text.rfind(":") + 2:]}"\n\n' \
              f'Ответ: {message.text}'
        await bot.api.messages.send(user_id=int(id_user), message=msg, random_id=0)
        await message.answer('Ответ отправлен!')


# Base handler #
@bot.on.private_message()
async def logged_menu_auto(message: Message):
    is_auth = await db.get(message.from_id)
    if is_auth:
        user = is_auth[0][-2]
        try:
            await bot.state_dispenser.delete(message.peer_id)
        except:
            pass
        if user == 'МОУ гимназия № 10':
            paylo = {'logged': 'schedule'}
        else:
            paylo = {'schedule': 'week'}
        keyboard = (
            Keyboard(inline=False, one_time=False)
            .add(Text('Boпpосы пo РДШ/Группе', {'menu': 'question'}), color=KeyboardButtonColor.PRIMARY)
            .row()
            .add(Text('📚 Дневник на текущую неделю', {'schedule': 'full_week'}), color=KeyboardButtonColor.POSITIVE)
            .row()
            .add(Text('📖 Дневник', {'logged': 'diary'}), color=KeyboardButtonColor.POSITIVE)
            .row()
            .add(Text('📅 Расписание', payload=paylo), color=KeyboardButtonColor.PRIMARY)
            .add(Text('📝 Отчет', {'menu': 'reports'}), color=KeyboardButtonColor.PRIMARY)
            .row()
            .add(Text('⚙ Настройки', {'logged': 'settings'}), color=KeyboardButtonColor.SECONDARY)
        )
        if not await islogged(message.from_id):
            text = 'Добро пожаловать в тестовый режим!\n\nВы можете протестировать функции, кнопочки и всё необходимое.\n' \
                   'Будет показываться выдуманное расписание с выдуманными предметами, заданиями и оценками.\n\n' \
                   'Для входа в свой дневник воспользуйтесь соответствующей кнопкой ниже = )'
            keyboard.row().add(Text('Войти в свой дневник', {'variant': 'login'}),
                               color=KeyboardButtonColor.POSITIVE)
        else:
            text = 'Меню...'
        if message.from_id == developer_id:
            keyboard.row().add(Text('Отчет', {'admin_report_week': 'global_admin_report'}), color=KeyboardButtonColor.SECONDARY)
        await message.answer(message=text, keyboard=keyboard)
    else:
        name = await bot.api.users.get(message.from_id)
        msg = f'Новый вопрос от ' \
              f'[id{message.from_id}|{name[0].first_name} {name[0].last_name}] \n\n' \
              f'Ответьте на это сообщение для ответа на вопрос\n\n' \
              f'Текст вопроса: {message.text}'
        await bot.api.messages.send(message=msg, peer_id=question_chat,
                                    forward_messages=message.id, random_id=0)
        await message.answer(
            message='✅ Вопрос успешно отправлен администраторам!\n Вскоре вам ответят = )')


if __name__ == '__main__':
    with open(path_to_online_json, 'r', encoding='utf-8') as file:
        online_data = json.load(file)

    start_time = time.time()
    bot.run_forever()
