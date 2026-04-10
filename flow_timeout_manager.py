from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()

mac_to_port = {}

def _handle_ConnectionUp(event):
    log.info("Switch %s connected", event.dpid)
    mac_to_port[event.dpid] = {}

def _handle_PacketIn(event):
    packet = event.parsed
    dpid = event.dpid
    in_port = event.port

    if not packet.parsed:
        return

    src = packet.src
    dst = packet.dst

    # Learn MAC address
    mac_to_port[dpid][src] = in_port

    log.info("Packet: %s -> %s", src, dst)

    msg = of.ofp_flow_mod()
    msg.match = of.ofp_match.from_packet(packet, in_port)

    # Decide output port
    if dst in mac_to_port[dpid]:
        out_port = mac_to_port[dpid][dst]
    else:
        out_port = of.OFPP_FLOOD

    msg.actions.append(of.ofp_action_output(port=out_port))

    # Timeouts
    msg.idle_timeout = 10
    msg.hard_timeout = 30
    msg.priority = 10
    msg.flags = of.OFPFF_SEND_FLOW_REM

    # Install flow
    event.connection.send(msg)

    # IMPORTANT: send current packet also
    packet_out = of.ofp_packet_out()
    packet_out.data = event.ofp
    packet_out.in_port = in_port
    packet_out.actions.append(of.ofp_action_output(port=out_port))

    event.connection.send(packet_out)

    log.info("Flow installed (idle=10, hard=30)")

def _handle_FlowRemoved(event):
    reason_map = {
        0: "IDLE TIMEOUT",
        1: "HARD TIMEOUT",
        2: "DELETE",
        3: "GROUP DELETE"
    }

    reason = reason_map.get(event.ofp.reason, str(event.ofp.reason))
    log.info("Flow removed! Reason: %s", reason)

def launch():
    core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp)
    core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
    core.openflow.addListenerByName("FlowRemoved", _handle_FlowRemoved)
    log.info("Flow Timeout Manager started")