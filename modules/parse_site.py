"""
### WATERMARK ###

# Dev: Pavel Krupenko #
# Git: greench2020 #
# VK: @greench_2021 #
# Telegram: @Andeeeyyy #
# Discord: '3EJLEHblN 4EJLOBEK#3374'

### WATERMARK ###


Скрипт для парсинга сайта 'https://gimnasiumten.ru/' с целью добавления новости.
Функция добавлена по просьбе администрации школы.
"""

import datetime

import requests

from modules.config import uid_pass, uid_login


def edit_text(text, attachments):
    new_line = ''
    files = []
    full_data = {}
    for line in text.split('\n'):
        new_line += f'<p><span style="font-size:12px;"><span style="font-family:Verdana,Geneva,sans-serif;">{line}</span></span>&nbsp;</p>'
    new_line += '\n'

    if attachments:
        if len(attachments) <= 3:
            for attach_num in range(len(attachments)):
                photo = requests.get(attachments[attach_num]).content
                data = {f'file{attach_num + 1}': photo,
                        f'h{attach_num + 1}': f'$IMAGE{attach_num + 1}$',
                        f'img{attach_num + 1}_title': '',
                        f'img{attach_num + 1}_alt': '',
                        f'iws{attach_num + 1}': 400,
                        f'ihs{attach_num + 1}': 500,
                        f't{attach_num + 1}': f'$IMG{attach_num + 1}_TITLE$',
                        f'a{attach_num + 1}': f'$IMG{attach_num + 1}_ALT$'
                        }
                files.append((f'file{attach_num + 1}', (f'name_file{attach_num + 1}.png', photo, 'image/png')))
                for key in data.keys():
                    full_data[key] = data[key]

                if attach_num < 2:
                    new_line += f'$IMAGE{attach_num + 1}$  '
                elif attach_num == 2:
                    new_line += f'\n$IMAGE{attach_num + 1}$'

        else:
            for attach_num in range(3):
                photo = requests.get(attachments[attach_num]).content
                data = {f'file{attach_num + 1}': photo,
                        f'h{attach_num + 1}': f'$IMAGE{attach_num + 1}$',
                        f'img{attach_num + 1}_title': '',
                        f'img{attach_num + 1}_alt': '',
                        f'iws{attach_num + 1}': 400,
                        f'ihs{attach_num + 1}': 500,
                        f't{attach_num + 1}': f'$IMG{attach_num + 1}_TITLE$',
                        f'a{attach_num + 1}': f'$IMG{attach_num + 1}_ALT$'
                        }
                files.append((f'file{attach_num + 1}', (f'name_file{attach_num + 1}.png', photo, 'image/png')))
                for key in data.keys():
                    full_data[key] = data[key]

                if attach_num < 3:
                    new_line += f'$IMAGE{attach_num + 1}$  '
                elif attach_num == 3:
                    new_line += f'\n$IMAGE{attach_num + 1}$'

    return new_line, full_data, files


def post_to_site(categoty, header, attachments, short_text):
    with requests.Session() as session:
        url = 'https://gimnasiumten.ru/'
        data = {'user': uid_login, 'password': uid_pass, 'rem': 1, 'a': 2, 'ajax': 2, '_tp_': 'xml'}
        cookies = session.post(url='https://gimnasiumten.ru/index/sub/', data=data).cookies
        short_text, not_full_data, files = edit_text(short_text, attachments)

        data = {'jkd498': '1',
                'jkd428': '1',
                'cat': categoty,
                'title': header,
                'fsize': '0',
                'ffont': '0',
                'fcolor': '0',
                'brief': short_text,
                'edttbrief': '1',
                'html_brief': '1',
                'message': short_text,
                'edttmessage': '1',
                'html_message': '1',
                'user': 'pirmarina',
                'ya': '2023',
                'ma': str(datetime.date.today().month),
                'da': str(datetime.date.today().day),
                'ha': '22',
                'mia': '34',
                'file1': '',
                'tags': '',
                'a': '2',
                'ssid': 'S7_xyMPp',
                'coms_allowed': '1',
                '_tp_': 'xml',
                '_wi': '1'}
        for tag in not_full_data.keys():
            data[tag] = not_full_data[tag]

        # Posting
        session.post(url=(url + 'news'), cookies=cookies, data=data, files=files)


print('[*] Parsing script was successfully upload')
