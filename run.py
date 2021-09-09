from flaskblog import app
from os import path
from flaskblog import db


def create_database(app):
    if not path.exists(f"site.db"):
        db.create_all(app=app)
        print(" * Database created!")


if __name__ == "__main__":
    db.init_app(app)
    create_database(app)
    app.run(debug=True)
