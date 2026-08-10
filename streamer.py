import asyncio
import aiohttp
import logging
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
                await session.post("http://127.0.0.1:3000/alerts/clear", json=payload)
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
                    
                await session.post("http://127.0.0.1:3000/alerts/trigger", json=payload)
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")

class PatchedWSSClient(WSSClient):
    def subscribe_symbols(self, symbols):
        self.clear_raw_messages()
        symbol_str = ','.join(symbols)
        msg = f'42["regs","{{\\"action\\":\\"join\\",\\"list\\":\\"{symbol_str}\\"}}"]'
        self.add_raw_message(msg)
        logger.info(f"Added subscription for symbols: {symbol_str}")
        if self.is_connected():
            asyncio.create_task(self.send_message(msg))

class ChartCandle:
    """In-progress 1m candle cho chart realtime. Ponytail: KHÔNG bucket lại,
    chỉ update last bar close=last_price + track high/low. Khi time > bucket_end → new bar."""
    __slots__ = ('time', 'open', 'high', 'low', 'close', 'volume')

    def __init__(self, time, price, volume=0):
        self.time = time
        self.open = price
        self.high = price
        self.low = price
        self.close = price
        self.volume = volume

    def update(self, price, volume=0):
        self.close = price
        if price > self.high: self.high = price
        if price < self.low: self.low = price
        self.volume += volume

    def to_dict(self):
        return {'time': self.time, 'open': self.open, 'high': self.high,
                'low': self.low, 'close': self.close, 'volume': self.volume}


class ChartProcessor(DataProcessor):
    """Consume tick → update ChartCandle per symbol → notify WS subscriber queues.
    Ponytail: 1-minute bucket fixed (interval='1m' cho chart realtime). Tick→candle đơn giản:
    seed bar đầu, mỗi tick update last bar; khi minute đổi → new bar."""

    BUCKET_SECONDS = 60  # 1m fixed cho chart realtime

    def __init__(self):
        super().__init__()
        # symbol -> ChartCandle (last bar hiện tại)
        self.candles: dict[str, ChartCandle] = {}
        # symbol -> set[asyncio.Queue] (mỗi WS subscriber 1 queue)
        self.subscribers: dict[str, set] = {}

    def subscribe(self, symbol: str) -> asyncio.Queue:
        """WS route gọi khi client connect. Trả queue để đọc candle updates."""
        symbol = symbol.upper()
        q = asyncio.Queue(maxsize=100)
        self.subscribers.setdefault(symbol, set()).add(q)
        logger.info(f"Chart WS subscriber added for {symbol}, total: {len(self.subscribers.get(symbol, set()))}")
        return q

    def unsubscribe(self, symbol: str, q: asyncio.Queue):
        """WS route gọi khi client disconnect."""
        symbol = symbol.upper()
        if symbol in self.subscribers:
            self.subscribers[symbol].discard(q)
            if not self.subscribers[symbol]:
                del self.subscribers[symbol]
                # Clear candle state khi không còn subscriber
                self.candles.pop(symbol, None)

    async def seed_candle(self, symbol: str):
        """Seed last 1m bar từ REST ohlcv (gọi 1 lần khi subscribe mới).

        Sol R4: REST call moved to asyncio.to_thread (was blocking event loop).
        After await, re-check candle existence — a tick arriving during the
        await must not be overwritten by stale seed data.
        """
        symbol = symbol.upper()
        # Re-check: if a tick arrived while we were waiting, don't overwrite.
        if symbol in self.candles:
            return  # candle already exists from a concurrent tick
        try:
            from vnstock_data import Market
            from datetime import datetime, timezone, timedelta

            def _fetch():
                vn_tz = timezone(timedelta(hours=7))
                now = datetime.now(vn_tz)
                end = now.strftime('%Y-%m-%d %H:%M:%S')
                start = (now - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
                return Market().equity(symbol).ohlcv(interval='1m', start=start, end=end)

            df = await asyncio.to_thread(_fetch)
            # Re-check after await: tick may have set candle during fetch.
            if symbol in self.candles:
                return  # don't overwrite running candle
            if df is not None and len(df) > 0:
                last = df.iloc[-1]
                t = int(last['time'].timestamp()) if hasattr(last['time'], 'timestamp') else int(datetime.now(timezone(timedelta(hours=7))).timestamp())
                bucket = (t // self.BUCKET_SECONDS) * self.BUCKET_SECONDS
                self.candles[symbol] = ChartCandle(bucket, float(last['close']), int(last.get('volume', 0) or 0))
                logger.info(f"Seeded candle for {symbol}: {self.candles[symbol].to_dict()}")
        except Exception as e:
            logger.warning(f"Seed candle {symbol} failed (OK nếu ngoài giờ): {e}")

    async def process(self, data):
        """DataProcessor callback — mỗi tick từ WS stream."""
        symbol = data.get('symbol')
        price = data.get('last_price') or data.get('price') or data.get('close_price')
        volume = data.get('last_volume') or data.get('lastVol') or 0
        if not symbol or price is None:
            return
        symbol = symbol.upper()
        # Chỉ process nếu có subscriber cho symbol này
        if symbol not in self.subscribers:
            return
        # Update hoặc tạo candle
        now_ts = int(datetime.now().timestamp())
        bucket = (now_ts // self.BUCKET_SECONDS) * self.BUCKET_SECONDS
        c = self.candles.get(symbol)
        is_new_bar = False
        if c is None or bucket > c.time:
            # New bar (bucket đổi) hoặc chưa có
            if c is not None:
                # Push final bar (closed) trước khi tạo new
                await self._notify(symbol, c.to_dict())
            c = ChartCandle(bucket, price, volume)
            self.candles[symbol] = c
            is_new_bar = True
        else:
            c.update(price, volume)
        # Notify subscribers (mỗi tick)
        await self._notify(symbol, c.to_dict())

    async def _notify(self, symbol: str, candle: dict):
        """Push candle tới tất cả queues của symbol. Drop nếu queue full (slow consumer)."""
        subs = self.subscribers.get(symbol)
        if not subs:
            return
        for q in list(subs):
            try:
                q.put_nowait(candle)
            except asyncio.QueueFull:
                # Drop oldest để nhường chỗ (realtime > historical trong queue)
                try:
                    q.get_nowait()
                    q.put_nowait(candle)
                except Exception:
                    pass


class AppStreamer:
    def __init__(self):
        self.client = PatchedWSSClient()
        self.processor = AlertProcessor()
        self.client.add_processor(self.processor)
        # Chart processor cho WS realtime route (Phase 3.5 backend)
        self.chart_processor = ChartProcessor()
        self.client.add_processor(self.chart_processor)
        self.symbols = set()  # alert symbols
        self.chart_symbols = set()  # chart-watched symbols (từ WS route)
        self.running = False
        self.is_healthy = False
        self.connected_since = None
        self.refresh_event = asyncio.Event()

    def force_refresh(self):
        """Signal the update loop to refresh rules immediately."""
        self.refresh_event.set()
        logger.info("Force refresh triggered")

    def subscribe_chart_symbol(self, symbol: str):
        """WS route gọi khi client subscribe 1 symbol mới. Đăng ký với upstream WS."""
        symbol = symbol.upper()
        if symbol in self.chart_symbols:
            return  # đã subscribe
        self.chart_symbols.add(symbol)
        self._sync_desired_subscriptions()
        logger.info(f"Chart symbol subscribed: {symbol}, total chart: {len(self.chart_symbols)}")

    def unsubscribe_chart_symbol(self, symbol: str):
        """WS route gọi khi client disconnect (cleanup). Giữ symbol nếu alert còn dùng."""
        symbol = symbol.upper()
        self.chart_symbols.discard(symbol)
        self._sync_desired_subscriptions()
        logger.info(f"Chart symbol unsubscribed: {symbol}, total chart: {len(self.chart_symbols)}")

    def _sync_desired_subscriptions(self):
        """Sol R6: single helper that syncs raw_messages with the desired union.

        Always clears raw_messages first, then re-adds the current union
        (alert symbols | chart symbols). This ensures reconnect uses only
        the current desired set — never stale symbols from a previous state.

        Union empty → raw_messages cleared → reconnect subscribes nothing.
        Never sends join(""). All 3 mutation paths route through this helper.
        """
        all_syms = list(self.symbols | self.chart_symbols)
        self.client.clear_raw_messages()
        if all_syms:
            self.client.subscribe_symbols(all_syms)

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
                    async with session.get("http://127.0.0.1:3000/alerts/rules") as resp:
                        if resp.status == 200:
                            rules = await resp.json()
                            self.processor.update_rules(rules)
                            
                            new_symbols = set([r['symbol'] for r in rules])
                            if new_symbols != self.symbols:
                                logger.info(f"Alert symbols changed from {self.symbols} to {new_symbols}")
                                self.symbols = new_symbols
                                self._sync_desired_subscriptions()
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
