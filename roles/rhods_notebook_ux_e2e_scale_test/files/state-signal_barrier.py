
import state_signals
import argparse

CONN_TIMEOUT = 60
DEFAULT_WAIT_TIMEOUT = -1

DEFAULT_REDIS_PORT = 6379

class StateSignalsExporter:

    def __init__(self, redis_host: str, redis_port: int, clients: int, wait_timeout: int):
        self.redis_host = redis_host
        self.redis_port = redis_port

        self.clients = clients
        self.wait_timeout = wait_timeout

    def state_signals_exporter(self):
        sig_ex = state_signals.SignalExporter("rhods-test", redis_host=self.redis_host, redis_port=self.redis_port, conn_timeout=CONN_TIMEOUT, log_level="WARN")
        sub_code = sig_ex.initialize_and_wait(await_sub_count=self.clients, legal_events=["barrier", "fail", "success"], periodic=True, timeout=self.wait_timeout)
        if sub_code != 0:
            print("Timed out waiting for subscribers...")
            res_code = 110 # ETIMEDOUT
            # Error handle
        else:
            res_code, msgs = sig_ex.publish_signal("barrier")

        if res_code != 0:
            if res_code == 1:
                print("One sub responded with failure status")
            elif res_code == 2:
                print("Not all subs responded, timed out waiting...")

            print("Fail", res_code)
            sig_ex.publish_signal("fail")
        else:
            print("Success", res_code)
            sig_ex.publish_signal("success")

        sig_ex.shutdown()
        return res_code


class StateSignalsResponder:
    def __init__(self, redis_host: str, redis_port: int):
        self.redis_host = redis_host
        self.redis_port = redis_port

    def _listener(self):
        sig_resp = state_signals.SignalResponder(redis_host=self.redis_host,
                                                 redis_port=self.redis_port,
                                                 conn_timeout=CONN_TIMEOUT)
        for signal in sig_resp.listen():
            if signal.event != "initialization":
                print(signal)

            ras = 1
            sig_resp.srespond(signal, ras)

            if signal.event == "fail":
                return 1
            elif signal.event == "success":
                return 0


def main():
    # Instantiate the parser
    parser = argparse.ArgumentParser(description='Signal State Exporter')

    # Required positional argument
    parser.add_argument('redis_host', type=str, help='Redis host')

    parser.add_argument('--redis-port', type=int, help='Redis port', nargs='?', default=DEFAULT_REDIS_PORT)

    parser.add_argument('--exporter', type=int, help='Act as an exporter, wait for N clients to reach the barrier')
    parser.add_argument('--delay', type=int, help='', nargs='?', const=DEFAULT_WAIT_TIMEOUT)

    args = parser.parse_args()
    if args.exporter:
        print(f"Running the StateSignal controller. Waiting for {args.exporter} clients for {args.delay}s.")
        run = StateSignalsExporter(redis_host=args.redis_host, redis_port=args.redis_port, clients=args.exporter, wait_timeout=args.delay)
        return run.state_signals_exporter()
    else:
        print("Connecting to the StateSignal barrier ...")
        run = StateSignalsResponder(redis_host=args.redis_host, redis_port=args.redis_port)
        return run._listener()

if __name__ == "__main__":
    raise SystemExit(main())
