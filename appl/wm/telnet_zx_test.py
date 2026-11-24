#!/usr/bin/env python3
"""Check the ZX Telnet IAC rules and live TCP session against a local mock telnet server."""
import os
import socket
import threading
import time

from wm_app_test import Guest, arguments, private_display, run_model, until

GREY = (221, 221, 221)
WIN_W, WIN_H = 640, 440


def check_model(env):
    message = run_model('telnet', 'telnet_states.expected', env)
    assert message == 'Telnet matched IAC negotiation, SB TERM, AYT, CRLF and word-erase rules', message
    print('Telnet model matched IAC negotiation, SB TERM, AYT, CRLF and word-erase rules')


class MockTelnetServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('127.0.0.1', 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(4)
        self.sock.settimeout(0.5)
        self.stop_ev = threading.Event()
        self.received = bytearray()
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        while not self.stop_ev.is_set():
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                conn.settimeout(0.5)
                # Send IAC DO TERM, IAC SB TERM SEND IAC SE, IAC AYT, and a greeting line.
                conn.sendall(
                    bytes([255, 253, 24, 255, 250, 24, 1, 255, 240, 255, 246])
                    + b'Welcome to Mock Telnet\r\n'
                )
                while not self.stop_ev.is_set():
                    try:
                        chunk = conn.recv(4096)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    self.received.extend(chunk)
                    if b'ping' in self.received:
                        conn.sendall(b'PONG\r\n')

    def close(self):
        self.stop_ev.set()
        try:
            self.sock.close()
        except OSError:
            pass


def window_origin(image):
    pixels = image.load()
    for y in range(10, image.height - WIN_H + 1):
        for x in range(0, image.width - WIN_W + 1):
            if pixels[x, y] == GREY and pixels[x + WIN_W - 1, y] == GREY \
                    and pixels[x, y + WIN_H - 1] == GREY and pixels[x + WIN_W - 1, y + WIN_H - 1] == GREY:
                return x, y
    return None


def check_window(env, args):
    srv = MockTelnetServer()
    try:
        with Guest(env, args, [], size='720x560') as guest:
            ox, oy = until(lambda: window_origin(guest.capture()), 'Telnet did not open its window')

            # Click Connect (x=45, y=15), enter 127.0.0.1 and port, click Dial.
            guest.click(ox + 45, oy + 15)
            time.sleep(0.2)
            guest.click(ox + 150, oy + 65)
            time.sleep(0.15)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', '127.0.0.1')
            time.sleep(0.15)
            guest.click(ox + 150, oy + 91)
            time.sleep(0.15)
            guest.run('xdotool', 'key', '--window', guest.window, 'ctrl+a', 'BackSpace')
            time.sleep(0.1)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', str(srv.port))
            time.sleep(0.2)
            guest.click(ox + 580, oy + 65)

            expected_sb = bytes([255, 250, 24, 0]) + b'dumb' + bytes([255, 240])
            until(
                lambda: (bytes([255, 251, 24]) in srv.received
                         and expected_sb in srv.received
                         and b'Inferno telnet V1.0\r\n' in srv.received) or None,
                'Telnet did not complete IAC WILL TERM, SB TERM dumb, and AYT response',
            )
            print('Telnet negotiated IAC TERM=dumb and answered AYT')

            # Click transcript area and type 'ping\n' to verify keyboard transmission.
            guest.click(ox + 150, oy + 150)
            time.sleep(0.15)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', 'ping')
            guest.run('xdotool', 'key', '--window', guest.window, 'Return')
            until(lambda: b'ping' in srv.received or None, 'Telnet did not transmit typed input')
            print('Telnet transmitted live keyboard input over TCP')
    finally:
        srv.close()


def main():
    args = arguments(__doc__, 'telnet.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
