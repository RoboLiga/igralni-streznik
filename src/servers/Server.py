# -*- coding: utf-8 -*-

from gevent import Greenlet
from gevent.event import Event


class Server(Greenlet):
    """Server that updates its information

    Server updates its own information, then triggers the event to let other greenlets know,

    Attributes:
        updated (Event): Event that fires when information is updated
    """
    def __init__(self):
        Greenlet.__init__(self)
        self.updated = Event()
