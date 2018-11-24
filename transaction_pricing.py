import events
import json
import datetime
import database


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

    def get_blocks_since(self, epoch):
        selected_events = self.node_update_event.get_events_since(epoch)
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


if __name__ == "__main__":
    epoch = datetime.datetime() - datetime.timedelta(hours=24)
    db = database.Database()

