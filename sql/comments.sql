-- Table: profiles | Documentation for settings --
COMMENT ON COLUMN profiles.receive_highlights IS
'Dictates whether you''ll receive highlights from neo.

Expected Value Type: A boolean-like (`yes`/`no`) value
Default Value: `True`

**Current Value:** `{}`
';

COMMENT ON COLUMN profiles.hl_timeout IS
'Sets the amount of time (in minutes) that you must
be inactive (send no messages) in a channel for
highlights from that channel to be sent to you.

Expected Value Type: An integer (from 1 to 5)
Default Value: `1`

**Current Value:** `{}`
';

COMMENT ON COLUMN profiles.timezone IS
'Sets your local timezone.

Disclosure: This information is to be used
for several purposes:
- Localization of various features
- Public display
By setting your timezone, you acknowledge and
accept that this information will be displayed
publicly on your profile, along with your local
time (which is calculated from the timezone).

If at any point you want to remove this setting,
it can be reset like any other setting with
`settings reset`, and will remove your timezone.

Expected Value Type: A valid IANA timezone [[list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List)]
Default Value: `None`

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

COMMENT ON COLUMN servers.starboard IS
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
If this is set to an invalid emoji, starboard will
cease to function.

**WARNING:** Changing this will invalidate __all__ current stars.

Expected Value Type: An emoji
Default Value: `⭐`

**Current Value:** {}
';