# Privacy Policy

Effective date: 2026-11-22

Last updated: 2026-11-22

## Definitions

See the [Terms of Service](./TERMS_OF_SERVICE.md)'s definitions.

## What data is processed, and why?

The Bot may access and process any of the following data in the course of
operation (with the purpose of such specified in parentheses):

- The User ID of a Message author (for retrieving that User's Preferences).
- The Server ID of the server where a message is sent (for retrieving
  preferences set by that server's Admins).
- All Preferences associated with the author of a message and the server in
  which a message is sent or edited (for determining whether to Evaluate a
  message, and how to respond based on the results of an Evaluation).
- The Server ID, Category ID, Channel ID, and/or Thread ID where a message is
  sent or edited (to determine if it is in a location that should be Evaluated,
  as specified by User or Admin Preferences).
- The time at which a Message was sent (to determine if it was sent at a time
  that should be Evaluated, as specified by User or Admin Preferences).
- The content of a message (only when an Evaluation is to be performed, to
  perform that Evaluation)
- The name of servers a User shares with the Bot (for Users configuring
  Preferences that apply to entire servers, only at User's request)

In summary, the Bot may access Messages in any channel it has access to, but
only Evaluates Message content based on User- or Admin-set Preferences. If no
applicable Preferences allow Evaluation in the place and time a message is sent
or edited, the Message content is not accessed.

## What data is stored, for how long, and why?

The Bot may store and retrieve any of the following information in the course of
operation (with the purpose of such specified in parentheses):

- User IDs and Server IDs (for associating Preferences to the User or server
  they apply to).
- Role IDs (for Admins to optionally limit message evaluation to Users with
  specific roles in a server).
- Server IDs, Category IDs, Channel IDs, and/or Thread IDs (for checking whether
  a message is in a configured location)
- Various Preferences provided by Users or Admins, including but not limited to:
  - Emoji (to react with).
  - Text (which, if at the start of a message, indicates the message should not
    be Evaluated despite meeting all other Evaluation criteria).
  - Durations (during which to pause evaluation).
  - Times and Timezones (during which to enable evaluation).
  - Timezones (specified alongside a given time).

Preference data may be stored indefinitely, but Users may delete it at any time.
Admins may alter or delete Preference data which is assigned to their server by
themselves or other Admins.

In summary, the Bot only stores data it is explicitly provided by Users in the
process of assigning Preferences, and Users may delete that data at any time.
The Bot does not store Message content, User names, channel names, or server
names.

## How is data kept secure and private?

Message content and other data processed by the Bot are only accessed by the Bot
and its operator in the course of normal operation. Access to stored data is
restricted to the Bot and its operator, except for those instances where the Bot
explicitly provides a User access to data pertaining to themselves or the server
in which they are an Admin.

The Bot does not intentionally disclose stored or processed data to other Users.
Users cannot access data pertaining to other Users through the Bot. The Bot may
be hosted on a virtual private server accessible only to the Bot operator, but
which is provided by a third party.

## How can I delete my data?

If you would like to delete all data pertaining to yourself, you may run the
command `/lawa weka` (lit. "rule(s) remove") in any server you share with the
Bot or in private messages with the Bot. You may also reach out to `@gregdan3`
[on Discord](https://discord.com/users/497549183847497739),
[Telegram](https://gregdan3.t.me), or
[by email](mailto:gregdan3+iptpt@protonmail.com) to request such a deletion.

If you are a server Admin and would like to delete all data pertaining to your
server, you may run the command `/lawa_ma weka` (lit. "rule(s)_place remove") in
the relevant server. This will remove all Preferences pertaining to the server.

## When and how can this policy be updated?

This policy may be updated at any time the Bot's functionality or processing of
data changes. Updates to the Bot and/or its policies will be announced in
[the Discord server _pali pona_](https://discord.gg/GAupKNPTH7) (lit. "good
work").

### Questions or Concerns?

For questions or concerns about this Policy, contact the bot operator @gregdan3
[on Discord](https://discord.com/users/497549183847497739),
[Telegram](https://gregdan3.t.me), or
[by email](mailto:gregdan3+iptpt@protonmail.com). You may also join
[the aforementioned Discord server](https://discord.gg/GAupKNPTH7) to reach out.
