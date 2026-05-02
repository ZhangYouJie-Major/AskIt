import importlib
import asyncio
import sys
import types


class FakeCollection:
    def __init__(self):
        self.calls = []
        self.name = "documents"

    def add(self, **kwargs):
        self.calls.append(("add", kwargs))

    def query(self, **kwargs):
        self.calls.append(("query", kwargs))
        return {"ids": [[]], "distances": [[]], "metadatas": [[]]}

    def delete(self, **kwargs):
        self.calls.append(("delete", kwargs))

    def count(self):
        return 0


class FakeChromaModule(types.ModuleType):
    def __init__(self, fail_get_collection=False):
        super().__init__("chromadb")
        self.config = types.ModuleType("chromadb.config")
        self.config.Settings = object
        self.clients = []
        self.collections = []
        self.fail_get_collection = fail_get_collection

    def CloudClient(self, **kwargs):
        client = FakeClient("cloud", kwargs, self)
        self.clients.append(client)
        return client

    def PersistentClient(self, **kwargs):
        client = FakeClient("local", kwargs, self)
        self.clients.append(client)
        return client

    def Client(self, **kwargs):
        client = FakeClient("legacy", kwargs, self)
        self.clients.append(client)
        return client


class FakeClient:
    def __init__(self, mode, kwargs, module):
        self.mode = mode
        self.kwargs = kwargs
        self.module = module
        self.calls = []

    def get_collection(self, **kwargs):
        self.calls.append(("get_collection", kwargs))
        if self.module.fail_get_collection:
            self.module.fail_get_collection = False
            raise RuntimeError("missing collection")
        collection = FakeCollection()
        self.module.collections.append(collection)
        return collection

    def create_collection(self, **kwargs):
        self.calls.append(("create_collection", kwargs))
        collection = FakeCollection()
        self.module.collections.append(collection)
        return collection

    def delete_collection(self, **kwargs):
        self.calls.append(("delete_collection", kwargs))


def import_vector_store(monkeypatch, fail_get_collection=False, **env):
    fake_chromadb = FakeChromaModule(fail_get_collection=fail_get_collection)
    monkeypatch.setitem(sys.modules, "chromadb", fake_chromadb)
    monkeypatch.setitem(sys.modules, "chromadb.config", fake_chromadb.config)

    for key, value in env.items():
        monkeypatch.setenv(key, value)

    for module_name in [
        "app.core.config",
        "app.services.vector_store",
    ]:
        sys.modules.pop(module_name, None)

    module = importlib.import_module("app.services.vector_store")
    return module, fake_chromadb


def import_document_tasks_fresh():
    for module_name in [
        "app.tasks.celery_worker",
        "app.tasks.document_tasks",
        "app.tasks",
    ]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("app.tasks.document_tasks")


def test_cloud_mode_uses_chroma_cloud_client_from_settings(monkeypatch):
    module, fake_chromadb = import_vector_store(
        monkeypatch,
        CHROMA_MODE="cloud",
        CHROMA_API_KEY="cloud-key",
        CHROMA_TENANT="cloud-tenant",
        CHROMA_DATABASE="cloud-db",
    )

    assert fake_chromadb.clients[0].mode == "cloud"
    assert fake_chromadb.clients[0].kwargs == {
        "api_key": "cloud-key",
        "tenant": "cloud-tenant",
        "database": "cloud-db",
    }

    store = module.VectorStore()
    assert store.client.mode == "cloud"


def test_cloud_collection_operations_do_not_pass_tenant_or_database(monkeypatch):
    module, _fake_chromadb = import_vector_store(
        monkeypatch,
        CHROMA_MODE="cloud",
        CHROMA_API_KEY="cloud-key",
        CHROMA_TENANT="cloud-tenant",
        CHROMA_DATABASE="cloud-db",
    )
    store = module.VectorStore()

    async def run_operations():
        await store.init_collection()
        await store.insert_points(["doc-1"], [[0.1]], [{"document_id": 1}])
        await store.search([0.1])
        await store.delete_points(["doc-1"])
        await store.reset_collection()

    asyncio.run(run_operations())

    collection_call_kwargs = [
        kwargs
        for collection in _fake_chromadb.collections
        for _name, kwargs in collection.calls
    ]
    client_call_kwargs = [kwargs for _name, kwargs in store.client.calls]

    for kwargs in collection_call_kwargs + client_call_kwargs:
        assert "tenant" not in kwargs
        assert "database" not in kwargs


def test_cloud_init_collection_create_fallback_omits_tenant_and_database(monkeypatch):
    module, _fake_chromadb = import_vector_store(
        monkeypatch,
        fail_get_collection=True,
        CHROMA_MODE="cloud",
        CHROMA_API_KEY="cloud-key",
        CHROMA_TENANT="cloud-tenant",
        CHROMA_DATABASE="cloud-db",
    )
    store = module.VectorStore()

    asyncio.run(store.init_collection())

    assert [name for name, _kwargs in store.client.calls] == [
        "get_collection",
        "create_collection",
    ]
    for _name, kwargs in store.client.calls:
        assert "tenant" not in kwargs
        assert "database" not in kwargs


def test_local_mode_uses_chroma_persistent_client(monkeypatch, tmp_path):
    module, fake_chromadb = import_vector_store(
        monkeypatch,
        CHROMA_MODE="local",
        CHROMA_PERSIST_DIRECTORY=str(tmp_path),
    )

    assert fake_chromadb.clients[0].mode == "local"
    assert fake_chromadb.clients[0].kwargs == {"path": str(tmp_path)}

    store = module.VectorStore()
    assert store.client.mode == "local"


def test_document_tasks_importable_with_local_chroma_and_exposes_process_document(
    monkeypatch,
    tmp_path,
):
    import_vector_store(
        monkeypatch,
        CHROMA_MODE="local",
        CHROMA_PERSIST_DIRECTORY=str(tmp_path),
    )
    module = import_document_tasks_fresh()

    assert hasattr(module, "process_document")


def test_process_document_uses_temporary_processor_and_returns_task_payload(
    monkeypatch,
    tmp_path,
):
    import_vector_store(
        monkeypatch,
        CHROMA_MODE="local",
        CHROMA_PERSIST_DIRECTORY=str(tmp_path),
    )
    module = import_document_tasks_fresh()

    class FakeSession:
        async def __aenter__(self):
            return "db-session"

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    class FakeResult:
        document_id = 42
        chunk_count = 3
        status = "completed"
        error_message = None

    class FakeProcessor:
        def __init__(self, db):
            self.db = db

        async def process(self, document_id):
            assert self.db == "db-session"
            assert document_id == 42
            return FakeResult()

    from app.core import database
    from app.services import document_processor

    monkeypatch.setattr(database, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(document_processor, "DocumentProcessingService", FakeProcessor)

    assert module.process_document.run(42) == {
        "document_id": 42,
        "chunk_count": 3,
        "status": "completed",
        "error_message": None,
    }


def test_process_document_reuses_worker_event_loop(monkeypatch, tmp_path):
    import_vector_store(
        monkeypatch,
        CHROMA_MODE="local",
        CHROMA_PERSIST_DIRECTORY=str(tmp_path),
    )
    module = import_document_tasks_fresh()

    class FakeSession:
        async def __aenter__(self):
            return "db-session"

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    class FakeResult:
        document_id = 42
        chunk_count = 0
        status = "completed"
        error_message = None

    seen_loop_ids = []

    class FakeProcessor:
        def __init__(self, db):
            self.db = db

        async def process(self, document_id):
            seen_loop_ids.append(id(asyncio.get_running_loop()))
            return FakeResult()

    from app.core import database
    from app.services import document_processor

    monkeypatch.setattr(database, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(document_processor, "DocumentProcessingService", FakeProcessor)

    def forbidden_asyncio_run(coro):
        coro.close()
        raise AssertionError("process_document should reuse the worker task loop")

    monkeypatch.setattr(module.asyncio, "run", forbidden_asyncio_run)

    module.process_document.run(42)
    module.process_document.run(42)

    assert len(seen_loop_ids) == 2
    assert seen_loop_ids[0] == seen_loop_ids[1]


def test_batch_process_documents_queues_process_document_with_new_signature(
    monkeypatch,
    tmp_path,
):
    import_vector_store(
        monkeypatch,
        CHROMA_MODE="local",
        CHROMA_PERSIST_DIRECTORY=str(tmp_path),
    )
    module = import_document_tasks_fresh()
    queued_args = []

    class FakeAsyncResult:
        def __init__(self, task_id):
            self.id = task_id

    def fake_delay(document_id):
        queued_args.append((document_id,))
        return FakeAsyncResult(f"task-{document_id}")

    monkeypatch.setattr(module.process_document, "delay", fake_delay)

    assert module.batch_process_documents.run([10, 20]) == ["task-10", "task-20"]
    assert queued_args == [(10,), (20,)]
