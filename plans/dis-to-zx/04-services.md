# 4. Services - storage, network, name, auth, collab, usb and aux daemons - 96 rows

Owner: Services (unassigned after Claude commands-libs lane; next after section 2)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| dis/9660srv.dis | appl/cmd/9660srv.b |  | - |  |
| dis/9export.dis | appl/cmd/9export.b |  | - |  |
| dis/9srvfs.dis | appl/cmd/9srvfs.b |  | - |  |
| dis/archfs.dis | appl/cmd/archfs.b |  | - |  |
| dis/auth/changelogin.dis | appl/cmd/auth/changelogin.b |  | - |  |
| dis/auth/convpasswd.dis | appl/cmd/auth/convpasswd.b |  | - |  |
| dis/auth/factotum.dis | appl/cmd/auth/factotum/factotum.b | module/factotum.m | - |  |
| dis/auth/feedkey.dis | appl/cmd/auth/factotum/feedkey.b |  | - |  |
| dis/auth/infauth.dis | appl/cmd/auth/factotum/proto/infauth.b |  | - |  |
| dis/auth/keyfs.dis | appl/cmd/auth/keyfs.b |  | - |  |
| dis/auth/keysrv.dis | appl/cmd/auth/keysrv.b |  | - |  |
| dis/auth/logind.dis | appl/cmd/auth/logind.b |  | - |  |
| dis/auth/mkauthinfo.dis | appl/cmd/auth/mkauthinfo.b |  | - |  |
| dis/auth/passwd.dis | appl/cmd/auth/passwd.b |  | - |  |
| dis/auth/proto/authquery.dis | appl/cmd/auth/factotum/proto/authquery.b |  | - |  |
| dis/auth/proto/infauth.dis | appl/cmd/auth/factotum/proto/infauth.b |  | - |  |
| dis/auth/proto/p9any.dis | appl/cmd/auth/factotum/proto/p9any.b |  | - |  |
| dis/auth/proto/pass.dis | appl/cmd/auth/factotum/proto/pass.b |  | - |  |
| dis/auth/proto/rsa.dis | appl/cmd/auth/factotum/proto/rsa.b |  | - |  |
| dis/auth/rpc.dis | appl/cmd/auth/factotum/rpc.b |  | - |  |
| dis/auth/secstore.dis | appl/cmd/auth/secstore.b | module/secstore.m | - |  |
| dis/auth/signer.dis | appl/cmd/auth/signer.b |  | - |  |
| dis/auxi/camera.dis | appl/demo/camera/camera.b |  | - |  |
| dis/auxi/cpuslave.dis | appl/cmd/auxi/cpuslave.b |  | - |  |
| dis/auxi/fpgaload.dis | appl/cmd/auxi/fpgaload.b |  | - |  |
| dis/auxi/mangaload.dis | appl/cmd/auxi/mangaload.b |  | - |  |
| dis/auxi/odbcmnt.dis | appl/demo/odbc/odbcmnt.b |  | - |  |
| dis/auxi/pcmcia.dis | appl/cmd/auxi/pcmcia.b |  | - |  |
| dis/auxi/rdbgsrv.dis | appl/cmd/auxi/rdbgsrv.b |  | - |  |
| dis/auxi/rstyxd.dis | appl/cmd/auxi/rstyxd.b |  | - |  |
| dis/auxi/wbsrv.dis | unknown |  | - |  |
| dis/collab/clients/chat.dis | appl/collab/clients/chat.b |  | - |  |
| dis/collab/clients/poll.dis | appl/collab/clients/poll.b |  | - |  |
| dis/collab/clients/poller.dis | appl/collab/clients/poller.b |  | - |  |
| dis/collab/clients/whiteboard.dis | appl/collab/clients/whiteboard.b |  | - |  |
| dis/collab/collabsrv.dis | appl/collab/collabsrv.b |  | - |  |
| dis/collab/connect.dis | appl/collab/connect.b |  | - |  |
| dis/collab/lib/messages.dis | appl/collab/lib/messages.b |  | - |  |
| dis/collab/proxy.dis | appl/collab/proxy.b |  | - |  |
| dis/collab/servers/chatsrv.dis | appl/collab/servers/chatsrv.b |  | - |  |
| dis/collab/servers/memfssrv.dis | appl/collab/servers/memfssrv.b |  | - |  |
| dis/collab/servers/mpx.dis | appl/collab/servers/mpx.b |  | - |  |
| dis/collab/servers/wbsrv.dis | appl/collab/servers/wbsrv.b |  | - |  |
| dis/collab/srvmgr.dis | appl/collab/srvmgr.b |  | - |  |
| dis/dbfs.dis | appl/cmd/dbfs.b |  | - |  |
| dis/dossrv.dis | appl/cmd/dossrv.b |  | - |  |
| dis/ftpfs.dis | appl/cmd/ftpfs.b |  | - |  |
| dis/ip/bootpd.dis | appl/cmd/ip/bootpd.b |  | - |  |
| dis/ip/dhcp.dis | appl/cmd/ip/dhcp.b | module/dhcp.m | - |  |
| dis/ip/nppp/modem.dis | appl/cmd/ip/nppp/modem.b |  | - |  |
| dis/ip/nppp/ppplink.dis | appl/cmd/ip/nppp/ppplink.b |  | - |  |
| dis/ip/nppp/script.dis | appl/cmd/ip/nppp/script.b |  | - |  |
| dis/ip/ping.dis | appl/cmd/ip/ping.b |  | - |  |
| dis/ip/ppp/modem.dis | appl/cmd/ip/ppp/modem.b |  | - |  |
| dis/ip/ppp/pppclient.dis | appl/cmd/ip/ppp/pppclient.b |  | - |  |
| dis/ip/ppp/pppdial.dis | appl/cmd/ip/ppp/pppdial.b |  | - |  |
| dis/ip/ppp/pppgui.dis | appl/cmd/ip/ppp/pppgui.b |  | - |  |
| dis/ip/ppp/ppptest.dis | appl/cmd/ip/ppp/ppptest.b |  | - |  |
| dis/ip/ppp/script.dis | appl/cmd/ip/ppp/script.b |  | - |  |
| dis/ip/rip.dis | appl/cmd/ip/rip.b |  | - |  |
| dis/ip/sntp.dis | appl/cmd/ip/sntp.b |  | - |  |
| dis/ip/tftpd.dis | appl/cmd/ip/tftpd.b |  | - |  |
| dis/ip/virgild.dis | appl/cmd/ip/virgild.b |  | - |  |
| dis/listen.dis | appl/cmd/listen.b |  | - |  |
| dis/lockfs.dis | appl/cmd/lockfs.b |  | - |  |
| dis/memfs.dis | appl/cmd/memfs.b | module/memfs.m | - |  |
| dis/ndb/cs.dis | appl/cmd/ndb/cs.b |  | - |  |
| dis/ndb/dns.dis | appl/cmd/ndb/dns.b |  | - |  |
| dis/ndb/registry.dis | appl/cmd/ndb/registry.b |  | - |  |
| dis/plumber.dis | appl/cmd/plumber.b |  | - |  |
| dis/ramfile.dis | appl/cmd/ramfile.b |  | - |  |
| dis/rawdbfs.dis | appl/cmd/rawdbfs.b |  | - |  |
| dis/spki/verify.dis | appl/cmd/spki/verify.b |  | - |  |
| dis/svc/httpd/alarms.dis | appl/svc/httpd/alarms.b |  | - |  |
| dis/svc/httpd/cache.dis | appl/svc/httpd/cache.b |  | - |  |
| dis/svc/httpd/cgiparse.dis | appl/svc/httpd/cgiparse.b |  | - |  |
| dis/svc/httpd/contents.dis | appl/svc/httpd/contents.b |  | - |  |
| dis/svc/httpd/date.dis | appl/svc/httpd/date.b |  | - |  |
| dis/svc/httpd/echo.dis | appl/svc/httpd/echo.b |  | - |  |
| dis/svc/httpd/httpd.dis | appl/svc/httpd/httpd.b |  | - |  |
| dis/svc/httpd/imagemap.dis | appl/svc/httpd/imagemap.b |  | - |  |
| dis/svc/httpd/parser.dis | appl/svc/httpd/parser.b |  | - |  |
| dis/svc/httpd/redirect.dis | appl/svc/httpd/redirect.b |  | - |  |
| dis/svc/httpd/stats.dis | appl/svc/httpd/stats.b |  | - |  |
| dis/svc/webget/date.dis | appl/svc/webget/date.b |  | - |  |
| dis/svc/webget/file.dis | appl/svc/webget/file.b |  | - |  |
| dis/svc/webget/ftp.dis | appl/svc/webget/ftp.b |  | - |  |
| dis/svc/webget/http.dis | appl/svc/webget/http.b |  | - |  |
| dis/svc/webget/image2enc.dis | appl/svc/webget/image2enc.b |  | - |  |
| dis/svc/webget/message.dis | appl/svc/webget/message.b |  | - |  |
| dis/svc/webget/webget.dis | appl/svc/webget/webget.b | module/webget.m | - |  |
| dis/svc/webget/wgutils.dis | appl/svc/webget/wgutils.b |  | - |  |
| dis/tarfs.dis | appl/cmd/tarfs.b |  | - |  |
| dis/trfs.dis | appl/cmd/trfs.b |  | - |  |
| dis/usb/usbd.dis | appl/cmd/usb/usbd.b |  | - |  |
| dis/vacfs.dis | appl/cmd/vacfs.b |  | - |  |

