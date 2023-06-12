from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import mysql.connector
from datetime import datetime
from slack_sdk.errors import SlackApiError
import time

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN')

app = App(token=SLACK_BOT_TOKEN)

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

# Configuracion de las credenciales de MySQL y Slack
db_config = {
    'user': MYSQL_USER,
    'password': MYSQL_PASSWORD,
    'host': MYSQL_HOST,
    'database': MYSQL_DATABASE,
    'raise_on_warnings': True
}

attempts = 0

while attempts < 3:
    try:
        cnx = mysql.connector.connect(**db_config)
        print('se conecto piola')
        break
    except Exception as e:
        print(str(e))
        attempts += 1
        time.sleep(5)

cursor = cnx.cursor()


@app.event("app_mention")
def mention_handler(body, say):
	say('Hello World!')

# The echo command simply echoes on command Test command
@app.command("/echo")
def repeat_text(ack, respond, command):
	# Acknowledge command request
	ack()
	respond(f"{command['text']}")

# Comando /add <task_name> <username> *urgent*: Agrega una nueva tarea a la tabla "Tasks"
# si se le agrega la flag urgent marca la tarea como urgente cambiando el booleano is_urgent a true
@app.command("/add")
def add_task(ack, body, command):
    ack()
    text = command['text'].split()
    task_name = text[0]
    username = text[1]
    is_urgent = 0

    # Check if the 'urgent' flag is provided
    if len(text) > 2 and text[2].lower() == "urgent":
        is_urgent = 1

    try:
        # Verificar si el usuario existe en la tabla "Users"
        select_query = "SELECT * FROM Users WHERE username = %s"
        cursor.execute(select_query, (username,))
        user = cursor.fetchone()

        if user is None:
            message = "El usuario no existe"
            app.client.chat_postMessage(channel=body["channel_id"], text=message)
            return

        # Insertar la nueva tarea en la tabla "Tasks"
        insert_query = "INSERT INTO Tasks (task_name, user_id, is_urgent) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (task_name, user[0], is_urgent))
        cnx.commit()

        message = "Tarea agregada exitosamente"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)
    except mysql.connector.Error as err:
        print(f"Error al agregar la tarea: {err}")
        message = "Ocurrió un error al agregar la tarea"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)


# Comando /all: Lista todas las tareas de la tabla "Tasks" con colores por estado
@app.command("/all")
def list_all_tasks(ack, body):
    ack()
    try:
        # Joining the Tasks and Users tables using a JOIN query
        select_query = """
            SELECT Tasks.task_name, Users.username, Tasks.is_urgent, Tasks.is_done
            FROM Tasks
            INNER JOIN Users ON Tasks.user_id = Users.user_id
        """
        cursor.execute(select_query)
        tasks = cursor.fetchall()

        # Create a list of formatted tasks
        formatted_tasks = []
        for task in tasks:
            task_name, username, is_urgent, is_done = task
            task_status = "Pendiente"
            if is_done:
                task_status = "Finalizada"
            elif is_urgent:
                task_status = "Urgente"

            formatted_task = f"- {task_name} / {username} ({task_status})"
            formatted_tasks.append(formatted_task)

        message = "\n".join(formatted_tasks)
        app.client.chat_postMessage(channel=body["channel_id"], text=message)
    except mysql.connector.Error as err:
        print(f"Error al listar las tareas: {err}")
        message = "Ocurrió un error al listar las tareas"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)

# Comando /rm <task_name> <user_id>: Elimina una tarea de la tabla "Tasks"
@app.command("/rm")
def remove_task(ack, body, command):
    ack()
    text = command['text'].split()
    task_name = text[0]
    user_id = text[1]

    try:
        # Verificar si la tarea existe en la tabla "Tasks" para el usuario dado
        select_query = "SELECT * FROM Tasks WHERE task_name = %s AND user_id = %s"
        cursor.execute(select_query, (task_name, user_id))
        task = cursor.fetchone()

        if task is None:
            message = "La tarea no existe para el usuario dado"
            app.client.chat_postMessage(channel=body["channel_id"], text=message)
            return

        # Eliminar la tarea de la tabla "Tasks"
        delete_query = "DELETE FROM Tasks WHERE task_name = %s AND user_id = %s"
        cursor.execute(delete_query, (task_name, user_id))
        cnx.commit()

        message = "Tarea eliminada exitosamente"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)
    except mysql.connector.Error as err:
        print(f"Error al eliminar la tarea: {err}")
        message = "Ocurrió un error al eliminar la tarea"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)

# Comando /status_update <task_name> <username> <status>: Actualiza el estado de una tarea
@app.command("/status_update")
def update_task_status(ack, body, command):
    ack()
    text = command['text'].split()
    task_name = text[0]
    username = text[1]
    status = text[2].lower()

    try:
        # Verify if the task exists in the "Tasks" table
        select_query = "SELECT * FROM Tasks WHERE task_name = %s"
        cursor.execute(select_query, (task_name,))
        task = cursor.fetchone()

        if task is None:
            message = "La tarea no existe"
            app.client.chat_postMessage(channel=body["channel_id"], text=message)
            return

        # Verify if the user exists in the "Users" table
        select_query = "SELECT * FROM Users WHERE username = %s"
        cursor.execute(select_query, (username,))
        user = cursor.fetchone()

        if user is None:
            message = "El usuario no existe"
            app.client.chat_postMessage(channel=body["channel_id"], text=message)
            return

        # Update the status and updated_at field of the task in the "Tasks" table
        update_query = "UPDATE Tasks SET is_done = %s, is_urgent = %s, updated_at = %s WHERE task_name = %s AND user_id = %s"
        is_done = 1 if status == "done" else 0
        is_urgent = 1 if status == "urgent" else 0
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(update_query, (is_done, is_urgent, updated_at, task_name, user[0]))
        cnx.commit()

        message = f"Estado de la tarea actualizado a: {status.capitalize()}"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)
    except mysql.connector.Error as err:
        print(f"Error al actualizar el estado de la tarea: {err}")
        message = "Ocurrió un error al actualizar el estado de la tarea"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)

# Comando /list <status>: Lista las tareas dependiendo de su estado
@app.command("/list")
def list_tasks_by_status(ack, body, command):
    ack()
    status = command['text'].lower()

    try:
        if status not in ["pending", "done", "urgent"]:
            message = "Estado inválido. Los estados válidos son: pending, done, urgent."
            app.client.chat_postMessage(channel=body["channel_id"], text=message)
            return

        # Get tasks based on the specified status
        select_query = "SELECT task_name, username, CASE WHEN is_done = 1 THEN 'done' WHEN is_urgent = 1 THEN 'urgent' ELSE 'pending' END AS status FROM Tasks INNER JOIN Users ON Tasks.user_id = Users.user_id WHERE CASE WHEN %s = 'done' THEN is_done = 1 WHEN %s = 'urgent' THEN is_urgent = 1 ELSE is_done = 0 AND is_urgent = 0 END"
        cursor.execute(select_query, (status, status))
        tasks = cursor.fetchall()

        if not tasks:
            message = f"No se encontraron tareas con estado '{status}'"
            app.client.chat_postMessage(channel=body["channel_id"], text=message)
            return

        # Format the tasks list
        formatted_tasks = []
        for task in tasks:
            task_name, username, task_status = task
            formatted_task = f"- {task_name} / {username} ({task_status})"
            formatted_tasks.append(formatted_task)

        message = "\n".join(formatted_tasks)
        app.client.chat_postMessage(channel=body["channel_id"], text=message)
    except mysql.connector.Error as err:
        print(f"Error al listar las tareas: {err}")
        message = "Ocurrió un error al listar las tareas"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)

# Comando /clean <number>: Elimina un numero especifico de mensajes del chat
@app.command("/clean")
def clean_messages(ack, body, command):
    ack()
    num_messages = command['text']

    try:
        num_messages = int(num_messages)
    except ValueError:
        message = "El número de mensajes debe ser un número entero."
        app.client.chat_postMessage(channel=body["channel_id"], text=message)
        return

    try:
        # Get the channel's message history
        response = app.client.conversations_history(channel=body["channel_id"], limit=num_messages)
        messages = response["messages"]

        # Delete the specified number of messages
        for message in messages:
            try:
                app.client.chat_delete(channel=body["channel_id"], ts=message["ts"])
            except SlackApiError as e:
                print(f"Error al eliminar el mensaje: {e.response['error']}")

        message = f"{num_messages} mensajes eliminados."
        app.client.chat_postMessage(channel=body["channel_id"], text=message)
    except SlackApiError as e:
        print(f"Error al obtener el historial de mensajes: {e.response['error']}")
        message = "Ocurrió un error al limpiar los mensajes."
        app.client.chat_postMessage(channel=body["channel_id"], text=message)

# Comando /add_user <username> <email> <password>: Agrega un nuevo usuario a la tabla "Users"
@app.command("/add_user")
def add_user(ack, body, command):
    ack()
    text = command['text'].split()
    username = text[0]
    email = text[1] if len(text) > 1 else None
    password = text[2] if len(text) > 2 else None

    try:
        # Insert the new user into the Users table
        insert_query = "INSERT INTO Users (username, email, password) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (username, email, password))
        cnx.commit()

        message = "User added successfully"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)
    except mysql.connector.Error as err:
        print(f"Error adding the user: {err}")
        message = "An error occurred while adding the user"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)

# Comando /list_users: lista todos los usuarios con sus respectivas IDs
@app.command("/list_users")
def list_users(ack, body, command):
    ack()

    try:
        # Fetch all users from the Users table
        select_query = "SELECT * FROM Users"
        cursor.execute(select_query)
        users = cursor.fetchall()

        if not users:
            message = "No users found"
            app.client.chat_postMessage(channel=body["channel_id"], text=message)
            return

        # Format the user list
        user_list = "\n".join([f"- {user[1]} (User ID: {user[0]})" for user in users])

        message = f"List of users:\n{user_list}"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)
    except mysql.connector.Error as err:
        print(f"Error listing users: {err}")
        message = "An error occurred while listing users"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)

# Comando /rm_user <username> <user_id>: Elimina un usuario de la base de datos
@app.command("/rm_user")
def remove_user(ack, body, command):
    ack()
    text = command['text'].split()
    username = text[0]
    user_id = text[1]

    try:
        # Verify if the user exists in the Users table
        select_query = "SELECT * FROM Users WHERE username = %s AND user_id = %s"
        cursor.execute(select_query, (username, user_id))
        user = cursor.fetchone()

        if user is None:
            message = "The user does not exist"
            app.client.chat_postMessage(channel=body["channel_id"], text=message)
            return

        # Remove the user from the Users table
        delete_query = "DELETE FROM Users WHERE username = %s AND user_id = %s"
        cursor.execute(delete_query, (username, user_id))
        cnx.commit()

        message = "User removed successfully"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)
    except mysql.connector.Error as err:
        print(f"Error removing the user: {err}")
        message = "An error occurred while removing the user"
        app.client.chat_postMessage(channel=body["channel_id"], text=message)


if __name__ == "__main__":
	handler = SocketModeHandler(app, SLACK_APP_TOKEN)
	handler.start()
