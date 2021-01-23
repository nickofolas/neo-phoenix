CREATE TABLE highlights (
    user_id  BIGINT NOT NULL,
    content  TEXT NOT NULL,
    is_regex BOOLEAN DEFAULT FALSE,
    PRIMARY KEY(user_id, content, is_regex)
);

CREATE TABLE todos (
    user_id    BIGINT NOT NULL,
    content    TEXT NOT NULL,
    guild_id   TEXT NOT NULL, -- This can be an ID or @me, so we have to be inclusive
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL
);