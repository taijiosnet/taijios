# 4. Services - storage, network, name, auth, collab, usb and aux daemons - 96 rows

Owner: Services (unassigned after Claude commands-libs lane; next after section 2)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| zx/9660srv.dis | appl/cmd/9660srv.b |  | - |  |
| zx/9export.dis | appl/cmd/9export.b |  | - |  |
| zx/9srvfs.dis | appl/cmd/9srvfs.b |  | - |  |
| zx/archfs.dis | appl/cmd/archfs.b |  | - |  |
| zx/auth/changelogin.dis | appl/cmd/auth/changelogin.b |  | - |  |
| zx/auth/convpasswd.dis | appl/cmd/auth/convpasswd.b |  | - |  |
| zx/auth/factotum.dis | appl/cmd/auth/factotum/factotum.b | module/factotum.m | - |  |
| zx/auth/feedkey.dis | appl/cmd/auth/factotum/feedkey.b |  | - |  |
| zx/auth/infauth.dis | appl/cmd/auth/factotum/proto/infauth.b |  | - |  |
| zx/auth/keyfs.dis | appl/cmd/auth/keyfs.b |  | - |  |
| zx/auth/keysrv.dis | appl/cmd/auth/keysrv.b |  | - |  |
| zx/auth/logind.dis | appl/cmd/auth/logind.b |  | - |  |
| zx/auth/mkauthinfo.dis | appl/cmd/auth/mkauthinfo.b |  | - |  |
| zx/auth/passwd.dis | appl/cmd/auth/passwd.b |  | - |  |
| zx/auth/proto/authquery.dis | appl/cmd/auth/factotum/proto/authquery.b |  | - |  |
| zx/auth/proto/infauth.dis | appl/cmd/auth/factotum/proto/infauth.b |  | - |  |
| zx/auth/proto/p9any.dis | appl/cmd/auth/factotum/proto/p9any.b |  | - |  |
| zx/auth/proto/pass.dis | appl/cmd/auth/factotum/proto/pass.b |  | - |  |
| zx/auth/proto/rsa.dis | appl/cmd/auth/factotum/proto/rsa.b |  | - |  |
| zx/auth/rpc.dis | appl/cmd/auth/factotum/rpc.b |  | - |  |
| zx/auth/secstore.dis | appl/cmd/auth/secstore.b | module/secstore.m | - |  |
| zx/auth/signer.dis | appl/cmd/auth/signer.b |  | - |  |
| zx/auxi/camera.dis | appl/demo/camera/camera.b |  | - |  |
| zx/auxi/cpuslave.dis | appl/cmd/auxi/cpuslave.b |  | - |  |
| zx/auxi/fpgaload.dis | appl/cmd/auxi/fpgaload.b |  | - |  |
| zx/auxi/mangaload.dis | appl/cmd/auxi/mangaload.b |  | - |  |
| zx/auxi/odbcmnt.dis | appl/demo/odbc/odbcmnt.b |  | - |  |
| zx/auxi/pcmcia.dis | appl/cmd/auxi/pcmcia.b |  | - |  |
| zx/auxi/rdbgsrv.dis | appl/cmd/auxi/rdbgsrv.b |  | - |  |
| zx/auxi/rstyxd.dis | appl/cmd/auxi/rstyxd.b |  | - |  |
| zx/auxi/wbsrv.dis | unknown |  | - |  |
| zx/collab/clients/chat.dis | appl/collab/clients/chat.b |  | - |  |
| zx/collab/clients/poll.dis | appl/collab/clients/poll.b |  | - |  |
| zx/collab/clients/poller.dis | appl/collab/clients/poller.b |  | - |  |
| zx/collab/clients/whiteboard.dis | appl/collab/clients/whiteboard.b |  | - |  |
| zx/collab/collabsrv.dis | appl/collab/collabsrv.b |  | - |  |
| zx/collab/connect.dis | appl/collab/connect.b |  | - |  |
| zx/collab/lib/messages.dis | appl/collab/lib/messages.b |  | - |  |
| zx/collab/proxy.dis | appl/collab/proxy.b |  | - |  |
| zx/collab/servers/chatsrv.dis | appl/collab/servers/chatsrv.b |  | - |  |
| zx/collab/servers/memfssrv.dis | appl/collab/servers/memfssrv.b |  | - |  |
| zx/collab/servers/mpx.dis | appl/collab/servers/mpx.b |  | - |  |
| zx/collab/servers/wbsrv.dis | appl/collab/servers/wbsrv.b |  | - |  |
| zx/collab/srvmgr.dis | appl/collab/srvmgr.b |  | - |  |
| zx/dbfs.dis | appl/cmd/dbfs.b |  | - |  |
| zx/dossrv.dis | appl/cmd/dossrv.b |  | - |  |
| zx/ftpfs.dis | appl/cmd/ftpfs.b |  | - |  |
| zx/ip/bootpd.dis | appl/cmd/ip/bootpd.b |  | - |  |
| zx/ip/dhcp.dis | appl/cmd/ip/dhcp.b | module/dhcp.m | - |  |
| zx/ip/nppp/modem.dis | appl/cmd/ip/nppp/modem.b |  | - |  |
| zx/ip/nppp/ppplink.dis | appl/cmd/ip/nppp/ppplink.b |  | - |  |
| zx/ip/nppp/script.dis | appl/cmd/ip/nppp/script.b |  | - |  |
| zx/ip/ping.dis | appl/cmd/ip/ping.b |  | - |  |
| zx/ip/ppp/modem.dis | appl/cmd/ip/ppp/modem.b |  | - |  |
| zx/ip/ppp/pppclient.dis | appl/cmd/ip/ppp/pppclient.b |  | - |  |
| zx/ip/ppp/pppdial.dis | appl/cmd/ip/ppp/pppdial.b |  | - |  |
| zx/ip/ppp/pppgui.dis | appl/cmd/ip/ppp/pppgui.b |  | - |  |
| zx/ip/ppp/ppptest.dis | appl/cmd/ip/ppp/ppptest.b |  | - |  |
| zx/ip/ppp/script.dis | appl/cmd/ip/ppp/script.b |  | - |  |
| zx/ip/rip.dis | appl/cmd/ip/rip.b |  | - |  |
| zx/ip/sntp.dis | appl/cmd/ip/sntp.b |  | - |  |
| zx/ip/tftpd.dis | appl/cmd/ip/tftpd.b |  | - |  |
| zx/ip/virgild.dis | appl/cmd/ip/virgild.b |  | - |  |
| zx/listen.dis | appl/cmd/listen.b |  | - |  |
| zx/lockfs.dis | appl/cmd/lockfs.b |  | - |  |
| zx/memfs.dis | appl/cmd/memfs.b | module/memfs.m | - |  |
| zx/ndb/cs.dis | appl/cmd/ndb/cs.b |  | - |  |
| zx/ndb/dns.dis | appl/cmd/ndb/dns.b |  | - |  |
| zx/ndb/registry.dis | appl/cmd/ndb/registry.b |  | - |  |
| zx/plumber.dis | appl/cmd/plumber.b |  | - |  |
| zx/ramfile.dis | appl/cmd/ramfile.b |  | - |  |
| zx/rawdbfs.dis | appl/cmd/rawdbfs.b |  | - |  |
| zx/spki/verify.dis | appl/cmd/spki/verify.b |  | - |  |
| zx/svc/httpd/alarms.dis | appl/svc/httpd/alarms.b |  | - |  |
| zx/svc/httpd/cache.dis | appl/svc/httpd/cache.b |  | - |  |
| zx/svc/httpd/cgiparse.dis | appl/svc/httpd/cgiparse.b |  | - |  |
| zx/svc/httpd/contents.dis | appl/svc/httpd/contents.b |  | - |  |
| zx/svc/httpd/date.dis | appl/svc/httpd/date.b |  | - |  |
| zx/svc/httpd/echo.dis | appl/svc/httpd/echo.b |  | - |  |
| zx/svc/httpd/httpd.dis | appl/svc/httpd/httpd.b |  | - |  |
| zx/svc/httpd/imagemap.dis | appl/svc/httpd/imagemap.b |  | - |  |
| zx/svc/httpd/parser.dis | appl/svc/httpd/parser.b |  | - |  |
| zx/svc/httpd/redirect.dis | appl/svc/httpd/redirect.b |  | - |  |
| zx/svc/httpd/stats.dis | appl/svc/httpd/stats.b |  | - |  |
| zx/svc/webget/date.dis | appl/svc/webget/date.b |  | - |  |
| zx/svc/webget/file.dis | appl/svc/webget/file.b |  | - |  |
| zx/svc/webget/ftp.dis | appl/svc/webget/ftp.b |  | - |  |
| zx/svc/webget/http.dis | appl/svc/webget/http.b |  | - |  |
| zx/svc/webget/image2enc.dis | appl/svc/webget/image2enc.b |  | - |  |
| zx/svc/webget/message.dis | appl/svc/webget/message.b |  | - |  |
| zx/svc/webget/webget.dis | appl/svc/webget/webget.b | module/webget.m | - |  |
| zx/svc/webget/wgutils.dis | appl/svc/webget/wgutils.b |  | - |  |
| zx/tarfs.dis | appl/cmd/tarfs.b |  | - |  |
| zx/trfs.dis | appl/cmd/trfs.b |  | - |  |
| zx/usb/usbd.dis | appl/cmd/usb/usbd.b |  | - |  |
| zx/vacfs.dis | appl/cmd/vacfs.b |  | - |  |

