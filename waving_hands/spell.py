class Spell:

    """ A spell doesn't know what it does -- it just holds data.
        Basically, it's a struct!
    """

    def __init__(self, name, gesture, desc, kill):
        self._name = name
        self._gesture = gesture
        self._desc = desc
        self._kill = kill
        self._has_time = False
        self._time_remaining = 0

    @property
    def has_time(self):
        return self._has_time

    @has_time.setter
    def has_time(self, bool):
        self._has_time = bool

    @property
    def time_remaining(self):
        return self._time_remaining
    
    @time_remaining.setter
    def time_remaining(self, value):
        self._time_remaining = value

    @property
    def name(self):
        return self._name

    @property
    def gesture(self):
        return self._gesture
    
    @property
    def desc(self):
        return self._desc

    @property
    def kill(self):
        return self._kill