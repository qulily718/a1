"""
数据源管理器
实现多数据源负载均衡，减少对单一接口的依赖
支持历史日期查询
"""
import pandas as pd
import time
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import random

# 尝试导入各种数据源
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False

try:
    import baostock as bs
    BAOSTOCK_AVAILABLE = True
except ImportError:
    BAOSTOCK_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class DataSourceManager:
    """数据源管理器，实现负载均衡"""
    
    def __init__(self):
        """初始化数据源管理器"""
        self.sources = []
        self.source_stats = {}  # 统计每个数据源的成功/失败次数
        self.current_index = 0  # 当前使用的数据源索引
        
        # 初始化可用数据源
        if AKSHARE_AVAILABLE:
            self.sources.append({
                'name': 'akshare',
                'priority': 1,  # 最高优先级
                'weight': 10,  # 权重（用于负载均衡）
                'enabled': True,
                'fetch_func': self._fetch_akshare
            })
            self.source_stats['akshare'] = {'success': 0, 'fail': 0, 'rate_limit': 0}
        
        # baostock（免费，支持A股和B股，优先级2）
        if BAOSTOCK_AVAILABLE:
            self.sources.append({
                'name': 'baostock',
                'priority': 2,  # 中等优先级
                'weight': 5,   # 权重中等
                'enabled': True,
                'fetch_func': self._fetch_baostock
            })
            self.source_stats['baostock'] = {'success': 0, 'fail': 0, 'rate_limit': 0}
            # 初始化baostock（登录）
            try:
                bs.login()
            except:
                pass
        
        # yfinance优先级最低，权重也最低（仅作为最后备选）
        if YFINANCE_AVAILABLE:
            self.sources.append({
                'name': 'yfinance',
                'priority': 3,  # 最低优先级
                'weight': 1,   # 权重最低
                'enabled': True,
                'fetch_func': self._fetch_yfinance
            })
            self.source_stats['yfinance'] = {'success': 0, 'fail': 0, 'rate_limit': 0}
        
        # 按优先级排序
        self.sources.sort(key=lambda x: x['priority'])
    
    def _get_end_date(self, end_date: Optional[str] = None) -> datetime:
        """获取结束日期，如果未指定则使用今天"""
        if end_date:
            try:
                return datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                # 如果日期格式错误，使用今天
                print(f"⚠️ 日期格式错误: {end_date}，使用今天")
                return datetime.now()
        else:
            return datetime.now()
    
    def _adjust_to_trading_day(self, date_obj: datetime, symbol: str = None) -> datetime:
        """
        调整日期到最近的交易日
        
        Args:
            date_obj: 原始日期
            symbol: 股票代码（可选，用于确定市场）
        
        Returns:
            datetime: 调整后的日期（最近交易日）
        """
        # 简单实现：如果是周末，调整为周五
        # 更复杂的实现可以调用API检查是否是交易日
        weekday = date_obj.weekday()
        if weekday >= 5:  # 5=周六, 6=周日
            # 调整到上一个周五
            days_to_subtract = weekday - 4
            return date_obj - timedelta(days=days_to_subtract)
        return date_obj
    
    def _fetch_akshare(self, symbol: str, period: str = "1mo", end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """使用akshare获取数据"""
        if not AKSHARE_AVAILABLE:
            return None
        
        try:
            code = symbol.replace('.SS', '').replace('.SZ', '')
            
            # 检查是否为B股（9开头或2开头），akshare对B股支持可能不好
            # 上海B股：9开头，深圳B股：2开头
            if (code.startswith('9') or code.startswith('2')) and len(code) == 6:
                # B股可能不支持，返回None让系统尝试其他数据源（baostock）
                return None
            
            # 获取结束日期
            end_date_obj = self._get_end_date(end_date)
            end_date_obj = self._adjust_to_trading_day(end_date_obj, symbol)
            end_date_str = end_date_obj.strftime('%Y%m%d')
            
            # 计算开始日期
            days = self._period_to_days(period)
            start_date_obj = end_date_obj - timedelta(days=days)
            start_date_str = start_date_obj.strftime('%Y%m%d')
            
            # 获取数据
            df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                   start_date=start_date_str, end_date=end_date_str, adjust="qfq")
            
            if df is None or df.empty:
                return None
            
            # 转换为标准格式
            df = self._standardize_dataframe(df)
            
            # 确保数据按日期排序（升序），最后一行是最新的数据
            if df is not None and not df.empty:
                if hasattr(df.index, 'is_monotonic_increasing'):
                    if not df.index.is_monotonic_increasing:
                        df = df.sort_index()
                elif hasattr(df, 'sort_index'):
                    df = df.sort_index()
            
            return df
            
        except Exception as e:
            # 静默处理错误，让系统尝试其他数据源
            return None
    
    def _fetch_baostock(self, symbol: str, period: str = "1mo", end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """使用baostock获取数据（免费，支持A股和B股）"""
        if not BAOSTOCK_AVAILABLE:
            return None
        
        try:
            code = symbol.replace('.SS', '').replace('.SZ', '')
            
            # baostock代码格式：
            # A股：sh.600000（上海）或 sz.000001（深圳）
            # B股：sh.900901（上海B股）或 sz.200002（深圳B股）
            if '.SS' in symbol:
                # 上海市场（A股6开头，B股9开头）
                bs_code = f"sh.{code}"
            elif '.SZ' in symbol:
                # 深圳市场（A股0/3开头，B股2开头）
                bs_code = f"sz.{code}"
            else:
                # 默认根据代码判断
                if code.startswith('6') or code.startswith('9'):
                    bs_code = f"sh.{code}"
                else:
                    bs_code = f"sz.{code}"
            
            # 获取结束日期
            end_date_obj = self._get_end_date(end_date)
            end_date_obj = self._adjust_to_trading_day(end_date_obj, symbol)
            end_date_str = end_date_obj.strftime('%Y-%m-%d')
            
            # 计算开始日期
            days = self._period_to_days(period)
            start_date_obj = end_date_obj - timedelta(days=days)
            start_date_str = start_date_obj.strftime('%Y-%m-%d')
            
            # 获取数据
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume",
                start_date=start_date_str,
                end_date=end_date_str,
                frequency="d",
                adjustflag="2"  # 前复权
            )
            
            if rs.error_code != '0':
                return None
            
            # 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return None
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df.sort_index()  # 确保按日期排序
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 重命名为标准格式
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)
            
            # 添加Dividends和Stock Splits列
            df['Dividends'] = 0
            df['Stock Splits'] = 0
            
            return df
            
        except Exception as e:
            # 静默处理错误，让系统尝试其他数据源
            return None
    
    def _fetch_yfinance(self, symbol: str, period: str = "1mo", end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """使用yfinance获取数据（最后备选）"""
        if not YFINANCE_AVAILABLE:
            return None
        
        try:
            # 对于B股（9开头或2开头），优先使用baostock，避免yfinance连接问题
            code = symbol.replace('.SS', '').replace('.SZ', '')
            if (code.startswith('9') or code.startswith('2')) and len(code) == 6:
                # B股，跳过yfinance，避免连接问题
                return None
            
            # 检查是否应该使用yfinance（如果速率限制过多，直接跳过，更严格）
            if 'yfinance' in self.source_stats:
                stats = self.source_stats['yfinance']
                if stats['rate_limit'] > 3:
                    # 速率限制超过3次，直接跳过（更严格）
                    return None
            
            ticker = yf.Ticker(symbol)
            
            # 如果指定了结束日期，使用start和end参数
            if end_date:
                # 获取结束日期
                end_date_obj = self._get_end_date(end_date)
                end_date_obj = self._adjust_to_trading_day(end_date_obj, symbol)
                end_date_str = end_date_obj.strftime('%Y-%m-%d')
                
                # 计算开始日期
                days = self._period_to_days(period)
                start_date_obj = end_date_obj - timedelta(days=days)
                start_date_str = start_date_obj.strftime('%Y-%m-%d')
                
                # 使用start和end参数获取历史数据
                df = ticker.history(start=start_date_str, end=end_date_str)
            else:
                # 使用period参数
                df = ticker.history(period=period)
            
            # 更严格的None检查，防止NoneType错误
            if df is None:
                return None
            
            # 检查是否是DataFrame类型
            if not isinstance(df, pd.DataFrame):
                return None
            
            # 检查是否为空
            if df.empty:
                return None
            
            # 确保有必要的列，避免后续访问None
            if len(df.columns) == 0:
                return None
            
            # 确保数据按日期排序（升序），最后一行是最新的数据
            if hasattr(df.index, 'is_monotonic_increasing'):
                if not df.index.is_monotonic_increasing:
                    df = df.sort_index()
            elif hasattr(df, 'sort_index'):
                df = df.sort_index()
            
            return df
            
        except Exception as e:
            error_msg = str(e)
            # 捕获NoneType错误
            if "'NoneType' object is not subscriptable" in error_msg or "NoneType" in error_msg:
                # NoneType错误，说明yfinance返回了None或无效数据
                if 'yfinance' in self.source_stats:
                    self.source_stats['yfinance']['fail'] += 1
                return None
            
            if "Rate limited" in error_msg or "Too Many Requests" in error_msg:
                # 记录速率限制
                if 'yfinance' in self.source_stats:
                    self.source_stats['yfinance']['rate_limit'] += 1
                raise Exception("RATE_LIMIT")
            
            # 其他错误也记录失败
            if 'yfinance' in self.source_stats:
                self.source_stats['yfinance']['fail'] += 1
            return None
    
    def _period_to_days(self, period: str) -> int:
        """将周期转换为天数"""
        period_map = {
            '1d': 1, '5d': 5, '1mo': 30, '3mo': 90,
            '6mo': 180, '1y': 365, '2y': 730, '5y': 1825
        }
        return period_map.get(period, 180)
    
    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化DataFrame格式"""
        # 检查df是否为None或无效
        if df is None:
            return None
        
        if not isinstance(df, pd.DataFrame):
            return None
        
        if df.empty:
            return df
        
        # 确保有必要的列
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_cols:
            if col not in df.columns:
                if col == 'Open' and '开盘' in df.columns:
                    df['Open'] = df['开盘']
                elif col == 'High' and '最高' in df.columns:
                    df['High'] = df['最高']
                elif col == 'Low' and '最低' in df.columns:
                    df['Low'] = df['最低']
                elif col == 'Close' and '收盘' in df.columns:
                    df['Close'] = df['收盘']
                elif col == 'Volume' and '成交量' in df.columns:
                    df['Volume'] = df['成交量']
        
        return df
    
    def get_data(self, symbol: str, period: str = "1mo", 
                 end_date: Optional[str] = None,  # 新增：结束日期参数
                 preferred_source: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        获取股票数据（负载均衡），支持历史日期
        
        Args:
            symbol: 股票代码
            period: 数据周期
            end_date: 结束日期，格式为 'YYYY-MM-DD'，默认为今天
            preferred_source: 首选数据源（可选）
        
        Returns:
            DataFrame: 股票数据，如果所有数据源都失败则返回None
        """
        # 验证日期格式（如果提供）
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                print(f"⚠️ 日期格式错误: {end_date}，请使用 'YYYY-MM-DD' 格式")
                # 重置为None，使用今天
                end_date = None
        # 如果指定了首选数据源，优先使用
        if preferred_source:
            for source in self.sources:
                if source['name'] == preferred_source and source['enabled']:
                    try:
                        df = source['fetch_func'](symbol, period, end_date)
                        if df is not None and not df.empty:
                            self.source_stats[source['name']]['success'] += 1
                            return df
                    except Exception as e:
                        if "RATE_LIMIT" in str(e):
                            self.source_stats[source['name']]['rate_limit'] += 1
                        else:
                            self.source_stats[source['name']]['fail'] += 1
        
        # 负载均衡：按优先级和权重选择数据源
        available_sources = [s for s in self.sources if s['enabled']]
        
        # 如果yfinance最近有速率限制，降低其权重或暂时禁用（更严格的策略）
        if 'yfinance' in self.source_stats:
            yf_stats = self.source_stats['yfinance']
            if yf_stats['rate_limit'] > 3:
                # 如果速率限制超过3次，暂时禁用yfinance（更严格）
                for source in available_sources:
                    if source['name'] == 'yfinance':
                        source['enabled'] = False
                        print(f"⚠️ yfinance速率限制过多（{yf_stats['rate_limit']}次），暂时禁用，优先使用其他数据源")
                        break
                available_sources = [s for s in available_sources if s['name'] != 'yfinance']
            elif yf_stats['rate_limit'] > 1:
                # 如果速率限制超过1次，降低权重（更严格）
                for source in available_sources:
                    if source['name'] == 'yfinance':
                        source['weight'] = 0  # 权重设为0，基本不使用
                        print(f"⚠️ yfinance速率限制较多（{yf_stats['rate_limit']}次），降低优先级，优先使用baostock")
        
        if not available_sources:
            return None
        
        # 按优先级顺序尝试（高优先级先尝试）
        for source in available_sources:
            try:
                # 添加小延迟，避免请求过快
                # akshare已经有速率限制器，但为了更稳定，也添加小延迟
                # yfinance需要更长延迟，避免限流
                if source['name'] == 'yfinance':
                    time.sleep(0.5)  # yfinance延迟更长
                elif source['name'] == 'baostock':
                    time.sleep(0.1)  # baostock中等延迟
                elif source['name'] == 'akshare':
                    time.sleep(0.05)  # akshare已有速率限制器，小延迟即可
                else:
                    time.sleep(0.1)  # 其他数据源默认延迟
                
                df = source['fetch_func'](symbol, period, end_date)
                if df is not None and not df.empty:
                    self.source_stats[source['name']]['success'] += 1
                    return df
            except Exception as e:
                if "RATE_LIMIT" in str(e):
                    self.source_stats[source['name']]['rate_limit'] += 1
                    # 如果是速率限制，跳过这个数据源，尝试下一个
                    continue
                else:
                    self.source_stats[source['name']]['fail'] += 1
        
        # 所有数据源都失败
        return None
    
    def get_stats(self) -> Dict:
        """获取数据源统计信息"""
        return self.source_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        for source_name in self.source_stats:
            self.source_stats[source_name] = {'success': 0, 'fail': 0, 'rate_limit': 0}
        
        # 重新启用所有数据源
        for source in self.sources:
            source['enabled'] = True
    
    def __del__(self):
        """析构函数，关闭baostock连接"""
        if BAOSTOCK_AVAILABLE:
            try:
                bs.logout()
            except:
                pass


# 全局数据源管理器实例
_data_source_manager = None

def get_data_source_manager() -> DataSourceManager:
    """获取全局数据源管理器实例（单例模式）"""
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager()
    return _data_source_manager
