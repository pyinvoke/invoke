from spec import Spec, skip, eq_

from invoke.config import Config


class Config_(Spec):
    # Directly wraps etcaetera.Config? same args and all?
    # Otherwise, what does its init need? Right now we just pass in a single
    # dict which represents the Defaults.
    # Then we need to allow dict access & attribute access somehow, likely by
    # filtering the top level accesses & returning any dicts wrapped in a new
    # class (which is used as a mixin on the top class too I guess? Or some
    # other way of sharing code)
