CREATE TABLE highlights (
    user_id  BIGINT NOT NULL,
    content  TEXT NOT NULL,
    is_regex BOOLEAN DEFAULT FALSE,
    PRIMARY KEY(user_id, content, is_regex)
);