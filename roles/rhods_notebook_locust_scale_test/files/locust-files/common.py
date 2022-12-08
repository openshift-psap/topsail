import functools
import datetime
import logging

class LocustMetaEvent:
    def __init__(self, event):
        self.event = event

        self.start_time = None
        self.start_ts = None

    def __enter__(self):
        self.start_time = datetime.datetime.now()
        self.start_ts = datetime.datetime.timestamp(self.start_time)

    def __exit__(self, type, value, traceback):
        finish_time = datetime.datetime.now()
        event = self.event|{
            "response_time": (finish_time - self.start_time).total_seconds() * 1000,
            "context": {"hello": "world"},
            "start_time": self.start_ts,
        }

        if value and not event.get("exception"):
            event["exception"] = str(value)
        if value:
            logging.error(f"{value.__class__.__name__}: {value}")

        Context.context.client.request_event.fire(**event)

def Step(name):
    def decorator(fct):
        @functools.wraps(fct)
        def call_fct(*args, **kwargs):
            #print()
            #print(name)
            #print("="*len(name))
            #print()
            meta_event = {
                "request_type": f"STEP",
                "name": name,
                "response": "no answer",
                "url": "/"+name.replace(" ", "_").lower(),
                "response_length": 0,
                "exception": None,
            }
            with LocustMetaEvent(meta_event):
                return fct(*args, **kwargs)

        return call_fct

    return decorator

class Context():
    context = None
    def __init__(self, client, env, user_name):
        self.client = client
        self.env = env
        self.user_name = user_name

        Context.context = self

class ContextBase():
    def __init__(self, context):
        self.context = context
        self.client = context.client
        self.env = context.env
        self.user_name = context.user_name

def url_name(url, _query=None, _descr=None, **params):
    name = f"{url}?{_query}" if _query else url

    if _descr:
        name = f"{name} {_descr}"

    return dict(
        url=url.format(**params),
        name=name,
    )

def debug_point():
    if not Context.context.env.DEBUG_MODE:
        return

    import pdb;pdb.set_trace()
    pass

def check_status(response_json):
    if response_json["kind"] != "Status":
        return response_json
    debug_point()
    logging.warning(response_json)

    raise ScaleTestError("K8s error", response_json)


class ScaleTestError(Exception):
    def __init__(self, msg, unclear=False, known_bug=False):
        Exception.__init__(self)
        self.msg = msg
        self.unclear = unclear
        self.known_bug = known_bug

    def __str__(self):
        opts = ""
        if self.known_bug:
            opts += f", known_bug={self.known_bug}"
        if self.unclear:
            opts += f", unclear={self.unclear}"

        return f'{self.__class__.__name__}("{self.msg}"{opts})'
