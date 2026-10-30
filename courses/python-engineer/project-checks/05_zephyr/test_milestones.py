import asyncio
import json


class TestMilestone5:
    def test_middleware_order_and_background_tasks(self):
        from zephyr import Zephyr,BackgroundTasks
        from zephyr.app import TestClient
        app=Zephyr();events=[]
        @app.middleware('http')
        async def record(request,call_next):
            events.append('before');response=await call_next(request);events.append('after');return response
        @app.get('/')
        async def root(background_tasks:BackgroundTasks):
            events.append('handler');background_tasks.add_task(events.append,'background');return {'ok':True}
        assert TestClient(app).get('/').json()=={'ok':True}
        assert events==['before','handler','after','background']

    def test_exception_mro_and_headers(self):
        from zephyr import Zephyr
        from zephyr.app import TestClient
        from zephyr.responses import JSONResponse
        app=Zephyr()
        @app.exception_handler(LookupError)
        async def handle(request,error):return JSONResponse({'error':'missing'},status_code=404)
        @app.get('/')
        async def root():raise KeyError('private detail')
        response=TestClient(app).get('/')
        assert response.status_code==404 and response.json()=={'error':'missing'}


class TestMilestone6:
    def test_openapi_and_local_docs(self):
        from zephyr import Zephyr
        from zephyr.app import TestClient
        app=Zephyr(title='Course')
        @app.get('/items/{item_id}')
        async def item(item_id:int)->dict:return {'id':item_id}
        client=TestClient(app);schema=client.get('/openapi.json').json()
        assert schema['openapi'].startswith('3.1')
        assert '/items/{item_id}' in schema['paths']
        docs=client.get('/docs')
        assert docs.status_code==200 and 'https://' not in docs.text

    def test_websocket_echo(self):
        from zephyr import Zephyr
        from zephyr.app import TestClient
        app=Zephyr()
        @app.websocket('/ws')
        async def echo(ws):
            await ws.accept();text=await ws.receive_text();await ws.send_text(text);await ws.close()
        with TestClient(app).websocket_connect('/ws') as ws:
            ws.send_text('hello');assert ws.receive_text()=='hello'

    def test_static_ranges_and_etag(self,tmp_path):
        from zephyr import Zephyr
        from zephyr.app import TestClient
        from zephyr.staticfiles import StaticFiles
        (tmp_path/'a.txt').write_text('abcdef')
        app=Zephyr();app.mount('/static',StaticFiles(directory=tmp_path));client=TestClient(app)
        response=client.get('/static/a.txt',headers={'Range':'bytes=1-3'})
        assert response.status_code==206 and response.text=='bcd'
        assert response.headers['etag'] and response.headers['last-modified']
