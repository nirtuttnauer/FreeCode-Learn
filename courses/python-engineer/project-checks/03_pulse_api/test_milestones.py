import asyncio
import pytest


class TestMilestone2:
    @pytest.mark.parametrize('backend',['memory','sqlite'])
    def test_repository_roundtrip_duplicate_and_transaction(self,backend,tmp_path):
        from pulse.repositories import MemoryLinkRepository,SQLiteLinkRepository
        from pulse.domain import ShortLink,ShortCode,Url,CodeTaken
        from datetime import datetime,timezone
        async def scenario():
            repo=MemoryLinkRepository() if backend=='memory' else SQLiteLinkRepository(tmp_path/'links.db')
            link=ShortLink(code=ShortCode('abc123'),target=Url('https://example.com'),owner_id='owner',created_at=datetime(2026,1,1,tzinfo=timezone.utc))
            await repo.add(link)
            assert (await repo.get('abc123')).target==link.target
            with pytest.raises(CodeTaken):await repo.add(link)
            with pytest.raises(RuntimeError):
                async with repo.transaction():
                    await repo.delete('abc123')
                    raise RuntimeError('rollback')
            assert await repo.get('abc123') is not None
            if backend=='sqlite':
                reopened=SQLiteLinkRepository(tmp_path/'links.db')
                assert (await reopened.get('abc123')).target==link.target
        asyncio.run(scenario())


class TestMilestone3:
    def test_services_create_resolve_and_enforce_quota(self):
        from pulse.services import ShortenerService
        from pulse.repositories import MemoryLinkRepository,MemoryClickRepository
        from pulse.domain import QuotaExceeded,LinkNotFound
        from datetime import datetime,timezone
        import random
        async def scenario():
            links,clicks=MemoryLinkRepository(),MemoryClickRepository();events=[]
            service=ShortenerService(links=links,clicks=clicks,clock=lambda:datetime(2026,1,1,tzinfo=timezone.utc),rng=random.Random(7),bus=events.append,quota=1)
            link=await service.create('https://example.com','owner')
            assert str(await service.resolve(str(link.code)))=='https://example.com'
            with pytest.raises(QuotaExceeded):await service.create('https://other.example','owner')
            with pytest.raises(LinkNotFound):await service.resolve('zzzzzz')
            assert len(events)==1
        asyncio.run(scenario())


class TestMilestone4:
    def test_http_contract(self):
        from pulse.app import create_app
        from fastapi.testclient import TestClient
        client=TestClient(create_app(testing=True))
        assert client.get('/health').status_code==200
        assert client.post('/api/links',json={'target':'https://example.com'}).status_code==401
        headers={'X-API-Key':'course-test-key'}
        response=client.post('/api/links',json={'target':'https://example.com'},headers=headers)
        assert response.status_code==201 and response.headers['location']
        code=response.json()['code']
        redirect=client.get('/'+code,follow_redirects=False)
        assert redirect.status_code==307 and redirect.headers['location']=='https://example.com'
        assert redirect.headers['etag'] and redirect.headers['cache-control']
        assert client.get('/api/links',headers=headers).status_code==200
        assert client.delete('/api/links/'+code,headers=headers).status_code==204


class TestMilestone5:
    def test_html_escape_content_negotiation_and_csrf(self):
        from pulse.app import create_app
        from fastapi.testclient import TestClient
        client=TestClient(create_app(testing=True))
        page=client.get('/',headers={'Accept':'text/html'})
        assert page.status_code==200 and 'text/html' in page.headers['content-type']
        assert 'csrf' in page.text.lower()
        assert client.post('/links',data={'target':'https://example.com'}).status_code==403
        from pulse.templates import environment
        env=environment()
        assert env.from_string('{{ value }}').render(value='<script>')=='&lt;script&gt;'
        with pytest.raises(Exception): env.from_string('{{ missing }}').render()


class TestMilestone6:
    def test_settings_and_safe_logs(self):
        from pulse.operations import Settings,format_log
        with pytest.raises(ValueError): Settings(dsn='')
        log=format_log({'message':'request','api_key':'secret','trace_id':'abc'})
        assert 'secret' not in log and 'abc' in log

    def test_lifespan_closes_owned_resources(self):
        from pulse.app import create_app
        from fastapi.testclient import TestClient
        app=create_app(testing=True)
        with TestClient(app) as client:
            assert client.get('/ready').status_code==200
            pool=app.state.pool
        assert pool.closed is True
