"""
速率限制器模块
用于控制API请求频率，避免触发速率限制
"""
import time
from datetime import datetime, timedelta
from collections import deque
from typing import Optional


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        初始化速率限制器
        
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times = deque()  # 存储请求时间戳
        self.last_request_time = None  # 最后一次请求时间
        self.min_interval = time_window / max_requests  # 最小请求间隔
    
    def wait_if_needed(self):
        """
        如果需要，等待直到可以发送下一个请求
        """
        now = time.time()
        
        # 移除超出时间窗口的请求记录
        while self.request_times and now - self.request_times[0] > self.time_window:
            self.request_times.popleft()
        
        # 如果请求数已达到上限，等待
        if len(self.request_times) >= self.max_requests:
            oldest_request = self.request_times[0]
            wait_time = self.time_window - (now - oldest_request) + 0.1  # 加0.1秒缓冲
            if wait_time > 0:
                print(f"⏳ 速率限制：等待 {wait_time:.1f} 秒...")
                time.sleep(wait_time)
                now = time.time()
        
        # 确保最小请求间隔
        if self.last_request_time:
            elapsed = now - self.last_request_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                time.sleep(wait_time)
                now = time.time()
        
        # 记录本次请求
        self.request_times.append(now)
        self.last_request_time = now
    
    def reset(self):
        """重置速率限制器"""
        self.request_times.clear()
        self.last_request_time = None


class AdaptiveRateLimiter(RateLimiter):
    """自适应速率限制器（根据错误率动态调整）"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60, initial_interval: float = 0.1):
        """
        初始化自适应速率限制器
        
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
            initial_interval: 初始请求间隔（秒）
        """
        super().__init__(max_requests, time_window)
        self.current_interval = initial_interval
        self.error_count = 0
        self.success_count = 0
        self.last_error_time = None
    
    def wait_if_needed(self):
        """等待直到可以发送下一个请求（自适应调整）"""
        # 先执行基础速率限制
        super().wait_if_needed()
        
        # 如果最近有错误，增加等待时间
        if self.error_count > 0:
            # 根据错误次数增加等待时间
            extra_wait = self.current_interval * (self.error_count * 0.5)
            if extra_wait > 0:
                time.sleep(extra_wait)
    
    def record_success(self):
        """记录成功请求"""
        self.success_count += 1
        # 成功次数增加，可以适当减少间隔
        if self.success_count > 10:
            self.current_interval = max(0.05, self.current_interval * 0.95)
            self.success_count = 0
    
    def record_error(self, error_type: str = "rate_limit"):
        """记录错误请求"""
        self.error_count += 1
        self.last_error_time = time.time()
        
        # 如果是速率限制错误，增加等待时间
        if error_type == "rate_limit":
            self.current_interval = min(2.0, self.current_interval * 1.5)
            print(f"⚠️ 检测到速率限制，增加请求间隔至 {self.current_interval:.2f} 秒")
        
        # 如果连续成功，重置错误计数
        if self.success_count > 5:
            self.error_count = max(0, self.error_count - 1)
    
    def reset(self):
        """重置速率限制器"""
        super().reset()
        self.current_interval = 0.1
        self.error_count = 0
        self.success_count = 0
        self.last_error_time = None


# 全局速率限制器实例
# 对于akshare：每分钟最多30个请求（保守估计）
akshare_limiter = AdaptiveRateLimiter(max_requests=30, time_window=60, initial_interval=0.1)

# 对于yfinance：每分钟最多5个请求（非常保守，避免速率限制）
yfinance_limiter = AdaptiveRateLimiter(max_requests=5, time_window=60, initial_interval=1.0)
