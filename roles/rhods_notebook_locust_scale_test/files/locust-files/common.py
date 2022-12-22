import functools
import datetime
import logging
import threading, queue
import collections
import io, csv

env = None # set by locustfile.py

class LocustMetaEvent:
    def __init__(self, event):

        self.start_time = None
        self.start_ts = None

        BASE_EVENT = {
            "request_type": "NONE",
            "context": {"no": "context"},
            "response": "no response",
            "response_length": 0,
            "exception": None,
            "url": "no url",

            "user_name": "no user_name",
            "user_index": "no user_index",
            "name": "no name",
        }
        self.event = {} | BASE_EVENT | event

    def __enter__(self):
        self.start_time = datetime.datetime.now()
        self.start_ts = datetime.datetime.timestamp(self.start_time)
        self.event["start_time"] = self.start_ts,

        logging.info("")
        logging.info(f"<START> {self.event['request_type']}\t{self.event['user_name']} {self.event['name']}")

        return self

    def __exit__(self, type, value, traceback):
        finish_event_data = {}

        if value and "exception" not in finish_event_data:
            finish_event_data["exception"] = str(value)

        if value:
            logging.error(f"{value.__class__.__name__}: {value}")

        return self.fire(finish_event_data)

    def fire(self, extra_event_data={}):
        finish_time = datetime.datetime.now()

        event = self.event | extra_event_data | {
            "response_time": (finish_time - self.start_time).total_seconds() * 1000,
        }

        env.csv_progress.write(CsvProgressEntry(
            event["request_type"],
            event["user_name"],
            event["user_index"],
            event["name"],
            self.start_ts,
            datetime.datetime.timestamp(finish_time),
            event.get("exception")
        ))

        logging.info(f"<FIRE> {event['request_type']}\t{event['user_name']} {event['name']} {finish_time - self.start_time}\n")

        return self

def Step(name):
    def decorator(fct):
        @functools.wraps(fct)
        def call_fct(*args, **kwargs):
            if not isinstance(args[0], ContextBase):
                import pdb;pdb.set_trace()
                raise ValueError(f"Step: {args[0]=} should be a subclass of ContextBase ...")
            caller = args[0]

            meta_event = {
                "request_type": "STEP",
                "name": name,
                "url": "/"+name.replace(" ", "_").lower(),
                "user_name": caller.user_name,
                "user_index": caller.user_index,
            }
            with LocustMetaEvent(meta_event) as evt:
                evt.fire(dict(request_type="STEP_START"))
                return fct(*args, **kwargs)

        return call_fct

    return decorator

class Context():
    context = None
    def __init__(self, client, env, user_name, user_index):
        self.client = client
        self.env = env
        self.user_name = user_name
        self.user_index = user_index

        Context.context = self

class ContextBase():
    def __init__(self, context):
        self.context = context
        self.client = context.client
        self.env = context.env
        self.user_name = context.user_name
        self.user_index = context.user_index

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

def check_status(response):
    try:
        response_json = response.json()
    except Exception as e:
        debug_point()
        logging.warning(f"Couldn't parse the response as json: {e} [{response.url}] [{response}]")
        logging.warning(response.text)
        raise ScaleTestError("K8s error (invalid response)", response)

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

class CsvFileWriter(threading.Thread):
    def __init__(self, filepath, csv_class):
        threading.Thread.__init__(self, daemon=True)
        self.queue = queue.Queue()
        self.filepath = filepath
        self.csv_class = csv_class

        self.queue.put(",".join(self.csv_class._fields) + "\n")
        self.start()

    def run(self):
        with open(self.filepath, 'w') as f:
            while True:
                csv_line = self.queue.get()
                f.write(csv_line)
                f.flush()
                self.queue.task_done()

    def write(self, csv_obj):
        output = io.StringIO()
        wr = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        wr.writerow([getattr(csv_obj, attr) for attr in self.csv_class._fields])

        self.queue.put(output.getvalue())

CsvProgressEntry = collections.namedtuple(
    "CsvProgressEntry",
    ["type", "user_name", "user_index", "step_name", "start", "stop", "exception"]
)

CsvBugHitEntry = collections.namedtuple(
    "CsvBugHit",
    ["jira_id", "user_name", "timestamp", "details"]
)

def bug_hit(jira_id, user_name, details=""):
    logging.warning(f"User {user_name} hit {jira_id}" + f"({details})" if details else "")
    now = datetime.datetime.timestamp(datetime.datetime.now())
    Context.context.env.csv_bug_hits.write(CsvBugHitEntry(
        jira_id, user_name, now, details,
    ))
