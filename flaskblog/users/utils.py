from os import path
from secrets import token_hex
from PIL import Image
from flask import url_for, current_app
from flask_mail import Message
from flaskblog import mail


def save_avatar(form_avatar):
    random_hex = token_hex(8)
    _, extension = path.splitext(form_avatar.filename)
    random_filename = random_hex + extension
    avatar_path = path.join(
        current_app.root_path, "static/profile_pics", random_filename
    )

    output_size = (125, 125)
    new_avatar = Image.open(form_avatar)
    new_avatar.thumbnail(output_size)
    new_avatar.save(avatar_path)

    return random_filename


def send_reset_email(user):
    token = user.get_reset_token()
    message = Message(
        "Password Reset Request", sender="noreply@demo.com", recipients=[user.email]
    )
    message.body = f"""To reset your password visit the following link:
{url_for("users.reset_token", token=token, _external=True)}

If you did not make this request then simply ignore this email.
    """

    mail.send(message)
