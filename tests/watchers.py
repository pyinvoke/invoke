from spec import Spec, skip, eq_

from invoke import Responder


# NOTE: StreamWatcher is basically just an interface/protocol; no behavior to
# test of its own. So this file tests Responder primarily. (FailingResponder is
# mostly tested in Context tests for .sudo().)

class Responder_(Spec):
    def keeps_track_of_seen_index_per_thread(self):
        skip()
        # - instantiate a single responder
        # - thread body func that takes a responder and queue/s, writes queue
        #   data to responder and writes responder submissions back to queue
        # - create two threads from that body func, and queues for each
        # - start the threads
        # - write text to 1st thread and expect response from it only
        # - write text to 2nd thread and expect response from it only
        # - join the threads in a finally

    def yields_response_when_regular_string_pattern_seen(self):
        r = Responder(pattern='empty', response='handed')
        eq_(list(r.submit('the house was empty')), ['handed'])

    def yields_response_when_regex_seen(self):
        r = Responder(pattern=r'tech.*debt', response='pay it down')
        eq_(list(r.submit("technically, it's still debt")), ['pay it down'])

    def multiple_hits_within_stream_yield_multiple_responses(self):
        r = Responder(pattern='jump', response='how high?')
        eq_(list(r.submit('jump, wait, jump, wait')), ['how high?'] * 2)

    def patterns_span_multiple_lines(self):
        r = Responder(pattern=r'call.*problem', response='So sorry')
        output = """
You only call me
when you have a problem
You never call me
Just to say hi
"""
        eq_(list(r.submit(output)), ['So sorry'])
