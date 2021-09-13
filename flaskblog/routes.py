from os import path
from secrets import token_hex
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog import app, db, bcrypt, mail
from flaskblog.models import User, Post
from flaskblog.forms import (
    RegistrationForm,
    LoginForm,
    UpdateAccountForm,
    PostForm,
    RequestResetForm,
    ResetPasswordForm,
)
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message


@app.route("/")
@app.route("/home")
def home():
    page = request.args.get("page", 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=3)
    return render_template("home.html", posts=posts)


@app.route("/about")
def about():
    return render_template("about.html", title="About")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
            "utf-8"
        )
        new_user = User(
            username=form.username.data, email=form.email.data, password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        flash(
            f"Your account has been created! You are now able to log in.",
            category="success",
        )
        return redirect(url_for("home"))

    return render_template("register.html", title="Register", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            flash("Login successful!", category="success")
            login_user(user, remember=form.remember_details.data)
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("home"))
        else:
            flash(
                "Login unsuccessful. Please check email and password.",
                category="danger",
            )
    return render_template("login.html", title="Login", form=form)


@app.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out!", category="success")
    return redirect(url_for("home"))


def save_avatar(form_avatar):
    random_hex = token_hex(8)
    _, extension = path.splitext(form_avatar.filename)
    random_filename = random_hex + extension
    avatar_path = path.join(app.root_path, "static/profile_pics", random_filename)

    output_size = (125, 125)
    new_avatar = Image.open(form_avatar)
    new_avatar.thumbnail(output_size)
    new_avatar.save(avatar_path)

    return random_filename


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.avatar.data:
            avatar_filename = save_avatar(form.avatar.data)
            current_user.avatar_file = avatar_filename
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash("Your account has been updated!", category="success")
        return redirect(url_for("account"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for("static", filename=f"profile_pics/{current_user.avatar_file}")
    return render_template(
        "account.html", title="Account", image_file=image_file, form=form
    )


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.title.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Post has been created!", category="success")
        return redirect(url_for("home"))
    return render_template(
        "create_post.html", title="New Post", form=form, legend="New Post"
    )


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)

    return render_template("post.html", title=post.title, post=post)


@app.route("/post/<int:post_id>/update", methods=["GET", "POST"])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)

    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash("Your post has been updated!", category="success")
        return redirect(url_for("post", post_id=post.id))
    elif request.method == "GET":
        form.title.data = post.title
        form.content.data = post.content

    return render_template(
        "create_post.html", title="Update Post", form=form, legend="Update Post"
    )


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)

    db.session.delete(post)
    db.session.commit()
    flash("Your post has been deleted", category="success")
    return redirect(url_for("home"))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get("page", 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = (
        Post.query.filter_by(author=user)
        .order_by(Post.date_posted.desc())
        .paginate(page=page, per_page=3)
    )
    return render_template("user_posts.html", user=user, posts=posts)


def send_reset_email(user):
    token = user.get_reset_token()
    message = Message(
        "Password Reset Request", sender="noreply@demo.com", recipients=[user.email]
    )
    message.body = f"""To reset your password visit the following link:
{url_for("reset_token", token=token, _external=True)}

If you did not make this request then simply ignore this email.
    """

    mail.send(message)


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash(
            "An email has been sent with instructions to reset your password!",
            category="info",
        )
        return redirect(url_for("login"))

    return render_template("reset_request.html", title="Reset Password", form=form)


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    user = User.verify_reset_token(token)
    if user is None:
        flash("That is an invalid or expired token!", category="warning")
        return redirect(url_for("reset_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
            "utf-8"
        )
        user.password = hashed_password
        db.session.commit()
        flash(
            f"Your password has been updated.",
            category="info",
        )
        return redirect(url_for("login"))

    return render_template("reset_token.html", title="Reset Password", form=form)
