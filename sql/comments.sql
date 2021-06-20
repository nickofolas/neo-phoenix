-- Table: profiles | Documentation for settings --
COMMENT ON COLUMN profiles.receive_highlights IS
'Dictates whether you''ll receive highlights from neo.

Expected Value Type: A boolean-like (`yes`/`no`) value
Default Value: `True`

**Current Value:** `{}`
';

-- Table: servers | Documentation for settings --
COMMENT ON COLUMN servers.prefix IS
'Sets the bot''s prefix for the server.
Pinging the bot is always an alternative prefix.

Expected Value Type: A string of text
Default Value: `n!`

**Current Value:** `{}`
';

COMMENT ON COLUMN servers.starboard_enabled IS
'Dictates whether the server''s starboard is enabled.

Expected Value Type: A boolean-like (`yes`/`no`) value
Default Value: `False`

**Current Value:** `{}`
';

-- Table: starboards | Documentation for settings --
COMMENT ON COLUMN starboards.channel IS
'Sets the channel that starred messages will be sent to
when they exceed the configured star threshold.

**WARNING:** Changing this will invalidate __all__ current stars.

Expected Value Type: A channel mention

**Current Value:** `{}`
';

COMMENT ON COLUMN starboards.threshold IS
'The threshold which must be exceeded for a message to
be sent to the starboard.

Expected Value Type: An integer
Default Value: `5`

**Current Value:** `{}`
';

COMMENT ON COLUMN starboards.star_format IS
'The format that starred messages will follow.

Expected Value Type: A string of text
Format Variables:
- `stars`: The number of stars a message has.
Default Value: `⭐ **{{stars}}**`

**Current Value:** `{}`
';

COMMENT ON COLUMN starboards.max_days IS
'The maximum age (in days) that a message can be before 
it can no longer be sent to starboard.

Expected Value Type: An integer
Default Value: `7`

**Current Value:** `{}`
';

COMMENT ON COLUMN starboards.emoji IS
'The emoji that will be used to star messages.

**WARNING:** Changing this will invalidate __all__ current stars.

Expected Value Type: An emoji
Default Value: `⭐`

**Current Value:** {}
';