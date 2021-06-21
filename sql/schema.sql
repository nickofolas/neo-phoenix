CREATE TABLE profiles (
    user_id            BIGINT PRIMARY KEY,
    hl_blocks          BIGINT[] DEFAULT ARRAY[]::BIGINT[],
    receive_highlights BOOLEAN  DEFAULT TRUE,
    hl_timeout         BIGINT CHECK (hl_timeout >= 1 AND hl_timeout <= 5) DEFAULT 1,
    created_at         TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
    timezone           TEXT DEFAULT NULL
);

CREATE TABLE servers (
    server_id         BIGINT PRIMARY KEY,
    prefix            TEXT DEFAULT 'n!',
    starboard_enabled BOOLEAN DEFAULT FALSE
);

CREATE TABLE highlights (
    user_id  BIGINT NOT NULL,
    content  TEXT NOT NULL,
    PRIMARY KEY (user_id, content),
    FOREIGN KEY (user_id) REFERENCES profiles (user_id) ON DELETE CASCADE
);

CREATE TABLE todos (
    user_id    BIGINT NOT NULL,
    content    TEXT NOT NULL,
    guild_id   TEXT NOT NULL, -- This can be an ID or @me, so we have to be inclusive
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    edited     BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES profiles (user_id) ON DELETE CASCADE
);

-- Use foreign keys so that, if a server is deleted from the servers
-- table, all related entries in starboard tables are also deleted
CREATE TABLE starboards (
    server_id      BIGINT PRIMARY KEY,
    channel        BIGINT,
    threshold      BIGINT DEFAULT 5,
    star_format    VARCHAR(200) DEFAULT '⭐ **{stars}**',
    max_days       BIGINT CHECK (max_days > 1) DEFAULT 7,
    emoji          TEXT DEFAULT '⭐',
    ignored        BIGINT[] DEFAULT ARRAY[]::BIGINT[],
    FOREIGN KEY (server_id) REFERENCES servers (server_id) ON DELETE CASCADE
);

-- Same as above with foreign keys
CREATE TABLE stars (
    server_id             BIGINT NOT NULL,
    message_id            BIGINT NOT NULL,
    channel_id            BIGINT NOT NULL,
    stars                 BIGINT NOT NULL,
    starboard_message_id  BIGINT NOT NULL,
    PRIMARY KEY (server_id, message_id, channel_id),
    FOREIGN KEY (server_id) REFERENCES starboards (server_id) ON DELETE CASCADE
);