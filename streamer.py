import asyncio
import aiohttp
import logging
from vnstock_pipeline.stream import WSSClient
from vnstock_pipeline.stream.processors import DataProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlertStreamer")

class AlertProcessor(DataProcessor):
    def __init__(self):
        super().__init__()
        self.rules = []

    def update_rules(self, new_rules):
        self.rules = new_rules
        logger.info(f"Updated rules, active count: {len(self.rules)}")

    async def process(self, data):
        symbol = data.get('symbol')
        price = data.get('price') or data.get('close_price') or data.get('closePrice')
        
        if not price:
            price = data.get('referencePrice') or data.get('reference_price') or data.get('refPrice')

        if not symbol or not price:
            return
            
        price = price / 1000

        for rule in self.rules:
            if rule['symbol'] != symbol:
                continue

            condition = rule.get('condition')
            target = rule.get('targetPrice')
            offsets = rule.get('offsets', [])
            
            if target is None or not condition:
                continue
                
            best_offset = None

            if condition == '>=':
                # highest target first
                sorted_offsets = sorted(offsets, reverse=True)
                for off in sorted_offsets:
                    if price >= target * (1 + off / 100):
                        best_offset = off
                        break
            else: # '<='
                # lowest target first
                sorted_offsets = sorted(offsets)
                for off in sorted_offsets:
                    if price <= target * (1 + off / 100):
                        best_offset = off
                        break
                        
            if best_offset is not None:
                reason = "Streamer trigger"
                await self.trigger_alert(rule['id'], price, reason, best_offset)

    async def trigger_alert(self, record_id, current_price, reason, offset_triggered=None):
        logger.info(f"Triggering alert for {record_id} at {current_price} (offset {offset_triggered})")
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "recordId": record_id,
                    "currentPrice": current_price,
                    "reason": reason
                }
                if offset_triggered is not None:
                    payload["offsetTriggered"] = offset_triggered
                    
                await session.post("http://127.0.0.1:3000/alerts/trigger", json=payload)
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")

class AppStreamer:
    def __init__(self):
        self.client = WSSClient()
        self.processor = AlertProcessor()
        self.client.add_processor(self.processor)
        self.symbols = set()
        self.running = False

    async def update_loop(self):
        async with aiohttp.ClientSession() as session:
            while self.running:
                try:
                    async with session.get("http://127.0.0.1:3000/alerts/rules") as resp:
                        if resp.status == 200:
                            rules = await resp.json()
                            self.processor.update_rules(rules)
                            
                            new_symbols = set([r['symbol'] for r in rules])
                            if new_symbols != self.symbols:
                                logger.info(f"Symbols changed from {self.symbols} to {new_symbols}")
                                self.symbols = new_symbols
                                if self.symbols:
                                    self.client.subscribe_symbols(list(self.symbols))
                except Exception as e:
                    logger.error(f"Error fetching rules: {e}")
                
                await asyncio.sleep(30)

    async def start(self):
        self.running = True
        asyncio.create_task(self.update_loop())
        try:
            await self.client.connect()
        except Exception as e:
            logger.error(f"Streamer disconnected: {e}")
