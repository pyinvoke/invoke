from invoke import Context, Config
from invocations import ci as ci_mod


class Context_:
    class sudo:
        def base_case(self):
            c = Context()
            # Grab CI-oriented sudo user/pass direct from invocations.ci
            # TODO: might be nice to give Collection a way to get a Config
            # object direct, instead of a dict?
            ci_conf = Config(ci_mod.ns.configuration()).ci.sudo
            user = ci_conf.user
            c.config.sudo.password = ci_conf.password
            # Safety 1: ensure configured user even exists
            assert c.run(f"id {user}", warn=True)
            # Safety 2: make sure we ARE them (and not eg root already)
            assert c.run("whoami", hide=True).stdout.strip() == user
            assert c.sudo("whoami", hide=True).stdout.strip() == "root"
