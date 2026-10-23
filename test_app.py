import unittest, tempfile, json
from pathlib import Path
from app import Queue, signature

import uuid


class Scratch:
    def __init__(self):
        self.path = Path(__file__).parent / ".test-tmp" / uuid.uuid4().hex
        self.path.mkdir(parents=True)
        self.name = str(self.path)

    def cleanup(self):
        for file in self.path.iterdir():
            if file.is_file():
                file.unlink()
        self.path.rmdir()


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Scratch()
        self.q = Queue(Path(self.tmp.name) / "q.sqlite")
        self.secret = "a-long-test-secret"
        self.body = json.dumps({"id": "1", "timestamp": 1000, "data": {}}).encode()

    def tearDown(self):
        self.q.close()
        self.tmp.cleanup()

    def ingest(self):
        return self.q.ingest(self.body, signature(self.body, self.secret), self.secret, 1000)

    def test_signature_rejected(self):
        with self.assertRaises(ValueError):
            self.q.ingest(self.body, "bad", self.secret, 1000)

    def test_replay_deduplication(self):
        self.assertEqual(self.ingest(), "accepted")
        self.assertEqual(self.ingest(), "duplicate")
        self.assertEqual(len(self.q.rows()), 1)

    def test_old_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            self.q.ingest(self.body, signature(self.body, self.secret), self.secret, 2000)

    def test_success_delivered_once(self):
        calls = []
        self.ingest()
        self.q.run_due(lambda e, k: calls.append(k), 1000)
        self.q.run_due(lambda e, k: calls.append(k), 2000)
        self.assertEqual(calls, ["1"])

    def test_backoff_and_dead_letter(self):
        def fail(e, k):
            raise RuntimeError("secret should not appear in logs")

        self.ingest()
        self.q.run_due(fail, 1000)
        self.assertEqual(self.q.run_due(fail, 1001), 0)
        self.q.run_due(fail, 1002)
        self.q.run_due(fail, 1006)
        r = self.q.rows()[0]
        self.assertEqual(r["status"], "dead_letter")
        self.assertEqual(r["attempts"], 3)
        self.assertNotIn("secret", r["last_error"])

    def test_retry_then_success(self):
        def fail(e, k):
            raise RuntimeError()

        self.ingest()
        self.q.run_due(fail, 1000)
        self.q.run_due(lambda e, k: None, 1002)
        self.assertEqual(self.q.rows()[0]["status"], "delivered")

    def test_persists_after_reopen(self):
        self.ingest()
        self.q.close()
        self.q = Queue(Path(self.tmp.name) / "q.sqlite")
        self.assertEqual(len(self.q.rows()), 1)

    def test_oversized_event_rejected(self):
        with self.assertRaises(ValueError):
            self.q.ingest(b"x" * 100001, "", self.secret, 1000)


if __name__ == "__main__":
    unittest.main()
