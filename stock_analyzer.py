"""
股票分析模块
提供股票数据获取、技术分析和交易信号生成功能
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
import warnings
import time
warnings.filterwarnings('ignore')

# 导入速率限制器
try:
    from rate_limiter import akshare_limiter, yfinance_limiter
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False
    # 如果没有速率限制器，使用简单的延迟
    class SimpleLimiter:
        def wait_if_needed(self):
            time.sleep(0.1)  # 默认0.1秒延迟
        def record_success(self):
            pass
        def record_error(self, error_type=""):
            pass
    
    akshare_limiter = SimpleLimiter()
    yfinance_limiter = SimpleLimiter()

# 导入数据源管理器（负载均衡）
try:
    from data_source_manager import get_data_source_manager
    DATA_SOURCE_MANAGER_AVAILABLE = True
except ImportError:
    DATA_SOURCE_MANAGER_AVAILABLE = False

# 尝试导入akshare（用于A股数据）
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


def get_stocks_by_sectors(sector_names: List[str]) -> pd.DataFrame:
    """
    根据板块名称获取板块中的股票列表
    
    Args:
        sector_names: 板块名称列表
    
    Returns:
        DataFrame: 包含股票代码和名称的DataFrame
    """
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    
    if not sector_names:
        return pd.DataFrame()
    
    all_stocks_set = set()
    
    try:
        for sector_name in sector_names:
            try:
                # 获取板块成分股
                # 注意：akshare的API可能变化，这里使用常见的API
                df = ak.stock_board_industry_cons_em(symbol=sector_name)
                
                if df is not None and not df.empty:
                    # 提取股票代码和名称
                    for idx, row in df.iterrows():
                        code = None
                        name = None
                        
                        # 尝试不同的列名
                        for col in df.columns:
                            col_str = str(col).lower()
                            if '代码' in col_str or 'code' in col_str:
                                code = row[col]
                            elif '名称' in col_str or 'name' in col_str:
                                name = row[col]
                        
                        if code:
                            # 添加市场后缀
                            if str(code).startswith('6'):
                                symbol = f"{code}.SS"
                            else:
                                symbol = f"{code}.SZ"
                            
                            all_stocks_set.add((symbol, code, name if name else code))
                
                # 添加小延迟，避免请求过快
                time.sleep(0.1)
                
            except Exception as e:
                print(f"获取板块 {sector_name} 的成分股失败: {e}")
                continue
        
        # 转换为DataFrame
        if all_stocks_set:
            result = pd.DataFrame(list(all_stocks_set), columns=['symbol', 'code', 'name'])
            return result
        else:
            return pd.DataFrame()
            
    except Exception as e:
        print(f"获取板块股票列表失败: {e}")
        return pd.DataFrame()


def get_all_a_stock_list() -> pd.DataFrame:
    """
    获取所有A股股票代码列表
    
    Returns:
        DataFrame: 包含股票代码和名称的DataFrame
    """
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    
    try:
        # 获取A股实时行情数据（包含所有A股代码）
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 提取需要的列：代码、名称
        result = pd.DataFrame()
        if '代码' in df.columns:
            result['code'] = df['代码']
        elif 'code' in df.columns:
            result['code'] = df['code']
        
        if '名称' in df.columns:
            result['name'] = df['名称']
        elif 'name' in df.columns:
            result['name'] = df['name']
        
        # 添加市场后缀
        result['symbol'] = result['code'].apply(lambda x: f"{x}.SS" if str(x).startswith('6') else f"{x}.SZ")
        
        # 保留A股、ETF/基金和B股
        # A股：0、3、6开头（6位数字）
        # ETF/基金：15、16、51开头（6位数字）
        # B股：9开头（6位数字）
        result = result[result['code'].astype(str).str.match(r'^[036]\d{5}$|^1[56]\d{4}$|^51\d{4}$|^9\d{5}$')]
        
        return result[['symbol', 'code', 'name']]
    except Exception as e:
        print(f"获取A股列表失败: {e}")
        # 备用方法：使用股票信息接口
        try:
            df = ak.stock_info_a_code_name()
            if df is None or df.empty:
                return pd.DataFrame()
            
            result = pd.DataFrame()
            if 'code' in df.columns:
                result['code'] = df['code']
            if 'name' in df.columns:
                result['name'] = df['name']
            
            result['symbol'] = result['code'].apply(lambda x: f"{x}.SS" if str(x).startswith('6') else f"{x}.SZ")
            
            # 保留A股、ETF/基金和B股
            # A股：0、3、6开头（6位数字）
            # ETF/基金：15、16、51开头（6位数字）
            # B股：9开头（6位数字）
            result = result[result['code'].astype(str).str.match(r'^[036]\d{5}$|^1[56]\d{4}$|^51\d{4}$|^9\d{5}$')]
            
            return result[['symbol', 'code', 'name']]
        except Exception as e2:
            print(f"备用方法获取A股列表也失败: {e2}")
            return pd.DataFrame()


class StockAnalyzer:
    """股票分析器"""
    
    def __init__(self, symbol: str, period: str = "1mo"):
        """
        初始化股票分析器
        
        Args:
            symbol: 股票代码（如 'AAPL', 'TSLA', '000001.SS'）
            period: 数据周期 ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
        """
        self.symbol = symbol.upper()
        self.period = period
        self.stock = None
        self.data = None
        
    def _is_china_stock(self, symbol: str) -> bool:
        """判断是否为中国股票（A股）"""
        if '.SS' in symbol or '.SZ' in symbol:
            # 提取代码部分
            code = symbol.replace('.SS', '').replace('.SZ', '')
            # A股代码：0、3、6开头（排除9开头的B股）
            if len(code) == 6 and code.isdigit():
                return code.startswith(('0', '3', '6'))
        return False
    
    def _is_china_b_stock(self, symbol: str) -> bool:
        """判断是否为中国B股（9开头）"""
        if '.SS' in symbol or '.SZ' in symbol:
            code = symbol.replace('.SS', '').replace('.SZ', '')
            if len(code) == 6 and code.isdigit():
                return code.startswith('9')
        return False
    
    def _is_etf_or_fund(self, symbol: str) -> bool:
        """判断是否为ETF或基金（15、16、51开头）"""
        if '.SS' in symbol or '.SZ' in symbol:
            code = symbol.replace('.SS', '').replace('.SZ', '')
            if len(code) == 6 and code.isdigit():
                # 15开头：ETF
                # 16开头：基金
                # 51开头：ETF（上海）
                return code.startswith(('15', '16', '51'))
        return False
    
    def _is_supported_stock(self, symbol: str) -> bool:
        """判断是否为支持的股票类型（A股，排除B股、ETF、基金等）"""
        # 只支持A股（0、3、6开头）
        return self._is_china_stock(symbol)
    
    def _convert_period_to_days(self, period: str) -> int:
        """将周期转换为天数"""
        period_map = {
            '1d': 1,
            '5d': 5,
            '1mo': 30,
            '3mo': 90,
            '6mo': 180,
            '1y': 365,
            '2y': 730,
            '5y': 1825
        }
        return period_map.get(period, 180)
    
    def _fetch_akshare_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """使用akshare获取A股数据（带重试和超时机制）"""
        if not AKSHARE_AVAILABLE:
            return None
        
        # 重试配置
        max_retries = 3
        timeout = 10  # 10秒超时
        
        for attempt in range(max_retries):
            try:
                # 提取股票代码（去掉.SS或.SZ后缀）
                code = symbol.replace('.SS', '').replace('.SZ', '')
                
                # 判断是上海还是深圳
                if '.SS' in symbol or (code.startswith('6') and len(code) == 6):
                    market = 'sh'  # 上海
                elif '.SZ' in symbol or (len(code) == 6 and not code.startswith('6')):
                    market = 'sz'  # 深圳
                else:
                    return None
                
                # 获取历史数据
                days = self._convert_period_to_days(self.period)
                
                # 使用今天的日期作为end_date（akshare会自动返回最近的交易日数据）
                # 如果今天是周末或节假日，akshare会返回上一个交易日的数据
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
                
                # 使用akshare获取数据（会自动获取到最新的交易日数据）
                df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                
                if df is None or df.empty:
                    if attempt < max_retries - 1:
                        time.sleep(1)  # 等待1秒后重试
                        continue
                    return None
                
                # 成功获取数据，跳出重试循环
                break
                
            except Exception as e:
                error_msg = str(e)
                # 检查是否是超时或连接错误
                is_timeout = 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower() or 'ConnectTimeout' in error_msg
                is_connection_error = 'Connection' in error_msg or 'Max retries' in error_msg
                
                if (is_timeout or is_connection_error) and attempt < max_retries - 1:
                    # 网络错误，等待后重试（减少等待时间，提高响应性）
                    wait_time = (attempt + 1) * 1  # 递增等待时间：1秒、2秒、3秒（从2秒、4秒、6秒减少）
                    time.sleep(wait_time)
                    continue
                else:
                    # 其他错误或最后一次尝试失败，静默处理（避免日志过多）
                    return None
        
        # 如果所有重试都失败
        if 'df' not in locals() or df is None or df.empty:
            return None
        
        try:
            # 动态处理列名（akshare的列数可能变化）
            actual_columns = df.columns.tolist()
            
            # 找到日期列（通常是第一列或包含'日期'的列）
            date_col = None
            for col in actual_columns:
                if '日期' in str(col) or 'date' in str(col).lower() or '时间' in str(col):
                    date_col = col
                    break
            
            if date_col is None and len(actual_columns) > 0:
                date_col = actual_columns[0]
            
            # 设置日期索引
            try:
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col])
                    df = df.set_index(date_col)
                else:
                    # 如果date_col不在列中，可能是索引
                    df.index = pd.to_datetime(df.index)
            except:
                try:
                    df.index = pd.to_datetime(df.index)
                except:
                    pass
            
            df = df.sort_index()
            
            # 创建列名映射（根据akshare的实际列名）
            column_mapping = {}
            for col in actual_columns:
                col_str = str(col).lower()
                if '开盘' in col_str or 'open' in col_str:
                    column_mapping['Open'] = col
                elif '收盘' in col_str or 'close' in col_str:
                    column_mapping['Close'] = col
                elif '最高' in col_str or 'high' in col_str:
                    column_mapping['High'] = col
                elif '最低' in col_str or 'low' in col_str:
                    column_mapping['Low'] = col
                elif '成交量' in col_str or 'volume' in col_str:
                    column_mapping['Volume'] = col
            
            # 如果映射失败，尝试按位置索引（akshare的标准格式）
            # 通常格式：日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, ...
            numeric_cols = [col for col in actual_columns if col != date_col]
            if len(numeric_cols) >= 5:
                if 'Open' not in column_mapping:
                    column_mapping['Open'] = numeric_cols[0] if len(numeric_cols) > 0 else None
                if 'Close' not in column_mapping:
                    column_mapping['Close'] = numeric_cols[1] if len(numeric_cols) > 1 else None
                if 'High' not in column_mapping:
                    column_mapping['High'] = numeric_cols[2] if len(numeric_cols) > 2 else None
                if 'Low' not in column_mapping:
                    column_mapping['Low'] = numeric_cols[3] if len(numeric_cols) > 3 else None
                if 'Volume' not in column_mapping:
                    column_mapping['Volume'] = numeric_cols[4] if len(numeric_cols) > 4 else None
            
            # 创建标准格式的DataFrame
            df_standard = pd.DataFrame(index=df.index)
            
            # 复制数据
            if 'Open' in column_mapping and column_mapping['Open'] in df.columns:
                df_standard['Open'] = pd.to_numeric(df[column_mapping['Open']], errors='coerce')
            if 'Close' in column_mapping and column_mapping['Close'] in df.columns:
                df_standard['Close'] = pd.to_numeric(df[column_mapping['Close']], errors='coerce')
            if 'High' in column_mapping and column_mapping['High'] in df.columns:
                df_standard['High'] = pd.to_numeric(df[column_mapping['High']], errors='coerce')
            if 'Low' in column_mapping and column_mapping['Low'] in df.columns:
                df_standard['Low'] = pd.to_numeric(df[column_mapping['Low']], errors='coerce')
            if 'Volume' in column_mapping and column_mapping['Volume'] in df.columns:
                df_standard['Volume'] = pd.to_numeric(df[column_mapping['Volume']], errors='coerce')
            
            # 确保有Close列（必需）
            if 'Close' not in df_standard.columns or df_standard['Close'].isna().all():
                return None
            
            # 填充缺失的列
            if 'Open' not in df_standard.columns or df_standard['Open'].isna().all():
                df_standard['Open'] = df_standard['Close']
            if 'High' not in df_standard.columns or df_standard['High'].isna().all():
                df_standard['High'] = df_standard['Close']
            if 'Low' not in df_standard.columns or df_standard['Low'].isna().all():
                df_standard['Low'] = df_standard['Close']
            if 'Volume' not in df_standard.columns or df_standard['Volume'].isna().all():
                df_standard['Volume'] = 0
            
            # 填充NaN值
            df_standard = df_standard.bfill().ffill()
            
            # 添加yfinance格式需要的列
            df_standard['Dividends'] = 0
            df_standard['Stock Splits'] = 0
            
            return df_standard
            
        except Exception as e:
            print(f"akshare获取数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_data(self) -> bool:
        """
        获取股票数据
        
        Returns:
            bool: 是否成功获取数据
        """
        # 不再过滤B股，支持B股数据获取
        
        # 如果是A股、ETF/基金或B股，使用数据源管理器（负载均衡）
        is_a_stock = self._is_china_stock(self.symbol)
        is_etf_fund = self._is_etf_or_fund(self.symbol)
        is_b_stock = self._is_china_b_stock(self.symbol)
        
        if is_a_stock or is_etf_fund or is_b_stock:
            # 使用数据源管理器，优先akshare，失败后自动尝试其他数据源（包括baostock）
            if DATA_SOURCE_MANAGER_AVAILABLE:
                manager = get_data_source_manager()
                # 对于A股，优先使用akshare
                # 对于B股和ETF/基金，不指定首选，让管理器自动选择（B股优先使用baostock）
                preferred = 'akshare' if is_a_stock else ('baostock' if is_b_stock else None)
                df = manager.get_data(self.symbol, self.period, preferred_source=preferred)
                
                if df is not None and not df.empty:
                    self.data = df
                    self.stock = None
                    return True
                else:
                    # 数据源管理器已尝试所有可用数据源（akshare -> baostock -> yfinance）
                    # 如果都失败，直接返回False，不再尝试yfinance（避免速率限制）
                    print(f"⚠️ {self.symbol} 所有数据源（akshare/baostock/yfinance）获取失败")
                    return False
            else:
                # 如果没有数据源管理器，使用原来的方法
                # 对于B股，akshare可能不支持，直接跳过
                if not is_b_stock:
                    akshare_data = self._fetch_akshare_data(self.symbol)
                    if akshare_data is not None and not akshare_data.empty:
                        self.data = akshare_data
                        self.stock = None
                        return True
                # 如果没有数据源管理器且是B股，直接返回False（避免使用yfinance）
                print(f"⚠️ {self.symbol} 数据源管理器不可用，且无法使用akshare")
                return False
        
        # 尝试使用yfinance（仅用于非A股、非B股、非ETF/基金，如美股等，带重试机制）
        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries):
            try:
                self.stock = yf.Ticker(self.symbol)
                self.data = self.stock.history(period=self.period)
                
                if self.data.empty:
                    # 如果yfinance失败且是A股，尝试不同的格式
                    if self._is_china_stock(self.symbol):
                        # 尝试不带后缀的格式
                        code = self.symbol.replace('.SS', '').replace('.SZ', '')
                        if '.SS' in self.symbol:
                            alt_symbol = f"{code}.SS"
                        elif '.SZ' in self.symbol:
                            alt_symbol = f"{code}.SZ"
                        else:
                            alt_symbol = f"{code}.SS"  # 默认尝试上海
                        
                        if alt_symbol != self.symbol:
                            try:
                                self.stock = yf.Ticker(alt_symbol)
                                self.data = self.stock.history(period=self.period)
                                if not self.data.empty:
                                    self.symbol = alt_symbol
                                    return True
                            except:
                                pass
                    
                    # 如果数据为空，且是A股，尝试akshare
                    if self._is_china_stock(self.symbol):
                        akshare_data = self._fetch_akshare_data(self.symbol)
                        if akshare_data is not None and not akshare_data.empty:
                            self.data = akshare_data
                            self.stock = None
                            return True
                    
                    return False
                    
                return True
            except Exception as e:
                error_msg = str(e)
                print(f"yfinance获取数据失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                # 如果是速率限制错误，等待后重试（增加等待时间）
                if "Rate limited" in error_msg or "Too Many Requests" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1) * 2  # 增加等待时间：4秒、8秒、12秒
                        print(f"遇到速率限制，等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # 最后一次重试也失败，如果是A股，尝试akshare
                        if self._is_china_stock(self.symbol):
                            print(f"yfinance速率限制，尝试使用akshare获取A股数据...")
                            akshare_data = self._fetch_akshare_data(self.symbol)
                            if akshare_data is not None and not akshare_data.empty:
                                self.data = akshare_data
                                self.stock = None
                                return True
                        # 如果是B股或非A股，直接返回False（避免无限重试）
                        print(f"yfinance速率限制，无法获取数据（可能是B股或非A股）")
                        return False
                
                # 如果不是速率限制错误，直接返回False
                if "Rate limited" not in error_msg and "Too Many Requests" not in error_msg:
                    break
        
        return False
    
    def get_current_info(self) -> Dict:
        """
        获取当前股票信息
        
        Returns:
            dict: 包含股票基本信息的字典
        """
        if self.data is None or self.data.empty:
            return {}
        
        try:
            current_price = self.data['Close'].iloc[-1] if not self.data.empty else 0
            prev_close = self.data['Close'].iloc[-2] if len(self.data) > 1 else current_price
            change = current_price - prev_close
            change_percent = (change / prev_close * 100) if prev_close > 0 else 0
            
            # 尝试获取股票详细信息
            name = self.symbol
            market_cap = 0
            currency = 'CNY' if self._is_china_stock(self.symbol) else 'USD'
            
            if self.stock:
                try:
                    info = self.stock.info
                    name = info.get('longName', info.get('shortName', self.symbol))
                    market_cap = info.get('marketCap', 0)
                    currency = info.get('currency', currency)
                except:
                    pass
            
            # 如果是A股且akshare可用，尝试获取股票名称
            if self._is_china_stock(self.symbol) and AKSHARE_AVAILABLE:
                try:
                    code = self.symbol.replace('.SS', '').replace('.SZ', '')
                    stock_info = ak.stock_individual_info_em(symbol=code)
                    if stock_info is not None and not stock_info.empty:
                        name_row = stock_info[stock_info['item'] == '股票简称']
                        if not name_row.empty:
                            name = name_row.iloc[0]['value']
                except:
                    pass
            
            return {
                'symbol': self.symbol,
                'name': name,
                'current_price': round(current_price, 2),
                'prev_close': round(prev_close, 2),
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'volume': int(self.data['Volume'].iloc[-1]) if not self.data.empty else 0,
                'market_cap': market_cap,
                'currency': currency
            }
        except Exception as e:
            print(f"获取股票信息失败: {e}")
            return {}
    
    def calculate_indicators(self) -> pd.DataFrame:
        """
        计算技术指标
        
        Returns:
            DataFrame: 包含技术指标的DataFrame
        """
        if self.data is None or self.data.empty:
            return pd.DataFrame()
        
        df = self.data.copy()
        
        # 移动平均线
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA50'] = df['Close'].rolling(window=50).mean()
        
        # RSI (相对强弱指标)
        df['RSI'] = self._calculate_rsi(df['Close'], period=14)
        
        # MACD
        macd_data = self._calculate_macd(df['Close'])
        df['MACD'] = macd_data['MACD']
        df['MACD_Signal'] = macd_data['Signal']
        df['MACD_Hist'] = macd_data['Histogram']
        
        # 布林带
        bollinger = self._calculate_bollinger_bands(df['Close'], period=20)
        df['BB_Upper'] = bollinger['Upper']
        df['BB_Middle'] = bollinger['Middle']
        df['BB_Lower'] = bollinger['Lower']
        
        # 成交量移动平均
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal
        
        return {
            'MACD': macd,
            'Signal': macd_signal,
            'Histogram': macd_hist
        }
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict:
        """计算布林带"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        return {
            'Upper': sma + (std * std_dev),
            'Middle': sma,
            'Lower': sma - (std * std_dev)
        }
    
    def generate_signals(self) -> Dict:
        """
        生成交易信号
        
        Returns:
            dict: 包含交易信号和建议的字典
        """
        if self.data is None or self.data.empty:
            return {'signal': 'NONE', 'strength': 0, 'reason': '数据不足'}
        
        df = self.calculate_indicators()
        
        if df.empty or len(df) < 50:
            return {'signal': 'NONE', 'strength': 0, 'reason': '数据不足，无法分析'}
        
        # 获取最新数据
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        signals = []
        buy_score = 0
        sell_score = 0
        
        # 1. 移动平均线信号（改进版：支持短期多头/空头）
        current_price = latest['Close']
        # 检查均线是否有效
        ma5_valid = not pd.isna(latest['MA5'])
        ma10_valid = not pd.isna(latest['MA10'])
        ma20_valid = not pd.isna(latest['MA20'])
        
        if ma5_valid and ma10_valid and ma20_valid:
            # 完整多头排列
            if current_price > latest['MA5'] > latest['MA10'] > latest['MA20']:
                buy_score += 2
                signals.append("价格位于多条均线之上，趋势向上")
            # 短期多头（价格>MA5>MA10，但MA20可能不在）
            elif current_price > latest['MA5'] > latest['MA10']:
                buy_score += 1
                signals.append("短期多头排列，趋势向上")
            # 完整空头排列
            elif current_price < latest['MA5'] < latest['MA10'] < latest['MA20']:
                sell_score += 2
                signals.append("价格位于多条均线之下，趋势向下")
            # 短期空头（价格<MA5<MA10，但MA20可能不在）
            elif current_price < latest['MA5'] < latest['MA10']:
                sell_score += 1
                signals.append("短期空头排列，趋势向下")
        
        # 2. RSI信号（改进版：添加背离检测）
        rsi = latest['RSI']
        if not pd.isna(rsi):
            if rsi < 30:
                buy_score += 3
                signals.append(f"RSI={rsi:.1f}，超卖区域，可能反弹")
            elif rsi > 70:
                sell_score += 3
                signals.append(f"RSI={rsi:.1f}，超买区域，可能回调")
            elif 30 <= rsi <= 50:
                buy_score += 1
                signals.append(f"RSI={rsi:.1f}，处于低位，有上涨空间")
            elif 50 < rsi <= 70:
                sell_score += 1
                signals.append(f"RSI={rsi:.1f}，处于高位，注意风险")
            
            # RSI背离检测（需要至少20日数据）
            if len(df) >= 20:
                # 查找最近20日的最低点和最高点
                recent_low_idx = df['Close'].iloc[-20:].idxmin()
                recent_high_idx = df['Close'].iloc[-20:].idxmax()
                recent_low_price = df.loc[recent_low_idx, 'Close']
                recent_high_price = df.loc[recent_high_idx, 'Close']
                recent_low_rsi = df.loc[recent_low_idx, 'RSI'] if not pd.isna(df.loc[recent_low_idx, 'RSI']) else rsi
                recent_high_rsi = df.loc[recent_high_idx, 'RSI'] if not pd.isna(df.loc[recent_high_idx, 'RSI']) else rsi
                
                # 底背离：价格创新低，RSI未创新低
                if current_price <= recent_low_price * 1.02 and rsi > recent_low_rsi * 1.05:
                    buy_score += 2
                    signals.append("RSI底背离，可能反弹")
                
                # 顶背离：价格创新高，RSI未创新高
                if current_price >= recent_high_price * 0.98 and rsi < recent_high_rsi * 0.95:
                    sell_score += 2
                    signals.append("RSI顶背离，可能回调")
        
        # 3. MACD信号（改进版：添加零轴突破检测）
        macd = latest['MACD']
        macd_signal = latest['MACD_Signal']
        macd_hist = latest['MACD_Hist']
        prev_macd = prev['MACD'] if not pd.isna(prev['MACD']) else 0
        
        if not pd.isna(macd) and not pd.isna(macd_signal):
            # MACD金叉/死叉
            if macd > macd_signal and prev['MACD'] <= prev['MACD_Signal']:
                buy_score += 2
                signals.append("MACD金叉，买入信号")
            elif macd < macd_signal and prev['MACD'] >= prev['MACD_Signal']:
                sell_score += 2
                signals.append("MACD死叉，卖出信号")
            
            # MACD柱状图方向
            if macd_hist > 0:
                buy_score += 1
            else:
                sell_score += 1
            
            # MACD零轴突破检测
            if macd > 0 and prev_macd <= 0:
                buy_score += 1
                signals.append("MACD上穿零轴，多头动能增强")
            elif macd < 0 and prev_macd >= 0:
                sell_score += 1
                signals.append("MACD下穿零轴，空头动能增强")
        
        # 4. 布林带信号（改进版：添加收口/张口判断）
        if not pd.isna(latest['BB_Lower']) and not pd.isna(latest['BB_Upper']) and not pd.isna(latest['BB_Middle']):
            # 价格触及上下轨
            if current_price <= latest['BB_Lower']:
                buy_score += 2
                signals.append("价格触及布林带下轨，可能反弹")
            elif current_price >= latest['BB_Upper']:
                sell_score += 2
                signals.append("价格触及布林带上轨，可能回调")
            
            # 布林带收口/张口判断
            if len(df) >= 2:
                prev_bb_upper = prev['BB_Upper'] if not pd.isna(prev['BB_Upper']) else latest['BB_Upper']
                prev_bb_lower = prev['BB_Lower'] if not pd.isna(prev['BB_Lower']) else latest['BB_Lower']
                prev_bb_middle = prev['BB_Middle'] if not pd.isna(prev['BB_Middle']) else latest['BB_Middle']
                
                # 计算带宽（布林带宽度）
                current_bandwidth = (latest['BB_Upper'] - latest['BB_Lower']) / latest['BB_Middle'] if latest['BB_Middle'] > 0 else 0
                prev_bandwidth = (prev_bb_upper - prev_bb_lower) / prev_bb_middle if prev_bb_middle > 0 else 0
                
                if prev_bandwidth > 0:
                    bandwidth_change_rate = (current_bandwidth - prev_bandwidth) / prev_bandwidth
                    
                    # 张口扩大（趋势启动或加速）
                    if bandwidth_change_rate > 0.1:
                        if current_price > prev['Close']:
                            buy_score += 1
                            signals.append("布林带张口，上涨趋势启动")
                        elif current_price < prev['Close']:
                            sell_score += 1
                            signals.append("布林带张口，下跌趋势加速")
        
        # 5. 成交量信号（改进版：添加量价背离检测）
        volume_ratio = latest['Volume'] / latest['Volume_MA'] if latest['Volume_MA'] > 0 else 1
        price_change = current_price - prev['Close']
        price_change_pct = (price_change / prev['Close'] * 100) if prev['Close'] > 0 else 0
        
        # 放量上涨/下跌
        if volume_ratio > 1.5:
            if price_change > 0:
                buy_score += 1
                signals.append("放量上涨，资金流入")
            elif price_change < 0:
                sell_score += 1
                signals.append("放量下跌，资金流出")
        
        # 量价背离检测
        if volume_ratio < 0.8:
            if price_change_pct > 0:
                # 价格上涨但成交量萎缩（上涨动能不足）
                sell_score += 1
                signals.append("量价背离：上涨但缩量，动能不足")
            elif price_change_pct < 0:
                # 价格下跌但成交量萎缩（抛压减轻）
                buy_score += 1
                signals.append("量价背离：下跌但缩量，抛压减轻")
        
        # 综合判断（改进版：分级阈值系统）
        total_score = buy_score + sell_score
        net_score = buy_score - sell_score  # 净分数差值
        
        if total_score == 0:
            signal = 'HOLD'
            strength = 0
            reason = "无明显信号，建议持有观望"
        elif net_score >= 8:
            signal = 'STRONG_BUY'  # 强烈买入
            signal_type = 'BUY'
        elif net_score >= 4:
            signal = 'BUY'  # 买入
            signal_type = 'BUY'
        elif net_score >= 2:
            signal = 'CAUTIOUS_BUY'  # 谨慎买入
            signal_type = 'BUY'
        elif net_score <= -8:
            signal = 'STRONG_SELL'  # 强烈卖出
            signal_type = 'SELL'
        elif net_score <= -4:
            signal = 'SELL'  # 卖出
            signal_type = 'SELL'
        elif net_score <= -2:
            signal = 'CAUTIOUS_SELL'  # 谨慎卖出
            signal_type = 'SELL'
        else:
            signal = 'HOLD'
            signal_type = 'HOLD'
            strength = 0
            reason = "多空力量均衡，建议持有观望"
        
        # 计算信号强度（买入或卖出）
        if signal_type == 'BUY':
            # 改进的信号强度计算：
            # 1. 基础强度：买入分数在总分数中的占比
            base_strength = (buy_score / total_score) * 100 if total_score > 0 else 0
            
            # 2. 根据买入分数的绝对值调整（买入分数越高，强度越高）
            # 最大买入分数约为18分（包含新增的背离、零轴突破等信号）
            # RSI超卖3 + RSI背离2 + MACD金叉2 + MACD零轴1 + 均线2 + 布林带2 + 布林带张口1 + 成交量1 + 量价背离1 + MACD柱1 + RSI低位1 + 其他
            max_possible_buy_score = 18
            score_factor = min((buy_score / max_possible_buy_score) * 100, 100)
            
            # 3. 综合计算：基础强度占60%，分数因子占40%
            # 这样即使卖出分数为0，买入分数低时强度也不会是100%
            strength = int(base_strength * 0.6 + score_factor * 0.4)
            strength = min(strength, 100)
            
            reason = " | ".join(signals[:3])
        elif signal_type == 'SELL':
            # 同样的逻辑用于卖出信号
            base_strength = (sell_score / total_score) * 100 if total_score > 0 else 0
            max_possible_sell_score = 18  # 更新最大分数（包含新增的背离等信号）
            score_factor = min((sell_score / max_possible_sell_score) * 100, 100)
            strength = int(base_strength * 0.6 + score_factor * 0.4)
            strength = min(strength, 100)
            reason = " | ".join(signals[:3])
        
        # 信号强度等级划分
        if signal_type in ['BUY', 'SELL']:
            if strength >= 80:
                strength_level = "极强"
            elif strength >= 70:
                strength_level = "强"
            elif strength >= 60:
                strength_level = "中等"
            elif strength >= 50:
                strength_level = "弱"
            elif strength >= 40:
                strength_level = "很弱"
            else:
                strength_level = "极弱"
        else:
            strength_level = "无"
        
        return {
            'signal': signal,  # 详细信号：STRONG_BUY, BUY, CAUTIOUS_BUY, HOLD, CAUTIOUS_SELL, SELL, STRONG_SELL
            'signal_type': signal_type if 'signal_type' in locals() else 'HOLD',  # 简化信号：BUY, SELL, HOLD
            'strength': strength,
            'strength_level': strength_level if 'strength_level' in locals() else '无',
            'buy_score': buy_score,
            'sell_score': sell_score,
            'net_score': net_score,  # 净分数差值
            'reason': reason,
            'indicators': {
                'RSI': round(rsi, 2) if not pd.isna(rsi) else None,
                'MACD': round(macd, 2) if not pd.isna(macd) else None,
                'MA5': round(latest['MA5'], 2) if not pd.isna(latest['MA5']) else None,
                'MA20': round(latest['MA20'], 2) if not pd.isna(latest['MA20']) else None,
            }
        }
