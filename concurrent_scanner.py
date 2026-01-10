"""
并发股票扫描模块
提供并发扫描功能，大幅提升扫描速度
"""
import concurrent.futures
import time
from typing import List, Dict, Optional
import pandas as pd
from threading import Lock
from datetime import datetime
from stock_analyzer import StockAnalyzer, PredictiveSignalModel
from scan_cache import ScanCache

# 全局锁，用于线程安全的结果更新
_result_lock = Lock()

def should_skip_stock(symbol: str, name: str) -> bool:
    """判断是否应该跳过该股票"""
    name_str = str(name)
    # 跳过ST股票
    if 'ST' in name_str.upper():
        return True
    
    # 跳过退市股票
    if '退市' in name_str:
        return True
    
    # 跳过无效代码
    code = symbol.replace('.SS', '').replace('.SZ', '')
    if (code.startswith('920') or code.startswith('900')) and len(code) == 6:
        return True
    
    return False

def analyze_single_stock_worker(symbol: str, name: str, period: str, end_date_str: Optional[str], 
                                scan_cache: ScanCache, scan_scope: str, realtime_results_file: str, cache_date: str) -> Optional[Dict]:
    """
    单个股票分析的工作线程函数（用于并发处理）
    
    Args:
        symbol: 股票代码
        name: 股票名称
        period: 数据周期
        end_date_str: 结束日期字符串
        scan_cache: 扫描缓存对象
        scan_scope: 扫描范围
        realtime_results_file: 实时结果文件路径
    
    Returns:
        Dict: 分析结果，如果失败返回None
    """
    try:
        analyzer = StockAnalyzer(symbol, period, end_date=end_date_str)
        
        if analyzer.fetch_data():
            signals = analyzer.generate_signals()
            info = analyzer.get_current_info()
            
            if signals and info:
                # 计算预测因子（用于预测模型）
                predictive_factors = {}
                predictive_recommendation = {}
                try:
                    predictive_factors = analyzer.calculate_predictive_factors()
                    
                    # 创建预测模型实例（每个线程独立）
                    predictive_model = PredictiveSignalModel()
                    
                    # 获取市场趋势评分
                    market_trend_score = predictive_model.get_market_trend_score()
                    
                    # 生成预测推荐
                    sector_consensus = 0.0  # 全盘扫描时暂时不使用板块共识度
                    
                    # 准备信号字典（包含current_price）
                    signal_dict = signals.copy()
                    signal_dict['current_price'] = info.get('current_price', 0)
                    
                    # 生成预测推荐
                    predictive_recommendation = predictive_model.generate_recommendation_strength(
                        stock_factors=predictive_factors,
                        sector_consensus=sector_consensus,
                        market_trend_score=market_trend_score,
                        stock_signal=signal_dict
                    )
                except Exception as e:
                    # 预测模型失败不影响基础分析
                    pass
                
                # 确定信号类型
                signal_value = signals.get('signal', 'HOLD')
                signal_type_value = signals.get('signal_type', 'HOLD')
                if signal_type_value == 'HOLD':
                    if signals.get('buy_score', 0) > signals.get('sell_score', 0):
                        signal_type_value = 'BUY'
                    elif signals.get('sell_score', 0) > signals.get('buy_score', 0):
                        signal_type_value = 'SELL'
                
                result = {
                    'symbol': symbol,
                    'name': name,
                    'price': info.get('current_price', 0),
                    'change_percent': info.get('change_percent', 0),
                    'signal': signal_value,
                    'signal_type': signal_type_value,
                    'strength': signals.get('strength', 0),
                    'strength_level': signals.get('strength_level', ''),
                    'buy_score': signals.get('buy_score', 0),
                    'sell_score': signals.get('sell_score', 0),
                    'net_score': signals.get('net_score', 0),
                    'reason': signals.get('reason', ''),
                    'predictive_score': predictive_recommendation.get('final_score', 0),
                    'predictive_recommendation': predictive_recommendation.get('recommendation', ''),
                    'predictive_stop_loss': predictive_recommendation.get('stop_loss', 0),
                    'predictive_position': predictive_recommendation.get('position_suggestion', ''),
                    'suggested_stop_loss': signals.get('suggested_stop_loss', 0),
                    'position_suggestion': signals.get('position_suggestion', ''),
                    'stop_loss_type': predictive_recommendation.get('stop_loss_type', ''),
                    'time_stop_loss': predictive_recommendation.get('time_stop_loss', '')
                }
                
                # 保存到缓存（线程安全，使用正确的日期）
                with _result_lock:
                    scan_cache.add_scanned_stock('signal_analysis', symbol, result, 
                                                date=cache_date, scan_scope=scan_scope, period=period)
                
                # 如果是买入信号，写入实时文件（线程安全）
                if signal_type_value == 'BUY':
                    try:
                        with _result_lock:
                            with open(realtime_results_file, 'a', encoding='utf-8') as f:
                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                f.write(f"\n{'='*80}\n")
                                f.write(f"时间: {timestamp}\n")
                                f.write(f"股票代码: {result['symbol']}\n")
                                f.write(f"股票名称: {result['name']}\n")
                                f.write(f"当前价格: {result['price']:.2f}\n")
                                f.write(f"涨跌幅: {result['change_percent']:.2f}%\n")
                                f.write(f"信号类型: {result['signal']}\n")
                                f.write(f"信号强度: {result['strength']}%\n")
                                f.write(f"强度等级: {result.get('strength_level', 'N/A')}\n")
                                f.write(f"买入分数: {result.get('buy_score', 0)}\n")
                                f.write(f"净分数: {result.get('net_score', 0)}\n")
                                f.write(f"分析原因: {result.get('reason', 'N/A')}\n")
                                f.write(f"{'='*80}\n")
                                f.flush()
                    except Exception as e:
                        pass
                
                return result
    except Exception as e:
        # 静默处理错误，避免影响其他线程
        pass
    
    return None

def analyze_stocks_concurrent(stock_list: pd.DataFrame, period: str, end_date_str: Optional[str],
                             scan_cache: ScanCache, scan_scope: str, realtime_results_file: str,
                             cache_date: str, max_workers: int = 10, batch_size: int = 50) -> List[Dict]:
    """
    并发分析股票
    
    Args:
        stock_list: 股票列表DataFrame
        period: 数据周期
        end_date_str: 结束日期字符串
        scan_cache: 扫描缓存对象
        scan_scope: 扫描范围
        realtime_results_file: 实时结果文件路径
        max_workers: 并发线程数
        batch_size: 每批处理数量
    
    Returns:
        List[Dict]: 分析结果列表
    """
    results = []
    failed_stocks = []
    
    # 过滤掉需要跳过的股票
    valid_stocks = []
    for idx, row in stock_list.iterrows():
        symbol = row['symbol']
        name = row.get('name', symbol)
        if not should_skip_stock(symbol, name):
            valid_stocks.append((idx, row))
    
    if not valid_stocks:
        return results
    
    # 将股票列表分成批次
    batches = []
    for i in range(0, len(valid_stocks), batch_size):
        batch = valid_stocks[i:i+batch_size]
        batches.append(batch)
    
    for batch_idx, batch in enumerate(batches, 1):
        batch_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_stock = {}
            for idx, row in batch:
                symbol = row['symbol']
                name = row.get('name', symbol)
                
                future = executor.submit(
                    analyze_single_stock_worker,
                    symbol, name, period, end_date_str,
                    scan_cache, scan_scope, realtime_results_file, cache_date
                )
                future_to_stock[future] = (symbol, name)
            
            # 处理完成的任务
            completed = 0
            for future in concurrent.futures.as_completed(future_to_stock):
                symbol, name = future_to_stock[future]
                try:
                    result = future.result(timeout=30)  # 30秒超时
                    if result:
                        batch_results.append(result)
                        completed += 1
                    else:
                        failed_stocks.append(symbol)
                except concurrent.futures.TimeoutError:
                    failed_stocks.append(symbol)
                except Exception as e:
                    failed_stocks.append(symbol)
        
        results.extend(batch_results)
        
        # 每批之间添加延迟，避免限流
        if batch_idx < len(batches):
            time.sleep(1)  # 批次间延迟1秒
    
    return results
