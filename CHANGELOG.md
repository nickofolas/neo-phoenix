# Release v0.10.3
## Fixes
* Fix issues with ignoring entities from a starboard
* Fix highlights not being compiled as case-insensitive
* Implement potential fix for issues with invite dropdown failing to respond

## Other
* Implement event system separate from `discord.Client.dispatch` due to volatility of that API


# Release v0.10.2
## Fixes
* Fix an AttributeError when setting a starboard channel (was caused due to residual code)


# Release v0.10.1
## Fixes
* Fix an unintentionally public IndexError


# Release v0.10.0
Release v0.10.0 implements a couple of utility commands.

## Additions
* `serverinfo`/`si` command
    * Displays relevant information pertaining to the current guild
* `translate`/`tr` command
    * Translates text across languages via the Google Translate API
    * Supports a directive-based specification for controlling source and destination languages

## Improvements
* Demote `command_error` errors to `warn` logging level
* Added `support`, `source`, and `privacy` aliases to the `info` command
* Reworked functionality of `exec` command and backend
    * Notably, solved the recursion that was previously present in the `scope`
* Logically partitioned `requirements.txt`


# Release v0.9.3
## Improvements
* Rename `eval` command to `exec`
* Remove extraneous `Starboard` attributes
* Change type of `Starboard.ignored`


# Release v0.9.2
## Fixes
* Fixed an issue with reminders occasionally wrongly displaying "[source deleted]" when delivered in direct messages


# Release v0.9.1
0.9.1 fixes issues found in 0.9.0 and earlier.

## Improvements
* Removed an extraneous attribute from starboard objects

## Fixes
* When sending messages in a channel is impossible, the error is logged and ignored silently
* Fixed parameter issues in `on_error`
* Fixed mobile formatting regression with ephemeral privacy policy


# Release v0.9.0
Release v0.9.0 cleans up and slightly enhances neo phoenix.

## Legal
* Revised privacy policy

## Improvements
* Highlight context now displays *around* the trigger message. This means that up to 3 earlier and up to 3 later messages will be displayed
* The collection mechanism for highlight has been improved
* The invite URL is now displayed as an inline hyperlink
* All icons have been refreshed
* Pass for documentation, improving clarity where it may have been lacking

## Other
* Optimizations for profile code


# Release v0.8.0
This release is mostly comprised of polish for existing features.

## Legal
* Updated privacy policy (made public in repository, rewrote for better clarity)
* Licensed project under the GNU Affero General Public License v3.0 (AGPLv3)

## Improvements
* Reworked menus for several commands (`help`, `google`, `define`) to supply dropdown menus, making it easier to quickly access a page
* Tweaked the buttons for and added an `invite` alias to the `info` command
* Command aliases are now displayed in that command's help embed
* Shortened the `star_format` starboard option to `format`

## Fixes
* Fixed an issue with unicode starboard emojis that caused incorrect validation, and prevented stars from registering
* Fixed the behavior of index chaining in the `remind cancel` command
* Fixed the help command behaving incorrectly because of the global cooldown

## Other
* Optimization:
    * Remove `bot.get_server` and `bot.get_profile` in favor of accessing the attribute directly or using `__contains__` for membership checks (sidesteps lookup overhead)
    * Where it is known that a value will always exist, direct `__getitem__` access is used instead of `dict.get`, which shaves off further attribute lookup
    * Restricted gateway intents to only the required ones, rather than using the defaults
    * Optimize starboard with `__getitem__` rather than `dict.get` (where appropriate)
    * Implement `__slots__` in far more locations, significantly reducing memory footprint
* Implement maximum number of todos (100)
* Revised internal terminology for server configs:
    * Dropped use of "`server`" in backend
    * Anything that was previously referred to as a "`server`" has been labelled as a "`config`"/"`guild config`"
    * Note that these changes are internal only, and that frontend interfaces all still refer to `config`s as `server`s
* Rework `modules.paginator`:
    * Rename module to `modules.menus`
    * Rework `Paginator` object to function as a subclass of `discord.ui.View`
    * Implement a `DropdownMenu` for creating menus that can be paged via both buttons or a dropdown menu (support up to 25 items)
    * `Pages` now supports a `template_embed` keyword-only argument, for defining a static template embed that is merged with the `Pages` object's content


# Release v0.7.0
In large part, this release extends and improves existing features.

## Improvements
* Highlights have been updated to work with Discord's upcoming threads feature
    * A thread's parent channel permissions are checked to confirm if a user can receive highlights from a given public thread
    * Highlights will **never** be triggered by private threads, regardless of permissions
* Stickers will now be listed in highlight embeds in the same way images and embeds are shown
* Indexing for list-based interfaces now begins at `1`
    * This affects interfaces including highlights, and todos
* Implemented index chaining and the `~` operator for the `highlight remove` command
* Shortened the `starboard_enabled` server config key to `starboard`
* `avatar` command now uses a `MemberConverter` as a conversion strategy, enabling lookup by display/user name
* `info` command now uses persistent views, so its buttons can be utilized indefinitely

## Additions
* Added `Support Server` button to `info` command output
    * Added corresponding key to config file, along with key for configuring whether the button is enabled or not
* Overhauled flow of `Invite neo phoenix` button on the `info` command
    * Responds ephemerally now
    * Uses dropdown menus to allow users to select permission presets for inviting neo phoenix

## Other
* Added `uvloop` as a conditional dependency for `linux` systems, improving `asyncio` performance
* Updated default name for auto-generated config templates, and added a comment to the top of auto-generated files


# Release v0.6.0
This release fleshes out neo phoenix's feature set further.

## Highlight Collection
* As of v0.6.0, highlights are delivered via a "collection" method
* A periodic timer triggers highlight delivery every 5 seconds
    * Highlight context embeds aren't generated until delivery time, rather than at the instant of being triggered
* Any highlights triggered in a given channel within the 5 second period will be collected into a single highlight notification, rather than delivering an individual message for each highlight (the latter is the behavior of legacy `neo` highlights)

## Other
* Implemented a developer `addon` command for loading, unloading, and reloading neo phoenix addons post-runtime
* Implemented a `PeriodicTimer` class to support the highlight collection feature
    * Also added an accompanying decorator to simplify the creation of timers


# Release v0.5.0
This release implements features to bring neo phoenix closer to a stable 1.0.0 release.

## Front-End Changes/Additions
* Implemented a bot info command, `info`
    * Includes version info, uptime, relevant links, and a button to display privacy information
    * Privacy information describes in greater detail how timezone data will be used
* Exceptions are now displays in their `__str__` representation, rather than their `__repr__`, providing a more user-friendly experience when errors are raised
* Additionally, added a list of ignored exceptions, so that more obstructive exceptions don't send messages
* To avoid usability regressions, an `image` command has been added as a shortcut for invoking `google --image`
* Renamed the `server init` and `profile init` commands to `server create` and `profile create`, for a more straightforward usage

## Back-End Changes/Additions
* All logging now uses ANSI escapes to add color to messages
* Added a script `config_gen.py` for automatically generating example config files from a real config file
* Changed converters from `commands.Converter` subclasses to standalone functions
* Resolved an issue causing starboards to behave improperly when their emoji setting was changed


# Release v0.4.0
## Reminders
This release implements a full `Reminders` system.

Below is a comparison between the system's predecessor (legacy `neo` `Reminders`) and the new implementation.

#### Similarities to predecessor:
* Front-facing interface aims to be as familiar as possible
* Provides the capability to schedule reminders from both relative offsets, and absolute datetimes
* Implements the same basic functions `remind list`, `remind cancel`
* Implements a similar fallback hierarchy for reminder deliver (reply to invocation message -> mention user in channel of invocation -> send user a direct message with content -> fail silently)
* Reminders can still be scheduled from within a server, or from a direct message

#### Differences from predecessor:
* Separates reminder scheduling into 2 separate commands, one for relative offsets, the other for absolute datetimes
    * Relative offset scheduling is assigned to the parent group `remind`
    * Absolute datetime scheduling is assigned to the subcommand `remind [on/at]`
        * Naming aims to be as conducive to natural datetime expression as possible (`remind on June 7, 20XX Do something`)
* Implements subcommand `remind [view/show]` for viewing the full content of a reminder (reminder content is truncated to 50 characters in the list view)
* Both relative offset and absolute datetime scheduling are built from lightweight parsers that take advantage of strict bounds on allowed inputs
    * Parsing also now allows for the actual content of a reminder to be separated from its deadline (both relative and absolute, unlike legacy `neo` reminders which only separated content from absolutes)
    * Strict parsing allows for more informative documentation, along with examples, increasing ease of use versus legacy `neo` reminders
* Implements a maximum number of reminders (15 as of initial release)
* Increased maximum length for reminder content (1,000 versus legacy `neo`'s 200)
* Implements implied localization for users who have configured a timezone in their profile
    * Absolute datetimes *only* will be constructed with a user's configured timezone
    * Absolute datetimes for users without a configured timezone will mirror legacy `neo`'s use of UTC
* Reminders are linked to a user's profile via `FOREIGN KEY`, versus the free-standing structure of legacy `neo` reminders
    * Users are required to have initialized a profile in order to access the reminder interface
    * This change allows for both increased consistency for users, and creates a more connected structure for the database

## Other Changes
* User setting `hl_timeout` has been implemented, introducing the ability to customize the duration of time for which a user must be absent from a channel for them to be considered "inactive", and thus, able to receive highlights
    * Value is set in minutes, with the default being 1, and having a constraint of `>= 1 AND <= 5`
* Implement developer command `sql` for streamlined database interfacing
    * Depends on new `Table` class for formatting entries into an optimally readable form


# Release v0.3.1
* Fixed an issue with `Starboard` editing brand-new stars upon creation


# Release v0.3.0
This release mainly targets the profile system, and improves upon it significantly.
* Renamed `user_settings` extension to `profile`
* Implemented command group `profile`, which shows information pertaining to the specified user's profile (provided they have a profile, otherwise exiting)
* Implemented commands for:
    * Creating a user profile, `profile init`, which creates a base profile
    * Deleting a user profile, `profile delete`, which deletes a user profile, also deleting all associated data (todos, highlights, ...) via cascade
* Implemented a custom `Context`
    * Implemented a prompt method on this, allowing for interactive prompting of users
* Implemented a `reset` subcommand on both `server` and `settings` groups
    * This command resets an option to the default that is provided in the database
* Expanded upon data stored in a user profile
    * Added `created_at`, which stores the timestamp of the account's creation
    * Added `timezone`, which stores a user's timezone
        * This is entirely opt-in
        * By setting this value (via the `settings set` command), the user acknowledges the ways in which their timezone will be used (as is explicitly laid out in the documentation for the field)
        * Being a profile setting, this can be reset by the user at any point via the `settings reset` command


# Release v0.2.1
* Addresses minor bugs in `Starboard`
* Implements a command to manually initialize a server's config entry if, for some reason, it is not automatically generated (which it is not, yet)


# Release v0.2.0
This release implements the `Starboard` feature, and its full functionality. It functions largely identically to its predecessor, with several key improvements:
* Management of starboard settings has been consolidated to a single, extensible system, utilizing SQL comments for logical, standardized documentation
* neo phoenix's starboard features the ability to ignore/unignore message and channel IDs, preventing them from reaching starboard
* Code style and fluency has also been improved all-around


# Release v0.1.0
* Includes a reasonable amount of initial features
* Introduces various frameworks for convenience

*Note: Ideally, this release could have been released alongside the initial commit, but that didn't happen. Releases will follow commits more closely going forward.*