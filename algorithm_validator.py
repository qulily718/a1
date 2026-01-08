"""
算法验证程序
用于验证app.py中的算法
"""
import streamlit as st
from datetime import datetime, timedelta
from market_analyzer import MarketAnalyzer
from scan_cache import ScanCache
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

# 分析按钮
date_str = selected_date.strftime('%Y%m%d')
cache_file = os.path.join("scan_cache", f"market_env_{date_str}.json")

# 初始化session_state
if 'market_env' not in st.session_state:
    st.session_state.market_env = None
if 'current_date' not in st.session_state:
    st.session_state.current_date = None

# 如果日期改变，清空结果
if st.session_state.current_date != date_str:
    st.session_state.market_env = None
    st.session_state.current_date = date_str

# 如果当前日期没有结果，尝试从文件读取
if st.session_state.market_env is None:
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                st.session_state.market_env = json.load(f)
        except Exception as e:
            st.session_state.market_env = None

if st.button("🔍 分析市场环境", type="primary"):
    # 检查是否已分析过
    if os.path.exists(cache_file) and st.session_state.market_env is not None:
        st.info(f"📋 {date_str} 的市场环境分析结果已存在，直接使用已有结果")
    else:
        st.info(f"正在分析 {date_str} 的市场环境...")
        
        # 调用app.py中的市场环境分析算法
        market_analyzer = MarketAnalyzer()
        
        with st.spinner("正在分析市场环境..."):
            market_env = market_analyzer.analyze_market_environment()
        
        if market_env:
            # 保存结果到文件
            os.makedirs("scan_cache", exist_ok=True)
            
            try:
                # 处理DataFrame（转换为字典以便JSON序列化）
                market_env_copy = market_env.copy()
                if 'sector_details_df' in market_env_copy and isinstance(market_env_copy['sector_details_df'], pd.DataFrame):
                    if not market_env_copy['sector_details_df'].empty:
                        market_env_copy['sector_details_df'] = market_env_copy['sector_details_df'].to_dict('records')
                    else:
                        market_env_copy['sector_details_df'] = []
                
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(market_env_copy, f, ensure_ascii=False, indent=2, default=str)
                st.success(f"✅ 分析结果已保存到: `scan_cache/market_env_{date_str}.json`")
                
                # 保存到session_state
                st.session_state.market_env = market_env
            except Exception as e:
                st.warning(f"⚠️ 保存分析结果失败: {e}")
        else:
            st.error("❌ 市场环境分析失败")

# 显示市场环境结果
if st.session_state.market_env:
    market_env = st.session_state.market_env
    st.success("✅ 市场环境分析完成")
    
    # 显示市场环境结果
    st.subheader("📊 市场环境分析结果")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        status_color = "🟢" if market_env['market_status'] == "积极" else "🟡" if market_env['market_status'] == "中性" else "🔴"
        st.metric("市场状态", f"{status_color} {market_env['market_status']}")
    with col2:
        st.metric("情绪指数", f"{market_env['sentiment_score']:.1f}/100")
    with col3:
        st.metric("强势板块", f"{len(market_env['strong_sectors'])}个")
    
    # 显示市场建议
    if market_env['recommendation'] == "空仓观望":
        st.warning(f"⚠️ **建议：{market_env['recommendation']}** - 市场环境不佳，建议暂停操作")
    elif market_env['recommendation'] == "积极操作":
        st.success(f"✅ **建议：{market_env['recommendation']}** - 市场环境良好，可以积极寻找机会")
    else:
        st.info(f"ℹ️ **建议：{market_env['recommendation']}** - 市场环境中性，谨慎操作")
    
    # 显示强势板块列表
    if market_env['strong_sectors']:
        st.subheader("📈 强势板块列表")
        sector_df = pd.DataFrame(market_env['strong_sectors'], columns=['板块名称', '强度得分'])
        sector_df = sector_df.sort_values('强度得分', ascending=False)
        st.dataframe(sector_df, hide_index=True, use_container_width=True)
    
    # 扫描推荐股票
    st.markdown("---")
    st.subheader("📈 扫描推荐股票")
    
    # 创建两个按钮：扫描强势板块和扫描全盘A股
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        scan_strong_sectors = st.button("🔍 扫描强势板块推荐股票", type="primary", use_container_width=True)
    
    with col_btn2:
        scan_all_stocks = st.button("🔍 扫描全盘A股", type="primary", use_container_width=True)
    
    if scan_strong_sectors:
        # 检查是否已经扫描过（与app.py的逻辑一致）
        results_file = os.path.join("scan_results", f"trend_start_signal_realtime_strong_sectors_{date_str}.txt")
        if os.path.exists(results_file):
            st.info(f"📋 {date_str} 的扫描结果已存在，直接使用已有结果")
            # 读取已有结果
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                st.text_area("已有扫描结果", content, height=300)
            except Exception as e:
                st.warning(f"⚠️ 读取已有结果失败: {e}")
        else:
            # 获取强势板块的股票列表
            strong_sector_names = [s[0] for s in market_env['strong_sectors']]
            
            if not strong_sector_names:
                st.warning("⚠️ 未找到强势板块")
            else:
                from stock_analyzer import get_stocks_by_sectors
                # 导入app.py中的核心算法函数（验证程序应该调用app.py的算法）
                from app import analyze_single_stock_for_trend_signal
                
                # 初始化扫描缓存（与app.py使用相同的逻辑）
                scan_cache = ScanCache()
                
                with st.spinner("正在获取强势板块中的股票列表..."):
                    stock_list = get_stocks_by_sectors(strong_sector_names)
                
                if stock_list.empty:
                    st.warning("⚠️ 无法获取强势板块股票列表")
                else:
                    # 获取该日期已扫描的股票列表（与app.py的逻辑一致）
                    # 强势板块扫描时，使用对应的扫描范围
                    scanned_stocks = scan_cache.get_scanned_stocks('trend_start_signal', date_str, scan_scope='strong_sectors')
                    
                    # 强势板块扫描时，先检查全盘扫描缓存，如果有就直接读取
                    all_stocks_scanned = scan_cache.get_scanned_stocks('trend_start_signal', date_str, scan_scope='all_stocks')
                    if all_stocks_scanned:
                        # 检查强势板块中的股票是否在全盘扫描中已有结果
                        strong_sector_stocks_in_all = set(stock_list['symbol']).intersection(all_stocks_scanned)
                        if strong_sector_stocks_in_all:
                            st.info(f"ℹ️ 强势板块扫描：发现 {len(strong_sector_stocks_in_all)} 只股票已在全盘扫描中，将直接读取全盘扫描结果")
                            # 从全盘扫描缓存中读取这些股票的结果
                            cached_results = []
                            for symbol in strong_sector_stocks_in_all:
                                cached_result = scan_cache.get_cached_results_from_other_scope('trend_start_signal', symbol, date_str, other_scope='all_stocks')
                                if cached_result:
                                    cached_results.append(cached_result)
                            # 显示已读取的结果
                            if cached_results:
                                st.success(f"✅ 从全盘扫描缓存中读取到 {len(cached_results)} 只股票的结果")
                                # 将这些股票也加入已扫描列表，避免重复扫描
                                scanned_stocks = scanned_stocks.union(strong_sector_stocks_in_all)
                    
                    total_stocks_before_filter = len(stock_list)
                    scanned_count = len(scanned_stocks) if scanned_stocks else 0
                    
                    # 过滤掉已扫描的股票（与app.py的逻辑一致）
                    if scanned_stocks:
                        stock_list = stock_list[~stock_list['symbol'].isin(scanned_stocks)]
                    
                    pending_count = len(stock_list)
                    
                    if scanned_count > 0:
                        st.info(f"📊 共 {total_stocks_before_filter} 只股票，其中 {scanned_count} 只已扫描，将扫描剩余 {pending_count} 只")
                    else:
                        st.info(f"📊 成功获取 {len(stock_list)} 只强势板块股票，开始扫描...")
                    
                    if pending_count == 0:
                        st.warning(f"⚠️ 全部股票已扫描完成（共 {total_stocks_before_filter} 只，已扫描 {scanned_count} 只）")
                    else:
                        recommendations = []
                        skipped_count = 0
                        skipped_stocks = []
                        progress_bar = st.progress(0)
                        
                        # 扫描股票（调用app.py中的核心算法）
                        total_stocks = len(stock_list)
                        processed_count = 0
                        for idx, row in stock_list.iterrows():
                            symbol = row['symbol']  # get_stocks_by_sectors已经返回了带后缀的symbol
                            name = row['name']
                            
                            # 再次检查是否已扫描过（与app.py的逻辑一致）
                            current_scanned_stocks = scan_cache.get_scanned_stocks('trend_start_signal', date_str, scan_scope='strong_sectors')
                            # 也检查全盘扫描缓存
                            all_stocks_scanned = scan_cache.get_scanned_stocks('trend_start_signal', date_str, scan_scope='all_stocks')
                            if all_stocks_scanned:
                                current_scanned_stocks = current_scanned_stocks.union(all_stocks_scanned)
                            if symbol in current_scanned_stocks:
                                # 已扫描过，跳过
                                continue
                            
                            # 调用app.py中的核心算法函数（与app.py使用完全相同的逻辑）
                            try:
                                should_skip, result = analyze_single_stock_for_trend_signal(
                                    symbol, 
                                    period="1mo", 
                                    strong_sector_names=strong_sector_names,
                                    skip_invalid_codes=True
                                )
                                
                                if should_skip:
                                    # 跳过920/900开头的无效代码
                                    skipped_count += 1
                                    code = symbol.replace('.SS', '').replace('.SZ', '')
                                    code_type = "920开头" if code.startswith('920') else "900开头.SZ"
                                    skipped_stocks.append({
                                        'symbol': symbol,
                                        'code': code,
                                        'name': name,
                                        'type': code_type
                                    })
                                    
                                    # 不再保存到文件（用户要求移除）
                                    
                                    # 保存到缓存（即使跳过也要保存，避免重复处理）
                                    scan_cache.add_scanned_stock('trend_start_signal', symbol, None, date_str, scan_scope='strong_sectors')
                                elif result is not None:
                                    # 找到信号股票
                                    recommendations.append({
                                        'symbol': result['symbol'],
                                        'name': result['name'],
                                        'price': result['price'],
                                        'change_percent': result['change_percent'],
                                        'signal_strength': result['strength'],
                                        'stop_loss': result['stop_loss'],
                                        'reason': result['reason'],
                                    })
                                    
                                    # 保存到缓存（有信号）
                                    scan_cache.add_scanned_stock('trend_start_signal', symbol, result, date_str, scan_scope='strong_sectors')
                                else:
                                    # 没有信号，但也要保存到缓存（与app.py的逻辑一致：无论是否有信号都保存，避免重复扫描）
                                    scan_cache.add_scanned_stock('trend_start_signal', symbol, None, date_str, scan_scope='strong_sectors')
                            except Exception as e:
                                # 分析失败，也要保存到缓存（与app.py的逻辑一致：即使失败也记录到缓存，避免重复尝试）
                                scan_cache.add_scanned_stock('trend_start_signal', symbol, None, date_str, scan_scope='strong_sectors')
                            
                            # 更新进度（确保值在[0.0, 1.0]范围内）
                            processed_count += 1
                            progress = min(processed_count / total_stocks, 1.0)
                            progress_bar.progress(progress)
                        
                        # 显示跳过的股票信息
                        if skipped_count > 0:
                            st.info(f"ℹ️ 已跳过 {skipped_count} 只无效代码股票（920开头或900开头.SZ）")
                            if skipped_stocks:
                                with st.expander(f"⚠️ 已跳过 {skipped_count} 只无效代码股票（点击查看详情）", expanded=False):
                                    st.markdown("**说明：** 这些920开头或900开头的代码不是标准A股代码，可能是内部标识符或特殊证券代码。")
                                    skipped_df = pd.DataFrame(skipped_stocks)
                                    st.dataframe(skipped_df[['symbol', 'code', 'name', 'type']], use_container_width=True, hide_index=True)
                        
                        # 显示结果
                        if recommendations:
                            st.success(f"✅ 找到 {len(recommendations)} 只推荐股票")
                            
                            # 显示推荐股票列表
                            st.subheader("📋 推荐股票列表")
                            df_recommendations = pd.DataFrame(recommendations)
                            st.dataframe(df_recommendations, use_container_width=True, hide_index=True)
                            
                            # 保存结果到文件（与app.py的格式一致）
                            results_file = os.path.join("scan_results", f"trend_start_signal_realtime_strong_sectors_{date_str}.txt")
                            os.makedirs("scan_results", exist_ok=True)
                            
                            with open(results_file, 'w', encoding='utf-8') as f:
                                for stock in recommendations:
                                    f.write("=" * 80 + "\n")
                                    f.write(f"时间: {date_str}\n")
                                    f.write(f"股票代码: {stock['symbol']}\n")
                                    f.write(f"股票名称: {stock['name']}\n")
                                    f.write(f"当前价格: {stock['price']:.2f}\n")
                                    f.write(f"涨跌幅: {stock['change_percent']:.2f}%\n")
                                    f.write(f"信号强度: {stock['signal_strength']}%\n")
                                    f.write(f"止损位: {stock['stop_loss']:.2f}\n")
                                    f.write(f"启动理由: {stock['reason']}\n")
                                    f.write("=" * 80 + "\n\n")
                            
                            st.success(f"✅ 推荐股票已保存到: `scan_results/trend_start_signal_realtime_strong_sectors_{date_str}.txt`")
                        else:
                            st.info("ℹ️ 未找到符合条件的推荐股票")
                            
    elif scan_all_stocks:
        # 检查是否已经扫描过（与app.py的逻辑一致）
        results_file = os.path.join("scan_results", f"trend_start_signal_realtime_all_stocks_{date_str}.txt")
        if os.path.exists(results_file):
            st.info(f"📋 {date_str} 的全盘扫描结果已存在，直接使用已有结果")
            # 读取已有结果
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                st.text_area("已有扫描结果", content, height=300)
            except Exception as e:
                st.warning(f"⚠️ 读取已有结果失败: {e}")
        else:
            from stock_analyzer import get_all_a_stock_list
            # 导入app.py中的核心算法函数（验证程序应该调用app.py的算法）
            from app import analyze_single_stock_for_trend_signal
            
            # 初始化扫描缓存（与app.py使用相同的逻辑）
            scan_cache = ScanCache()
            
            with st.spinner("正在获取全部A股列表..."):
                stock_list = get_all_a_stock_list()
            
            if stock_list.empty:
                st.warning("⚠️ 无法获取A股列表")
            else:
                # 获取该日期已扫描的股票列表（与app.py的逻辑一致）
                # 全盘扫描时，使用对应的扫描范围
                scanned_stocks = scan_cache.get_scanned_stocks('trend_start_signal', date_str, scan_scope='all_stocks')
                
                # 全盘扫描时，也检查强势板块的缓存，跳过已扫描的股票
                strong_sectors_scanned = scan_cache.get_scanned_stocks('trend_start_signal', date_str, scan_scope='strong_sectors')
                if strong_sectors_scanned:
                    scanned_stocks = scanned_stocks.union(strong_sectors_scanned)
                    st.info(f"ℹ️ 全盘扫描：已跳过强势板块中已扫描的 {len(strong_sectors_scanned)} 只股票")
                
                total_stocks_before_filter = len(stock_list)
                scanned_count = len(scanned_stocks) if scanned_stocks else 0
                
                # 过滤掉已扫描的股票（与app.py的逻辑一致）
                if scanned_stocks:
                    stock_list = stock_list[~stock_list['symbol'].isin(scanned_stocks)]
                
                pending_count = len(stock_list)
                
                if scanned_count > 0:
                    st.info(f"📊 共 {total_stocks_before_filter} 只股票，其中 {scanned_count} 只已扫描，将扫描剩余 {pending_count} 只")
                else:
                    st.info(f"📊 成功获取 {len(stock_list)} 只A股，开始扫描...")
                
                if pending_count == 0:
                    st.warning(f"⚠️ 全部股票已扫描完成（共 {total_stocks_before_filter} 只，已扫描 {scanned_count} 只）")
                else:
                    recommendations = []
                    skipped_count = 0
                    skipped_stocks = []
                    progress_bar = st.progress(0)
                    
                    # 扫描股票（调用app.py中的核心算法）
                    total_stocks = len(stock_list)
                    processed_count = 0
                    for idx, row in stock_list.iterrows():
                        symbol = row['symbol']  # get_all_a_stock_list已经返回了带后缀的symbol
                        name = row['name']
                        
                        # 再次检查是否已扫描过（与app.py的逻辑一致）
                        current_scanned_stocks = scan_cache.get_scanned_stocks('trend_start_signal', date_str, scan_scope='all_stocks')
                        # 也检查强势板块的缓存
                        strong_sectors_scanned = scan_cache.get_scanned_stocks('trend_start_signal', date_str, scan_scope='strong_sectors')
                        if strong_sectors_scanned:
                            current_scanned_stocks = current_scanned_stocks.union(strong_sectors_scanned)
                        if symbol in current_scanned_stocks:
                            # 已扫描过，跳过
                            continue
                        
                        # 调用app.py中的核心算法函数
                        try:
                            # 获取强势板块名称（用于算法分析）
                            strong_sector_names = [s[0] for s in market_env['strong_sectors']] if market_env.get('strong_sectors') else []
                            
                            # 调用app.py中的核心算法（skip_invalid_codes=True会自动过滤920和900开头的股票）
                            # 使用与强势板块扫描相同的period参数
                            skipped, result = analyze_single_stock_for_trend_signal(
                                symbol, "1y", strong_sector_names, skip_invalid_codes=True
                            )
                            
                            if skipped:
                                # 被跳过的股票（920或900开头）
                                skipped_count += 1
                                code = symbol.replace('.SS', '').replace('.SZ', '')
                                skipped_stocks.append({
                                    'symbol': symbol,
                                    'code': code,
                                    'name': name,
                                    'type': '920/900开头无效代码'
                                })
                                
                                # 不再保存到文件（用户要求移除）
                                
                                # 保存到缓存（即使跳过也要保存，避免重复处理）
                                scan_cache.add_scanned_stock('trend_start_signal', symbol, None, date_str, scan_scope='all_stocks')
                            elif result is not None:
                                # 找到信号股票
                                recommendations.append({
                                    'symbol': result['symbol'],
                                    'name': result['name'],
                                    'price': result['price'],
                                    'change_percent': result['change_percent'],
                                    'signal_strength': result['strength'],
                                    'stop_loss': result['stop_loss'],
                                    'reason': result['reason'],
                                })
                                
                                # 保存到缓存（有信号）
                                scan_cache.add_scanned_stock('trend_start_signal', symbol, result, date_str, scan_scope='all_stocks')
                            else:
                                # 没有信号，但也要保存到缓存（与app.py的逻辑一致：无论是否有信号都保存，避免重复扫描）
                                scan_cache.add_scanned_stock('trend_start_signal', symbol, None, date_str, scan_scope='all_stocks')
                        except Exception as e:
                            # 分析失败，也要保存到缓存（与app.py的逻辑一致：即使失败也记录到缓存，避免重复尝试）
                            scan_cache.add_scanned_stock('trend_start_signal', symbol, None, date_str, scan_scope='all_stocks')
                            # 记录错误信息（用于调试）
                            st.warning(f"⚠️ 分析 {symbol} ({name}) 时出错: {str(e)[:100]}")
                        
                        # 更新进度（确保值在[0.0, 1.0]范围内）
                        processed_count += 1
                        progress = min(processed_count / total_stocks, 1.0)
                        progress_bar.progress(progress)
                    
                    # 显示跳过的股票信息
                    if skipped_count > 0:
                        st.info(f"ℹ️ 已跳过 {skipped_count} 只无效代码股票（920开头或900开头.SZ）")
                        if skipped_stocks:
                            with st.expander(f"⚠️ 已跳过 {skipped_count} 只无效代码股票（点击查看详情）", expanded=False):
                                st.markdown("**说明：** 这些920开头或900开头的代码不是标准A股代码，可能是内部标识符或特殊证券代码。")
                                skipped_df = pd.DataFrame(skipped_stocks)
                                st.dataframe(skipped_df[['symbol', 'code', 'name', 'type']], use_container_width=True, hide_index=True)
                    
                    # 显示结果
                    if recommendations:
                        st.success(f"✅ 找到 {len(recommendations)} 只推荐股票")
                        
                        # 显示推荐股票列表
                        st.subheader("📋 推荐股票列表")
                        df_recommendations = pd.DataFrame(recommendations)
                        st.dataframe(df_recommendations, use_container_width=True, hide_index=True)
                        
                        # 保存结果到文件（与app.py的格式一致）
                        results_file = os.path.join("scan_results", f"trend_start_signal_realtime_all_stocks_{date_str}.txt")
                        os.makedirs("scan_results", exist_ok=True)
                        
                        with open(results_file, 'w', encoding='utf-8') as f:
                            for stock in recommendations:
                                f.write("=" * 80 + "\n")
                                f.write(f"时间: {date_str}\n")
                                f.write(f"股票代码: {stock['symbol']}\n")
                                f.write(f"股票名称: {stock['name']}\n")
                                f.write(f"当前价格: {stock['price']:.2f}\n")
                                f.write(f"涨跌幅: {stock['change_percent']:.2f}%\n")
                                f.write(f"信号强度: {stock['signal_strength']}%\n")
                                f.write(f"止损位: {stock['stop_loss']:.2f}\n")
                                f.write(f"启动理由: {stock['reason']}\n")
                                f.write("=" * 80 + "\n\n")
                        
                        st.success(f"✅ 推荐股票已保存到: `scan_results/trend_start_signal_realtime_all_stocks_{date_str}.txt`")
                    else:
                        st.info("ℹ️ 未找到符合条件的推荐股票")
    
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
        # 检查是否有该日期的扫描结果
        strong_sectors_file = os.path.join("scan_results", f"trend_start_signal_realtime_strong_sectors_{date_str}.txt")
        all_stocks_file = os.path.join("scan_results", f"trend_start_signal_realtime_all_stocks_{date_str}.txt")
        
        # 解析推荐股票的函数
        def parse_result_file(file_path):
            """解析扫描结果文件"""
            recommendations = []
            if not os.path.exists(file_path):
                return recommendations
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析文件内容
                import re
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
        
        # 先解析强势板块的推荐股票
        strong_sectors_recommendations = parse_result_file(strong_sectors_file)
        # 再解析全盘A股的推荐股票
        all_stocks_recommendations = parse_result_file(all_stocks_file)
        
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
                    """分析单只股票的收益"""
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
                        # 格式化显示
                        display_columns = ['symbol', 'name', 'source', 'buy_price', 
                                          't1_price', 't1_close', 't1_return', 
                                          't2_price', 't2_close', 't2_return',
                                          't3_price', 't3_close', 't3_return',
                                          't4_price', 't4_close', 't4_return',
                                          't5_price', 't5_close', 't5_return',
                                          'status']
                        
                        available_columns = [col for col in display_columns if col in df_strong.columns]
                        display_df_strong = df_strong[available_columns].copy()
                        
                        # 重命名列
                        column_mapping = {
                            'symbol': '股票代码',
                            'name': '股票名称',
                            'source': '来源',
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
                        price_columns = ['买入价', 'T+1最高价', 'T+1收盘', 'T+2最高价', 'T+2收盘', 'T+3最高价', 'T+3收盘', 'T+4最高价', 'T+4收盘', 'T+5最高价', 'T+5收盘']
                        return_columns = ['T+1收益率(%)', 'T+2收益率(%)', 'T+3收益率(%)', 'T+4收益率(%)', 'T+5收益率(%)']
                        
                        for col in price_columns:
                            if col in display_df_strong.columns:
                                display_df_strong[col] = display_df_strong[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) and x != 'N/A' else "N/A")
                        
                        for col in return_columns:
                            if col in display_df_strong.columns:
                                display_df_strong[col] = display_df_strong[col].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) and x != 'N/A' else "N/A")
                        
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
                        
                        # 格式化显示完整结果
                        df_all = pd.DataFrame(analysis_results)
                        
                        # 显示所有列（包括T+4和T+5）
                        display_columns = ['symbol', 'name', 'source', 'buy_price', 
                                          't1_price', 't1_close', 't1_return', 
                                          't2_price', 't2_close', 't2_return', 
                                          't3_price', 't3_close', 't3_return',
                                          't4_price', 't4_close', 't4_return',
                                          't5_price', 't5_close', 't5_return',
                                          'status']
                        
                        available_columns = [col for col in display_columns if col in df_all.columns]
                        display_df_all = df_all[available_columns].copy()
                        
                        # 重命名列
                        column_mapping = {
                            'symbol': '股票代码',
                            'name': '股票名称',
                            'source': '来源',
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
                        price_columns = ['买入价', 'T+1最高价', 'T+1收盘', 'T+2最高价', 'T+2收盘', 'T+3最高价', 'T+3收盘', 'T+4最高价', 'T+4收盘', 'T+5最高价', 'T+5收盘']
                        return_columns = ['T+1收益率(%)', 'T+2收益率(%)', 'T+3收益率(%)', 'T+4收益率(%)', 'T+5收益率(%)']
                        
                        for col in price_columns:
                            if col in display_df_all.columns:
                                display_df_all[col] = display_df_all[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) and x != 'N/A' else "N/A")
                        
                        for col in return_columns:
                            if col in display_df_all.columns:
                                display_df_all[col] = display_df_all[col].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) and x != 'N/A' else "N/A")
                        
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
