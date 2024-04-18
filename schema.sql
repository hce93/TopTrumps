-- DROP TABLE IF EXISTS users;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL
);

DROP TABLE IF EXISTS cards;
-- keep id and title as first two attributes
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(50) UNIQUE NOT NULL,
    strength INTEGER NOT NULL,
    stealth INTEGER NOT NULL,
    shooting INTEGER NOT NULL,
    magic INTEGER NOT NULL
);

DROP TABLE IF EXISTS game;
CREATE TABLE game (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    card_id INTEGER NOT NULL,
    card_order INTEGER NOT NULL,
    FOREIGN KEY (player_id) REFERENCES users(id),
    FOREIGN KEY (card_id) REFERENCES cards(id)
);

DROP TABLE IF EXISTS middle;
CREATE TABLE middle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    FOREIGN KEY (card_id) REFERENCES cards(id)
);

DROP TABLE IF EXISTS stats;
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    win INTEGER DEFAULT 0 NOT NULL,
    draw INTEGER DEFAULT 0 NOT NULL,
    loss INTEGER DEFAULT 0 NOT NULL,
    date_joined DATE DEFAULT CURRENT_DATE, 
    FOREIGN KEY (player_id) REFERENCES users(id)
);

-- CREATE TABLE card_stats(
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     FOREIGN KEY (card_id) REFERENCES cards(id),
--     win INTEGER,
--     draw INTEGER,
--     loss INTEGER
-- );
    