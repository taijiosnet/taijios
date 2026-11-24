#!/usr/bin/env python3
"""Check the ZX Sendmail SMTP rules and live delivery against a local mock SMTP server."""
import os
import socket
import threading
import time

from wm_app_test import Guest, arguments, ocr, private_display, run_model, until

GREY = (221, 221, 221)
WIN_W, WIN_H = 560, 440


def check_model(env):
    message = run_model('sendmail', 'sendmail_states.expected', env)
    assert message == 'Sendmail matched SMTP response, address, netmkaddr and reply-header rules', message
    print('Sendmail model matched SMTP response, address, netmkaddr and reply-header rules')


class MockSmtpServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('127.0.0.1', 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(4)
        self.sock.settimeout(0.5)
        self.stop_ev = threading.Event()
        self.commands = []
        self.data_received = ''
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
                conn.sendall(b'220 mock.local ESMTP ready\r\n')
                buf = b''
                in_data = False
                data_buf = b''
                while not self.stop_ev.is_set():
                    try:
                        chunk = conn.recv(4096)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    if in_data:
                        data_buf += chunk
                        if b'\r\n.\r\n' in data_buf:
                            self.data_received = data_buf.split(b'\r\n.\r\n', 1)[0].decode('utf-8', errors='replace')
                            in_data = False
                            conn.sendall(b'250 Queued ok\r\n')
                        continue
                    buf += chunk
                    while b'\r\n' in buf:
                        line, buf = buf.split(b'\r\n', 1)
                        cmd = line.decode('utf-8', errors='replace')
                        self.commands.append(cmd)
                        upper = cmd.upper()
                        if upper.startswith('DATA'):
                            in_data = True
                            data_buf = buf
                            buf = b''
                            conn.sendall(b'354 Go ahead\r\n')
                            break
                        elif upper.startswith('QUIT'):
                            conn.sendall(b'221 Bye\r\n')
                            return
                        else:
                            conn.sendall(b'250 OK\r\n')

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
    smtp = MockSmtpServer()
    try:
        with Guest(env, args, [], size='640x560') as guest:
            origin = until(lambda: window_origin(guest.capture()), 'Sendmail did not open its window')
            ox, oy = origin

            # Open Connect panel, fill Mail Server and User Name, click Dial.
            guest.click(ox + 45, oy + 15)
            time.sleep(0.2)
            # Mail Server field at x=160, y=65
            guest.click(ox + 160, oy + 65)
            time.sleep(0.15)
            guest.run('xdotool', 'key', '--window', guest.window, 'ctrl+a', 'BackSpace')
            time.sleep(0.1)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', f'tcp!127.0.0.1!{smtp.port}')
            time.sleep(0.2)
            # User Name field at x=160, y=91
            guest.click(ox + 160, oy + 91)
            time.sleep(0.15)
            guest.run('xdotool', 'key', '--window', guest.window, 'ctrl+a', 'BackSpace')
            time.sleep(0.1)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', 'alice@example.org')
            time.sleep(0.2)
            # Click Dial at x=500, y=65
            guest.click(ox + 500, oy + 65)

            until(
                lambda: any(c.startswith('HELO example.org') for c in smtp.commands) or None,
                'Sendmail did not connect and send HELO to mock SMTP server',
            )
            print('Sendmail dialed local SMTP server and completed HELO')

            # Fill Mail To (y=59), Subject (y=111), and Body (y=165).
            guest.click(ox + 140, oy + 59)
            time.sleep(0.15)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', 'bob@example.org')
            time.sleep(0.15)
            guest.click(ox + 140, oy + 111)
            time.sleep(0.15)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', 'TestSubject')
            time.sleep(0.15)
            guest.click(ox + 140, oy + 165)
            time.sleep(0.15)
            guest.run('xdotool', 'type', '--window', guest.window, '--delay', '50', 'Hello from ZX Sendmail')
            time.sleep(0.25)

            # Click Send at x=120, y=15.
            guest.click(ox + 120, oy + 15)
            until(
                lambda: ('Hello from ZX Sendmail' in smtp.data_received and 'Subject: TestSubject' in smtp.data_received) or None,
                'Sendmail did not deliver message body and subject over SMTP',
            )
            assert 'MAIL FROM:<alice@example.org>' in smtp.commands, smtp.commands
            assert 'RCPT TO:<bob@example.org>' in smtp.commands, smtp.commands
            print('Sendmail delivered MAIL FROM, RCPT TO, Subject and body over SMTP')
    finally:
        smtp.close()


def main():
    args = arguments(__doc__, 'sendmail.zx')
    check_model(os.environ.copy())
    with private_display() as env:
        check_window(env, args)


if __name__ == '__main__':
    main()
