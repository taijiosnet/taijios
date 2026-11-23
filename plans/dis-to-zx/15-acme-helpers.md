# 15. Acme helper binaries outside dis/ - 3 rows

Owner: Acme helpers outside dis/ (acme lane)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

Tracked `.dis` helper binaries installed outside `dis/` by the acme build (mkfile targets under `appl/acme/acme/`). Same family and done rule as acme; each is removed via `git rm` in the acme family's tested commit.

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| acme/mail/Mail.dis | appl/acme/acme/mail/src/Mail.b |  | - |  |
| acme/mail/Mailpop3.dis | appl/acme/acme/mail/src/Mailpop3.b |  | - |  |
| acme/mail/mkbox.dis | appl/acme/acme/mail/mkbox.b |  | - | mkfile source in appl/acme/acme/mail/, not src/ |

