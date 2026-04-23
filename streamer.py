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
        
        if not symbol or not price:
            return

        for rule in self.rules:
            if rule['symbol'] != symbol:
                continue

            upper = rule.get('upperLimit')
            lower = rule.get('lowerLimit')

            should_alert = False
            reason = ""

            if upper is not None and price >= upper:
                should_alert = True
                reason = f"Vượt chặn trên ({upper})"
            elif lower is not None and price <= lower:
                should_alert = True
                reason = f"Thủng chặn dưới ({lower})"

            if should_alert:
                await self.trigger_alert(rule['id'], price, reason)

    async def trigger_alert(self, record_id, current_price, reason):
        logger.info(f"Triggering alert for {record_id} at {current_price}: {reason}")
        try:
            async with aiohttp.ClientSession() as session:
                await session.post("http://127.0.0.1:3000/alerts/trigger", json={
                    "recordId": record_id,
                    "currentPrice": current_price,
                    "reason": reason
                })
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
