class Client:
    def __init__(self, **mock_functions):
        self.nickname = "bot"
        self.server_supports = {}
        for n, f in mock_functions.items():
            setattr(self, n, f)
