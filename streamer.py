import asyncio
import aiohttp
import logging
import os
from datetime import datetime
from vnstock_pipeline.stream import WSSClient
from vnstock_pipeline.stream.processors import DataProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlertStreamer")

class AlertProcessor(DataProcessor):
    def __init__(self):
        super().__init__()
        self.rules = []
        self.state = {}

    def update_rules(self, new_rules):
        self.rules = new_rules
        new_state = {}
        for rule in new_rules:
            rule_id = rule['id']
            triggered_state = rule.get('triggeredState') or {}
            # Sync lastOffset từ database state
            new_state[rule_id] = triggered_state.get('lastOffset')
        self.state = new_state
        logger.info(f"Updated rules, active count: {len(self.rules)}")

    async def process(self, data):
        symbol = data.get('symbol')
        price = data.get('last_price') or data.get('price') or data.get('close_price') or data.get('closePrice')

        if not price:
            price = data.get('reference_price') or data.get('referencePrice') or data.get('refPrice')

        if not symbol or not price:
            return

        try:
            # WebSocket data from VPS already comes in thousands (nghìn đồng)
            # e.g. lastPrice=25.5 means 25,500 VND — do NOT divide by 1000
            price = float(price)
        except (TypeError, ValueError):
            return

        # Get reference price for alert messages (also in nghìn đồng from WebSocket)
        ref_price = None
        ref_raw = data.get('reference_price') or data.get('referencePrice') or data.get('refPrice')
        if ref_raw:
            try:
                ref_price = float(ref_raw)
            except (TypeError, ValueError):
                pass

        for rule in self.rules:
            if rule['symbol'] != symbol:
                continue

            try:
                rule_id = rule['id']
                condition = rule.get('condition')
                target = rule.get('targetPrice')
                offsets = rule.get('offsets', [])

                if target is None or not condition:
                    continue

                try:
                    target = float(target)
                except (TypeError, ValueError):
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

                last_offset = self.state.get(rule_id)

                if best_offset != last_offset:
                    if best_offset is not None:
                        reason = "Streamer trigger"
                        await self.trigger_alert(rule_id, price, reason, best_offset, ref_price)
                    else:
                        await self.clear_alert(rule_id)
                    self.state[rule_id] = best_offset
            except Exception as e:
                logger.error(f"Error processing rule {rule.get('id')}: {e}")

    async def clear_alert(self, record_id):
        logger.info(f"Clearing alert state for {record_id}")
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"recordId": record_id}
                headers = self._get_internal_headers()
                await session.post("http://127.0.0.1:3000/alerts/clear", json=payload, headers=headers)
        except Exception as e:
            logger.error(f"Failed to clear alert state: {e}")

    async def trigger_alert(self, record_id, current_price, reason, offset_triggered=None, reference_price=None):
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
                if reference_price is not None:
                    payload["referencePrice"] = reference_price
                    
                headers = self._get_internal_headers()
                await session.post("http://127.0.0.1:3000/alerts/trigger", json=payload, headers=headers)
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")

    @staticmethod
    def _get_internal_headers():
        api_key = os.environ.get("INTERNAL_API_KEY")
        if api_key:
            return {"X-API-Key": api_key}
        return {}

class PatchedWSSClient(WSSClient):
    def subscribe_symbols(self, symbols):
        self.clear_raw_messages()
        symbol_str = ','.join(symbols)
        msg = f'42["regs","{{\\"action\\":\\"join\\",\\"list\\":\\"{symbol_str}\\"}}"]'
        self.add_raw_message(msg)
        logger.info(f"Added subscription for symbols: {symbol_str}")
        if self.is_connected():
            asyncio.create_task(self.send_message(msg))

class AppStreamer:
    def __init__(self):
        self.client = PatchedWSSClient()
        self.processor = AlertProcessor()
        self.client.add_processor(self.processor)
        self.symbols = set()
        self.running = False
        self.is_healthy = False
        self.connected_since = None
        self.refresh_event = asyncio.Event()

    def force_refresh(self):
        """Signal the update loop to refresh rules immediately."""
        self.refresh_event.set()
        logger.info("Force refresh triggered")

    def _is_trading_time(self):
        """Check if current time is within Vietnam stock market trading hours."""
        try:
            from vnstock_pipeline.stream.utils.market_hours import trading_hours
            status = trading_hours(self.client.market)
            return status.get('is_trading_hour', False)
        except Exception:
            # Fallback: manual check for Vietnam market hours (UTC+7)
            from datetime import timezone, timedelta
            vn_tz = timezone(timedelta(hours=7))
            now = datetime.now(vn_tz)
            if now.weekday() >= 5:  # Saturday=5, Sunday=6
                return False
            t = now.hour * 60 + now.minute
            return (540 <= t <= 690) or (780 <= t <= 900)  # 9:00-11:30, 13:00-15:00

    async def update_loop(self):
        async with aiohttp.ClientSession() as session:
            while self.running:
                if not self._is_trading_time():
                    self.refresh_event.clear()
                    await asyncio.sleep(60)
                    continue

                try:
                    headers = AlertProcessor._get_internal_headers()
                    async with session.get("http://127.0.0.1:3000/alerts/rules", headers=headers) as resp:
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
                
                # Wait for either 30 seconds or a force refresh signal
                self.refresh_event.clear()
                try:
                    await asyncio.wait_for(self.refresh_event.wait(), timeout=30)
                    logger.info("Refresh event received, fetching rules immediately")
                except asyncio.TimeoutError:
                    pass  # Normal 30s cycle

    async def start(self):
        self.running = True
        asyncio.create_task(self.update_loop())
        try:
            self.is_healthy = True
            self.connected_since = datetime.utcnow().isoformat()
            logger.info("Streamer connected and healthy")
            await self.client.connect()
            if getattr(self.client, 'session_manager', None):
                asyncio.create_task(self.client.start_session_monitoring())
        except Exception as e:
            self.is_healthy = False
            self.connected_since = None
            logger.error(f"Streamer disconnected: {e}")

    def get_health(self):
        is_connected = self.client.is_connected()
        healthy = self.is_healthy
        
        if healthy and getattr(self.client, 'session_manager', None):
            try:
                from vnstock_pipeline.stream.utils.market_hours import trading_hours
                status = trading_hours(self.client.market)
                is_trading = status.get('is_trading_hour', False)
                if is_trading and not is_connected:
                    healthy = False
            except Exception as e:
                logger.error(f"Error checking market hours in health check: {e}")
                
        return {
            "healthy": healthy,
            "connected_since": self.connected_since,
            "symbols_count": len(self.symbols),
            "rules_count": len(self.processor.rules),
            "client_connected": is_connected,
        }
