"""
### WATERMARK ###

# Dev: Pavel Krupenko #
# Git: greench2020 #
# VK: @greench_2021 #
# Telegram: @Andeeeyyy #
# Discord: '3EJLEHblN 4EJLOBEK#3374'

### WATERMARK ###


Скрипт для создания изображений, используемых ботов при работе.
"""

import datetime
import locale
import os

import pymorphy2
from PIL import Image, ImageDraw, ImageFont

from modules.config import w_daya, base_total
from modules.paths import *

morph = pymorphy2.MorphAnalyzer()
days = {}
data_days = {}


def updating_image(h_w, pos, im):
    draw_text = ImageDraw.Draw(im)
    font = ImageFont.truetype(path_to_arial_ttf, 13)
    if len(h_w) > 171:
        h_w = h_w[:h_w[:171].rfind(' ')] + '...'
    if len(h_w) > 57:
        num = h_w[:57].rfind(' ')
        old_mess = h_w[:num]
        new_mes = h_w[num + 1:]
        new_pos = (pos[0], pos[1] + 16)
        draw_text.text(pos, old_mess, fill='#1c0606', font=font)
        updating_image(new_mes, new_pos, im)
    else:
        draw_text.text(pos, h_w, fill='#1c0606', font=font)


def edit_msg(subject, h_w, mark, pos, im):
    other_homework = ''
    draw_text = ImageDraw.Draw(im)
    font = ImageFont.truetype(path_to_arial_ttf, 13)

    if len(h_w) > 104:
        other_homework = [{subject: h_w}]
        h_w = h_w[:h_w[:104].rfind(' ')] + '...'
    # homework writing
    if len(h_w) > 57:
        num = h_w[:57].rfind(' ')
        old_mess = h_w[:num]
        new_mes = h_w[num + 1:]
        new_pos = (pos[0], pos[1] + 16)
        draw_text.text(pos, old_mess, fill='#1c0606', font=font)
        updating_image(new_mes, new_pos, im)
    else:
        draw_text.text(pos, h_w, fill='#1c0606', font=font)

    # subject writing
    sub_pos = (pos[0] - 214, pos[1] + 2)
    font = ImageFont.truetype(path_to_arial_bd_ttf, 17)
    draw_text.text(sub_pos, subject, fill='#008ac9', font=font)

    # mark writing
    sub_pos = (pos[0] + 462, pos[1] - 2)

    color = '#0058c1'
    print(subject, mark.split(), sep=' ')
    if mark != '':
        if len(mark.split()) > 1:
            sub_pos = (pos[0] + 420, pos[1])
            for i in mark.split():
                if int(i) == 2:
                    color = '#ff0000'
                font = ImageFont.truetype(path_to_ton_ttf, 40)
                draw_text.text((sub_pos[0] + 28, sub_pos[1]), i, fill=color, font=font)
                sub_pos = (sub_pos[0] + 28, sub_pos[1])
        else:
            if int(mark) == 2:
                color = '#ff0000'
            font = ImageFont.truetype(path_to_ton_ttf, 40)
            draw_text.text((sub_pos[0], sub_pos[1]), mark, fill=color, font=font)
    return other_homework


def create_img(lessons, user_id):
    first_pos = (260, 60)
    other_homeworks = []
    im = Image.open(path_to_days_jpg)
    date = lessons[0]

    for lesson in lessons[1:]:
        lesson = lesson.strip()
        subject = lesson[:lesson.find(':')]
        print(lesson)
        if len(subject) > 17:
            subject = subject[:18] + '...'
        if lesson[-8:] != 'Оценка: ':
            mark = lesson[lesson.rfind(':') + 1:]
        else:
            mark = ''
        homework = lesson[lesson.find(':') + 2:lesson.find(' Оценка: ')]
        rec_homework = edit_msg(subject, homework.replace('Оценка', '').replace('Не задано', ''), mark.strip(" "), first_pos, im)
        if rec_homework:
            other_homeworks.append(rec_homework)
        first_pos = (first_pos[0], first_pos[1] + 57)

    # Creating rotated img with week_day
    date = lessons[0].strip()
    locale.setlocale(
        category=locale.LC_ALL,
        locale="Russian"
    )

    word = datetime.date.today().strftime('%d %B %Y').split(' ')[1]
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    label = f"{w_daya[date.weekday()]}, {str(date.strftime('%d %B %Y')).split(' ')[0]} " \
            f"{morph.parse(word)[0].inflect({'gent'}).word.title()} " \
            f"{str(date.strftime('%d %B %Y')).split(' ')[2]}"
    font = ImageFont.truetype(path_to_arial_ttf, 18)

    fontimage = Image.new('RGB', (789, 42), color='#438c03')
    ImageDraw.Draw(fontimage).text((275, 10), str(label), fill='#ffffef', font=font)

    im.paste(fontimage, (0, 0))

    im.save(f'{os.getcwd() + os.sep}mlok/BotData/Pics/' + str(user_id) + '.jpg')
    path = f'{os.getcwd() + os.sep}mlok/BotData/Pics/' + str(user_id) + '.jpg'

    locale.setlocale(
        category=locale.LC_ALL, locale='en_GB'
    )

    return [path, other_homeworks]


# Main function
def create_report(report, user_id):
    list_averages = []
    dict_mark = {'5': 0, '4': 0, '3': 0, '2': 0, 'average': 0, 'term': 0}
    list_pre_report = []
    mark_pos = (917, 16)
    for subject in report['subjects'].keys():
        each_lesson = {'5': report['subjects'][subject]['5'], '4': report['subjects'][subject]['4'],
                       '3': report['subjects'][subject]['3'], '2': report['subjects'][subject]['2'],
                       'average': report['subjects'][subject]['average'], 'term': report['subjects'][subject]['term'],
                       'subject': subject}
        list_pre_report.append(each_lesson)

    total = report['total']

    im = generating_head_report(list_pre_report, user_id)
    im2 = Image.open(path_to_end_png)
    draw_text = ImageDraw.Draw(im2)
    font = ImageFont.truetype(path_to_arial_bd_ttf, 30)
    for keys in total.keys():
        if keys.isnumeric() or keys.isalnum():
            if len(total[keys]) == 1:
                mark_pos = (mark_pos[0] + 66, mark_pos[1])
            else:
                mark_pos = (mark_pos[0] + 62, mark_pos[1])
            draw_text.text(mark_pos, total[keys], fill='black', font=font)

    for mark in report['subjects'].keys():
        if report['subjects'][mark]['average'] != '\xa0':
            list_averages.append(float(report['subjects'][mark]['average'].replace(',', '.')))

    if list_averages:
        average_term = round((sum(list_averages) / len(list_averages)), 2)
    else:
        average_term = '\xa0'

    draw_text.text((mark_pos[0] + 10, mark_pos[1]), str(average_term), fill='black', font=font)

    w_1, h_1 = im.size
    w_2, h_2 = im2.size
    new_im = Image.new('RGB', (w_1, h_1 + h_2), 'white')
    new_im.paste(im, (0, 0))
    new_im.paste(im2, (0, h_1))

    new_im.save(f'{os.getcwd()}/mlok/BotData/Pics/{user_id}.png')
    os.remove(f'{os.getcwd()}/mlok/{user_id}.png')
    return f'{os.getcwd()}/mlok/BotData/Pics/{user_id}.png'


def generating_head_report(list_reports, user_id):

    list_numeric = []
    mark_pos = (983, 350)
    im = Image.open(path_to_head_half_year_png)
    draw_text = ImageDraw.Draw(im)
    font = ImageFont.truetype(path_to_arial_bd_ttf, 30)
    subject = list_reports[0]['subject']

    if len(subject) > 57:
        point = subject[:58].rfind(' ')
        subject = subject[:58][:point] + '\n' + subject[point + 1:]
        pos = (12, 330)
    else:
        pos = (15, 350)

    draw_text.text(pos, subject, fill='black', font=font)
    for keys in list_reports[0].keys():

        if keys.isnumeric() or keys.isalnum():
            list_numeric.append(f'{keys}, {list_reports[0][keys]}')
            draw_text.text(mark_pos, list_reports[0][keys], fill='black', font=font)
            mark_pos = (mark_pos[0] + 66, mark_pos[1])
    return generating_body_report(im, user_id, list_reports)


def generating_body_report(im, user_id, list_reports):
    for i in range(1, len(list_reports)):

        # Base Data
        mark_pos = (917, 38)
        im2 = Image.open(path_to_pattern_png)
        draw_text = ImageDraw.Draw(im2)
        font = ImageFont.truetype(path_to_arial_bd_ttf, 30)
        subject = list_reports[i]['subject']

        # Detection len subject and getting position
        if len(subject) > 54:
            point = subject[:55].rfind(' ')
            subject = subject[:55][:point] + '\n' + subject[point + 1:]
            pos = (15, 24)
        else:
            pos = (15, 35)

        # Drawing subject and detecting and drawing marks
        draw_text.text(pos, subject, fill='black', font=font)
        for keys in list_reports[i].keys():
            if keys.isnumeric() or keys.isalnum():
                if len(list_reports[i][keys]) == 1:
                    mark_pos = (mark_pos[0] + 66, mark_pos[1])
                else:
                    mark_pos = (mark_pos[0] + 57, mark_pos[1])
                draw_text.text(mark_pos, list_reports[i][keys], fill='black', font=font)

        # Creating new image
        w_1, h_1 = im.size
        w_2, h_2 = im2.size
        new_im = Image.new('RGB', (w_1, h_1 + h_2), 'white')
        new_im.paste(im, (0, 0))
        new_im.paste(im2, (0, h_1))
        im = new_im

    # Saving final image as .png
    new_im.save(f'{os.getcwd()}/mlok/{user_id}.png')

    # Return path to image
    return new_im

# DEVELOPING #


def creating_total_report_img(user_id, example_marks, s_class):
    if s_class not in [10, 11]:
        opening_pic = path_to_7_body_toll_png
        head = Image.open(path_to_7_head_7_png)
        m_pos = (280, 8)
        adding_p = 83
    else:
        head = Image.open(path_to_11_head_png)
        opening_pic = path_to_11_body_png
        m_pos = (425, 8)
        adding_p = 70

    for subject, marks in example_marks.items():

        pic = Image.open(opening_pic)
        draw_text = ImageDraw.Draw(pic)

        if len(subject) > 28:
            point = subject[:29].rfind(' ')
            subject = subject[:29][:point] + '\n' + subject[point + 1:]
            pos = (35, 2)
            font = ImageFont.truetype(path_to_arial_bd_ttf, 11)

        else:
            font = ImageFont.truetype(path_to_arial_bd_ttf, 13)
            pos = (35, 8)

        draw_text.text(pos, subject, fill='black', font=font)

        if marks:
            mark_pos = m_pos
            font = ImageFont.truetype(path_to_arial_bd_ttf, 14)
            for mark in marks:
                draw_text.text(mark_pos, mark, fill='black', font=font)
                mark_pos = (mark_pos[0] + adding_p, mark_pos[1])
        w_1, h_1 = head.size
        w_2, h_2 = pic.size
        new_im = Image.new('RGB', (w_1, h_1 + h_2), 'white')
        new_im.paste(head, (0, 0))
        new_im.paste(pic, (0, h_1))
        head = new_im
    head.save(f'{os.getcwd()}/mlok/total_{user_id}.png')
    return f'{os.getcwd()}/mlok/total_{user_id}.png'


def generation_total_report(user_id, total_report, s_class):
    total_data = {}
    for quarter in total_report.keys():
        for subject in total_report[quarter]:
            if subject in total_data:
                total_data[subject] += [total_report[quarter][subject]]
            else:
                total_data[subject] = [total_report[quarter][subject]]

    return creating_total_report_img(user_id, total_data, s_class)



print('[*] Creating images was successfully upload!')
