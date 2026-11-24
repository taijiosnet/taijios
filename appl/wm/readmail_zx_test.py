#!/usr/bin/env python3
"""Check the ZX Readmail POP3 rules and live session against a local mock POP3 server."""
import hashlib
import os
import socket
import threading
import time

from wm_app_test import Guest, arguments, ocr, private_display, run_model, until

GREY = (221, 221, 221)
WIN_W, WIN_H = 620, 480


def check_model(env):
    message = run_model('readmail', 'readmail_states.expected', env)
    assert message == 'Readmail matched POP3, APOP, header, split and navigation rules', message
    print('Readmail model matched POP3, APOP, header, split and navigation rules')


class MockPop3Server:
    CHALLENGE = '<42.99@mock.local>'
    SECRET = 's3cr3t'
    MESSAGES = {
        1: (
            'From: Alice <alice@example.org>\r\n'
            'Subject: First Mail\r\n'
            'Date: Mon, 1 Jan 2026\r\n\r\n'
            'Body of first message.\r\n'
        ),
        2: (
            'From: Bob <bob@example.org>\r\n'
            'Subject: Second Mail\r\n'
            'Date: Tue, 2 Jan 2026\r\n\r\n'
            'Body of second message.\r\n'
        ),
    }

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('127.0.0.1', 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(4)
        self.sock.settimeout(0.5)
        self.stop_ev = threading.Event()
        self.commands = []
        self.expected_apop = hashlib.md5((self.CHALLENGE + self.SECRET).encode('utf-8')).hexdigest()
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
                conn.settimeout(5.0)
                conn.sendall(f'+OK mock POP3 ready {self.CHALLENGE}\r\n'.encode('utf-8'))
                buf = b''
                while not self.stop_ev.is_set():
                    try:
                        chunk = conn.recv(4096)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    buf += chunk
                    while b'\r\n' in buf:
                        line, buf = buf.split(b'\r\n', 1)
                        cmd = line.decode('utf-8', errors='replace')
                        self.commands.append(cmd)
                        parts = cmd.split()
                        if not parts:
                            continue
                        op = parts[0].upper()
                        if op == 'APOP':
                            if len(parts) == 3 and parts[2] == self.expected_apop:
                                conn.sendall(b'+OK authenticated\r\n')
                            else:
                                conn.sendall(b'-ERR bad apop digest\r\n')
                        elif op == 'STAT':
                            total = sum(len(m) for m in self.MESSAGES.values())
                            conn.sendall(f'+OK {len(self.MESSAGES)} {total}\r\n'.encode('utf-8'))
                        elif op == 'RETR':
                            idx = int(parts[1])
                            msg = self.MESSAGES[idx]
                            conn.sendall(f'+OK {len(msg)} octets\r\n{msg}\r\n.\r\n'.encode('utf-8'))
                        elif op == 'TOP':
                            idx = int(parts[1])
                            hdr = self.MESSAGES[idx].split('\r\n\r\n', 1)[0] + '\r\n\r\n'
                            conn.sendall(f'+OK {len(hdr)} octets\r\n{hdr}\r\n.\r\n'.encode('utf-8'))
                        elif op == 'DELE':
                            conn.sendall(f'+OK message {parts[1]} deleted\r\n'.encode('utf-8'))
                        elif op == 'QUIT':
                            conn.sendall(b'+OK bye\r\n')
                            return
                        else:
                            conn.sendall(b'-ERR unknown\r\n')

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
    pop3 = MockPop3Server()
    try:
        with Guest(env, args, [], size='700x600') as guest:
            ox, oy = until(lambda: window_origin(guest.capture()), 'Readmail did not open its window')

            # Open Connect panel, enter server, user, secret, and click Dial.
            guest.click(ox + 45, oy + 15)
            time.sleep(0.2)
            guest.click(ox + 160, oy + 65)
            time.sleep(0.15)
            guest.run('xdotool', 'key', '--window', guest.window, 'ctrl+a', 'BackSpace')
            time.sleep(0.1)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', f'tcp!127.0.0.1!{pop3.port}')
            time.sleep(0.15)

            guest.click(ox + 160, oy + 91)
            time.sleep(0.15)
            guest.run('xdotool', 'key', '--window', guest.window, 'ctrl+a', 'BackSpace')
            time.sleep(0.1)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', 'alice')
            time.sleep(0.15)

            guest.click(ox + 160, oy + 117)
            time.sleep(0.15)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', pop3.SECRET)
            time.sleep(0.2)

            # Click Dial at x=560, y=65.
            guest.click(ox + 560, oy + 65)
            until(
                lambda: ('STAT' in pop3.commands and 'RETR 2' in pop3.commands) or None,
                'Readmail did not authenticate with APOP and fetch message 2',
            )
            assert any(c.startswith(f'APOP alice {pop3.expected_apop}') for c in pop3.commands), pop3.commands
            print('Readmail authenticated via APOP MD5 and loaded message 2')

            # Click Next (x=168, y=15) to read message 1.
            guest.click(ox + 168, oy + 15)
            until(lambda: 'RETR 1' in pop3.commands or None, 'Readmail Next did not fetch message 1')

            # Click Headers (x=420, y=15) to run TOP 2 0 and TOP 1 0.
            guest.click(ox + 420, oy + 15)
            until(
                lambda: ('TOP 2 0' in pop3.commands and 'TOP 1 0' in pop3.commands) or None,
                'Readmail Headers did not send TOP for mailbox messages',
            )
            print('Readmail navigated messages and fetched TOP headers')
    finally:
        pop3.close()


def main():
    args = arguments(__doc__, 'readmail.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
