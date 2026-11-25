# 11. Demo - demonstration apps - 6 rows

Owner: Demo (`agy-taijios-dis-app-families`)

Index: [plans/dis-to-zx.md](../dis-to-zx.md)

| Path | Limbo source | Interface | Boot | Notes |
|---|---|---|---|---|
| zx/demo/lego/firmdl.dis | appl/demo/lego/firmdl.b |  | - | restored: ZX port was reduced (packet length/start in decimal, extra zero byte, checksum differed) |
| zx/demo/lego/legolink.dis | appl/demo/lego/legolink.b |  | - | restored: ZX port lost the 250 ms poll empty message, POLLDO, and the 1500 ms re-settle |
| zx/demo/lego/rcxsend.dis | appl/demo/lego/rcxsend.b |  | - | restored with legolink (shared poll loop) |
| zx/demo/lego/timers.dis | appl/demo/lego/timers.b | module/timers.m | - | restored with legolink |
| zx/demo/whiteboard/wbsrv.dis | appl/demo/whiteboard/wbsrv.b |  | - | restored: ZX port inverted CMAP8 (0=black, 255=white) and only saved inside the 9P read loop |
| zx/demo/whiteboard/whiteboard.dis | appl/demo/whiteboard/whiteboard.b |  | - | restored client; runwb.sh now serves /zx/demo/whiteboard/whiteboard.dis |

