import os

from .base import Adapter
from ..utils import format_key


class Env(Adapter):
    """Environment variables adapter

    The Env adapter goal is mainly to fetch and expose
    key-value pairs from the system environment to a Config object.

    To select system environment keys provide it as an uppercased
    strings *keys list. If you need to fetch a given env key as another
    end name, for example you'd wanna register USER env variable as
    MY_USER adapter key, provide your associations as a 
    {src: dest, src: dest...} **mapping dict.

    :param  keys: keys to be fetched from system environment
    :type   keys: *args

    :param  mapping: key to be fetched from env to adapter destination mapping
    :type   mapping: **kwargs
    """
    def __init__(self, *keys, **mapping):
        super(Env, self).__init__()
        self.keys = [format_key(k) for k in keys]
        self.mapping = dict((format_key(k), format_key(v)) for k, v in mapping.items())

    def load(self, formatter=None):
        env_keys = self.keys + list(self.mapping.keys())

        for key in [format_key(k) for k in env_keys]:
            env_value = os.environ.get(format_key(key))

            if env_value is not None:
                if key in self.mapping:
                    self[self.format(self.mapping[key], self.formatter)] = env_value
                else:
                    self[self.format(key, self.formatter)] = env_value
