-- Table: profiles | Documentation for settings --
COMMENT ON COLUMN profiles.receive_highlights IS
'Dictates whether you''ll receive highlights from neo.

Expected Value Type: A boolean-like (`yes`/`no`) value
Default Value: `True`

**Current Value:** `{}`';

-- Table: servers | Documentation for settings --
COMMENT ON COLUMN servers.prefix IS
'Sets the bot''s prefix for the server.

Expected Value Type: A string of text
Default Value: `n!`

**Current Value:** `{}`';