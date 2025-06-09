from elasticsearch import Elasticsearch, helpers
import uuid

from .schema import DailyReport
from .my_logger import get_logger

logger = get_logger(__name__)

class ESWriter:
    def __init__(self, host, port, scheme, user, password, index):
        self.index = index
        try:
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
                raise ConnectionError("Cannot connect to Elasticsearch: Ping failed.")
            logger.info(f"Elasticsearch client initialized and connected to index '{self.index}'.")

        except Exception as e:
            logger.error("Failed to initialize Elasticsearch client.", exc_info=True)
            raise e


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
            logger.debug("Attempted to write an empty list of alerts. No action taken.")
            return 0
        
        try:
            success_count, errors = helpers.bulk(
                client=self.client,
                actions=self._generate_alert_actions(alerts),
                raise_on_error=True, 
                raise_on_exception=True
            )
            
            logger.info(f"Successfully wrote {success_count} alerts to index '{self.index}'.")
            if errors:
                logger.warning(f"Some documents failed during bulk insert: {errors}")
            return success_count

        except helpers.BulkIndexError as e:
            logger.error(f"Bulk indexing failed for {len(e.errors)} documents. Wrote {e.successes} successfully to '{self.index}'.")
            return e.successes
        except Exception as e:
            logger.error(f"An Elasticsearch error occurred during bulk write to '{self.index}'.", exc_info=True)
            return 0

    # def write_report(self, report: DailyReport):
    #     """Writes a single daily report document to Elasticsearch."""
    #     try:
    #         report_dict = report.model_dump(mode="json")
    #         report_id = report.timestamp

    #         self.client.index(
    #             index=self.index,
    #             id=report_id,
    #             document=report_dict
    #         )
    #         logger.info(f"Successfully wrote daily report for '{report_id}' to index '{self.index}'.")
    #     except Exception as e:
    #         logger.error(f"Failed to write daily report for '{report.date}' to index '{self.index}'.", exc_info=True)
    #         raise
    def write_report(self, report: DailyReport):
        """Writes one flattened document per host in the daily report."""
        try:
            for host, host_data in report.host_reports.items():
                flat_doc = {
                    "timestamp": report.timestamp,
                    "host": host,
                    "avg_cpu": host_data.avg_cpu,
                    "avg_mem": host_data.avg_mem,
                    "avg_disk": host_data.avg_disk,
                    "stddev_cpu": host_data.stddev_cpu,
                    "stddev_mem": host_data.stddev_mem,
                    "stddev_disk": host_data.stddev_disk,
                    "max_cpu": host_data.max_cpu,
                    "max_mem": host_data.max_mem,
                    "max_disk": host_data.max_disk,
                }
                doc_id = f"{report.timestamp}_{host}"
                self.client.index(
                    index=self.index,
                    id=doc_id,
                    document=flat_doc
                )
            logger.info(f"✅ Flattened daily report written to index '{self.index}'")
        except Exception as e:
            logger.error("❌ Failed to write flattened daily report", exc_info=True)
            raise
