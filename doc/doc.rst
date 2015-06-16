Introduction to asyncirc
========================

Asyncirc is an IRC library based on Python's asyncio. It is designed to be easy
to use, to provide a nice way of processing IRC events, and to provide a Good
Enough(TM) abstraction of the IRC protocol. It is *not* designed to be a ready-
made bot framework, or to be used without some knowledge of how IRC works.

Installation
------------
You can install asyncirc from PyPI, using whatever method you prefer. The
package name is ``asyncio-irc``.

Signals
-------
Instead of using callback-style event handler registration, asyncirc uses
*signals*. Signals are provided by the excellent Blinker library. It would be 
advisable to read that page for more information on signals, but the tl;dr is::

    # register a signal handler
    signal("signal-name").connect(signal_handler_function)

    # send a signal
    signal("signal-name").send(sender, some="keyword", argu="ments")

Asyncirc defines a lot of signals, which are covered in detail below.

Usage
=====

Actually using asyncirc is pretty simple. First you need to import it::

    from asyncirc import irc

Then you need to create a connection::

    conn = irc.connect("chat.freenode.net", 6697, use_ssl=True)

You'll need to register with the server::

    conn.register("nickname", "ident", "realname (can contain spaces)")

Once you're registered and connected, you'll want to join some channels::

    @conn.on("irc-001")
    def autojoin_channels(message):
        conn.join(["#channel1", "#channel2"])

Maybe you want to connect some event handlers::

    @conn.on("join")
    def on_join(message, user, channel):
        conn.say(channel, "Hi {}! You're connecting from {}.".format(user.nick, user.host))

Once you're done with that, you need to run the event loop::

    import asyncio
    asyncio.get_event_loop().run_forever()

Your shiny new IRC client should now connect and do what you told it to!
Congratulations!

Using plugins
-------------
Plugins let you do new stuff with your connection. To use them, you import them
before you initially make the connection::

    from asyncirc import irc
    import asyncirc.plugins.addressed

    conn = irc.connect(...)
    ...

Plugins usually send new signals, so you want to handle those::

    @conn.on("addressed")
    def on_addressed(message, user, target, text):
        # triggers on "bot_nickname: " or similar
        bot.say(target, "{}: You said {} to me!".format(user.nick, text))

Fundamental types
=================

There are a few arguments to your handlers that are instances of specific
classes. Here are those:

``user`` is usually an instance of the ``User`` class, which has some important
attributes:

* ``User.nick`` contains the nickname of the user
* ``User.user`` contains the ident of the user
* ``User.host`` contains the host of the user
* ``User.hostmask`` contains the full hostmask of the user

The ``IRCProtocol`` object
======================

Your connection handle (above, named ``conn``) can do some useful stuff. Here's
a list of some functions that you might find helpful when writing your code.

* ``IRCProtocol.say(target, message)`` will send ``message`` to either a channel
  or user ``target``.
* ``IRCProtocol.join(channel_or_channels)`` will join either a single channel or
  a list of channels, depending on what you give it.
* ``IRCProtocol.part(channel_or_channels)`` works in a similar way to ``join``.
* ``IRCProtocol.anything(arguments)`` will send the IRC command ANYTHING to the
  server. It's basically a catch-all for any missing method.

Events you can handle
=====================

There are a lot of things that can happen on IRC. As such, there are a lot of
signals that asyncirc generates. Here's a list of some useful ones, with event
handler signatures::

    @conn.on("private-message")
    def on_private_message(message, user, target, text):
        ...

    @conn.on("public-message")
    def on_public_message(message, user, target, text):
        ...

    @conn.on("message")
    def on_any_message(message, user, target, text):
        ...

    @conn.on("private-notice")
    def on_private_notice(message, user, target, text):
        ...

    @conn.on("public-notice")
    def on_public_notice(message, user, target, text):
        ...

    @conn.on("notice")
    def on_any_notice(message, user, target, text):
        ...

    @conn.on("join")
    def on_join(message, user, channel):
        ...

    @conn.on("part")
    def on_join(message, user, channel, reason):
        # reason defaults to None if there is no reason
        ...

    @conn.on("quit")
    def on_quit(message, user, reason):
        ...

    @conn.on("kick")
    def on_kick(message, kicker, kickee, channel, reason):
        # kicker is a User object
        # kickee is just a nickname
        ...

    @conn.on("nick")
    def on_nick_change(message, user, new_nick):
        ...

These signals are actually sent by the ``core`` plugin, so that's pretty neat.

Just what is that ``message`` handler argument, anyway?
-------------------------------------------------------

``message`` is a special argument. It contains the parsed commands from the IRC
server. It has a few useful attributes:

    ``message.params`` has the arguments of the command

    ``message.verb`` has the actual IRC verb

    ``message.sender`` has the hostmask of the sender

``message`` is especially useful when you want to take care of events that don't
already have a signal attached to them. You can hook into the ``irc`` event, or
the ``irc-verb`` event to handle specific verbs. Handlers for that will take a
single argument ``message``.

Plugins
=======

There are a few plugins packaged with asyncirc. These are documented here.

``asyncirc.plugins.nickserv``
-----------------------------
Sends events when authentication to NickServ succeeds or fails. Automatically
tries to regain your nickname when it is not available (usually doesn't work
unless you've authenticated with SASL).

Events::

    @conn.on("nickserv-auth-success")
    def auth_success(message_text):
        # yay! you're authed to nickserv now.
        ...

    @conn.on("nickserv-auth-fail")
    def auth_fail(message_text):
        # oh no, you had the wrong password!
        # try again or exit!
        ...

``asyncirc.plugins.sasl``
-------------------------
Handles IRCv3 SASL authentication. After importing, there's a single method call
you need to worry about::

    asyncirc.plugins.sasl.auth(account_name, password)

And a single event::

    @conn.on("sasl-auth-complete")
    def sasl_auth_complete(message):
        # yay, you've authenticated with SASL.
        ...

You probably don't even have to worry about the event. This plugin talks to the
core plugin so that registration is delayed until SASL authentication is done.

``asyncirc.plugins.cap``
------------------------
Handles IRCv3 capability negotiation. There's only one method you need to call
to request a capability once you've imported this plugin::

    asyncirc.plugins.cap.request_capability("extended-join") # or whatever

The ``caps-acknowledged`` event will be fired when the server has acknowledged
our request for capabilities. As soon as we know what set of capabilities the
server supports, the ``caps-known`` event is fired.

``asyncirc.plugins.tracking``
-----------------------------
Full state tracking. Some methods::

    user = asyncirc.plugins.tracking.get_user(hostmask_or_nick)
    chan = asyncirc.plugins.tracking.get_channel(channel_name)

Based on that, here's some stuff you can do::

    chan.users     # a list of nicknames in the channel
    user.channels  # a list of channels that the user is in
    user.account   # the user's services account name. works best if you've
                   # requested the extended-join and account-notify capabilities
    chan.mode      # return the channel's mode string
    user.previous_nicks  # return the user's previous nicknames that we know of

How it actually works is really complicated. Don't even ask.

``asyncirc.plugins.addressed``
------------------------------
It has an event that fires when someone mentions your bot by name in IRC::

    @conn.on("addressed")
    def on_me_addressed(message, user, target, text):
        # text contains the text without the "your_bot: " part
        ...

You can also register command characters that can be used instead of your bot's
nickname::

    asyncirc.plugins.addressed.register_command_character(";;")

Questions? Issues? Just want to chat?
=====================================

I'm fwilson on freenode, if you have any questions. I hang out in
``#watchtower`` along with the rest of the Watchtower dev team. Feel free to
join us!
