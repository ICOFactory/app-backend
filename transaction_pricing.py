import events
import json
import datetime
import database
import time
from events import NodeUpdateEvent

# in minutes
CACHE_TIME = 8
MOVING_AVERAGE_WINDOW = 100


class BlockData:
    def __init__(self, block_hash, block_data):
        self.block_hash = block_hash
        self.size = block_data["block_size"]
        self.number = block_data["block_number"]
        self.gas_used = block_data["gas_used"]
        self.gas_limit = block_data["gas_limit"]
        self.timestamp = datetime.datetime.utcfromtimestamp(block_data["timestamp"])
        self.transaction_count = block_data["tx_count"]
        self.gas_price = block_data["gas_price"]


class BlockInfo:
    def __init__(self, db, logger=None):
        self.logger = logger
        self.db = db
        self.node_update_event = events.Event("Ethereum Node Update", db, logger=logger)

    def get_blocks_since(self, epoch, node_id=None):
        if node_id:
            selected_events = self.node_update_event.get_events_since(epoch)
        else:
            selected_events = self.node_update_event.get_events_since(epoch,user_id=node_id)
        blocks = {}
        block_objects = []
        for each_event in selected_events:
            event_data = json.loads(each_event[0])
            if event_data["synchronized"]:
                latest_block_hash = event_data["latest_block_hash"]
                if latest_block_hash not in blocks:
                    block_data = {"block_size": event_data["latest_block_size"],
                                  "block_number": event_data["latest_block_number"],
                                  "gas_used": event_data["latest_block_gas_used"],
                                  "gas_limit": event_data["latest_block_gas_limit"],
                                  "timestamp": event_data["latest_block_timestamp"],
                                  "tx_count": event_data["latest_block_transaction_count"],
                                  "gas_price": event_data["gas_price"]}
                    block_objects.append(BlockData(latest_block_hash, block_data))
                sorted_block_data = sorted(block_data, key=lambda block: block.block.number)
        return sorted_block_data

    def _calculate_secondary_graphs(self, db, logger=None):
        self.db = db
        self.logger = logger
        erc20_node_update = NodeUpdateEvent(db, logger=logger)
        eth_nodes = db.list_ethereum_nodes()
        all_events = []
        metrics = {
            "moving_average": {},
            "London": {},
            "Amsterdam": {},
            "Dallas": {},
        }

        for node in eth_nodes:
            metrics[node["node_identifier"]] = []
            node_events = erc20_node_update.get_events_since(epoch)
            for each in node_events:
                if each.synchronized:
                    if each.node_id == node["id"]:
                        metrics[node["node_identifier"]].append(each.gas_price)
                    all_events.append(each)
        synchronized_events = list(filter(lambda event_obj: event_obj.synchronized, all_events))
        sorted(synchronized_events, key=lambda event_data: event_data.latest_block_timestamp)
        for x in range(0, (len(synchronized_events) - MOVING_AVERAGE_WINDOW)):
            moving_average_window = synchronized_events[x:x + MOVING_AVERAGE_WINDOW]
            gas_price_window = map(lambda event_data: event_data.gas_price, moving_average_window)
            moving_average = float(sum(gas_price_window)) / float(MOVING_AVERAGE_WINDOW)
            metrics["moving_average"]["gas_price"].append(moving_average)

        return metrics

    def _calculate_main_graphs(self, db, logger=None):
        self.db = db
        self.logger = logger
        erc20_node_update = NodeUpdateEvent(db, logger=logger)
        eth_nodes = db.list_ethereum_nodes()
        all_events = []
        metrics = {
            "moving_average": {"gas_price": []},
            "London": {"gas_price": []},
            "Amsterdam": {"gas_price": []},
            "Dallas": {"gas_price": []}
        }
        epoch = datetime.timedelta(hours=24)
        for node in eth_nodes:
            node_identifier = node["node_identifier"]
            metrics[node_identifier] = []
            node_events = erc20_node_update.get_events_since(epoch)
            for each in node_events:
                if each.synchronized:
                    if each.node_id == node["id"]:
                        try:
                            metrics[node_identifier]["gas_price"].append(each.gas_price)
                        except TypeError:
                            pass
                    all_events.append(each)
        synchronized_events = list(filter(lambda event_obj: event_obj.synchronized, all_events))
        sorted(synchronized_events, key=lambda event_data: event_data.latest_block_timestamp)
        for x in range(0, (len(synchronized_events) - MOVING_AVERAGE_WINDOW)):
            moving_average_window = synchronized_events[x:x + MOVING_AVERAGE_WINDOW]
            gas_price_window = map(lambda event_data: event_data.gas_price, moving_average_window)
            moving_average = float(sum(gas_price_window)) / float(MOVING_AVERAGE_WINDOW)
            metrics["moving_average"]["gas_price"].append(moving_average)

        return metrics

    def calculate_main_graphs(self):
        metrics = self._calculate_main_graphs(db, logger=self.logger)
        return metrics


if __name__ == "__main__":
    epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
    db = database.Database()
    uncached_start = time.time()
    block_info = BlockInfo(db, None)
    metrics = block_info.calculate_main_graphs()
    uncached_end = time.time()
    uncached_elapsed = uncached_end - uncached_start
    print("Elapsed uncached main graphs call: {0}".format(uncached_elapsed))
    cached_start = time.time()
    metrics = block_info.calculate_main_graphs()
    cached_end = time.time()
    uncached_elapsed = uncached_end -uncached_start
    print("Cached main graphs call: {0}".format(uncached_elapsed))
