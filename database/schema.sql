-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    bio TEXT,
    avatar_url VARCHAR(255) DEFAULT 'default_avatar.png',
    gender VARCHAR(20),
    google_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id_1 INTEGER NOT NULL,
    user_id_2 INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'matched',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id_1) REFERENCES users (id),
    FOREIGN KEY (user_id_2) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    message_type VARCHAR(10) DEFAULT 'text',
    content TEXT,
    is_read BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users (id),
    FOREIGN KEY (receiver_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    profile_visible INTEGER NOT NULL DEFAULT 1,
    show_online INTEGER NOT NULL DEFAULT 1,
    allow_messages INTEGER NOT NULL DEFAULT 1,
    read_receipts INTEGER NOT NULL DEFAULT 1,
    allow_audio INTEGER NOT NULL DEFAULT 1,
    theme VARCHAR(30) NOT NULL DEFAULT 'ivoire-rose',
    notifications_enabled INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
