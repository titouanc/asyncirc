# asyncirc [![Build Status](https://travis-ci.org/watchtower/asyncirc.svg?branch=master)](https://travis-ci.org/watchtower/asyncirc) [![Code Climate](https://codeclimate.com/github/watchtower/asyncirc/badges/gpa.svg)](https://codeclimate.com/github/watchtower/asyncirc)

**Asyncirc** is an asyncio-based IRC framework for Python.

## Installation

```
pip install asyncio-irc
```

And you're done!

## Connecting

```python
from asyncirc import irc

bot = irc.connect("chat.freenode.net", 6697, use_ssl=True)
bot.register("nickname", "ident", "realname", password="pass") # password optional
```

## Subscribing to events

```python
@bot.on("message")
def incoming_message(parsed, user, target, text):
    # parsed is an RFC1459Message object
    # user is a User object with nick, user, and host attributes
    # target is a string representing nick/channel the message was sent to
    # text is the text of the message
    bot.say(target, "{}: you said {}".format(user.nick, text))
```

## Using plugins

```python
import asyncirc.plugins.tracking # channel/user state tracking
import asyncirc.plugins.addressed # events that fire when the bot is addressed
import asyncirc.plugins.nickserv # events that fire on nickserv authentication responses
```

## Writing code without a reference to the IRCProtocol object

Asyncirc uses the excellent [Blinker](https://pythonhosted.org/blinker/) library.
That means that you can just run `from blinker import signal` and hook into
asyncirc's events without needing a reference to the IRCProtocol object. This is
especially useful in writing plugins; take a look at plugin code for examples.
