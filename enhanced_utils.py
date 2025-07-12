from cachetools import TTLCache
import asyncio
import yfinance as yf

SCORING_THRESHOLDS = {
    'EXPLOSIVE': 70,
    'STRONG': 65,
    'MODERATE': 60,
    'AVOID': 50
}


def enhanced_pre_filter(symbol_data):
    """Stricter liquidity and volatility pre-filter for symbols."""
    if symbol_data.get('volume_avg', 0) < 1_000_000:
        return False
    if abs(symbol_data.get('5_day_change', 0)) < 3.0:
        return False
    if symbol_data.get('options_volume', 0) < 1000:
        return False
    return True


class OptimizedDataFetcher:
    """Batch API fetcher with caching to reduce requests."""

    def __init__(self, ttl: int = 300, maxsize: int = 1000):
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)

    async def fetch_symbol(self, symbol: str):
        try:
            df = yf.Ticker(symbol).history(period="1d")
            if not df.empty:
                return symbol, {'price': float(df['Close'].iloc[-1])}
        except Exception:
            pass
        return symbol, None

    async def parallel_fetch(self, symbols, batch_size=50):
        tasks = [self.fetch_symbol(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return {s: d for s, d in results if d is not None}

    async def fetch_batch_data(self, symbols):
        cached = {s: self.cache[s] for s in symbols if s in self.cache}
        to_fetch = [s for s in symbols if s not in self.cache]
        batch_data = {}
        if to_fetch:
            batch_data = await self.parallel_fetch(to_fetch)
            self.cache.update(batch_data)
        return {**cached, **batch_data}

