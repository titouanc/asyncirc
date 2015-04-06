from blinker import signal

def handle_public_messages(message, user, target, text):
    prefix = message.client.nickname
    triggers = [i.format(prefix) for i in ["{}: ", "{}, ", "{} "]]
    for trigger in triggers:
        if text.startswith(trigger):
            text = text[len(trigger):]
            signal("addressed").send(message, user=user, target=target, text=text)
            return

signal("public-message").connect(handle_public_messages)
signal("plugin-registered").send("asyncirc.plugins.addressed")
