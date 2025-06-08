import logging
from influxdb_client import InfluxDBClient
from elasticsearch import Elasticsearch, ConnectionError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Initializer] - %(message)s'
)

def initialize_sinks(config: dict, bucket_name: str = None, index_name: str = None, index_mapping: dict = None):

    if bucket_name:
        _ensure_influx_bucket(config['influx'], bucket_name)

    if index_name:
        if not index_mapping:
            logging.error(f"Cannot create index '{index_name}' without providing a mapping.")
            return
        _ensure_es_index(config['elasticsearch'], index_name, index_mapping)


def _ensure_influx_bucket(influx_config: dict, bucket_name: str):
    client = None
    try:
        client = InfluxDBClient(
            url=influx_config["url"],
            token=influx_config["token"],
            org=influx_config["org"]
        )
        if not client.ping():
            logging.error("Cannot connect to InfluxDB.")
            return

        logging.info("Successfully connected to InfluxDB.")
        buckets_api = client.buckets_api()

        if buckets_api.find_bucket_by_name(bucket_name):
            logging.info(f"InfluxDB bucket '{bucket_name}' already exists.")
        else:
            logging.warning(f"InfluxDB bucket '{bucket_name}' not found. Creating it...")
            buckets_api.create_bucket(bucket_name=bucket_name, org_id=influx_config["org"])
            logging.info(f"Successfully created InfluxDB bucket '{bucket_name}'.")

    except Exception as e:
        logging.error(f"An error occurred with InfluxDB setup: {e}")
    finally:
        if client:
            client.close()


def _ensure_es_index(es_config: dict, index_name: str, mapping_body: dict):
    """Checks for and creates a single specified Elasticsearch index."""
    es_client = None
    try:
        es_client = Elasticsearch(
            f"{es_config.get('scheme', 'http')}://{es_config['host']}:{es_config['port']}",
            basic_auth=(es_config.get('user'), es_config.get('password')),
            verify_certs=False
        )
        if not es_client.ping():
            raise ConnectionError("Cannot connect to Elasticsearch")

        logging.info("Successfully connected to Elasticsearch.")

        if es_client.indices.exists(index=index_name):
            logging.info(f"Elasticsearch index '{index_name}' already exists.")
        else:
            logging.warning(f"Elasticsearch index '{index_name}' not found. Creating it...")
            es_client.indices.create(index=index_name, mappings=mapping_body)
            logging.info(f"Successfully created Elasticsearch index '{index_name}'.")

    except ConnectionError as e:
        logging.error(e)
    except Exception as e:
        logging.error(f"An error occurred with Elasticsearch setup: {e}")
    finally:
        if es_client:
            es_client.close()