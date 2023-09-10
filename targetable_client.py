class TargetableClient:

    def __init__(self, name, hp, e_type, invisibility=False, rank=1, target_name = "No target", master_name = "No master"):
        self._name        = name
        self._hp          = hp
        self._e_type      = e_type
        self._invisible   = invisibility
        self._rank        = rank
        self._target_name = target_name
        self._master_name = master_name

        if not target_name:
            self._target_name = "No target"

    @property
    def e_type(self):
        return self._e_type

    @property
    def hp(self):
        return self._hp

    @property
    def invisible(self):
        return self._invisible

    @property
    def master_name(self):
        return self._master_name

    @property
    def name(self):
        return self._name

    @property
    def rank(self):
        return self._rank

    @property
    def target_name(self):
        return self._target_name