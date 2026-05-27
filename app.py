import logging
from flask import Flask
from flask_cors import CORS

from flask_multi_auth_example.constants import BASE_URL
from flask_multi_auth_example.routes.auth import auth_bp
from flask_multi_auth_example.routes.usuarios import usuarios_bp

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')

app = Flask(__name__)
app.json.sort_keys = False

# Habilitar CORS para que el frontend pueda consumir la API
CORS(app)

app.register_blueprint(auth_bp, url_prefix=BASE_URL)
app.register_blueprint(usuarios_bp, url_prefix=BASE_URL)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
