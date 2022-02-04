#!/usr/bin/env python

# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

import base64
from binascii import hexlify
import os
import socket
import sys
import threading
import traceback
import subprocess

import selectors

import paramiko
from paramiko.py3compat import b, u, decodebytes


# setup logging
paramiko.util.log_to_file("demo_server.log")


if not os.getenv("SSH_KEY"):
    raise RuntimeError("SSH_KEY must point to the ssh host key")

if not int(os.getenv("SSHD_PORT")):
    raise RuntimeError("SSHD_PORT must specify the port number for SSHD to listen to")

host_key = paramiko.ECDSAKey(filename=os.getenv("SSH_KEY"))
with open(os.getenv("SSH_KEY")+".pub") as f:
    line = f.readlines()[0]
    public_key = line.split()[1]

print("Private key fingerprint: " + u(hexlify(host_key.get_fingerprint())))
print("Public key fingerprint: " + public_key)

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
    chan.send_exit_status(process.returncode)

    print("bye", process.poll())

class Server(paramiko.ServerInterface):
    # 'data' is the output of base64.b64encode(key)
    # (using the "user_rsa_key" files)

    good_pub_key = paramiko.ECDSAKey(data=decodebytes(public_key.encode('ascii')))

    def __init__(self):
        self.exec_event = threading.Event()
        self.rq_event = threading.Event()
        self.rq = "UNSET"

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED

        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_publickey(self, username, key):
        print(f"Auth attempt {username} with key: " + u(hexlify(key.get_fingerprint())))
        print()
        if key == self.good_pub_key:
            print("Authentication is valid")
            return paramiko.AUTH_SUCCESSFUL
        print("Authentication isn't valid")

        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "publickey"

    def check_channel_exec_request(self, channel, cmd, value=None):
        self.rq = cmd.decode("ascii")
        self.exec_event.set()
        self.rq_event.set()

        return True

    def check_channel_shell_request(self, channel):
        print("check_channel_shell_request --> no!")
        self.rq = "SHELL"
        self.rq_event.set()

        return False

    def check_channel_env_request(self, channel, key, value):
        print(f"check_channel_env_request: {key.decode('ascii')}={value.decode('ascii')}")
        return True

    def check_channel_pty_request(self, *args, **kwargs):
        print("check_channel_pty_request --> no")
        self.rq = "PTY"
        self.rq_event.set()

        return False

    def get_banner(self):
        return ("Hello World\n", "en-US")


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
            self.process_to_ssh(self.process.stdout, ssh_channel.sendall),
            self.process_to_ssh(self.process.stderr, ssh_channel.sendall_stderr),
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

DoGSSAPIKeyExchange = True

# now connect
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", int(os.getenv("SSHD_PORT"))))
except Exception as e:
    print("*** Bind failed: " + str(e))
    traceback.print_exc()
    sys.exit(1)

try:
    sock.listen(100)
    print("Listening for connection ...")
    client, addr = sock.accept()
except Exception as e:
    print("*** Listen/accept failed: " + str(e))
    traceback.print_exc()
    sys.exit(1)

print("Got a connection!")

try:
    t = paramiko.Transport(client, gss_kex=DoGSSAPIKeyExchange)
    t.set_gss_host(socket.getfqdn(""))
    try:
        t.load_server_moduli()
    except:
        print("(Failed to load moduli -- gex will be unsupported.)")
        raise
    t.add_server_key(host_key)
    server = Server()
    try:
        t.start_server(server=server)
    except paramiko.SSHException:
        print("*** SSH negotiation failed.")
        sys.exit(1)

    # wait for auth
    chan = t.accept(20)
    if chan is None:
        print("*** No channel.")
        sys.exit(1)

    print("Authenticated!")

    server.rq_event.wait(10)

    #f = chan.makefile("rU")
    #username = f.readline().strip("\r\n")

    if not server.exec_event.is_set():
        print("*** Client never asked for a exec.", server.rq)
        chan.send("*** Client never asked for an exec.\r\n")
        chan.send("bye\r\n")
        chan.close()
        print("Bye.")
        sys.exit(1)

    print("*** Client asked for a command:", server.rq)
    chan.send(f"*** Client asked for command: {server.rq}\r\n")
    communicate_process(chan, server.rq)
    chan.close()
    print("Bye.")


except Exception as e:
    print("*** Caught exception: " + str(e.__class__) + ": " + str(e))
    traceback.print_exc()

    try: t.close()
    except: pass

    sys.exit(1)
