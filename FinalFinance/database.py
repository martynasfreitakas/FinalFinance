from flask_sqlalchemy import SQLAlchemy

# Initialize the SQLAlchemy object
db = SQLAlchemy()


def init_db(app):
    """
    Initialize the database with the Flask application.

    This function sets up the SQLAlchemy database connection within the Flask application context,
    creating all the database tables defined in the models.

    Args:
        app (Flask): The Flask application instance to initialize the database with.
    """
    # Attach the app to the SQLAlchemy object
    db.init_app(app)

    # Create database tables within the application context
    with app.app_context():
        db.create_all()
