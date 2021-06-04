CREATE TABLE profiles (
    user_id            BIGINT PRIMARY KEY,
    hl_blocks          BIGINT[] DEFAULT ARRAY[]::BIGINT[],
    receive_highlights BOOLEAN  DEFAULT TRUE
);

CREATE TABLE servers (
    server_id BIGINT PRIMARY KEY,
    prefix    TEXT DEFAULT 'n!'
);

CREATE TABLE highlights (
    user_id  BIGINT NOT NULL,
    content  TEXT NOT NULL
    PRIMARY KEY(user_id, content)
);

CREATE TABLE todos (
    user_id    BIGINT NOT NULL,
    content    TEXT NOT NULL,
    guild_id   TEXT NOT NULL, -- This can be an ID or @me, so we have to be inclusive
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL
);