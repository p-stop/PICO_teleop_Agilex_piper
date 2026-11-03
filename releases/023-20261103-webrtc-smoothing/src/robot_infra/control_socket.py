"""Dedicated WebSocket input listener; media HTTP cannot fill its connection pool."""
from http import HTTPStatus
import json
import threading
import time
from urllib.parse import urlsplit


class ControlSocketServer:
    def __init__(self,app,host,port,ssl_context,web_port):
        from websockets.sync.server import serve
        from websockets.exceptions import ConnectionClosed
        self.app=app;self.lock=threading.Lock();self.connections=set()
        def handshake(connection,request):
            if request.headers.get('Upgrade','').lower()!='websocket':
                return connection.respond(HTTPStatus.OK,'Robot Infra control input ready. Return to the VR page.\n')
            origin=urlsplit(request.headers.get('Origin',''))
            host_name=urlsplit('https://'+request.headers['Host']).hostname
            if request.path!='/input' or origin.scheme!='https' or origin.hostname!=host_name or origin.port!=web_port:
                return connection.respond(HTTPStatus.FORBIDDEN,'Use the device VR page origin.\n')
        def handler(connection):
            sid=None
            with self.lock:self.connections.add(connection)
            try:
                connection.send(json.dumps({'type':'ready','schema_version':'webxr-control/1','server_s':time.monotonic()}))
                for raw in connection:
                    try:
                        packet=json.loads(raw)
                        began=time.monotonic()
                        result=app.input(packet);sid=packet['session_id']
                        response={'type':'ack','seq':packet['seq'],'result':result,'server_s':time.monotonic(),
                            'server_timing':{'input_ms':(time.monotonic()-began)*1000}}
                    except (ValueError,KeyError,PermissionError) as exc:
                        response={'type':'error','error':str(exc),'server_s':time.monotonic()}
                    connection.send(json.dumps(response,allow_nan=False))
            except ConnectionClosed:pass
            except Exception:
                app.pause('control_socket_failure')
                raise
            finally:
                with self.lock:self.connections.discard(connection)
                if sid and app.session and app.session.viewer==sid:app.pause('control_socket_closed')
        self.server=serve(handler,host,port,ssl=ssl_context,process_request=handshake,compression=None,
                          max_size=65536,max_queue=4,open_timeout=5,close_timeout=1)
        self.port=self.server.socket.getsockname()[1]
        self.thread=threading.Thread(target=self.server.serve_forever,name='xr-control-listener',daemon=True);self.thread.start()

    def close(self):
        self.server.shutdown()
        with self.lock:connections=list(self.connections)
        for connection in connections:connection.close(code=1001,reason='session stopping')
        self.thread.join(timeout=2)
