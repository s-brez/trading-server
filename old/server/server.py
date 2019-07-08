from datamanager import Datamanager


class Server:
    """ Server
    """

    data = None

    def __init__(self):

        self.data = Datamanager()

        # self.data.start_listeners()
        # self.data.backfill()
