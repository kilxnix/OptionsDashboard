import time
import threading
from queue import Queue, Empty
from typing import Optional, Callable, Any
import yfinance as yf

class YahooFinanceManager:
    """Global Yahoo Finance request manager with rate limiting and queuing"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return

        self.request_queue = Queue()
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests
        self.requests_per_minute = 0
        self.minute_start = time.time()
        self.max_requests_per_minute = 25  # Conservative limit
        self.worker_thread = None
        self.running = False
        self.results = {}
        self.initialized = True

    def start_worker(self):
        """Start the worker thread for processing requests"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            print("🔧 Yahoo Finance manager worker started")

    def stop_worker(self):
        """Stop the worker thread"""
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
            print("🔧 Yahoo Finance manager worker stopped")

    def _worker_loop(self):
        """Worker loop for processing queued requests"""
        while self.running:
            try:
                # Get request from queue (timeout to allow checking self.running)
                request_id, func, args, kwargs = self.request_queue.get(timeout=1.0)

                # Rate limiting
                current_time = time.time()

                # Reset per-minute counter if needed
                if current_time - self.minute_start >= 60:
                    self.requests_per_minute = 0
                    self.minute_start = current_time

                # Check if we need to wait
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.min_request_interval:
                    wait_time = self.min_request_interval - time_since_last
                    time.sleep(wait_time)

                # Check per-minute limit
                if self.requests_per_minute >= self.max_requests_per_minute:
                    wait_time = 60 - (current_time - self.minute_start) + 1
                    if wait_time > 0:
                        print(f"⏳ Yahoo Finance per-minute limit reached, waiting {wait_time:.1f}s")
                        time.sleep(wait_time)
                        self.requests_per_minute = 0
                        self.minute_start = time.time()

                # Execute request
                try:
                    result = func(*args, **kwargs)
                    self.results[request_id] = {'success': True, 'data': result}
                except Exception as e:
                    self.results[request_id] = {'success': False, 'error': str(e)}

                self.last_request_time = time.time()
                self.requests_per_minute += 1
                self.request_queue.task_done()

            except Empty:
                continue  # Timeout reached, check if still running
            except Exception as e:
                print(f"❌ Yahoo Finance manager error: {e}")

    def request_options_data(self, symbol: str, timeout: float = 30.0) -> Optional[Any]:
        """Request options data for a symbol with managed rate limiting"""
        if not self.running:
            self.start_worker()

        request_id = f"{symbol}_{time.time()}"

        # Define the function to execute
        def get_options():
            ticker = yf.Ticker(symbol)
            expirations = ticker.options[:2]  # Limit to 2 expirations

            if not expirations:
                return None

            all_options = []
            for exp_date in expirations:
                try:
                    option_chain = ticker.option_chain(exp_date)

                    # Process calls
                    calls = option_chain.calls.copy()
                    calls['type'] = 'call'
                    calls['expiration'] = exp_date
                    calls['symbol'] = symbol

                    # Process puts
                    puts = option_chain.puts.copy()
                    puts['type'] = 'put'
                    puts['expiration'] = exp_date
                    puts['symbol'] = symbol

                    if not calls.empty:
                        all_options.append(calls)
                    if not puts.empty:
                        all_options.append(puts)

                except Exception as e:
                    print(f"⚠️ Error fetching {exp_date} options for {symbol}: {e}")
                    continue

            # Combine all DataFrames into one
            if all_options:
                import pandas as pd
                try:
                    combined_options = pd.concat(all_options, ignore_index=True)
                    return combined_options
                except Exception as e:
                    print(f"⚠️ Error combining options data for {symbol}: {e}")
                    return None
            else:
                return None

        # Queue the request
        self.request_queue.put((request_id, get_options, [], {}))

        # Wait for result
        start_time = time.time()
        while time.time() - start_time < timeout:
            if request_id in self.results:
                result = self.results.pop(request_id)
                if result['success']:
                    return result['data']
                else:
                    print(f"❌ Yahoo Finance request failed for {symbol}: {result['error']}")
                    return None
            time.sleep(0.1)

        print(f"⏰ Yahoo Finance request timeout for {symbol}")
        return None

# Global instance
yahoo_manager = YahooFinanceManager()