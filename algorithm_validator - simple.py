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

# 净评分过滤条件
st.subheader("🔍 净评分过滤条件")
col_min, col_max = st.columns(2)
with col_min:
    net_score_min = st.text_input(
        "净评分最小值",
        value="",
        key="net_score_min",
        help="留空表示负无穷大（不限制下限）。例如：输入 4 表示只统计 net_score ≥ 4 的股票"
    )
with col_max:
    net_score_max = st.text_input(
        "净评分最大值",
        value="",
        key="net_score_max",
        help="留空表示正无穷大（不限制上限）。例如：输入 8 表示只统计 net_score ≤ 8 的股票"
    )

# 初始化session_state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'analysis_date' not in st.session_state:
    st.session_state.analysis_date = None
if 'display_df_all' not in st.session_state:
    st.session_state.display_df_all = None

# 如果日期改变，清空结果
if st.session_state.analysis_date != date_str:
    st.session_state.analysis_results = None
    st.session_state.display_df_all = None
    st.session_state.analysis_date = date_str

# 检查是否有已保存的分析结果
has_saved_results = (st.session_state.analysis_results is not None and 
                     st.session_state.display_df_all is not None and
                     st.session_state.analysis_date == date_str)

# 如果有保存的结果，显示提示信息
if has_saved_results:
    st.info(f"💡 已加载 {date_str} 的分析结果。修改筛选条件后，结果会自动更新。如需重新分析，请点击下方按钮。")

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
            # 应用净评分过滤条件
            original_count = len(all_recommendations)
            filtered_recommendations = []
            
            # 解析过滤条件
            min_value = None
            max_value = None
            if net_score_min.strip():
                try:
                    min_value = float(net_score_min.strip())
                except ValueError:
                    st.warning(f"⚠️ 净评分最小值格式错误，将忽略该条件")
            if net_score_max.strip():
                try:
                    max_value = float(net_score_max.strip())
                except ValueError:
                    st.warning(f"⚠️ 净评分最大值格式错误，将忽略该条件")
            
            # 应用过滤
            # 如果设置了过滤条件，只保留符合条件的股票
            if min_value is not None or max_value is not None:
                for stock in all_recommendations:
                    net_score = stock.get('net_score', None)
                    # 如果股票没有net_score字段，过滤掉（不保留）
                    if net_score is None:
                        continue
                    
                    # 检查是否满足最小值条件
                    if min_value is not None and net_score < min_value:
                        continue
                    
                    # 检查是否满足最大值条件
                    if max_value is not None and net_score > max_value:
                        continue
                    
                    # 通过过滤
                    filtered_recommendations.append(stock)
            else:
                # 如果没有设置过滤条件，保留所有股票
                filtered_recommendations = all_recommendations.copy()
            
            # 更新推荐股票列表为过滤后的列表
            all_recommendations = filtered_recommendations
            
            # 显示过滤信息
            if original_count != len(all_recommendations):
                min_display = net_score_min.strip() if net_score_min.strip() else '-∞'
                max_display = net_score_max.strip() if net_score_max.strip() else '+∞'
                st.info(f"📊 净评分过滤: {original_count} 只 → {len(all_recommendations)} 只（范围: {min_display} ~ {max_display}）")
            
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
            
            # 分析过滤后的推荐股票（使用过滤后的all_recommendations列表）
            if all_recommendations:
                st.subheader("📊 分析推荐股票收益")
                progress_bar = st.progress(0)
                total = len(all_recommendations)
                
                for idx, stock in enumerate(all_recommendations):
                    # 添加延迟，避免请求过快导致限流
                    if idx > 0:
                        import time
                        time.sleep(0.1)
                    
                    result = analyze_stock_return(stock, stock.get('source', '全盘A股'))
                    analysis_results.append(result)
                    
                    # 更新进度
                    progress = min((idx + 1) / total, 1.0)
                    progress_bar.progress(progress)
                
                # 显示分析结果
                if analysis_results:
                    st.subheader("📊 收益分析结果")
                    
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
                    
                    st.dataframe(display_df_all, width='stretch', hide_index=True)
                    
                    # 统计信息
                    st.subheader("📈 统计信息")
                    
                    # 显示当前应用的净评分过滤条件
                    if net_score_min.strip() or net_score_max.strip():
                        min_display = net_score_min.strip() if net_score_min.strip() else '-∞'
                        max_display = net_score_max.strip() if net_score_max.strip() else '+∞'
                        st.info(f"📊 当前统计基于净评分过滤条件: {min_display} ~ {max_display}（共 {len(df_all)} 只股票）")
                    
                    # 使用过滤后的数据进行统计（数据已经在分析时过滤过了）
                    df_filtered = df_all.copy()
                    valid_t1 = df_filtered['t1_return'].notna().sum()
                    valid_t2 = df_filtered['t2_return'].notna().sum()
                    valid_t3 = df_filtered['t3_return'].notna().sum()
                    valid_t4 = df_filtered['t4_return'].notna().sum()
                    valid_t5 = df_filtered['t5_return'].notna().sum()
                    
                    # T+1统计
                    if valid_t1 > 0:
                        avg_t1 = df_filtered['t1_return'].mean()
                        win_rate_t1 = (df_filtered['t1_return'] > 0).sum() / valid_t1 * 100
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("T+1平均收益", f"{avg_t1:+.2f}%", f"有效数据: {valid_t1}/{len(df_filtered)}")
                        with col2:
                            st.metric("T+1胜率", f"{win_rate_t1:.1f}%")
                        with col3:
                            max_t1 = df_filtered['t1_return'].max()
                            min_t1 = df_filtered['t1_return'].min()
                            st.metric("T+1收益范围", f"{min_t1:.2f}% ~ {max_t1:.2f}%")
                    
                    # T+2统计
                    if valid_t2 > 0:
                        avg_t2 = df_filtered['t2_return'].mean()
                        win_rate_t2 = (df_filtered['t2_return'] > 0).sum() / valid_t2 * 100
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("T+2平均收益", f"{avg_t2:+.2f}%", f"有效数据: {valid_t2}/{len(df_filtered)}")
                        with col2:
                            st.metric("T+2胜率", f"{win_rate_t2:.1f}%")
                        with col3:
                            max_t2 = df_filtered['t2_return'].max()
                            min_t2 = df_filtered['t2_return'].min()
                            st.metric("T+2收益范围", f"{min_t2:.2f}% ~ {max_t2:.2f}%")
                    
                    # T+3统计
                    if valid_t3 > 0:
                        avg_t3 = df_filtered['t3_return'].mean()
                        win_rate_t3 = (df_filtered['t3_return'] > 0).sum() / valid_t3 * 100
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("T+3平均收益", f"{avg_t3:+.2f}%", f"有效数据: {valid_t3}/{len(df_filtered)}")
                        with col2:
                            st.metric("T+3胜率", f"{win_rate_t3:.1f}%")
                        with col3:
                            max_t3 = df_filtered['t3_return'].max()
                            min_t3 = df_filtered['t3_return'].min()
                            st.metric("T+3收益范围", f"{min_t3:.2f}% ~ {max_t3:.2f}%")
                    
                    # T+4统计
                    if valid_t4 > 0:
                        avg_t4 = df_filtered['t4_return'].mean()
                        win_rate_t4 = (df_filtered['t4_return'] > 0).sum() / valid_t4 * 100
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("T+4平均收益", f"{avg_t4:+.2f}%", f"有效数据: {valid_t4}/{len(df_filtered)}")
                        with col2:
                            st.metric("T+4胜率", f"{win_rate_t4:.1f}%")
                        with col3:
                            max_t4 = df_filtered['t4_return'].max()
                            min_t4 = df_filtered['t4_return'].min()
                            st.metric("T+4收益范围", f"{min_t4:.2f}% ~ {max_t4:.2f}%")
                    
                    # T+5统计
                    if valid_t5 > 0:
                        avg_t5 = df_filtered['t5_return'].mean()
                        win_rate_t5 = (df_filtered['t5_return'] > 0).sum() / valid_t5 * 100
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("T+5平均收益", f"{avg_t5:+.2f}%", f"有效数据: {valid_t5}/{len(df_filtered)}")
                        with col2:
                            st.metric("T+5胜率", f"{win_rate_t5:.1f}%")
                        with col3:
                            max_t5 = df_filtered['t5_return'].max()
                            min_t5 = df_filtered['t5_return'].min()
                            st.metric("T+5收益范围", f"{min_t5:.2f}% ~ {max_t5:.2f}%")
                    
                    # 保存分析结果（保存格式化后的数据，与页面显示一致）
                    analysis_file = os.path.join("scan_results", f"return_analysis_{date_str}.csv")
                    try:
                        # 确保目录存在
                        os.makedirs("scan_results", exist_ok=True)
                        display_df_all.to_csv(analysis_file, index=False, encoding='utf-8-sig')
                        st.success(f"✅ 收益分析结果已保存到: `scan_results/return_analysis_{date_str}.csv`")
                    except PermissionError:
                        st.warning(f"⚠️ 无法保存文件（文件可能正在被其他程序使用，如Excel）: `scan_results/return_analysis_{date_str}.csv`\n请关闭该文件后重试。")
                    except Exception as e:
                        st.warning(f"⚠️ 保存文件时出错: {str(e)}")
                    
                    # 保存到session_state，以便页面刷新后仍能显示
                    st.session_state.analysis_results = analysis_results
                    st.session_state.display_df_all = display_df_all
                    st.session_state.analysis_date = date_str
                    
                    # ========== 四步选股法决策分析 ==========
                    st.markdown("---")
                    st.subheader("🎯 四步选股法决策分析")
                    st.markdown("""
                    **专为3-5天短线稳健操作设计的选股决策系统**
                    
                    本功能将帮助您按照科学的四步流程，从分析结果中筛选出最具潜力的股票。
                    """)
                    
                    # 第一步：初选清单
                    st.markdown("### 第一步：初选清单 — 聚焦\"预测推荐强度\"")
                    
                    # 筛选条件
                    col_filter1, col_filter2 = st.columns(2)
                    with col_filter1:
                        max_candidates = st.number_input(
                            "核心观察池数量",
                            min_value=3,
                            max_value=20,
                            value=8,
                            help="建议选择5-8只股票作为核心观察池"
                        )
                    with col_filter2:
                        min_predictive_score = st.number_input(
                            "最低预测评分",
                            min_value=0.0,
                            max_value=100.0,
                            value=50.0,
                            step=1.0,
                            help="只考虑预测评分高于此值的股票"
                        )
                    
                    # 筛选逻辑
                    def filter_step1(df):
                        """第一步筛选：基于预测推荐和预测评分"""
                        if df.empty:
                            return pd.DataFrame()
                        
                        filtered = df.copy()
                        
                        # 如果有预测评分字段，先按预测评分筛选
                        if '预测评分' in filtered.columns:
                            # 将预测评分转换为数值（如果包含非数字字符）
                            def parse_score(score):
                                if pd.isna(score):
                                    return 0
                                if isinstance(score, (int, float)):
                                    return float(score)
                                # 尝试从字符串中提取数字
                                try:
                                    return float(str(score).replace('%', '').strip())
                                except:
                                    return 0
                            
                            filtered['预测评分_数值'] = filtered['预测评分'].apply(parse_score)
                            filtered = filtered[filtered['预测评分_数值'] >= min_predictive_score]
                            
                            # 如果有预测推荐字段，进一步筛选
                            if '预测推荐' in filtered.columns:
                                # 筛选：预测推荐为"强力买入"或"买入"，如果没有符合条件的，则显示所有满足评分条件的
                                recommended = filtered[
                                    (filtered['预测推荐'] == '强力买入') | 
                                    (filtered['预测推荐'] == '买入')
                                ].copy()
                                
                                # 如果有符合条件的，使用它们；否则使用所有满足评分条件的
                                if len(recommended) > 0:
                                    filtered = recommended
                            
                            # 按预测评分从高到低排序
                            filtered = filtered.sort_values('预测评分_数值', ascending=False)
                        else:
                            # 如果没有预测评分字段，按预测推荐筛选
                            if '预测推荐' in filtered.columns:
                                filtered = filtered[
                                    (filtered['预测推荐'] == '强力买入') | 
                                    (filtered['预测推荐'] == '买入')
                                ].copy()
                                
                                # 按预测推荐排序（强力买入优先）
                                filtered['排序权重'] = filtered['预测推荐'].apply(
                                    lambda x: 2 if x == '强力买入' else 1
                                )
                                filtered = filtered.sort_values('排序权重', ascending=False)
                            else:
                                # 如果既没有预测评分也没有预测推荐，返回空
                                return pd.DataFrame()
                        
                        # 取前N只
                        return filtered.head(max_candidates)
                    
                    step1_candidates = filter_step1(display_df_all.copy())
                    
                    if len(step1_candidates) == 0:
                        # 添加调试信息
                        debug_info = []
                        if '预测推荐' in display_df_all.columns:
                            unique_recommendations = display_df_all['预测推荐'].unique()
                            debug_info.append(f"预测推荐字段存在，唯一值: {list(unique_recommendations)}")
                        else:
                            debug_info.append("预测推荐字段不存在")
                        
                        if '预测评分' in display_df_all.columns:
                            # 尝试解析预测评分
                            def parse_score(score):
                                if pd.isna(score):
                                    return None
                                if isinstance(score, (int, float)):
                                    return float(score)
                                try:
                                    return float(str(score).replace('%', '').strip())
                                except:
                                    return None
                            
                            scores = display_df_all['预测评分'].apply(parse_score)
                            valid_scores = scores[scores.notna()]
                            if len(valid_scores) > 0:
                                max_score = valid_scores.max()
                                min_score = valid_scores.min()
                                count_above_threshold = (valid_scores >= min_predictive_score).sum()
                                debug_info.append(f"预测评分字段存在，范围: {min_score:.1f} ~ {max_score:.1f}，高于{min_predictive_score}的股票数: {count_above_threshold}")
                            else:
                                debug_info.append("预测评分字段存在，但无法解析为数值")
                        else:
                            debug_info.append("预测评分字段不存在")
                        
                        st.warning(f"⚠️ 第一步筛选：未找到符合条件的股票。\n\n**调试信息：**\n" + "\n".join(debug_info) + "\n\n请检查预测推荐字段或调整筛选条件。")
                    else:
                        st.success(f"✅ 第一步筛选完成：找到 {len(step1_candidates)} 只符合条件的股票")
                        
                        # 显示初选清单
                        step1_display_cols = ['股票代码', '股票名称', '预测推荐', '预测评分', '原始信号', '信号强度', '强度等级']
                        available_cols = [col for col in step1_display_cols if col in step1_candidates.columns]
                        if available_cols:
                            st.dataframe(
                                step1_candidates[available_cols].copy(),
                                width='stretch',
                                hide_index=True
                            )
                        
                        # 第二步：深度验证
                        st.markdown("### 第二步：深度验证 — 解读\"技术信号\"与\"原因\"")
                        
                        def filter_step2(df):
                            """第二步筛选：验证技术信号质量"""
                            results = []
                            
                            for idx, row in df.iterrows():
                                score = 0
                                issues = []
                                recommendations = []
                                
                                # 检查原始信号
                                original_signal = str(row.get('原始信号', '')).upper()
                                signal = str(row.get('信号', '')).upper()
                                
                                if 'BUY' in original_signal or 'STRONG_BUY' in original_signal:
                                    score += 3
                                    recommendations.append("✅ 原始信号为买入信号")
                                elif 'HOLD' in original_signal:
                                    score += 1
                                    issues.append("⚠️ 原始信号为观望，需谨慎")
                                else:
                                    issues.append("❌ 原始信号非买入，需高度警惕")
                                
                                # 检查信号强度
                                strength_str = str(row.get('信号强度', ''))
                                try:
                                    # 尝试提取强度数值
                                    strength_val = float(str(strength_str).replace('%', '').strip())
                                    if strength_val >= 60:
                                        score += 2
                                        recommendations.append(f"✅ 信号强度{strength_val:.0f}%，质量良好")
                                    elif strength_val >= 50:
                                        score += 1
                                        recommendations.append(f"⚠️ 信号强度{strength_val:.0f}%，中等")
                                    else:
                                        issues.append(f"⚠️ 信号强度{strength_val:.0f}%，较弱")
                                except:
                                    pass
                                
                                # 检查强度等级
                                strength_level = str(row.get('强度等级', ''))
                                if strength_level in ['极强', '强', '中等']:
                                    score += 1
                                    recommendations.append(f"✅ 强度等级：{strength_level}")
                                
                                # 检查原因
                                reason = str(row.get('原始原因', ''))
                                if '放量上涨' in reason or 'MACD金叉' in reason:
                                    score += 1
                                    recommendations.append("✅ 包含健康的技术信号")
                                if '涨幅较大' in reason or '涨幅过大' in reason:
                                    score -= 2
                                    issues.append("⚠️ 包含涨幅过大警告，需降低优先级")
                                
                                # 使用股票代码作为唯一标识符
                                stock_code = str(row.get('股票代码', ''))
                                results.append({
                                    '股票代码': stock_code,
                                    'score': score,
                                    'issues': ' | '.join(issues) if issues else '无',
                                    'recommendations': ' | '.join(recommendations) if recommendations else '无'
                                })
                            
                            # 转换为DataFrame并排序
                            results_df = pd.DataFrame(results)
                            if len(results_df) > 0:
                                results_df = results_df.sort_values('score', ascending=False)
                            
                            return results_df
                        
                        step2_analysis = filter_step2(step1_candidates)
                        
                        if len(step2_analysis) > 0:
                            # 合并分析结果（使用股票代码匹配）
                            step2_final = step1_candidates.copy()
                            step2_analysis_dict = step2_analysis.set_index('股票代码')
                            
                            def get_value(code, col):
                                if code in step2_analysis_dict.index:
                                    return step2_analysis_dict.loc[code, col]
                                return 0 if col == 'score' else '无'
                            
                            step2_final['验证评分'] = step2_final['股票代码'].apply(
                                lambda x: get_value(str(x), 'score')
                            )
                            step2_final['验证问题'] = step2_final['股票代码'].apply(
                                lambda x: get_value(str(x), 'issues')
                            )
                            step2_final['验证建议'] = step2_final['股票代码'].apply(
                                lambda x: get_value(str(x), 'recommendations')
                            )
                            step2_final = step2_final.sort_values('验证评分', ascending=False)
                            
                            st.info(f"📊 第二步验证完成：对 {len(step2_final)} 只股票进行了技术信号质量评估")
                            
                            # 显示验证结果
                            step2_display_cols = [
                                '股票代码', '股票名称', '预测推荐', '预测评分',
                                '原始信号', '信号强度', '强度等级', '验证评分', '验证问题', '验证建议'
                            ]
                            available_cols = [col for col in step2_display_cols if col in step2_final.columns]
                            if available_cols:
                                st.dataframe(
                                    step2_final[available_cols].copy(),
                                    width='stretch',
                                    hide_index=True
                                )
                            
                            # 第三步：制定计划
                            st.markdown("### 第三步：制定计划 — 锚定\"风险控制\"参数")
                            
                            # 选择要制定计划的股票
                            selected_stocks = st.multiselect(
                                "选择要制定交易计划的股票（可多选）",
                                options=step2_final['股票代码'].tolist(),
                                default=step2_final['股票代码'].head(3).tolist() if len(step2_final) >= 3 else step2_final['股票代码'].tolist(),
                                help="选择您准备交易的股票，系统将为您生成详细的交易计划"
                            )
                            
                            if selected_stocks:
                                st.markdown("#### 📋 交易计划详情")
                                
                                for stock_code in selected_stocks:
                                    stock_row = step2_final[step2_final['股票代码'] == stock_code]
                                    if len(stock_row) == 0:
                                        continue
                                    
                                    stock_row = stock_row.iloc[0]
                                    
                                    with st.expander(f"📌 {stock_code} - {stock_row.get('股票名称', 'N/A')}", expanded=True):
                                        col_plan1, col_plan2 = st.columns(2)
                                        
                                        with col_plan1:
                                            st.markdown("**💰 买入计划**")
                                            
                                            # 获取当前价格（如果有）
                                            current_price_str = str(stock_row.get('买入价', 'N/A'))
                                            try:
                                                current_price = float(current_price_str)
                                            except:
                                                current_price = None
                                            
                                            if current_price:
                                                st.markdown(f"""
                                                - **当前价格**: {current_price:.2f} 元
                                                - **首次买入点**: 次日开盘涨幅 < 3% 且未大幅低开时，开盘后30分钟内介入
                                                - **首次仓位**: 计划总仓位的 50%
                                                - **加仓点**: 股价回调至止损位上方附近且止跌时
                                                - **加仓仓位**: 计划总仓位的 50%
                                                """)
                                            else:
                                                st.markdown("""
                                                - **首次买入点**: 次日开盘涨幅 < 3% 且未大幅低开时，开盘后30分钟内介入
                                                - **首次仓位**: 计划总仓位的 50%
                                                - **加仓点**: 股价回调至止损位上方附近且止跌时
                                                - **加仓仓位**: 计划总仓位的 50%
                                                """)
                                        
                                        with col_plan2:
                                            st.markdown("**🛡️ 风险控制**")
                                            
                                            # 止损位
                                            stop_loss_str = str(stock_row.get('建议止损', 'N/A'))
                                            try:
                                                stop_loss = float(stop_loss_str)
                                                if current_price:
                                                    stop_loss_pct = ((stop_loss - current_price) / current_price) * 100
                                                    st.markdown(f"""
                                                    - **止损价**: {stop_loss:.2f} 元 ({stop_loss_pct:.2f}%)
                                                    - **执行原则**: 无条件执行，盘中触及或跌破立即卖出
                                                    """)
                                                else:
                                                    st.markdown(f"""
                                                    - **止损价**: {stop_loss:.2f} 元
                                                    - **执行原则**: 无条件执行，盘中触及或跌破立即卖出
                                                    """)
                                            except:
                                                st.markdown("""
                                                - **止损价**: 待确定
                                                - **执行原则**: 无条件执行，盘中触及或跌破立即卖出
                                                """)
                                        
                                        st.markdown("**🎯 止盈策略**")
                                        st.markdown("""
                                        **移动止盈法**：
                                        1. 买入后，若股价上涨，将止损价上移至成本价（保证不亏）
                                        2. 当股价从买入后的最高点回落 3-5% 时，卖出止盈
                                        3. 或者，简单持有3天后，无论盈亏都卖出，进行纪律性换仓
                                        """)
                                        
                                        # 显示关键信息
                                        st.markdown("**📊 关键指标**")
                                        key_info = []
                                        if '预测推荐' in stock_row:
                                            key_info.append(f"预测推荐: {stock_row['预测推荐']}")
                                        if '预测评分' in stock_row:
                                            key_info.append(f"预测评分: {stock_row['预测评分']}")
                                        if '信号强度' in stock_row:
                                            key_info.append(f"信号强度: {stock_row['信号强度']}")
                                        if '预测仓位' in stock_row:
                                            key_info.append(f"建议仓位: {stock_row['预测仓位']}")
                                        
                                        st.info(" | ".join(key_info))
                            
                            # 第四步：动态跟踪与纪律
                            st.markdown("### 第四步：动态跟踪与纪律")
                            
                            st.markdown("""
                            **📋 交易纪律清单**：
                            
                            1. **仓位管理**：
                               - 严格遵守"仓位建议"（position_suggestion）
                               - 单只股票占用总资金不超过建议比例
                               - 同时持有2-3只股票，分散风险
                            
                            2. **时间止损**：
                               - 牢记"3日不涨即平仓"原则
                               - 买入后连续3天横盘、无法脱离成本区，果断卖出换股
                            
                            3. **复盘调整**：
                               - 收盘后回顾当天操作与系统推荐
                               - 分析止损触发原因（市场原因 vs 信号失效）
                               - 不断优化对模型参数的理解和信任度
                            
                            **⚠️ 重要提醒**：
                            - 系统是"概率优势"工具，而非"确定性预言"
                            - 严格执行止损和仓位纪律，比追求每次选对股票更重要
                            """)
                            
                            # 生成决策清单（仅在选择了股票时显示）
                            if selected_stocks:
                                st.markdown("### 📝 快速决策清单")
                                
                                decision_checklist = []
                                for stock_code in selected_stocks:
                                    stock_row = step2_final[step2_final['股票代码'] == stock_code]
                                    if len(stock_row) == 0:
                                        continue
                                    stock_row = stock_row.iloc[0]
                                    
                                    checklist_item = {
                                        '股票代码': stock_code,
                                        '股票名称': stock_row.get('股票名称', 'N/A'),
                                        '预测推荐': stock_row.get('预测推荐', 'N/A'),
                                        '预测评分': stock_row.get('预测评分', 'N/A'),
                                        '原始信号': stock_row.get('原始信号', 'N/A'),
                                        '信号强度': stock_row.get('信号强度', 'N/A'),
                                        '验证评分': stock_row.get('验证评分', 'N/A'),
                                    }
                                    decision_checklist.append(checklist_item)
                                
                                if decision_checklist:
                                    checklist_df = pd.DataFrame(decision_checklist)
                                    st.dataframe(
                                        checklist_df,
                                        width='stretch',
                                        hide_index=True
                                    )
                                    
                                    # 保存决策清单
                                    checklist_file = os.path.join("scan_results", f"decision_checklist_{date_str}.csv")
                                    try:
                                        # 确保目录存在
                                        os.makedirs("scan_results", exist_ok=True)
                                        checklist_df.to_csv(checklist_file, index=False, encoding='utf-8-sig')
                                        st.success(f"✅ 决策清单已保存到: `scan_results/decision_checklist_{date_str}.csv`")
                                    except PermissionError:
                                        st.warning(f"⚠️ 无法保存文件（文件可能正在被其他程序使用，如Excel）: `scan_results/decision_checklist_{date_str}.csv`\n请关闭该文件后重试。")
                                    except Exception as e:
                                        st.warning(f"⚠️ 保存文件时出错: {str(e)}")
                        else:
                            st.warning("⚠️ 第二步验证：无法进行深度验证分析")
else:
    # 如果有保存的结果，直接显示（不重新分析）
    if has_saved_results:
        analysis_results = st.session_state.analysis_results
        display_df_all = st.session_state.display_df_all
        
        # 显示分析结果
        st.subheader("📊 收益分析结果")
        
        # 显示来源文件名
        st.info("💡 显示已保存的分析结果。如需重新分析，请点击上方\"分析推荐股票收益\"按钮。")
        
        st.dataframe(display_df_all, width='stretch', hide_index=True)
        
        # 统计信息
        st.subheader("📈 统计信息")
        
        # 显示当前应用的净评分过滤条件
        if net_score_min.strip() or net_score_max.strip():
            min_display = net_score_min.strip() if net_score_min.strip() else '-∞'
            max_display = net_score_max.strip() if net_score_max.strip() else '+∞'
            st.info(f"📊 当前统计基于净评分过滤条件: {min_display} ~ {max_display}（共 {len(display_df_all)} 只股票）")
        
        # 使用过滤后的数据进行统计（数据已经在分析时过滤过了）
        df_filtered = display_df_all.copy()
        valid_t1 = df_filtered['T+1收益率(%)'].apply(lambda x: pd.notna(x) and str(x) != 'N/A').sum() if 'T+1收益率(%)' in df_filtered.columns else 0
        valid_t2 = df_filtered['T+2收益率(%)'].apply(lambda x: pd.notna(x) and str(x) != 'N/A').sum() if 'T+2收益率(%)' in df_filtered.columns else 0
        valid_t3 = df_filtered['T+3收益率(%)'].apply(lambda x: pd.notna(x) and str(x) != 'N/A').sum() if 'T+3收益率(%)' in df_filtered.columns else 0
        valid_t4 = df_filtered['T+4收益率(%)'].apply(lambda x: pd.notna(x) and str(x) != 'N/A').sum() if 'T+4收益率(%)' in df_filtered.columns else 0
        valid_t5 = df_filtered['T+5收益率(%)'].apply(lambda x: pd.notna(x) and str(x) != 'N/A').sum() if 'T+5收益率(%)' in df_filtered.columns else 0
        
        # 由于数据已经格式化，需要从原始数据计算统计
        if st.session_state.analysis_results:
            df_all = pd.DataFrame(st.session_state.analysis_results)
            df_filtered = df_all.copy()
            
            # 应用净评分过滤（如果设置了）
            if 'net_score' in df_filtered.columns:
                min_value = None
                max_value = None
                if net_score_min.strip():
                    try:
                        min_value = float(net_score_min.strip())
                    except:
                        pass
                if net_score_max.strip():
                    try:
                        max_value = float(net_score_max.strip())
                    except:
                        pass
                
                if min_value is not None or max_value is not None:
                    original_count = len(df_filtered)
                    if min_value is not None:
                        df_filtered = df_filtered[df_filtered['net_score'] >= min_value]
                    if max_value is not None:
                        df_filtered = df_filtered[df_filtered['net_score'] <= max_value]
            
            valid_t1 = df_filtered['t1_return'].notna().sum()
            valid_t2 = df_filtered['t2_return'].notna().sum()
            valid_t3 = df_filtered['t3_return'].notna().sum()
            valid_t4 = df_filtered['t4_return'].notna().sum()
            valid_t5 = df_filtered['t5_return'].notna().sum()
            
            # T+1统计
            if valid_t1 > 0:
                avg_t1 = df_filtered['t1_return'].mean()
                win_rate_t1 = (df_filtered['t1_return'] > 0).sum() / valid_t1 * 100
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("T+1平均收益", f"{avg_t1:+.2f}%", f"有效数据: {valid_t1}/{len(df_filtered)}")
                with col2:
                    st.metric("T+1胜率", f"{win_rate_t1:.1f}%")
                with col3:
                    max_t1 = df_filtered['t1_return'].max()
                    min_t1 = df_filtered['t1_return'].min()
                    st.metric("T+1收益范围", f"{min_t1:.2f}% ~ {max_t1:.2f}%")
            
            # T+2到T+5的统计（类似处理）
            # ... 可以添加类似的统计代码
        
        # 显示四步选股法决策分析（使用已保存的数据）
        # ========== 四步选股法决策分析 ==========
        st.markdown("---")
        st.subheader("🎯 四步选股法决策分析")
        st.markdown("""
        **专为3-5天短线稳健操作设计的选股决策系统**
        
        本功能将帮助您按照科学的四步流程，从分析结果中筛选出最具潜力的股票。
        """)
        
        # 第一步：初选清单（使用已保存的display_df_all）
        st.markdown("### 第一步：初选清单 — 聚焦\"预测推荐强度\"")
        
        # 筛选条件
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            max_candidates = st.number_input(
                "核心观察池数量",
                min_value=3,
                max_value=20,
                value=8,
                key="max_candidates",
                help="建议选择5-8只股票作为核心观察池"
            )
        with col_filter2:
            min_predictive_score = st.number_input(
                "最低预测评分",
                min_value=0.0,
                max_value=100.0,
                value=50.0,
                step=1.0,
                key="min_predictive_score",
                help="只考虑预测评分高于此值的股票"
            )
        
        # 筛选逻辑（复用之前的函数）
        def filter_step1(df):
            """第一步筛选：基于预测推荐和预测评分"""
            if df.empty:
                return pd.DataFrame()
            
            filtered = df.copy()
            
            # 如果有预测评分字段，先按预测评分筛选
            if '预测评分' in filtered.columns:
                def parse_score(score):
                    if pd.isna(score):
                        return 0
                    if isinstance(score, (int, float)):
                        return float(score)
                    try:
                        return float(str(score).replace('%', '').strip())
                    except:
                        return 0
                
                filtered['预测评分_数值'] = filtered['预测评分'].apply(parse_score)
                filtered = filtered[filtered['预测评分_数值'] >= min_predictive_score]
                
                # 如果有预测推荐字段，进一步筛选
                if '预测推荐' in filtered.columns:
                    # 筛选：预测推荐为"强力买入"或"买入"，如果没有符合条件的，则显示所有满足评分条件的
                    recommended = filtered[
                        (filtered['预测推荐'] == '强力买入') | 
                        (filtered['预测推荐'] == '买入')
                    ].copy()
                    
                    # 如果有符合条件的，使用它们；否则使用所有满足评分条件的
                    if len(recommended) > 0:
                        filtered = recommended
                
                # 按预测评分从高到低排序
                filtered = filtered.sort_values('预测评分_数值', ascending=False)
            else:
                # 如果没有预测评分字段，按预测推荐筛选
                if '预测推荐' in filtered.columns:
                    filtered = filtered[
                        (filtered['预测推荐'] == '强力买入') | 
                        (filtered['预测推荐'] == '买入')
                    ].copy()
                    
                    # 按预测推荐排序（强力买入优先）
                    filtered['排序权重'] = filtered['预测推荐'].apply(
                        lambda x: 2 if x == '强力买入' else 1
                    )
                    filtered = filtered.sort_values('排序权重', ascending=False)
                else:
                    # 如果既没有预测评分也没有预测推荐，返回空
                    return pd.DataFrame()
            
            return filtered.head(max_candidates)
        
        step1_candidates = filter_step1(display_df_all.copy())
        
        if len(step1_candidates) == 0:
            # 添加调试信息
            debug_info = []
            if '预测推荐' in display_df_all.columns:
                unique_recommendations = display_df_all['预测推荐'].unique()
                debug_info.append(f"预测推荐字段存在，唯一值: {list(unique_recommendations)}")
            else:
                debug_info.append("预测推荐字段不存在")
            
            if '预测评分' in display_df_all.columns:
                # 尝试解析预测评分
                def parse_score(score):
                    if pd.isna(score):
                        return None
                    if isinstance(score, (int, float)):
                        return float(score)
                    try:
                        return float(str(score).replace('%', '').strip())
                    except:
                        return None
                
                scores = display_df_all['预测评分'].apply(parse_score)
                valid_scores = scores[scores.notna()]
                if len(valid_scores) > 0:
                    max_score = valid_scores.max()
                    min_score = valid_scores.min()
                    count_above_threshold = (valid_scores >= min_predictive_score).sum()
                    debug_info.append(f"预测评分字段存在，范围: {min_score:.1f} ~ {max_score:.1f}，高于{min_predictive_score}的股票数: {count_above_threshold}")
                else:
                    debug_info.append("预测评分字段存在，但无法解析为数值")
            else:
                debug_info.append("预测评分字段不存在")
            
            st.warning(f"⚠️ 第一步筛选：未找到符合条件的股票。\n\n**调试信息：**\n" + "\n".join(debug_info) + "\n\n请检查预测推荐字段或调整筛选条件。")
        else:
            st.success(f"✅ 第一步筛选完成：找到 {len(step1_candidates)} 只符合条件的股票")
            
            # 显示初选清单
            step1_display_cols = ['股票代码', '股票名称', '预测推荐', '预测评分', '原始信号', '信号强度', '强度等级']
            available_cols = [col for col in step1_display_cols if col in step1_candidates.columns]
            if available_cols:
                st.dataframe(
                    step1_candidates[available_cols].copy(),
                    width='stretch',
                    hide_index=True
                )
            
            # 第二步及后续步骤（可以复用之前的代码，但需要从display_df_all中获取数据）
            st.info("💡 第二步、第三步、第四步的分析功能需要重新点击\"分析推荐股票收益\"按钮来生成完整数据。")
