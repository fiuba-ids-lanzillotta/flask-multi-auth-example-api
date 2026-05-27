-- =============================================================
--  Flask Multi Auth - Script DDL para MySQL
-- =============================================================
--  docker-compose lo ejecuta automaticamente al levantar el contenedor
--  (volumen montado en /docker-entrypoint-initdb.d).
--
--  La base `multi_auth` la crea el propio contenedor via MYSQL_DATABASE.
-- =============================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id            INT          AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(100) NOT NULL UNIQUE,
    nombre        VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    creado_en     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tokens para resetear password (link enviado por email).
-- Guardamos el HASH del token, nunca el valor crudo, para que un dump de la
-- DB no permita usar los tokens vigentes.
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          INT          AUTO_INCREMENT PRIMARY KEY,
    usuario_id  INT          NOT NULL,
    token_hash  VARCHAR(255) NOT NULL,
    expira_en   DATETIME     NOT NULL,
    usado_en    DATETIME     NULL,
    creado_en   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reset_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_reset_token_hash (token_hash)
);

-- Codigos de un solo uso para login passwordless (6 digitos enviados por email).
-- Mismo criterio: guardamos el hash, no el codigo en claro.
CREATE TABLE IF NOT EXISTS login_codes (
    id          INT          AUTO_INCREMENT PRIMARY KEY,
    usuario_id  INT          NOT NULL,
    codigo_hash VARCHAR(255) NOT NULL,
    expira_en   DATETIME     NOT NULL,
    usado_en    DATETIME     NULL,
    creado_en   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_code_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_code_usuario (usuario_id)
);

-- =============================================================
--  Para crear el primer usuario, hace un POST a /register desde
--  el frontend (o directamente con curl/postman pasando un
--  recaptcha_token valido si RECAPTCHA_DISABLED=false).
-- =============================================================
