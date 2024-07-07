from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import re
import logging
import openai
import random

import os
from models.Manager import PasswordManager
from models.Manager import DatabaseHandler
from models.Manager import SessionManager

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = "hi"
openai.api_key = os.getenv("OPENAI_API_KEY")
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'chat-bot'

mysql = MySQL(app)

def get_completion(messages, model="gpt-3.5-turbo"):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message["content"]

def give_title(user_text, model="gpt-3.5-turbo"):
    messages = [{"role": "user", "content": f"give a title for the next text in only 1-2 words and output only it without any extra words and symbols: {user_text}"}]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message["content"]


@app.route("/")
def start():
    return render_template("login.html")


@app.route('/chat-bot/chat/<int:chat_id>')
def open_chat(chat_id):
    if SessionManager.is_logged_in():
        dh = DatabaseHandler(mysql)
        account = dh.get_account_data_by_id(session['id'])
        username = account['username']
        chats = dh.get_chat_by_account_id(account['account_id'])
        chat = dh.get_chat_by_id(chat_id)
        messages = dh.get_messages_by_chat_id(chat_id)
        session["messages"] = messages
        return render_template('home.html', username=username, account=account, chats=chats, chat=chat, messages=messages)
    return redirect(url_for('login'))




@app.route('/chat-bot/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        hashed_password = PasswordManager.hash_password(password, app.secret_key)
        dh = DatabaseHandler(mysql)
        account = dh.get_user_by_username_and_password(username, hashed_password)
        if account:
            session['loggedin'] = True
            session['id'] = account['account_id']
            session['username'] = account['username']
            return redirect(url_for('home'))
        else:
            msg = 'Incorrect username/password!'
    return render_template('login.html', msg=msg)


@app.route('/chat-bot/register', methods=['GET', 'POST'])
def register():
    dh = DatabaseHandler(mysql)
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        account = dh.get_account_data_by_username(username)
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            hashed_password = PasswordManager.hash_password(password, app.secret_key)
            dh.insert_data_in_account(username, hashed_password, email)
            msg = 'You have successfully registered!'

    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)


@app.route('/chat-bot/get_ai_response', methods=['GET', 'POST'])
def get_bot_response():
    user_text = request.args.get('msg')
    dh = DatabaseHandler(mysql)

    if 'messages' not in session:
        session['messages'] = []
        dh = DatabaseHandler(mysql)
        account_id = session['id']
        chat_name = give_title(user_text)
        chat = dh.create_new_chat(account_id, chat_name)
        chat_id = dh.get_latest_chat_id(session['id'])
        print(chat_id)
    else:
        chat_id = dh.get_latest_chat_id(session['id'])
        if not session['messages']:
            db_messages = dh.get_all_messages(chat_id)
            session['messages'] = [
                {"chat_id": chat_id, "text": msg[1], "role": msg[0]}
                for msg in db_messages
            ]

    msgs = list(session['messages'])
    msgs.append({"role": "user", "text": user_text, "chat_id": chat_id})
    session['messages'] = msgs
    dh = DatabaseHandler(mysql)
    dh.insert_message(chat_id, user_text, "user")
    print(session['messages'])
    messages_for_AI = []
    for message in session['messages']:
        role = message["role"]
        content = message["text"]
        messages_for_AI.append({"role": role, "content": content})
    print(messages_for_AI)
    response = get_completion(messages_for_AI)
    session['messages'].append({"role": "assistant", "text": response, "chat_id": chat_id})
    dh.insert_message(chat_id, response, "assistant")

    session.modified = True

    return response


@app.route('/chat-bot/logout')
def logout():
    SessionManager.logout()
    return redirect(url_for('login'))

@app.route('/chat-bot/home')
def home():
    if SessionManager.is_logged_in():
        dh = DatabaseHandler(mysql)
        account = dh.get_account_data_by_id(session['id'])
        username = account['username']
        chats = dh.get_chat_by_account_id(account['account_id'])
        session.pop('messages', None)
        return render_template('home.html', username=username, account=account, chats=chats)
    return redirect(url_for('login'))



@app.route('/chat-bot/profile')
def profile():
    if SessionManager.is_logged_in():
        dh = DatabaseHandler(mysql)
        account = dh.get_account_data_by_id(session['id'])
        chats = dh.get_chat_by_account_id(account['account_id'])

        return render_template('profile.html', account=account, chats=chats)
    return redirect(url_for('login'))


@app.route('/chat-bot/change_password', methods=['GET', 'POST'])
def change_password():
    dh = DatabaseHandler(mysql)
    if not SessionManager(mysql).is_logged_in():
        return redirect(url_for('login'))

    msg = ''

    account = dh.get_account_data_by_id(session['id'])
    if request.method == 'POST' and 'old_password' in request.form and 'new_password' in request.form and 'confirm_password' in request.form:
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            msg = 'New password and confirm password do not match!'
        else:
            old_password_hashed = PasswordManager.hash_password(old_password, app.secret_key)
            print(old_password_hashed)
            account = dh.check_password(session['id'], old_password_hashed)

            if account:
                new_password_hashed = PasswordManager.hash_password(new_password, app.secret_key)
                dh.update_password(new_password_hashed, session['id'])
                msg = 'Password successfully changed!'
            else:
                msg = 'Incorrect old password!'

    account = dh.get_account_data_by_id(session['id'])
    chats = dh.get_chat_by_account_id(account['account_id'])
    return render_template('profile.html', account=account, msg=msg,chats=chats)




if __name__ == "__main__":
    app.run()