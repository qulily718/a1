"""
算法验证程序
用于验证app.py中的算法
"""
import streamlit as st
from datetime import datetime, timedelta
import os
import json
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="算法验证",
    page_icon="📊",
    layout="wide"
)

# 添加字体大小调整CSS和按钮颜色样式
st.markdown("""
<style>
    /* 全局字体大小调整 */
    .main .block-container {
    font-size: 14px;
    }
    
    /* 标题字体大小 */
    h1 {
    font-size: 1.5rem !important;
    }
    h2 {
    font-size: 1.25rem !important;
    }
    h3 {
    font-size: 1.1rem !important;
    }
    h4 {
    font-size: 1rem !important;
    }
    
    /* Streamlit组件字体大小 */
    .stMarkdown h1 {
    font-size: 1.5rem !important;
    }
    .stMarkdown h2 {
    font-size: 1.25rem !important;
    }
    .stMarkdown h3 {
    font-size: 1.1rem !important;
    }
    .stMarkdown h4 {
    font-size: 1rem !important;
    }
    
    /* 按钮颜色改为冷色调（蓝色/青色） */
    .stButton > button {
    background-color: #1f77b4 !important;
    color: white !important;
    border: none !important;
    border-radius: 0.25rem !important;
    transition: background-color 0.3s ease !important;
    }
    
    .stButton > button:hover {
    background-color: #2c8fc7 !important;
    }
    
    .stButton > button:active {
    background-color: #1565a0 !important;
    }
    
    /* 禁用状态的按钮 */
    .stButton > button:disabled {
    background-color: #94a3b8 !important;
    color: #cbd5e1 !important;
    cursor: not-allowed !important;
    }
    
    /* 侧边栏字体 */
    .css-1d391kg {
    font-size: 14px;
    }
    
    /* 按钮和输入框字体 */
    .stButton > button, .stTextInput > div > div > input,
    .stSelectbox > div > div > select {
    font-size: 14px;
    }
    
    /* 表格字体 */
    .stDataFrame {
    font-size: 13px;
    }
    
    /* 指标卡片字体 */
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
    font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 算法验证程序")
st.markdown("---")

# 日期选择
st.subheader("📅 选择日期")
selected_date = st.date_input(
    "选择要分析的日期",
    value=datetime.now(),
    min_value=datetime(2020, 1, 1),
    max_value=datetime.now()
)

# 日期字符串
date_str = selected_date.strftime('%Y%m%d')

# 收益分析功能
st.markdown("---")
st.subheader("📈 收益分析")

# 买入时机选择
st.subheader("💰 买入时机设置")
buy_timing = st.radio(
    "选择买入时机：",
    ["当天买入", "隔天买入"],
    horizontal=True,
    help="当天买入：买入价为所选日期当天的收盘价，T+1为所选日期的第二天\n隔天买入：买入价为所选日期后第一个交易日的开盘价，T+1为所选日期的第三天"
)

if st.button("📊 分析推荐股票收益", type="primary"):
    # 解析TXT文件的函数
    def parse_result_file(file_path):
        """解析扫描结果TXT文件"""
        recommendations = []
        if not os.path.exists(file_path):
            return recommendations
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析文件内容
            sections = content.split('=' * 80)
            for section in sections:
                if '股票代码:' in section:
                    lines = section.strip().split('\n')
                    stock_info = {}
                    for line in lines:
                        if '股票代码:' in line:
                            stock_info['symbol'] = line.split('股票代码:')[1].strip()
                        elif '股票名称:' in line:
                            stock_info['name'] = line.split('股票名称:')[1].strip()
                        elif '当前价格:' in line:
                            try:
                                stock_info['price'] = float(line.split('当前价格:')[1].strip())
                            except:
                                pass
                    
                    if 'symbol' in stock_info and 'price' in stock_info:
                        recommendations.append(stock_info)
        except Exception as e:
            st.error(f"❌ 解析扫描结果文件失败: {e}")
        
        return recommendations
    
    # 解析JSON文件的函数
    def parse_json_file(file_path):
        """解析扫描结果JSON文件，返回完整的股票信息（包括所有评分字段）"""
        recommendations = []
        if not os.path.exists(file_path):
            return recommendations
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 如果是列表格式（trend_start_signal_all_stocks_YYYYMMDD.json）
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'symbol' in item and 'price' in item:
                        # 返回完整的item字典，包含所有字段
                        recommendations.append(item.copy())
            # 如果是字典格式，包含results字段（signal_analysis_all_stocks_*_YYYYMMDD.json）
            elif isinstance(data, dict):
                if 'results' in data:
                    results = data['results']
                    for symbol, item in results.items():
                        if isinstance(item, dict):
                            # 只提取买入信号的股票
                            signal_type = item.get('signal_type', '')
                            signal = item.get('signal', '')
                            if signal_type == 'BUY' or signal == 'BUY' or signal in ['STRONG_BUY', 'CAUTIOUS_BUY']:
                                # 返回完整的item字典，包含所有字段
                                stock_info = item.copy()
                                # 确保symbol字段存在
                                if 'symbol' not in stock_info:
                                    stock_info['symbol'] = symbol
                                recommendations.append(stock_info)
                # 如果是直接的字典格式（trend_start_signal格式）
                elif 'symbol' in data and 'price' in data:
                    # 返回完整的数据字典
                    recommendations.append(data.copy())
        except Exception as e:
            st.error(f"❌ 解析JSON文件失败: {e}")
        
        return recommendations
    
    # 查找扫描结果文件的多种方式
    def find_scan_results(date_str):
        """查找指定日期的扫描结果，支持多种文件格式
        
        Returns:
            tuple: (recommendations, source_file) - 推荐股票列表和来源文件路径
        """
        recommendations = []
        source_file = None
        
        # 方式1: 从trend_start_signal_all_stocks_YYYYMMDD.json读取（scan_cache目录）
        json_file1 = os.path.join("scan_cache", f"trend_start_signal_all_stocks_{date_str}.json")
        if os.path.exists(json_file1):
            recommendations = parse_json_file(json_file1)
            if recommendations:
                return recommendations, json_file1
        
        # 方式2: 从signal_analysis_all_stocks_*_YYYYMMDD.json读取（scan_cache目录，支持多个period）
        # 尝试常见的period: 1y, 6mo, 3mo, 1mo, 5y, 2y
        periods = ['1y', '6mo', '3mo', '1mo', '5y', '2y']
        for period in periods:
            json_file2 = os.path.join("scan_cache", f"signal_analysis_all_stocks_{period}_{date_str}.json")
            if os.path.exists(json_file2):
                recommendations = parse_json_file(json_file2)
                if recommendations:
                    return recommendations, json_file2
        
        # 方式3: 从trend_start_signal_realtime_all_stocks_YYYYMMDD.txt读取（scan_results目录）
        txt_file = os.path.join("scan_results", f"trend_start_signal_realtime_all_stocks_{date_str}.txt")
        if os.path.exists(txt_file):
            recommendations = parse_result_file(txt_file)
            if recommendations:
                return recommendations, txt_file
        
        return recommendations, source_file
    
    # 查找强势板块的推荐股票（暂时保留，虽然appSimple.py不再生成）
    strong_sectors_file = os.path.join("scan_results", f"trend_start_signal_realtime_strong_sectors_{date_str}.txt")
    strong_sectors_recommendations = []
    strong_sectors_source_file = None
    if os.path.exists(strong_sectors_file):
        strong_sectors_recommendations = parse_result_file(strong_sectors_file)
        strong_sectors_source_file = strong_sectors_file
    
    # 查找全盘A股的推荐股票（使用新的查找逻辑）
    all_stocks_recommendations, all_stocks_source_file = find_scan_results(date_str)
    
    if not strong_sectors_recommendations and not all_stocks_recommendations:
        st.warning(f"⚠️ 未找到 {date_str} 的扫描结果文件，请先进行扫描")
    else:
        # 合并推荐股票列表，强势板块的股票添加标记
        all_recommendations = []
        if strong_sectors_recommendations:
            for stock in strong_sectors_recommendations:
                stock['source'] = '强势板块'  # 标记来源
                all_recommendations.append(stock)
        
        if all_stocks_recommendations:
            for stock in all_stocks_recommendations:
                # 检查是否已经在强势板块列表中（避免重复）
                if not any(s['symbol'] == stock['symbol'] for s in all_recommendations):
                    stock['source'] = '全盘A股'  # 标记来源
                    all_recommendations.append(stock)
        
        if not all_recommendations:
            st.warning("⚠️ 未找到推荐股票数据")
        else:
            strong_count = len(strong_sectors_recommendations) if strong_sectors_recommendations else 0
            all_count = len(all_stocks_recommendations) if all_stocks_recommendations else 0
            st.info(f"📊 找到 {strong_count} 只强势板块推荐股票，{all_count} 只全盘A股推荐股票，共 {len(all_recommendations)} 只，开始计算收益...")
            
            # 计算收益
            try:
                import akshare as ak
            except ImportError:
                st.error("❌ 需要安装 akshare: pip install akshare")
                st.stop()
            
            analysis_results = []
            
            # 定义一个函数来分析单只股票的收益
            def analyze_stock_return(stock, source_type):
                """分析单只股票的收益，并保留所有评分字段"""
                symbol = stock['symbol']
                name = stock.get('name', symbol)
                source = stock.get('source', source_type)
                
                result = {
                    'symbol': symbol,
                    'name': name,
                    'source': source,  # 标记来源
                    'buy_price': None,
                    't1_return': None,
                    't2_return': None,
                    't3_return': None,
                    't4_return': None,
                    't5_return': None,
                    't1_price': None,
                    't2_price': None,
                    't3_price': None,
                    't4_price': None,
                    't5_price': None,
                    't1_close': None,
                    't2_close': None,
                    't3_close': None,
                    't4_close': None,
                    't5_close': None,
                    'status': '未知'
                }
                
                # 从stock字典中提取所有评分字段
                score_fields = [
                    'signal', 'signal_type', 'strength', 'strength_level',
                    'buy_score', 'sell_score', 'net_score', 'reason',
                    'predictive_score', 'predictive_recommendation',
                    'predictive_stop_loss', 'predictive_stop_loss_type',
                    'predictive_time_stop', 'predictive_position',
                    'original_signal', 'original_reason',
                    'suggested_stop_loss', 'position_suggestion'
                ]
                
                for field in score_fields:
                    if field in stock:
                        result[field] = stock[field]
                
                try:
                    # 获取推荐日期后的价格数据
                    code = symbol.replace('.SS', '').replace('.SZ', '')
                    
                    # 计算日期范围（包含推荐日期当天）
                    rec_date = datetime.strptime(date_str, '%Y%m%d')
                    today = datetime.now()
                    
                    # 计算end_date：akshare只会返回到当前日期的数据，不会返回未来数据
                    # 所以end_date应该是今天，但我们需要确保有足够的交易日数据
                    # 如果今天是推荐日期+1天，可能只有1个交易日的数据
                    days_since_rec = (today.date() - rec_date.date()).days
                    
                    # end_date使用今天，akshare会自动返回到最新的交易日数据
                    end_date = today.strftime('%Y%m%d')
                    start_date = rec_date.strftime('%Y%m%d')
                    
                    # 注意：如果距离推荐日期太近，可能无法获取足够的交易日数据
                    # 但这不应该阻止我们尝试获取已有的数据
                    
                    # 获取历史数据（包含推荐日期当天）
                    df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                           start_date=start_date, end_date=end_date, adjust="qfq")
                    
                    if df is None or df.empty:
                        result['status'] = '数据获取失败'
                        return result
                    
                    # 确保日期列是日期类型
                    df['日期'] = pd.to_datetime(df['日期'])
                    rec_date_dt = pd.to_datetime(rec_date)
                    
                    # 获取所选日期当天的数据（用于当天买入）
                    # 如果推荐日期不是交易日，找到最近的交易日
                    rec_date_data = df[df['日期'] == rec_date_dt]
                    if rec_date_data.empty:
                        # 推荐日期不是交易日，找到最近的交易日（推荐日期之前最近的交易日）
                        rec_date_data = df[df['日期'] <= rec_date_dt].sort_values('日期')
                        if rec_date_data.empty:
                            result['status'] = '无法获取所选日期数据'
                            return result
                        rec_date_data = rec_date_data.iloc[-1:]
                        # 更新rec_date_dt为实际的交易日
                        actual_rec_date = rec_date_data.iloc[0]['日期']
                    else:
                        # 推荐日期是交易日
                        actual_rec_date = rec_date_dt
                    
                    # 找到推荐日期后的所有交易日（按日期排序）
                    # 使用实际的交易日日期来筛选后续交易日
                    future_dates = df[df['日期'] > actual_rec_date].sort_values('日期')
                    
                    if len(future_dates) == 0:
                        result['status'] = '无后续交易日数据'
                        return result
                    
                    # 检查交易日数据是否足够
                    if buy_timing == "当天买入":
                        if len(future_dates) < 3:
                            # 数据不足，但至少尝试获取已有的数据
                            result['status'] = f'交易日数据不足（需要3个，实际{len(future_dates)}个）'
                            # 不直接返回，继续处理已有的数据
                    elif buy_timing == "隔天买入":
                        if len(future_dates) < 2:
                            # 数据不足，但至少尝试获取已有的数据
                            result['status'] = f'交易日数据不足（需要2个，实际{len(future_dates)}个）'
                            # 不直接返回，继续处理已有的数据
                    
                    # 根据买入时机选择买入价
                    if buy_timing == "当天买入":
                        # 当天买入：买入价为所选日期当天的收盘价
                        buy_price = None
                        for col in rec_date_data.iloc[0].index:
                            if '收盘' in str(col) or 'close' in str(col).lower():
                                buy_price = rec_date_data.iloc[0][col]
                                break
                        
                        if buy_price is None:
                            result['status'] = '无法获取当天收盘价'
                            return result
                        
                        # 当天买入统计到T+5
                        t1_idx = 0
                        t2_idx = 1
                        t3_idx = 2
                        t4_idx = 3
                        t5_idx = 4
                    else:
                        # 隔天买入：买入价为所选日期后第一个交易日的开盘价
                        buy_date_data = future_dates.iloc[0]
                        
                        buy_price = None
                        for col in buy_date_data.index:
                            if '开盘' in str(col) or 'open' in str(col).lower():
                                buy_price = buy_date_data[col]
                                break
                        
                        if buy_price is None:
                            for col in buy_date_data.index:
                                if '收盘' in str(col) or 'close' in str(col).lower():
                                    buy_price = buy_date_data[col]
                                    break
                        
                        if buy_price is None:
                            result['status'] = '无法获取隔天开盘价'
                            return result
                        
                        # 隔天买入统计到T+5
                        t1_idx = 1
                        t2_idx = 2
                        t3_idx = 3
                        t4_idx = 4
                        t5_idx = 5
                    
                    result['buy_price'] = buy_price
                    
                    # 定义获取最高价和收盘价的函数
                    def get_high_price(row):
                        try:
                            for col in row.index:
                                if '最高' in str(col) or 'high' in str(col).lower():
                                    return row[col]
                            for col in row.index:
                                if '收盘' in str(col) or 'close' in str(col).lower():
                                    return row[col]
                            return None
                        except:
                            return None
                    
                    def get_close_price(row):
                        try:
                            for col in row.index:
                                if '收盘' in str(col) or 'close' in str(col).lower():
                                    return row[col]
                            return None
                        except:
                            return None
                    
                    # 获取T+1, T+2, T+3的价格
                    if len(future_dates) > t1_idx:
                        try:
                            result['t1_price'] = get_high_price(future_dates.iloc[t1_idx])
                            result['t1_close'] = get_close_price(future_dates.iloc[t1_idx])
                        except:
                            pass
                    
                    if len(future_dates) > t2_idx:
                        try:
                            result['t2_price'] = get_high_price(future_dates.iloc[t2_idx])
                            result['t2_close'] = get_close_price(future_dates.iloc[t2_idx])
                        except:
                            pass
                    
                    if t3_idx is not None and len(future_dates) > t3_idx:
                        try:
                            result['t3_price'] = get_high_price(future_dates.iloc[t3_idx])
                            result['t3_close'] = get_close_price(future_dates.iloc[t3_idx])
                        except:
                            pass
                    
                    if t4_idx is not None and len(future_dates) > t4_idx:
                        try:
                            result['t4_price'] = get_high_price(future_dates.iloc[t4_idx])
                            result['t4_close'] = get_close_price(future_dates.iloc[t4_idx])
                        except:
                            pass
                    
                    if t5_idx is not None and len(future_dates) > t5_idx:
                        try:
                            result['t5_price'] = get_high_price(future_dates.iloc[t5_idx])
                            result['t5_close'] = get_close_price(future_dates.iloc[t5_idx])
                        except:
                            pass
                    
                    # 计算收益率
                    result['t1_return'] = ((result['t1_price'] - buy_price) / buy_price * 100) if result['t1_price'] else None
                    result['t2_return'] = ((result['t2_price'] - buy_price) / buy_price * 100) if result['t2_price'] else None
                    result['t3_return'] = ((result['t3_price'] - buy_price) / buy_price * 100) if result['t3_price'] else None
                    result['t4_return'] = ((result['t4_price'] - buy_price) / buy_price * 100) if result['t4_price'] else None
                    result['t5_return'] = ((result['t5_price'] - buy_price) / buy_price * 100) if result['t5_price'] else None
                    result['status'] = '成功'
                    
                except Exception as e:
                    result['status'] = f'错误: {str(e)[:30]}'
                
                return result
            
            # 先分析强势板块的推荐股票
            if strong_sectors_recommendations:
                st.subheader("📊 分析强势板块推荐股票")
                strong_progress_bar = st.progress(0)
                strong_total = len(strong_sectors_recommendations)
                
                for idx, stock in enumerate(strong_sectors_recommendations):
                    # 添加延迟，避免请求过快导致限流
                    if idx > 0:
                        import time
                        time.sleep(0.1)
                    
                    result = analyze_stock_return(stock, '强势板块')
                    analysis_results.append(result)
                    
                    # 更新进度
                    progress = min((idx + 1) / strong_total, 1.0)
                    strong_progress_bar.progress(progress)
                
                # 显示强势板块的分析结果（先显示在表格中）
                if analysis_results:
                    df_strong = pd.DataFrame(analysis_results)
                    st.subheader("📊 强势板块推荐股票收益分析")
                    # 显示来源文件名
                    if strong_sectors_source_file:
                        st.info(f"📁 **数据来源：** `{strong_sectors_source_file}`")
                    # 格式化显示
                    display_columns = [
                        'symbol', 'name', 'source',
                        # 原始信号字段
                        'signal', 'signal_type', 'strength', 'strength_level',
                        'buy_score', 'sell_score', 'net_score', 'reason',
                        # 预测评分字段
                        'predictive_score', 'predictive_recommendation',
                        'predictive_stop_loss', 'predictive_stop_loss_type',
                        'predictive_time_stop', 'predictive_position',
                        'original_signal', 'original_reason',
                        'suggested_stop_loss', 'position_suggestion',
                        # 收益字段
                        'buy_price', 
                        't1_price', 't1_close', 't1_return', 
                        't2_price', 't2_close', 't2_return',
                        't3_price', 't3_close', 't3_return',
                        't4_price', 't4_close', 't4_return',
                        't5_price', 't5_close', 't5_return',
                        'status'
                    ]
                    
                    available_columns = [col for col in display_columns if col in df_strong.columns]
                    display_df_strong = df_strong[available_columns].copy()
                    
                    # 重命名列
                    column_mapping = {
                        'symbol': '股票代码',
                        'name': '股票名称',
                        'source': '来源',
                        # 原始信号字段
                        'signal': '信号',
                        'signal_type': '信号类型',
                        'strength': '信号强度',
                        'strength_level': '强度等级',
                        'buy_score': '买入评分',
                        'sell_score': '卖出评分',
                        'net_score': '净评分',
                        'reason': '原因',
                        # 预测评分字段
                        'predictive_score': '预测评分',
                        'predictive_recommendation': '预测推荐',
                        'predictive_stop_loss': '预测止损',
                        'predictive_stop_loss_type': '止损类型',
                        'predictive_time_stop': '时间止损',
                        'predictive_position': '预测仓位',
                        'original_signal': '原始信号',
                        'original_reason': '原始原因',
                        'suggested_stop_loss': '建议止损',
                        'position_suggestion': '仓位建议',
                        # 收益字段
                        'buy_price': '买入价',
                        't1_price': 'T+1最高价',
                        't1_close': 'T+1收盘',
                        't1_return': 'T+1收益率(%)',
                        't2_price': 'T+2最高价',
                        't2_close': 'T+2收盘',
                        't2_return': 'T+2收益率(%)',
                        't3_price': 'T+3最高价',
                        't3_close': 'T+3收盘',
                        't3_return': 'T+3收益率(%)',
                        't4_price': 'T+4最高价',
                        't4_close': 'T+4收盘',
                        't4_return': 'T+4收益率(%)',
                        't5_price': 'T+5最高价',
                        't5_close': 'T+5收盘',
                        't5_return': 'T+5收益率(%)',
                        'status': '状态'
                    }
                    display_df_strong.columns = [column_mapping.get(col, col) for col in display_df_strong.columns]
                    
                    # 格式化数值
                    price_columns = ['买入价', 'T+1最高价', 'T+1收盘', 'T+2最高价', 'T+2收盘', 'T+3最高价', 'T+3收盘', 'T+4最高价', 'T+4收盘', 'T+5最高价', 'T+5收盘', 
                                   '预测止损', '建议止损']
                    return_columns = ['T+1收益率(%)', 'T+2收益率(%)', 'T+3收益率(%)', 'T+4收益率(%)', 'T+5收益率(%)']
                    score_columns = ['信号强度', '买入评分', '卖出评分', '净评分', '预测评分']
                    
                    for col in price_columns:
                        if col in display_df_strong.columns:
                            display_df_strong[col] = display_df_strong[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else (str(x) if pd.notna(x) else "N/A"))
                    
                    for col in return_columns:
                        if col in display_df_strong.columns:
                            display_df_strong[col] = display_df_strong[col].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) and isinstance(x, (int, float)) else (str(x) if pd.notna(x) else "N/A"))
                    
                    for col in score_columns:
                        if col in display_df_strong.columns:
                            display_df_strong[col] = display_df_strong[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) and isinstance(x, (int, float)) else (str(x) if pd.notna(x) else "N/A"))
                    
                    # 标记强势板块股票（在股票名称前添加标记）
                    if '股票名称' in display_df_strong.columns:
                        display_df_strong['股票名称'] = '⭐ ' + display_df_strong['股票名称'].astype(str)
                    
                    st.dataframe(display_df_strong, use_container_width=True, hide_index=True)
            
            # 再分析全盘A股的推荐股票（追加到表格中）
            if all_stocks_recommendations:
                st.subheader("📊 分析全盘A股推荐股票")
                all_progress_bar = st.progress(0)
                all_total = len(all_stocks_recommendations)
                
                for idx, stock in enumerate(all_stocks_recommendations):
                    # 检查是否已经在强势板块列表中（避免重复）
                    if any(r['symbol'] == stock['symbol'] for r in analysis_results):
                        continue
                    
                    # 添加延迟，避免请求过快导致限流
                    if idx > 0:
                        import time
                        time.sleep(0.1)
                    
                    result = analyze_stock_return(stock, '全盘A股')
                    analysis_results.append(result)
                    
                    # 更新进度
                    progress = min((idx + 1) / all_total, 1.0)
                    all_progress_bar.progress(progress)
                
                # 显示追加后的完整结果
                if analysis_results:
                    st.subheader("📊 完整收益分析结果（强势板块 + 全盘A股）")
                    
                    # 显示来源文件名
                    source_files = []
                    if strong_sectors_source_file:
                        source_files.append(f"强势板块: `{strong_sectors_source_file}`")
                    if all_stocks_source_file:
                        source_files.append(f"全盘A股: `{all_stocks_source_file}`")
                    if source_files:
                        st.info(f"📁 **数据来源：** {' | '.join(source_files)}")
                    
                    # 格式化显示完整结果
                    df_all = pd.DataFrame(analysis_results)
                    
                    # 显示所有列（包括评分字段和T+4、T+5）
                    display_columns = [
                        'symbol', 'name', 'source',
                        # 原始信号字段
                        'signal', 'signal_type', 'strength', 'strength_level',
                        'buy_score', 'sell_score', 'net_score', 'reason',
                        # 预测评分字段
                        'predictive_score', 'predictive_recommendation',
                        'predictive_stop_loss', 'predictive_stop_loss_type',
                        'predictive_time_stop', 'predictive_position',
                        'original_signal', 'original_reason',
                        'suggested_stop_loss', 'position_suggestion',
                        # 收益字段
                        'buy_price', 
                        't1_price', 't1_close', 't1_return', 
                        't2_price', 't2_close', 't2_return', 
                        't3_price', 't3_close', 't3_return',
                        't4_price', 't4_close', 't4_return',
                        't5_price', 't5_close', 't5_return',
                        'status'
                    ]
                    
                    available_columns = [col for col in display_columns if col in df_all.columns]
                    display_df_all = df_all[available_columns].copy()
                    
                    # 重命名列
                    column_mapping = {
                        'symbol': '股票代码',
                        'name': '股票名称',
                        'source': '来源',
                        # 原始信号字段
                        'signal': '信号',
                        'signal_type': '信号类型',
                        'strength': '信号强度',
                        'strength_level': '强度等级',
                        'buy_score': '买入评分',
                        'sell_score': '卖出评分',
                        'net_score': '净评分',
                        'reason': '原因',
                        # 预测评分字段
                        'predictive_score': '预测评分',
                        'predictive_recommendation': '预测推荐',
                        'predictive_stop_loss': '预测止损',
                        'predictive_stop_loss_type': '止损类型',
                        'predictive_time_stop': '时间止损',
                        'predictive_position': '预测仓位',
                        'original_signal': '原始信号',
                        'original_reason': '原始原因',
                        'suggested_stop_loss': '建议止损',
                        'position_suggestion': '仓位建议',
                        # 收益字段
                        'buy_price': '买入价',
                        't1_price': 'T+1最高价',
                        't1_close': 'T+1收盘',
                        't1_return': 'T+1收益率(%)',
                        't2_price': 'T+2最高价',
                        't2_close': 'T+2收盘',
                        't2_return': 'T+2收益率(%)',
                        't3_price': 'T+3最高价',
                        't3_close': 'T+3收盘',
                        't3_return': 'T+3收益率(%)',
                        't4_price': 'T+4最高价',
                        't4_close': 'T+4收盘',
                        't4_return': 'T+4收益率(%)',
                        't5_price': 'T+5最高价',
                        't5_close': 'T+5收盘',
                        't5_return': 'T+5收益率(%)',
                        'status': '状态'
                    }
                    display_df_all.columns = [column_mapping.get(col, col) for col in display_df_all.columns]
                    
                    # 格式化数值
                    price_columns = ['买入价', 'T+1最高价', 'T+1收盘', 'T+2最高价', 'T+2收盘', 'T+3最高价', 'T+3收盘', 'T+4最高价', 'T+4收盘', 'T+5最高价', 'T+5收盘', 
                                   '预测止损', '建议止损']
                    return_columns = ['T+1收益率(%)', 'T+2收益率(%)', 'T+3收益率(%)', 'T+4收益率(%)', 'T+5收益率(%)']
                    score_columns = ['信号强度', '买入评分', '卖出评分', '净评分', '预测评分']
                    
                    for col in price_columns:
                        if col in display_df_all.columns:
                            display_df_all[col] = display_df_all[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else (str(x) if pd.notna(x) else "N/A"))
                    
                    for col in return_columns:
                        if col in display_df_all.columns:
                            display_df_all[col] = display_df_all[col].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) and isinstance(x, (int, float)) else (str(x) if pd.notna(x) else "N/A"))
                    
                    for col in score_columns:
                        if col in display_df_all.columns:
                            display_df_all[col] = display_df_all[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) and isinstance(x, (int, float)) else (str(x) if pd.notna(x) else "N/A"))
                    
                    # 标记强势板块股票（在股票名称前添加标记）
                    if '股票名称' in display_df_all.columns:
                        # 根据来源标记
                        for idx in display_df_all.index:
                            source = df_all.loc[idx, 'source'] if 'source' in df_all.columns else '全盘A股'
                            if source == '强势板块':
                                display_df_all.loc[idx, '股票名称'] = '⭐ ' + str(display_df_all.loc[idx, '股票名称'])
                    
                    st.dataframe(display_df_all, use_container_width=True, hide_index=True)
                    
                    # 统计信息
                    st.subheader("📈 统计信息")
                    valid_t1 = df_all['t1_return'].notna().sum()
                    valid_t2 = df_all['t2_return'].notna().sum()
                    valid_t3 = df_all['t3_return'].notna().sum()
                    valid_t4 = df_all['t4_return'].notna().sum()
                    valid_t5 = df_all['t5_return'].notna().sum()
                    
                    # T+1统计
                    if valid_t1 > 0:
                        avg_t1 = df_all['t1_return'].mean()
                        win_rate_t1 = (df_all['t1_return'] > 0).sum() / valid_t1 * 100
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("T+1平均收益", f"{avg_t1:+.2f}%", f"有效数据: {valid_t1}/{len(analysis_results)}")
                        with col2:
                            st.metric("T+1胜率", f"{win_rate_t1:.1f}%")
                        with col3:
                            max_t1 = df_all['t1_return'].max()
                            min_t1 = df_all['t1_return'].min()
                            st.metric("T+1收益范围", f"{min_t1:.2f}% ~ {max_t1:.2f}%")
                    
                    # T+2统计
                    if valid_t2 > 0:
                        avg_t2 = df_all['t2_return'].mean()
                        win_rate_t2 = (df_all['t2_return'] > 0).sum() / valid_t2 * 100
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("T+2平均收益", f"{avg_t2:+.2f}%", f"有效数据: {valid_t2}/{len(analysis_results)}")
                        with col2:
                            st.metric("T+2胜率", f"{win_rate_t2:.1f}%")
                        with col3:
                            max_t2 = df_all['t2_return'].max()
                            min_t2 = df_all['t2_return'].min()
                            st.metric("T+2收益范围", f"{min_t2:.2f}% ~ {max_t2:.2f}%")
                    
                    # T+3统计
                    if valid_t3 > 0:
                        avg_t3 = df_all['t3_return'].mean()
                        win_rate_t3 = (df_all['t3_return'] > 0).sum() / valid_t3 * 100
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("T+3平均收益", f"{avg_t3:+.2f}%", f"有效数据: {valid_t3}/{len(analysis_results)}")
                        with col2:
                            st.metric("T+3胜率", f"{win_rate_t3:.1f}%")
                        with col3:
                            max_t3 = df_all['t3_return'].max()
                            min_t3 = df_all['t3_return'].min()
                            st.metric("T+3收益范围", f"{min_t3:.2f}% ~ {max_t3:.2f}%")
                    
                    # T+4统计
                    if valid_t4 > 0:
                        avg_t4 = df_all['t4_return'].mean()
                        win_rate_t4 = (df_all['t4_return'] > 0).sum() / valid_t4 * 100
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("T+4平均收益", f"{avg_t4:+.2f}%", f"有效数据: {valid_t4}/{len(analysis_results)}")
                        with col2:
                            st.metric("T+4胜率", f"{win_rate_t4:.1f}%")
                        with col3:
                            max_t4 = df_all['t4_return'].max()
                            min_t4 = df_all['t4_return'].min()
                            st.metric("T+4收益范围", f"{min_t4:.2f}% ~ {max_t4:.2f}%")
                    
                    # T+5统计
                    if valid_t5 > 0:
                        avg_t5 = df_all['t5_return'].mean()
                        win_rate_t5 = (df_all['t5_return'] > 0).sum() / valid_t5 * 100
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("T+5平均收益", f"{avg_t5:+.2f}%", f"有效数据: {valid_t5}/{len(analysis_results)}")
                        with col2:
                            st.metric("T+5胜率", f"{win_rate_t5:.1f}%")
                        with col3:
                            max_t5 = df_all['t5_return'].max()
                            min_t5 = df_all['t5_return'].min()
                            st.metric("T+5收益范围", f"{min_t5:.2f}% ~ {max_t5:.2f}%")
                    
                    # 保存分析结果
                    analysis_file = os.path.join("scan_results", f"return_analysis_{date_str}.csv")
                    df_all.to_csv(analysis_file, index=False, encoding='utf-8-sig')
                    st.success(f"✅ 收益分析结果已保存到: `scan_results/return_analysis_{date_str}.csv`")
