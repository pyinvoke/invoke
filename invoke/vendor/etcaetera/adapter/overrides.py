from .base import Adapter
from ..utils import format_key


class Overrides(Adapter):
    def __init__(self, data={}, *args, **kwargs):
        super(Overrides, self).__init__(*args, **kwargs)
        self.data = data
        self.load()

    def load(self, formatter=None):
        self.data = dict((self.format(k, formatter), v) for k, v in self.data.items())
