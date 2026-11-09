"""Real local UDP/DTLS/SCTP round trip; never imports a hardware backend."""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest

pytest.importorskip('aiortc')
from aiortc import RTCConfiguration, RTCPeerConnection
from robot_infra.control_webrtc import WebRTCInputServer


def test_ordered_existing_packets_error_disconnect_and_cleanup():
    class App:
        session=SimpleNamespace(viewer=None)
        def __init__(self):self.calls=[];self.pauses=[];self.order=[]
        def input(self, packet):
            if packet['seq'] < 0:raise ValueError('reordered input')
            time.sleep(.01)  # Simulated work must not block the network loop.
            self.calls.append(packet);self.session.viewer=packet['session_id']
            self.order.append('input')
            return {'accepted':True}
        def pause(self, reason):self.pauses.append(reason);self.order.append('pause')
    app=App();server=WebRTCInputServer(app)

    async def scenario():
        pc=RTCPeerConnection(RTCConfiguration(iceServers=[]))
        dc=pc.createDataChannel('robot-input', ordered=True)
        replies=asyncio.Queue()
        dc.on('message',lambda raw:replies.put_nowait(json.loads(raw)))
        try:
            await pc.setLocalDescription(await pc.createOffer())
            answer=await asyncio.to_thread(server.offer,{'type':pc.localDescription.type,'sdp':pc.localDescription.sdp})
            from aiortc import RTCSessionDescription
            await pc.setRemoteDescription(RTCSessionDescription(**answer))
            assert (await asyncio.wait_for(replies.get(),5))['type']=='ready'
            packets=[{'schema_version':'webxr-input/1','session_id':'test','seq':i,'A':i%2} for i in range(8)]
            for packet in packets:dc.send(json.dumps(packet))  # No per-packet ACK gate.
            for i in range(8):
                reply=await asyncio.wait_for(replies.get(),5)
                assert reply['type']=='ack' and reply['seq']==i
            assert app.calls==packets
            dc.send(json.dumps({'seq':-1}))
            assert (await asyncio.wait_for(replies.get(),5))['type']=='error'
            dc.send('[]')
            assert (await asyncio.wait_for(replies.get(),5))['type']=='error'
            # Closing during application work must put pause AFTER that work,
            # rather than letting an already running input overwrite the stop.
            dc.send(json.dumps({'session_id':'test','seq':8}))
            await asyncio.sleep(.002)
        finally:await pc.close()
        for _ in range(100):
            if app.pauses:break
            await asyncio.sleep(.01)
        assert len(app.pauses)==1
        await asyncio.sleep(.03)
        assert app.order[-1]=='pause'
    try:asyncio.run(scenario())
    finally:server.close()
    assert not server.thread.is_alive()


def test_invalid_offer_does_not_reserve_a_peer():
    server=WebRTCInputServer(SimpleNamespace())
    try:
        for body in ([],{}, {'type':'answer','sdp':'x'}, {'type':'offer','sdp':'x'*60001}):
            with pytest.raises(ValueError):server.offer(body)
        with pytest.raises(ValueError):server.offer({'type':'offer','sdp':'invalid'})
        assert server.peer is None
    finally:server.close()


def test_new_page_takes_over_stale_connection():
    """A second page replaces the first: pause first, then the old channel is closed."""
    class App:
        session=SimpleNamespace(viewer=None)
        def __init__(self):self.pauses=[]
        def input(self, packet):
            self.session.viewer=packet['session_id'];return {'accepted':True}
        def pause(self, reason):self.pauses.append(reason)
    app=App();server=WebRTCInputServer(app)
    from aiortc import RTCSessionDescription

    async def connect():
        pc=RTCPeerConnection(RTCConfiguration(iceServers=[]))
        dc=pc.createDataChannel('robot-input', ordered=True)
        replies=asyncio.Queue();closed=asyncio.Event()
        dc.on('message',lambda raw:replies.put_nowait(json.loads(raw)))
        dc.on('close',closed.set)
        await pc.setLocalDescription(await pc.createOffer())
        answer=await asyncio.to_thread(server.offer,{'type':pc.localDescription.type,'sdp':pc.localDescription.sdp})
        await pc.setRemoteDescription(RTCSessionDescription(**answer))
        assert (await asyncio.wait_for(replies.get(),5))['type']=='ready'
        return pc,dc,replies,closed

    async def scenario():
        pc1,dc1,replies1,closed1=await connect()
        pc2=None
        try:
            dc1.send(json.dumps({'session_id':'old','seq':0}))
            assert (await asyncio.wait_for(replies1.get(),5))['type']=='ack'
            pc2,dc2,replies2,_=await connect()
            assert app.pauses[0]=='webrtc_replaced'
            await asyncio.wait_for(closed1.wait(),5)
            app.session.viewer=None
            dc2.send(json.dumps({'session_id':'new','seq':0}))
            assert (await asyncio.wait_for(replies2.get(),5))['type']=='ack'
        finally:
            await pc1.close()
            if pc2:await pc2.close()
    try:asyncio.run(scenario())
    finally:server.close()
    assert not server.thread.is_alive()
