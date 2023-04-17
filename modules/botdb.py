import sqlite3


"""
### WATERMARK ###

# Dev: Pavel Krupenko #
# Git: greengroat #
# VK: @greengroat
# Telegram: @greengroat #
# Discord: '3EJLEHblN 4EJLOBEK#3374'

### WATERMARK ###


Скрипт для управления Базой данных SQLite3. Описание функций не требуется, функционал понятен по названию
"""


class BotDB:

    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self.conn.commit()

    def making_table(self):
        self.cursor.execute(f"""CREATE TABLE IF NOT EXISTS 'school_db'(
                id integer primary key autoincrement,
                userid INT,
                sgo_login TEXT,
                sgo_password TEXT,
                output_type TEXT,
                name TEXT,
                sec_name TEXT,
                site_sgo TEXT,
                school TEXT,
                is_auth Text);
            """)
        self.conn.commit()

    async def adding_user(self, id_user, name, sec_name):
        if_id = (self.cursor.execute(f'SELECT "userid" FROM "school_db" WHERE "userid" = ?', (id_user,))).fetchall()
        if len(if_id) == 0:
            self.cursor.execute(f"INSERT INTO 'school_db'(userid, sgo_login, sgo_password, output_type,"
                                f"name, sec_name, site_sgo, school, is_auth) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (id_user, "", "", "Изображение", name, sec_name, 'https://sgo.volganet.ru/',
                                 'МОУ гимназия № 10', 'No'))
            self.conn.commit()

    async def get(self, id_user):
        one_result = self.cursor.execute(f'SELECT * FROM "school_db" WHERE "userid" = ?', (id_user,))
        return one_result.fetchall()

    async def update(self, user_id, sgo_l, sgo_pass, ):
        self.cursor.execute(f"""UPDATE 'school_db' SET sgo_login = ? WHERE userid = ?""", (sgo_l, user_id))
        self.cursor.execute(f"""UPDATE 'school_db' SET sgo_password = ? WHERE userid = ?""", (sgo_pass, user_id))
        self.conn.commit()
        return (self.cursor.execute(f'SELECT * FROM "school_db" WHERE "userid" = ?', (user_id,))).fetchone()

    async def set_site_and_school(self, user_id, school):
        self.cursor.execute(f"""UPDATE 'school_db' SET school = ? WHERE userid = ?""", (school, user_id))
        self.conn.commit()

    async def set_output_type(self, user_id, output_type):
        self.cursor.execute(f"""UPDATE 'school_db' SET output_type = ? WHERE userid = ?""", (output_type, user_id))
        self.conn.commit()

    async def set_authorize(self, user_id, value):
        self.cursor.execute(f"""UPDATE 'school_db' SET is_auth = ? WHERE userid = ?""", (value, user_id))
        self.conn.commit()

    async def del_user(self, user_id):
        try:
            if user_id >= 10000:
                self.cursor.execute('DELETE FROM school_db WHERE userid = ?', (user_id,))
                self.conn.commit()
            else:
                self.cursor.execute('DELETE FROM school_db WHERE id = ?', (user_id,))
                self.conn.commit()

            all_u = (self.cursor.execute("SELECT * FROM school_db")).fetchall()
            self.cursor.execute("DELETE FROM school_db")
            self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='school_db'")

            for i in all_u:
                self.cursor.execute(f"INSERT INTO 'school_db'(userid, sgo_login, sgo_password, output_type,"
                                    f"name, sec_name, site_sgo, school, is_auth) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                    i[1:])
            self.conn.commit()

            return 'Done'
        except:
            return 'Error'

    async def get_all(self):
        all_users = self.cursor.execute("SELECT * FROM school_db")
        return all_users.fetchall()

    async def change_user(self, user, param, value):
        if param == 'is_auth' and value == 'No':
            self.cursor.execute(f"UPDATE school_db SET {param} = ? WHERE id = ?", (value, user))
            self.cursor.execute(f"UPDATE school_db SET sgo_login = ? WHERE id = ?", ('', user))
            self.cursor.execute(f"UPDATE school_db SET sgo_password = ? WHERE id = ?", ('', user))
            self.conn.commit()
        else:
            self.cursor.execute(f"UPDATE school_db SET {param} = ? WHERE id = ?", (value, user))
        return 'Done'

    async def get_value_param(self, user, param):
        value = str(self.cursor.execute(f'SELECT {param} FROM school_db WHERE id = ?', (user,)).fetchone()[0])
        return value


print('[*] Bot DataBase upload!')
