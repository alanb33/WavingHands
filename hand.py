# a hand contains the history of its gestures.

class Hand:

    def __init__(self):
        self._history = ""

    def get_latest_gesture(self):
        if self.history[:-1] == "":
            # Nothing
            return "c"
        else:
            return self.history[-1:]

    @property
    def history(self):
        return self._history

    @history.setter
    def history(self, new_history):
        self._history = new_history

    def add_gesture(self, gesture):
        
        new_history = []

        if len(self.history) == 8:
            for i in range(1, len(self.history)):
                new_history.append(self.history[i])

            new_history.append(gesture)
            new_history = "".join(new_history)

            self.history = new_history
        else:
            self.history += gesture

        """
        if len(self.history) == 1:
            new_history = []
            for i in range(len(self.history)):
                new_history.append(self.history[i])
            new_history.append(gesture)
            self.history = "".join(new_history)

        self.history = self.history + gesture
        """

    def show_history(self):
        if len(self.history) > 0:
            return self.history
        else:
            return "Nothing yet."

    def erase_history(self):
        self._history = ""