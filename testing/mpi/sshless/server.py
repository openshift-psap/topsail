import socket
import ssl
import subprocess
import selectors
import sys, os

secret_path = os.getenv("SSHLESS_SECRET_PATH")
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(f'{secret_path}/tls.crt', f'{secret_path}/tls.key')

# Stream and StreamTransfer code from
# https://github.com/carletes/mock-ssh-server/blob/master/mockssh/server.py

class Stream:
    def __init__(self, fd, read, write, flush):
        self.fd = fd
        self.read = read
        self.write = write
        self.flush = flush

    def transfer(self):
        data = self.read()
        self.write(data)
        self.flush()
        return data

    def drain(self):
        while True:
            if not self.transfer():
                return

class StreamTransfer:
    BUFFER_SIZE = 1024

    def __init__(self, ssh_channel, process):
        self.process = process
        self.streams = [
            self.ssh_to_process(ssh_channel, self.process.stdin),
            self.process_to_ssh(self.process.stdout, ssh_channel.send),
            self.process_to_ssh(self.process.stderr, ssh_channel.send),
        ]

    def ssh_to_process(self, channel, process_stream):
        return Stream(channel, lambda: channel.recv(self.BUFFER_SIZE), process_stream.write, process_stream.flush)

    @staticmethod
    def process_to_ssh(process_stream, write_func):
        return Stream(process_stream, process_stream.readline, write_func, lambda: None)

    def run(self):
        with selectors.DefaultSelector() as selector:
            for stream in self.streams:
                selector.register(stream.fd, selectors.EVENT_READ, data=stream)

            self.transfer(selector)
            self.drain(selector)

    @staticmethod
    def ready_streams(selector):
        return (key.data for key, _ in selector.select(timeout=-1))

    def transfer(self, selector):
        while self.process.poll() is None:
            for stream in self.ready_streams(selector):
                stream.transfer()

    def drain(self, selector):
        for stream in self.ready_streams(selector):
            stream.drain()


def communicate_process(chan, cmd):
    def _read_chan(chan, stdin):
        x = chan.recv(1)
        if ord(x) == 13:
            chan.send("\r\n")
            stdin.write("\n")
        else:
            chan.send(x)
            stdin.write(x)
        stdin.flush()

    def _write_chan(chan, out):
        x = out.read(1)
        chan.send(x.replace(b"\n", b"\r\n"))

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    StreamTransfer(chan, process).run()
    return process.returncode

    print("bye", process.poll())

def wait_and_execute(addr, port):
    print(f"wait_and_execute: waiting for connection on {addr}:{port}", flush=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
        sock.bind((addr, port))
        sock.listen(5)
        with context.wrap_socket(sock, server_side=True) as ssock:
            while True:
                conn, addr = ssock.accept()
                print(f"wait_and_execute: got a connection from", addr, flush=True)

                conn_f = conn.makefile()
                command = conn_f.readline()
                if command.strip() == "SYNC":
                    print(f"wait_and_execute: synchrononization received.", flush=True)
                    conn.close()
                    conn.shutdown(socket.SHUT_RDWR)

                    continue

                print(f"wait_and_execute: execution request command={command}", flush=True)
                break

            conn.send(b"> executing ")
            conn.send(command.encode('ascii'))
            conn.send(b"\n")

            errcode = communicate_process(conn, command)
            print(f"wait_and_execute: done with command={command}", flush=True)
            print(f"wait_and_execute: errcode={errcode}", flush=True)
            conn.send(b"> done, errcode=")
            conn.send(str(errcode).encode("ascii"))
            conn.send(b"\n")

            conn.close()
            conn.shutdown(socket.SHUT_RDWR)
        sock.close()
        sock.shutdown(socket.SHUT_RDWR)

    print(f"wait_and_execute: done, errcode={errcode}", flush=True)

    return errcode

def wait_and_send_errcode(addr, port, errcode):
    print(f"wait_and_send_errcode: waiting for connection on {addr}:{port}", flush=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((addr, port))
        sock.listen(5)
        with context.wrap_socket(sock, server_side=True) as ssock:
            conn, addr = ssock.accept()
            print(f"wait_and_send_errcode: got a connection from", addr, flush=True)

            conn.send(b"errcode=")
            conn.send(str(errcode).encode("ascii"))
            conn.send(b"\n")
            conn.close()
        sock.close()
    print(f"wait_and_send_errcode: done", flush=True)

if __name__ == "__main__":
    ADDR = "0.0.0.0"
    BASE_PORT = 8440
    print(f"Running on {socket.gethostname()}:{BASE_PORT}")
    while True:
        try:
            errcode = wait_and_execute(ADDR, BASE_PORT)
        except Exception as e:
            print(e)
            errcode=255
        wait_and_send_errcode(ADDR, BASE_PORT+1, errcode)
        print("DONE")
