import logging

log = logging.getLogger("gamepulse")
if not log.handlers:
    log.addHandler(logging.NullHandler())
