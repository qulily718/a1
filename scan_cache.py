"""
扫描缓存模块
用于记录当天扫描过的股票，避免重复扫描
同时保存每天的扫描结果到文件，方便后续验证程序使用
"""
import json
import os
from datetime import datetime
from typing import Set, Optional, List, Dict
import pandas as pd


class ScanCache:
    """扫描缓存管理器"""
    
    def __init__(self, cache_dir: str = "scan_cache", results_dir: str = "scan_results"):
        """
        初始化扫描缓存
        
        Args:
            cache_dir: 缓存文件目录（用于快速查找已扫描股票）
            results_dir: 结果文件目录（用于保存完整的扫描结果，供验证程序使用）
        """
        self.cache_dir = cache_dir
        self.results_dir = results_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
    
    def _get_cache_file_path(self, scan_type: str, date: Optional[str] = None, scan_scope: Optional[str] = None, period: Optional[str] = None) -> str:
        """
        获取缓存文件路径
        
        Args:
            scan_type: 扫描类型（'signal_analysis' 或 'trend_start_signal'）
            date: 日期（YYYYMMDD格式），如果为None则使用今天
            scan_scope: 扫描范围（'strong_sectors' 或 'all_stocks'），如果为None则不区分范围
            period: 数据周期（如'1mo', '3mo', '1y'等），如果为None则不区分周期
        
        Returns:
            str: 缓存文件路径
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        # 对于 signal_analysis，根据扫描范围和period区分文件名（不同period应该使用不同的缓存）
        if scan_type == 'signal_analysis':
            if scan_scope and period:
                filename = f"{scan_type}_{scan_scope}_{period}_{date}.json"
            elif scan_scope:
                filename = f"{scan_type}_{scan_scope}_{date}.json"
            elif period:
                filename = f"{scan_type}_{period}_{date}.json"
            else:
                filename = f"{scan_type}_{date}.json"
        # 对于 trend_start_signal，根据扫描范围区分文件名
        elif scan_type == 'trend_start_signal' and scan_scope:
            filename = f"{scan_type}_{scan_scope}_{date}.json"
        else:
            filename = f"{scan_type}_{date}.json"
        
        return os.path.join(self.cache_dir, filename)
    
    def get_scanned_stocks(self, scan_type: str, date: Optional[str] = None, scan_scope: Optional[str] = None, period: Optional[str] = None) -> Set[str]:
        """
        获取指定日期已扫描的股票列表
        
        Args:
            scan_type: 扫描类型
            date: 日期（YYYYMMDD格式），如果为None则使用今天
            scan_scope: 扫描范围（'strong_sectors' 或 'all_stocks'），如果为None则不区分范围
            period: 数据周期（如'1mo', '3mo', '1y'等），如果为None则不区分周期
        
        Returns:
            Set[str]: 已扫描的股票代码集合
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        cache_file = self._get_cache_file_path(scan_type, date=date, scan_scope=scan_scope, period=period)
        
        if not os.path.exists(cache_file):
            return set()
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查是否是指定日期的缓存
                if data.get('date') == date:
                    return set(data.get('scanned_stocks', []))
                else:
                    # 不是指定日期的缓存，删除旧文件
                    os.remove(cache_file)
                    return set()
        except Exception as e:
            print(f"读取扫描缓存失败: {e}")
            return set()
    
    def get_cached_results_from_other_scope(self, scan_type: str, symbol: str, date: Optional[str] = None, other_scope: Optional[str] = None) -> Optional[dict]:
        """
        从另一个扫描范围的缓存中获取指定股票的扫描结果
        
        Args:
            scan_type: 扫描类型
            symbol: 股票代码
            date: 日期（YYYYMMDD格式），如果为None则使用今天
            other_scope: 另一个扫描范围（'strong_sectors' 或 'all_stocks'）
        
        Returns:
            dict: 扫描结果，如果不存在则返回None
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        if not other_scope:
            return None
        
        cache_file = self._get_cache_file_path(scan_type, date, other_scope)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查是否是指定日期的缓存
                if data.get('date') == date:
                    results = data.get('results', {})
                    return results.get(symbol)
        except Exception as e:
            print(f"读取其他范围缓存失败: {e}")
        
        return None
    
    def add_scanned_stock(self, scan_type: str, symbol: str, result: Optional[dict] = None, date: Optional[str] = None, scan_scope: Optional[str] = None, period: Optional[str] = None):
        """
        添加已扫描的股票
        
        Args:
            scan_type: 扫描类型
            symbol: 股票代码
            result: 扫描结果（可选，用于保存结果）
            date: 日期（YYYYMMDD格式），如果为None则使用今天
            scan_scope: 扫描范围（'strong_sectors' 或 'all_stocks'），如果为None则不区分范围
            period: 数据周期（如'1mo', '3mo', '1y'等），如果为None则不区分周期
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        cache_file = self._get_cache_file_path(scan_type, date=date, scan_scope=scan_scope, period=period)
        
        # 读取现有缓存
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = {'date': date, 'period': period, 'scanned_stocks': [], 'results': {}}
        else:
            data = {'date': date, 'period': period, 'scanned_stocks': [], 'results': {}}
        
        # 检查日期和period是否匹配
        if data.get('date') != date:
            # 不是指定日期的缓存，重新开始
            data = {'date': date, 'period': period, 'scanned_stocks': [], 'results': {}}
        elif period and data.get('period') != period:
            # period不匹配，重新开始（不同period应该使用不同的数据）
            data = {'date': date, 'period': period, 'scanned_stocks': [], 'results': {}}
        
        # 添加股票代码
        if symbol not in data['scanned_stocks']:
            data['scanned_stocks'].append(symbol)
        
        # 保存结果（如果有）
        if result is not None:
            if 'results' not in data:
                data['results'] = {}
            data['results'][symbol] = result
        
        # 写入文件
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()  # 立即刷新到磁盘，确保数据立即可读
            # 调试信息：显示生成的文件名
            if period:
                print(f"✅ 已保存扫描缓存: {os.path.basename(cache_file)} (period={period})")
        except Exception as e:
            print(f"❌ 保存扫描缓存失败: {e}, 文件路径: {cache_file}")
    
    def get_cached_results(self, scan_type: str, scan_scope: Optional[str] = None, period: Optional[str] = None) -> list:
        """
        获取今天已扫描的结果
        
        Args:
            scan_type: 扫描类型
            scan_scope: 扫描范围（'strong_sectors' 或 'all_stocks'），如果为None则不区分范围
            period: 数据周期（如'1mo', '3mo', '1y'等），如果为None则不区分周期
        
        Returns:
            list: 扫描结果列表
        """
        cache_file = self._get_cache_file_path(scan_type, scan_scope=scan_scope, period=period)
        
        if not os.path.exists(cache_file):
            return []
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 验证日期和period是否匹配
                if data.get('date') == datetime.now().strftime('%Y%m%d'):
                    # 如果指定了period，验证period是否匹配
                    if period and data.get('period') != period:
                        # period不匹配，返回空列表（不同period应该使用不同的数据）
                        return []
                    results = data.get('results', {})
                    return list(results.values())
                else:
                    return []
        except Exception as e:
            print(f"读取扫描结果失败: {e}")
            return []
    
    def clear_today_cache(self, scan_type: str, scan_scope: Optional[str] = None, period: Optional[str] = None):
        """
        清除今天的缓存
        
        Args:
            scan_type: 扫描类型
            scan_scope: 扫描范围（'strong_sectors' 或 'all_stocks'），如果为None则不区分范围
            period: 数据周期（如'1mo', '3mo', '1y'等），如果为None则不区分周期
        """
        cache_file = self._get_cache_file_path(scan_type, scan_scope=scan_scope, period=period)
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception as e:
                print(f"清除缓存失败: {e}")
    
    def get_cache_stats(self, scan_type: str, scan_scope: Optional[str] = None) -> dict:
        """
        获取缓存统计信息
        
        Args:
            scan_type: 扫描类型
            scan_scope: 扫描范围（'strong_sectors' 或 'all_stocks'），如果为None则不区分范围
        
        Returns:
            dict: 统计信息
        """
        scanned_stocks = self.get_scanned_stocks(scan_type, scan_scope=scan_scope)
        cached_results = self.get_cached_results(scan_type, scan_scope=scan_scope)
        
        return {
            'scanned_count': len(scanned_stocks),
            'cached_results_count': len(cached_results),
            'date': datetime.now().strftime('%Y-%m-%d')
        }
    
    def _get_results_file_path(self, scan_type: str, date: Optional[str] = None) -> tuple:
        """
        获取结果文件路径（CSV和JSON）
        
        Args:
            scan_type: 扫描类型
            date: 日期（YYYYMMDD格式），如果为None则使用今天
        
        Returns:
            tuple: (csv_path, json_path)
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        csv_filename = f"{scan_type}_results_{date}.csv"
        json_filename = f"{scan_type}_results_{date}.json"
        
        csv_path = os.path.join(self.results_dir, csv_filename)
        json_path = os.path.join(self.results_dir, json_filename)
        
        return csv_path, json_path
    
    def save_daily_results(self, scan_type: str, results: List[Dict], date: Optional[str] = None):
        """
        保存每天的扫描结果到文件（CSV和JSON格式）
        
        Args:
            scan_type: 扫描类型
            results: 扫描结果列表
            date: 日期（YYYYMMDD格式），如果为None则使用今天
        """
        if not results:
            return
        
        csv_path, json_path = self._get_results_file_path(scan_type, date)
        
        try:
            # 保存为CSV（便于Excel查看和验证程序使用）
            df = pd.DataFrame(results)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            # 保存为JSON（保留完整信息，包括嵌套的details等）
            results_data = {
                'date': date if date else datetime.now().strftime('%Y%m%d'),
                'scan_type': scan_type,
                'total_count': len(results),
                'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'results': results
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 扫描结果已保存: CSV={csv_path}, JSON={json_path}")
        except Exception as e:
            print(f"保存扫描结果失败: {e}")
    
    def get_historical_results(self, scan_type: str, date: str) -> Optional[Dict]:
        """
        获取指定日期的历史扫描结果
        
        Args:
            scan_type: 扫描类型
            date: 日期（YYYYMMDD格式，如 '20250106'）
        
        Returns:
            dict: 包含扫描结果的字典，如果不存在则返回None
        """
        _, json_path = self._get_results_file_path(scan_type, date)
        
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取历史扫描结果失败: {e}")
            return None
    
    def list_available_dates(self, scan_type: str) -> List[str]:
        """
        列出可用的历史扫描日期
        
        Args:
            scan_type: 扫描类型
        
        Returns:
            list: 日期列表（YYYYMMDD格式）
        """
        dates = []
        pattern = f"{scan_type}_results_"
        
        try:
            for filename in os.listdir(self.results_dir):
                if filename.startswith(pattern) and filename.endswith('.json'):
                    # 提取日期：scan_type_results_YYYYMMDD.json
                    date_part = filename.replace(pattern, '').replace('.json', '')
                    if len(date_part) == 8 and date_part.isdigit():
                        dates.append(date_part)
            
            dates.sort(reverse=True)  # 最新的在前
            return dates
        except Exception as e:
            print(f"列出历史日期失败: {e}")
            return []
    
    def get_historical_results_csv(self, scan_type: str, date: str) -> Optional[pd.DataFrame]:
        """
        获取指定日期的历史扫描结果（CSV格式，返回DataFrame）
        
        Args:
            scan_type: 扫描类型
            date: 日期（YYYYMMDD格式）
        
        Returns:
            DataFrame: 扫描结果DataFrame，如果不存在则返回None
        """
        csv_path, _ = self._get_results_file_path(scan_type, date)
        
        if not os.path.exists(csv_path):
            return None
        
        try:
            return pd.read_csv(csv_path, encoding='utf-8-sig')
        except Exception as e:
            print(f"读取历史CSV结果失败: {e}")
            return None
    
    def save_market_environment(self, market_env: Dict):
        """
        保存市场环境分析结果到文件（持久化存储，一天只分析一次）
        即使重启应用，文件仍然保留，无需重新分析
        
        Args:
            market_env: 市场环境分析结果字典
        """
        cache_file = os.path.join(self.cache_dir, f"market_env_{datetime.now().strftime('%Y%m%d')}.json")
        
        try:
            # 处理DataFrame（转换为字典以便JSON序列化）
            market_env_copy = market_env.copy()
            
            # 如果有sector_details_df，转换为字典
            if 'sector_details_df' in market_env_copy and isinstance(market_env_copy['sector_details_df'], pd.DataFrame):
                if not market_env_copy['sector_details_df'].empty:
                    market_env_copy['sector_details_df'] = market_env_copy['sector_details_df'].to_dict('records')
                else:
                    market_env_copy['sector_details_df'] = []
            
            # 保存到文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(market_env_copy, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"✅ 市场环境分析结果已保存: {cache_file}")
        except Exception as e:
            print(f"保存市场环境分析结果失败: {e}")
    
    def get_market_environment(self) -> Optional[Dict]:
        """
        从文件读取今天的市场环境分析结果（如果已分析过）
        即使重启应用，只要文件存在就能读取，无需重新分析
        
        Returns:
            dict: 市场环境分析结果，如果不存在则返回None
        """
        cache_file = os.path.join(self.cache_dir, f"market_env_{datetime.now().strftime('%Y%m%d')}.json")
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 检查日期
                if 'timestamp' in data:
                    cache_date = data['timestamp'][:10]  # 提取日期部分
                    today = datetime.now().strftime('%Y-%m-%d')
                    if cache_date != today:
                        # 不是今天的数据，删除旧文件
                        os.remove(cache_file)
                        return None
                
                # 恢复DataFrame（如果有）
                if 'sector_details_df' in data and isinstance(data['sector_details_df'], list):
                    if data['sector_details_df']:
                        data['sector_details_df'] = pd.DataFrame(data['sector_details_df'])
                    else:
                        data['sector_details_df'] = pd.DataFrame()
                
                return data
        except Exception as e:
            print(f"读取市场环境分析结果失败: {e}")
            return None
    
    def clear_market_environment_cache(self):
        """
        清除今天的市场环境分析缓存（强制重新分析）
        """
        cache_file = os.path.join(self.cache_dir, f"market_env_{datetime.now().strftime('%Y%m%d')}.json")
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception as e:
                print(f"清除市场环境缓存失败: {e}")
