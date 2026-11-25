# 15. Acme helper binaries outside zx/ - 2 rows

Owner: Acme helpers outside zx/ (acme lane)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

Tracked `.dis` helper binaries installed outside `zx/` by the acme build (mkfile targets under `appl/acme/acme/`). Same family and done rule as acme; each is removed via `git rm` in the acme family's tested commit.

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| acme/mail/Mail.dis | appl/acme/acme/mail/src/Mail.b |  | - | blocked: needs `taijios_io.Fwstat` on open fds, ZX `sendmail`, and concurrent multi-window event/timer loop |
| acme/mail/Mailpop3.dis | appl/acme/acme/mail/src/Mailpop3.b |  | - | blocked: needs Ziran `pop3` library (`zx/lib/pop3.dis`), `taijios_io.Fwstat`, and ZX `sendmail` |

