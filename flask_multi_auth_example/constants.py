import os
from dotenv import load_dotenv

load_dotenv()

# URL base de la API
BASE_URL = '/flask_multi_auth_example_api'

# Reglas de dominio sobre el password
PASSWORD_MIN_LEN = 8
PASSWORD_MAX_LEN = 64

# Configuracion JWT
JWT_SECRET    = os.getenv('JWT_SECRET', 'change-me-please')
JWT_ALGORITHM = 'HS256'
JWT_EXP_HORAS = int(os.getenv('JWT_EXP_HORAS', '8'))

# Configuracion de la base de datos MySQL (levantada via docker-compose)
DB_HOST     = os.getenv('DB_HOST', 'localhost')
DB_PORT     = int(os.getenv('DB_PORT', '3306'))
DB_USER     = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_NAME     = os.getenv('DB_NAME', 'multi_auth')
DB_URL      = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Configuracion de reCAPTCHA v2 (validacion server-side contra Google)
RECAPTCHA_SECRET      = os.getenv('RECAPTCHA_SECRET', '')
RECAPTCHA_DISABLED    = os.getenv('RECAPTCHA_DISABLED', 'false').lower() == 'true'
RECAPTCHA_VERIFY_URL  = 'https://www.google.com/recaptcha/api/siteverify'

# Password reset tokens
PASSWORD_RESET_TOKEN_BYTES   = 32   # bytes random => 64 chars en hex
PASSWORD_RESET_TOKEN_EXP_MIN = 30   # minutos de validez del link

# Codigos de login passwordless
LOGIN_CODE_LEN     = 6      # digitos
LOGIN_CODE_EXP_MIN = 10     # minutos de validez del codigo

# Codigos de error
ERROR_CODE_INVALID_BODY            = 'invalid.body'
ERROR_CODE_INVALID_MIN_VALUE       = 'invalid.min.value'
ERROR_CODE_INVALID_MAX_VALUE       = 'invalid.max.value'
ERROR_CODE_INVALID_EMAIL           = 'invalid.email.format'
ERROR_CODE_EMAIL_YA_REGISTRADO     = 'email.already.registered'
ERROR_CODE_USUARIO_NOT_FOUND       = 'usuario.not.found'
ERROR_CODE_CREDENCIALES            = 'invalid.credentials'
ERROR_CODE_RECAPTCHA_FALTANTE      = 'recaptcha.missing'
ERROR_CODE_RECAPTCHA_INVALIDO      = 'recaptcha.invalid'
ERROR_CODE_RESET_TOKEN_INVALIDO    = 'reset.token.invalid'
ERROR_CODE_RESET_TOKEN_EXPIRADO    = 'reset.token.expired'
ERROR_CODE_RESET_TOKEN_USADO       = 'reset.token.used'
ERROR_CODE_LOGIN_CODE_INVALIDO     = 'login.code.invalid'
ERROR_CODE_LOGIN_CODE_EXPIRADO     = 'login.code.expired'
ERROR_CODE_LOGIN_CODE_USADO        = 'login.code.used'
ERROR_CODE_TOKEN_FALTANTE          = 'auth.token.missing'
ERROR_CODE_TOKEN_INVALIDO          = 'auth.token.invalid'
ERROR_CODE_TOKEN_EXPIRADO          = 'auth.token.expired'
