import hashlib
import MySQLdb
from flask import session


class DatabaseHandler():
    def __init__(self, mysql):
        self.mysql = mysql
    def get_cursor(self):
        mysql = self.mysql
        return mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    def get_user_by_username_and_password(self, username, password):
        cursor = self.get_cursor()
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        return cursor.fetchone()

    def get_chat_by_account_id(self, account_id):
        dh = DatabaseHandler(self.mysql)
        cursor = dh.get_cursor()
        cursor.execute('SELECT * FROM chats WHERE account_id = %s', (account_id,))
        chat = cursor.fetchall()
        return chat

    def get_messages_by_chat_id(self, chat_id):
        dh = DatabaseHandler(self.mysql)
        cursor = dh.get_cursor()
        cursor.execute('SELECT * FROM messages WHERE chat_id = %s', (chat_id,))
        messages = cursor.fetchall()
        return messages

    def get_account_data_by_username(self, username):
        mysql = self.mysql
        dh = DatabaseHandler(mysql)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        return account

    def get_account_data_by_id(self, id):
        mysql = self.mysql
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE account_id = %s', (id,))
        account = cursor.fetchone()
        return account

    def insert_data_in_account(self, username, password, email):
        mysql = self.mysql
        dh = DatabaseHandler(mysql)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email,))
        mysql.connection.commit()

    def get_chat_by_id(self, card_id):
        mysql = self.mysql
        dh = DatabaseHandler(mysql)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM chats WHERE chat_id = %s', (card_id,))
        card = cursor.fetchone()
        return card

    def create_new_chat(self, account_id, chat_name):
        mysql = self.mysql
        dh = DatabaseHandler(mysql)
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO chats (`account_id`, `chat_name`) VALUES (%s, %s)",
            (account_id,chat_name)
        )
        mysql.connection.commit()
        cur.close()

    def get_latest_chat_id(self, account_id):
        cursor = self.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT MAX(chat_id) AS latest_chat_id FROM chats WHERE account_id = %s", (account_id,))
        result = cursor.fetchone()
        if result and result['latest_chat_id']:
            return result['latest_chat_id']
        else:
            return None

    def get_all_messages(self, chat_id):
        cursor = self.mysql.connection.cursor()
        cursor.execute("SELECT role, text FROM messages WHERE chat_id = %s", (chat_id,))
        messages = cursor.fetchall()
        cursor.close()
        return messages

    def insert_message(self, chat_id, text, role):
        mysql = self.mysql
        dh = DatabaseHandler(mysql)
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO messages (`chat_id`, `text`, `role`) VALUES (%s, %s, %s)",
            (chat_id, text, role)
        )
        mysql.connection.commit()
        cur.close()

    def check_password(self, account_id, password):
        print(account_id, password)
        mysql = self.mysql
        dh = DatabaseHandler(mysql)
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('SELECT * FROM accounts WHERE account_id = %s AND password = %s', (account_id, password))
        account = cur.fetchone()
        return account

    def update_password(self, new_password, id):
        mysql = self.mysql
        dh = DatabaseHandler(mysql)
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('UPDATE accounts SET password = %s WHERE account_id = %s', (new_password, session['id']))
        mysql.connection.commit()



class PasswordManager():
    @staticmethod
    def hash_password(password, secret_key):
        hash = password + secret_key
        hash = hashlib.sha1(hash.encode())
        password = hash.hexdigest()
        return password


class SessionManager():
    @staticmethod
    def is_logged_in():
        return 'loggedin' in session

    @staticmethod
    def logout():
        session.pop('loggedin', None)
        session.pop('id', None)
        session.pop('username', None)