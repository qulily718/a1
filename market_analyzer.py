"""
宏观与板块数据引擎
负责市场环境判断、板块强度分析、资金流向等
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# 尝试导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


class MarketAnalyzer:
    """市场环境分析器"""
    
    def __init__(self):
        """初始化市场分析器"""
        pass
    
    def get_market_spot_data(self) -> Optional[pd.DataFrame]:
        """获取A股实时行情数据"""
        if not AKSHARE_AVAILABLE:
            return None
        
        try:
            df = ak.stock_zh_a_spot_em()
            return df
        except Exception as e:
            print(f"获取市场行情数据失败: {e}")
            return None
    
    def calculate_market_sentiment(self) -> Dict:
        """
        计算市场情绪指数 (0-100分)
        
        Returns:
            dict: 包含市场情绪评分和详细信息的字典
        """
        if not AKSHARE_AVAILABLE:
            return {'sentiment_score': 50, 'status': '中性', 'details': {}}
        
        try:
            # 获取市场行情
            df = self.get_market_spot_data()
            if df is None or df.empty:
                return {'sentiment_score': 50, 'status': '中性', 'details': {}}
            
            sentiment_score = 0
            details = {}
            
            # 1. 计算涨跌家数比（权重30%）
            if '涨跌幅' in df.columns:
                up_count = len(df[df['涨跌幅'] > 0])
                down_count = len(df[df['涨跌幅'] < 0])
                total_count = len(df[df['涨跌幅'] != 0])
                
                if total_count > 0:
                    advance_decline_ratio = up_count / total_count
                    # 转换为0-100分：0.5为中性(50分)，1.0为满分(100分)，0为0分
                    adr_score = min(advance_decline_ratio * 100 * 2, 100)
                    sentiment_score += adr_score * 0.3
                    details['涨跌比'] = f"{up_count}/{down_count}"
                    details['涨跌比得分'] = round(adr_score, 2)
            
            # 2. 计算平均涨跌幅（权重30%）
            if '涨跌幅' in df.columns:
                avg_change = df['涨跌幅'].mean()
                # 转换为0-100分：0%为50分，+2%为100分，-2%为0分
                change_score = max(0, min(100, 50 + (avg_change / 0.02) * 50))
                sentiment_score += change_score * 0.3
                details['平均涨跌幅'] = f"{avg_change:.2f}%"
                details['涨跌幅得分'] = round(change_score, 2)
            
            # 3. 计算涨停板数量（权重20%）
            if '涨跌幅' in df.columns:
                limit_up_count = len(df[df['涨跌幅'] >= 9.8])  # 接近涨停
                # 涨停数量评分：0个为0分，50个为100分
                limit_up_score = min(limit_up_count * 2, 100)
                sentiment_score += limit_up_score * 0.2
                details['涨停数量'] = limit_up_count
                details['涨停得分'] = round(limit_up_score, 2)
            
            # 4. 计算成交量变化（权重20%）
            if '成交量' in df.columns and '成交额' in df.columns:
                # 简化处理：使用成交额作为参考
                total_volume = df['成交额'].sum() if '成交额' in df.columns else 0
                # 这里简化处理，实际应该对比历史均值
                volume_score = 50  # 默认中性
                sentiment_score += volume_score * 0.2
                details['成交量得分'] = round(volume_score, 2)
            
            # 确定市场状态
            if sentiment_score >= 60:
                status = "积极"
            elif sentiment_score >= 40:
                status = "中性"
            else:
                status = "谨慎"
            
            return {
                'sentiment_score': round(sentiment_score, 2),
                'status': status,
                'details': details
            }
        except Exception as e:
            print(f"计算市场情绪失败: {e}")
            return {'sentiment_score': 50, 'status': '中性', 'details': {}}
    
    def _get_sector_base_adjustment(self, sector_name: str) -> float:
        """
        获取板块基础调整分（用于逻辑合理性检查）
        某些板块因政策、宏观环境等因素被长期看淡，给予负向调整
        
        Returns:
            float: 调整分数（负数为降权，正数为加权）
        """
        # 长期看淡的板块（可根据实际情况调整）
        negative_sectors = {
            '房地产开发': -3.0,  # 房地产政策环境
            '房地产服务': -2.5,
            '物业管理': -2.0,
            '建筑装饰': -1.5,
            '建筑材料': -1.0,
        }
        
        # 长期看好的板块（可根据实际情况调整）
        positive_sectors = {
            '人工智能': 1.0,
            '新能源': 0.5,
            '半导体': 0.5,
        }
        
        # 检查是否匹配
        for key, value in negative_sectors.items():
            if key in sector_name:
                return value
        
        for key, value in positive_sectors.items():
            if key in sector_name:
                return value
        
        return 0.0  # 无调整
    
    def _check_long_term_trend(self, hist_df: pd.DataFrame) -> Tuple[bool, float]:
        """
        检查板块长期趋势（过滤器）
        
        Args:
            hist_df: 板块历史数据
        
        Returns:
            Tuple[bool, float]: (是否通过长期趋势检查, 趋势健康度得分)
        """
        if hist_df is None or hist_df.empty or len(hist_df) < 60:
            return True, 0.0  # 数据不足时不过滤
        
        try:
            # 动态查找收盘价列
            actual_columns = hist_df.columns.tolist()
            close_col = None
            for col in actual_columns:
                col_str = str(col).lower()
                if '收盘' in col_str or 'close' in col_str:
                    close_col = col
                    break
            
            if close_col is None:
                return True, 0.0  # 找不到收盘价列，不过滤
            
            # 计算MA60和MA120
            if len(hist_df) >= 60:
                ma60 = hist_df[close_col].iloc[-60:].mean()
            else:
                ma60 = hist_df[close_col].iloc[-len(hist_df):].mean()
            
            if len(hist_df) >= 120:
                ma120 = hist_df[close_col].iloc[-120:].mean()
            else:
                ma120 = hist_df[close_col].iloc[-len(hist_df):].mean()
            
            current_price = hist_df[close_col].iloc[-1]
            
            # 检查是否空头排列（MA60 < MA120 且 价格 < MA60）
            is_bearish = (ma60 < ma120) and (current_price < ma60)
            
            # 计算趋势健康度得分（0-100）
            # 如果多头排列且价格在均线上方，得分高
            if current_price > ma60 > ma120:
                health_score = 100.0
            elif current_price > ma60 and ma60 > ma120 * 0.95:  # 接近多头
                health_score = 70.0
            elif current_price > ma60:
                health_score = 50.0
            elif not is_bearish:
                health_score = 30.0
            else:
                health_score = 0.0
            
            # 如果长期空头排列，返回False（将被过滤）
            return not is_bearish, health_score
            
        except Exception as e:
            print(f"检查长期趋势失败: {e}")
            return True, 0.0  # 出错时不过滤
    
    def get_sector_strength_detailed(self, top_n: int = 30, include_details: bool = True) -> Tuple[List[Tuple[str, float]], pd.DataFrame]:
        """
        计算板块强度榜单（详细版，包含诊断信息）
        
        Args:
            top_n: 返回前N个强势板块（按百分比，如30表示前30%）
            include_details: 是否返回详细得分明细表
        
        Returns:
            Tuple[List[Tuple[str, float]], pd.DataFrame]: 
                ([(板块名称, 强度得分), ...], 详细得分明细表)
        """
        if not AKSHARE_AVAILABLE:
            return [], pd.DataFrame()
        
        try:
            # 获取行业板块数据
            sector_list = []
            
            # 方法1：获取行业板块实时行情
            try:
                df = ak.stock_board_industry_name_em()
                if df is not None and not df.empty:
                    for idx, row in df.iterrows():
                        sector_name = row.get('板块名称', '')
                        if sector_name:
                            sector_list.append(sector_name)
            except Exception as e:
                print(f"获取行业板块失败: {e}")
            
            # 去重
            sector_list = list(set(sector_list))
            
            # 计算每个板块的强度
            sector_strength = []
            detail_records = []
            
            for sector in sector_list[:100]:  # 增加扫描数量
                try:
                    # 获取板块历史数据
                    hist_df = ak.stock_board_industry_hist_em(symbol=sector, period="日k", adjust="")
                    
                    if hist_df is None or hist_df.empty or len(hist_df) < 20:
                        continue
                    
                    # 动态处理列名（akshare的列名可能变化）
                    actual_columns = hist_df.columns.tolist()
                    close_col = None
                    volume_col = None
                    
                    for col in actual_columns:
                        col_str = str(col).lower()
                        if '收盘' in col_str or 'close' in col_str:
                            close_col = col
                        elif '成交量' in col_str or 'volume' in col_str:
                            volume_col = col
                    
                    if close_col is None:
                        # 如果找不到收盘价列，跳过
                        continue
                    
                    # 检查长期趋势（过滤器）
                    trend_pass, trend_health = self._check_long_term_trend(hist_df)
                    if not trend_pass:
                        # 长期空头趋势，跳过或大幅降权
                        continue
                    
                    # 计算各期涨跌幅
                    change_5d = 0.0
                    change_10d = 0.0
                    change_20d = 0.0
                    
                    if len(hist_df) >= 5:
                        change_5d = (hist_df[close_col].iloc[-1] / hist_df[close_col].iloc[-5] - 1) * 100
                    if len(hist_df) >= 10:
                        change_10d = (hist_df[close_col].iloc[-1] / hist_df[close_col].iloc[-10] - 1) * 100
                    if len(hist_df) >= 20:
                        change_20d = (hist_df[close_col].iloc[-1] / hist_df[close_col].iloc[-20] - 1) * 100
                    
                    # 计算成交量因子
                    volume_factor = 0.0
                    if volume_col and volume_col in hist_df.columns and len(hist_df) >= 20:
                        volume_ratio = hist_df[volume_col].iloc[-5:].mean() / hist_df[volume_col].iloc[-20:].mean() if len(hist_df) >= 20 else 1
                        # 成交量因子：1.0为中性，1.5为放量，0.8为缩量
                        volume_factor = (volume_ratio - 1.0) * 50  # 转换为-10到+10分
                        volume_factor = max(-10, min(10, volume_factor))
                    
                    # 尝试获取资金流向数据
                    money_flow_score = 0.0
                    try:
                        # 获取板块资金流向（如果API支持）
                        # 这里简化处理，实际需要根据akshare的具体API调整
                        # 暂时使用成交量作为代理
                        if volume_col and volume_col in hist_df.columns:
                            # 使用近5日成交量相对20日均量的变化作为资金流向代理
                            recent_volume = hist_df[volume_col].iloc[-5:].mean()
                            avg_volume = hist_df[volume_col].iloc[-20:].mean()
                            if avg_volume > 0:
                                flow_ratio = (recent_volume / avg_volume - 1.0) * 100
                                money_flow_score = max(-10, min(10, flow_ratio / 2))  # 转换为-10到+10分
                    except:
                        pass
                    
                    # 优化后的权重配置（降低短期波动权重）
                    # 5日涨幅权重20%（原50%），10日涨幅权重15%，20日涨幅权重25%（原30%）
                    # 资金流向权重30%（新增），成交量权重10%（原20%）
                    score_5d = change_5d * 0.20
                    score_10d = change_10d * 0.15
                    score_20d = change_20d * 0.25
                    score_money = money_flow_score * 0.30
                    score_volume = volume_factor * 0.10
                    
                    # 趋势健康度权重（新增）
                    score_trend = (trend_health / 100.0) * 5.0  # 0-5分
                    
                    # 基础调整分（板块逻辑合理性）
                    base_adjustment = self._get_sector_base_adjustment(sector)
                    
                    # 综合得分
                    strength_score = score_5d + score_10d + score_20d + score_money + score_volume + score_trend + base_adjustment
                    
                    # 记录详细得分明细
                    if include_details:
                        detail_records.append({
                            '板块名称': sector,
                            '综合得分': round(strength_score, 2),
                            '5日涨幅(%)': round(change_5d, 2),
                            '5日贡献': round(score_5d, 2),
                            '10日涨幅(%)': round(change_10d, 2),
                            '10日贡献': round(score_10d, 2),
                            '20日涨幅(%)': round(change_20d, 2),
                            '20日贡献': round(score_20d, 2),
                            '资金流向得分': round(money_flow_score, 2),
                            '资金贡献': round(score_money, 2),
                            '成交量因子': round(volume_factor, 2),
                            '成交量贡献': round(score_volume, 2),
                            '趋势健康度': round(trend_health, 1),
                            '趋势贡献': round(score_trend, 2),
                            '基础调整': round(base_adjustment, 2),
                        })
                    
                    sector_strength.append((sector, strength_score))
                    
                except Exception as e:
                    print(f"分析板块 {sector} 失败: {e}")
                    continue
            
            # 按强度得分排序
            sector_strength.sort(key=lambda x: x[1], reverse=True)
            
            # 创建详细得分明细表
            detail_df = pd.DataFrame(detail_records)
            if not detail_df.empty:
                detail_df = detail_df.sort_values('综合得分', ascending=False)
            
            # 返回前N%（或前N个）
            if top_n <= 1:
                # 如果top_n是百分比
                result_count = int(len(sector_strength) * top_n / 100)
            else:
                # 如果top_n是数量
                result_count = min(top_n, len(sector_strength))
            
            return sector_strength[:result_count], detail_df
        
        except Exception as e:
            print(f"获取板块强度失败: {e}")
            return [], pd.DataFrame()
    
    def get_sector_strength(self, top_n: int = 30) -> List[Tuple[str, float]]:
        """
        计算板块强度榜单（简化版，兼容旧接口）
        
        Args:
            top_n: 返回前N个强势板块（按百分比，如30表示前30%）
        
        Returns:
            List[Tuple[str, float]]: [(板块名称, 强度得分), ...]
        """
        sector_strength, _ = self.get_sector_strength_detailed(top_n=top_n, include_details=False)
        return sector_strength
    
    def analyze_market_environment(self, include_details: bool = True) -> Dict:
        """
        综合分析市场环境
        
        Args:
            include_details: 是否包含详细的板块得分明细表
        
        Returns:
            dict: 包含市场状态、强势板块列表、详细得分明细等
        """
        # 计算市场情绪
        sentiment = self.calculate_market_sentiment()
        
        # 获取强势板块（详细版）
        strong_sectors, sector_details_df = self.get_sector_strength_detailed(top_n=30, include_details=include_details)  # 前30%
        
        # 综合判断
        market_status = sentiment['status']
        sentiment_score = sentiment['sentiment_score']
        
        # 如果市场状态为谨慎，且强势板块少于5个，建议空仓观望
        if market_status == "谨慎" and len(strong_sectors) < 5:
            recommendation = "空仓观望"
        elif market_status == "积极" and len(strong_sectors) >= 5:
            recommendation = "积极操作"
        else:
            recommendation = "谨慎操作"
        
        result = {
            'market_status': market_status,
            'sentiment_score': sentiment_score,
            'sentiment_details': sentiment['details'],
            'strong_sectors': strong_sectors,
            'recommendation': recommendation,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 添加详细得分明细表
        if include_details and not sector_details_df.empty:
            result['sector_details_df'] = sector_details_df
        
        return result


class TrendStartSignalDetector:
    """趋势启动信号识别器"""
    
    def __init__(self, period: str = "1mo"):
        """
        初始化趋势启动信号识别器
        
        Args:
            period: 数据周期
        """
        self.period = period
    
    def check_trend_start_signal(self, stock_data: pd.DataFrame, stock_code: str, 
                                 strong_sectors: List[str] = None) -> Tuple[bool, str, Dict]:
        """
        检查个股是否符合趋势启动信号
        
        Args:
            stock_data: 股票历史数据（包含技术指标）
            stock_code: 股票代码
            strong_sectors: 强势板块列表（可选）
        
        Returns:
            Tuple[bool, str, Dict]: (是否符合, 原因说明, 详细信息)
        """
        if stock_data is None or stock_data.empty or len(stock_data) < 20:
            return False, "数据不足", {}
        
        latest = stock_data.iloc[-1]
        prev = stock_data.iloc[-2] if len(stock_data) > 1 else latest
        
        details = {}
        reasons = []
        
        # 条件1：价格与均线趋势
        if 'MA5' in stock_data.columns and 'MA10' in stock_data.columns:
            ma5 = latest['MA5']
            ma10 = latest['MA10']
            current_price = latest['Close']
            
            # 计算MA10斜率（最近3日的平均变化）
            if len(stock_data) >= 3:
                ma10_slope = (ma10 - stock_data['MA10'].iloc[-3]) / stock_data['MA10'].iloc[-3] * 100
            else:
                ma10_slope = 0
            
            if current_price > ma10 and ma5 > ma10 and ma10_slope > 0:
                details['趋势条件'] = "通过"
                reasons.append("价格位于MA10之上，MA5>MA10，MA10斜率向上")
            else:
                return False, f"趋势条件不满足：价格={current_price:.2f}, MA5={ma5:.2f}, MA10={ma10:.2f}, MA10斜率={ma10_slope:.2f}%", details
        else:
            return False, "缺少均线数据", details
        
        # 条件2：量能检查
        if 'Volume' in stock_data.columns and 'Volume_MA' in stock_data.columns:
            volume = latest['Volume']
            volume_ma20 = latest['Volume_MA']
            
            volume_ratio = volume / volume_ma20 if volume_ma20 > 0 else 0
            
            if volume_ratio >= 1.8:
                details['量能条件'] = "通过"
                details['量能倍数'] = round(volume_ratio, 2)
                reasons.append(f"放量{volume_ratio:.2f}倍")
            else:
                return False, f"量能未达标：当前{volume_ratio:.2f}倍，需要≥1.8倍", details
        else:
            return False, "缺少成交量数据", details
        
        # 条件3：关键K线检查
        price_change = (current_price - prev['Close']) / prev['Close'] * 100 if prev['Close'] > 0 else 0
        
        # 检查是否创近10日新高
        if len(stock_data) >= 10:
            highest_10d = stock_data['Close'].iloc[-10:].max()
            is_new_high = current_price >= highest_10d * 0.995  # 允许0.5%误差
        else:
            is_new_high = False
        
        if price_change > 2.5 and is_new_high:
            details['K线条件'] = "通过"
            details['涨幅'] = f"{price_change:.2f}%"
            details['是否新高'] = "是"
            reasons.append(f"实体阳线{price_change:.2f}%，创近10日新高")
        else:
            return False, f"无关键启动K线：涨幅={price_change:.2f}%，新高={is_new_high}", details
        
        # 条件4：指标共振确认
        indicator_pass = False
        
        # RSI(6)在50-70之间
        if 'RSI' in stock_data.columns:
            rsi = latest['RSI']
            if not pd.isna(rsi) and 50 <= rsi <= 70:
                details['RSI'] = round(rsi, 2)
                reasons.append(f"RSI({rsi:.1f})处于强势区")
                indicator_pass = True
        
        # MACD在零轴上方金叉
        if 'MACD' in stock_data.columns and 'MACD_Signal' in stock_data.columns:
            macd = latest['MACD']
            macd_signal = latest['MACD_Signal']
            prev_macd = prev['MACD'] if not pd.isna(prev['MACD']) else 0
            
            if macd > 0 and macd > macd_signal and prev_macd <= prev['MACD_Signal']:
                details['MACD'] = "零轴上金叉"
                reasons.append("MACD零轴上方金叉")
                indicator_pass = True
        
        if not indicator_pass:
            return False, "指标共振条件不满足", details
        
        # 所有条件都满足
        details['信号强度'] = "高"
        details['启动理由'] = " | ".join(reasons)
        
        # 计算止损位（启动阳线最低价）
        stop_loss = latest['Low'] if 'Low' in stock_data.columns else current_price * 0.95
        
        return True, "符合趋势启动信号", {
            **details,
            'stop_loss': round(stop_loss, 2),
            'current_price': round(current_price, 2),
            'signal_strength': 85  # 趋势启动信号强度
        }
