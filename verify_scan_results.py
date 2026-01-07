"""
扫描结果验证程序示例
用于验证历史扫描结果的准确性
"""
import pandas as pd
from scan_cache import ScanCache
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class ScanResultVerifier:
    """扫描结果验证器"""
    
    def __init__(self):
        self.scan_cache = ScanCache()
    
    def load_historical_results(self, scan_type: str, date: str) -> Optional[pd.DataFrame]:
        """
        加载指定日期的历史扫描结果
        
        Args:
            scan_type: 扫描类型（'signal_analysis' 或 'trend_start_signal'）
            date: 日期（YYYYMMDD格式，如 '20250106'）
        
        Returns:
            DataFrame: 扫描结果DataFrame，如果不存在则返回None
        """
        return self.scan_cache.get_historical_results_csv(scan_type, date)
    
    def list_available_dates(self, scan_type: str) -> List[str]:
        """
        列出可用的历史扫描日期
        
        Args:
            scan_type: 扫描类型
        
        Returns:
            list: 日期列表（YYYYMMDD格式）
        """
        return self.scan_cache.list_available_dates(scan_type)
    
    def verify_signal_accuracy(self, scan_type: str, date: str, 
                               actual_prices: Dict[str, float]) -> Dict:
        """
        验证信号准确性
        
        Args:
            scan_type: 扫描类型
            date: 扫描日期
            actual_prices: 实际价格字典 {symbol: actual_price}
        
        Returns:
            dict: 验证结果统计
        """
        df = self.load_historical_results(scan_type, date)
        if df is None or df.empty:
            return {'error': '未找到该日期的扫描结果'}
        
        # 只验证买入信号
        if 'signal_type' in df.columns:
            buy_signals = df[df['signal_type'] == 'BUY'].copy()
        elif 'signal' in df.columns:
            buy_signals = df[df['signal'].str.contains('BUY', case=False, na=False)].copy()
        else:
            return {'error': '结果中未找到信号字段'}
        
        if buy_signals.empty:
            return {'total_signals': 0, 'message': '该日期没有买入信号'}
        
        # 计算收益率
        results = []
        for idx, row in buy_signals.iterrows():
            symbol = row.get('symbol', '')
            scan_price = row.get('price', 0)
            
            if symbol in actual_prices:
                actual_price = actual_prices[symbol]
                if scan_price > 0:
                    return_rate = (actual_price - scan_price) / scan_price * 100
                    results.append({
                        'symbol': symbol,
                        'name': row.get('name', ''),
                        'scan_price': scan_price,
                        'actual_price': actual_price,
                        'return_rate': return_rate,
                        'signal_strength': row.get('strength', 0)
                    })
        
        if not results:
            return {'total_signals': len(buy_signals), 'verified': 0, 
                   'message': '没有找到对应的实际价格数据'}
        
        results_df = pd.DataFrame(results)
        
        # 统计信息
        total_signals = len(buy_signals)
        verified_count = len(results)
        positive_returns = len(results_df[results_df['return_rate'] > 0])
        avg_return = results_df['return_rate'].mean()
        
        return {
            'date': date,
            'total_signals': total_signals,
            'verified_count': verified_count,
            'positive_returns': positive_returns,
            'win_rate': (positive_returns / verified_count * 100) if verified_count > 0 else 0,
            'avg_return': avg_return,
            'max_return': results_df['return_rate'].max(),
            'min_return': results_df['return_rate'].min(),
            'details': results_df.to_dict('records')
        }
    
    def compare_dates(self, scan_type: str, dates: List[str]) -> pd.DataFrame:
        """
        比较多个日期的扫描结果
        
        Args:
            scan_type: 扫描类型
            dates: 日期列表
        
        Returns:
            DataFrame: 比较结果
        """
        comparison_data = []
        
        for date in dates:
            df = self.load_historical_results(scan_type, date)
            if df is not None and not df.empty:
                if 'signal_type' in df.columns:
                    buy_count = len(df[df['signal_type'] == 'BUY'])
                elif 'signal' in df.columns:
                    buy_count = len(df[df['signal'].str.contains('BUY', case=False, na=False)])
                else:
                    buy_count = 0
                
                comparison_data.append({
                    'date': date,
                    'total_scanned': len(df),
                    'buy_signals': buy_count,
                    'signal_rate': (buy_count / len(df) * 100) if len(df) > 0 else 0
                })
        
        return pd.DataFrame(comparison_data)


# 使用示例
if __name__ == "__main__":
    verifier = ScanResultVerifier()
    
    # 示例1：列出可用的历史日期
    print("=== 可用的历史扫描日期 ===")
    dates = verifier.list_available_dates('trend_start_signal')
    print(f"趋势启动信号: {dates}")
    
    dates = verifier.list_available_dates('signal_analysis')
    print(f"技术指标评分: {dates}")
    
    # 示例2：加载指定日期的结果
    if dates:
        latest_date = dates[0]  # 最新的日期
        print(f"\n=== 加载 {latest_date} 的扫描结果 ===")
        df = verifier.load_historical_results('trend_start_signal', latest_date)
        if df is not None:
            print(f"共 {len(df)} 条记录")
            print(df.head())
    
    # 示例3：验证信号准确性（需要提供实际价格数据）
    # actual_prices = {
    #     '000001.SS': 12.50,  # 实际价格
    #     '600519.SS': 1800.00,
    #     # ... 更多股票的实际价格
    # }
    # verification = verifier.verify_signal_accuracy('trend_start_signal', latest_date, actual_prices)
    # print(f"\n=== 验证结果 ===")
    # print(verification)
    
    # 示例4：比较多个日期的结果
    # if len(dates) >= 2:
    #     comparison = verifier.compare_dates('trend_start_signal', dates[:3])
    #     print(f"\n=== 日期比较 ===")
    #     print(comparison)
