
from elasticsearch import Elasticsearch, helpers
import uuid

class ESWriter:
    def __init__(self, host, port, scheme, user, password, index):
        self.index = index

        self.client = Elasticsearch(
            f"{scheme}://{host}:{port}",
            basic_auth=(user, password),
            headers={
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
            },
            verify_certs=False
        )

        if not self.client.ping():
            raise ConnectionError("Cannot connect to Elasticsearch")
        print("✅ Connected to Elasticsearch")


    def _generate_alert_actions(self, alerts):

        for alert in alerts:
            yield {
                "_op_type": "index",
                "_index": self.index,
                "_id": str(uuid.uuid4()),
                "_source": {
                    "content": alert["content"],
                    **alert["metadata"],
                }
            }

    def write_alerts_batch(self, alerts):

        if not alerts:
            return 0
        
        try:
            success_count, errors = helpers.bulk(
                client=self.client,
                actions=self._generate_alert_actions(alerts)
            )
            
            print(f"✅ Wrote {success_count} alerts to {self.index}")
            return success_count

        except helpers.BulkIndexError as e:
            print(f"❌ Bulk indexing failed after some documents. Wrote {e.successes} successfully.")
            print(f"  Encountered {len(e.errors)} errors.")
            return e.successes
