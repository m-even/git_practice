from app import create_app, db
from app.models import User # Example model, adjust as per your models

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User}

if __name__ == '__main__':
    app.run(debug=True)
