from blinker import signal

def handle_public_messages(message, user, target, text):
    prefix = message.client.nickname
    triggers = ["{}: ", "{}, ", "{} "]
    for trigger in triggers:
        if text.startswith(trigger):
            text = text[len(trigger):]
            signal("addressed").send(message, user=user, target=target, text=text)
            return

signal("plugin-registered").send("asyncirc.plugins.addressed")
