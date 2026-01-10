"""
股票监控分析系统 - Streamlit Web应用
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from stock_analyzer import StockAnalyzer, get_all_a_stock_list, get_stocks_by_sectors
from market_analyzer import MarketAnalyzer, TrendStartSignalDetector
from scan_cache import ScanCache
from datetime import datetime
import time
import signal
import sys
import os

# 页面配置
st.set_page_config(
    page_title="",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .signal-buy {
        background-color: #d4edda;
        border: 1px solid #28a745;
        border-radius: 5px;
        padding: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    .signal-buy h4 {
        font-size: 0.9rem;
        margin: 0.3rem 0;
    }
    .signal-buy p {
        font-size: 0.8rem;
        margin: 0.2rem 0;
    }
    .signal-sell {
        background-color: #f8d7da;
        border: 1px solid #dc3545;
        border-radius: 5px;
        padding: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    .signal-sell h4 {
        font-size: 0.9rem;
        margin: 0.3rem 0;
    }
    .signal-sell p {
        font-size: 0.8rem;
        margin: 0.2rem 0;
    }
    .signal-hold {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        padding: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    .signal-hold h4 {
        font-size: 0.9rem;
        margin: 0.3rem 0;
        color: #6c757d;
    }
    .signal-hold p {
        font-size: 0.8rem;
        margin: 0.2rem 0;
        color: #6c757d;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
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
</style>
""", unsafe_allow_html=True)

def format_number(num):
    """格式化数字显示"""
    if num >= 1e9:
        return f"{num/1e9:.2f}B"
    elif num >= 1e6:
        return f"{num/1e6:.2f}M"
    elif num >= 1e3:
        return f"{num/1e3:.2f}K"
    return f"{num:.2f}"

def create_price_chart(df: pd.DataFrame, signals: dict):
    """创建价格图表"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=('价格走势与移动平均线', 'RSI指标', 'MACD指标'),
        row_heights=[0.5, 0.25, 0.25]
    )
    
    # 价格和移动平均线
    fig.add_trace(
        go.Scatter(x=df.index, y=df['Close'], name='收盘价', line=dict(color='#1f77b4', width=2)),
        row=1, col=1
    )
    
    if 'MA5' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['MA5'], name='MA5', line=dict(color='orange', width=1)),
            row=1, col=1
        )
    if 'MA20' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['MA20'], name='MA20', line=dict(color='red', width=1)),
            row=1, col=1
        )
    if 'MA50' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['MA50'], name='MA50', line=dict(color='purple', width=1)),
            row=1, col=1
        )
    
    # 布林带
    if 'BB_Upper' in df.columns and 'BB_Lower' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['BB_Upper'], name='布林带上轨', 
                      line=dict(color='gray', width=1, dash='dash'), showlegend=False),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['BB_Lower'], name='布林带下轨', 
                      line=dict(color='gray', width=1, dash='dash'), 
                      fill='tonexty', fillcolor='rgba(128,128,128,0.1)', showlegend=False),
            row=1, col=1
        )
    
    # RSI
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple', width=2)),
            row=2, col=1
        )
        # RSI超买超卖线
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1, 
                     annotation_text="超买线(70)")
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1,
                     annotation_text="超卖线(30)")
        fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1)
    
    # MACD
    if 'MACD' in df.columns and 'MACD_Signal' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='blue', width=2)),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['MACD_Signal'], name='Signal', line=dict(color='red', width=2)),
            row=3, col=1
        )
        if 'MACD_Hist' in df.columns:
            colors = ['green' if x >= 0 else 'red' for x in df['MACD_Hist']]
            fig.add_trace(
                go.Bar(x=df.index, y=df['MACD_Hist'], name='Histogram', marker_color=colors),
                row=3, col=1
            )
    
    fig.update_layout(
        height=800,
        showlegend=True,
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="日期", row=3, col=1)
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    
    return fig

def display_signal(signal_data: dict):
    """显示交易信号"""
    signal = signal_data.get('signal', 'NONE')
    signal_type = signal_data.get('signal_type', signal)  # 兼容旧版本
    strength = signal_data.get('strength', 0)
    strength_level = signal_data.get('strength_level', '')
    reason = signal_data.get('reason', '')
    net_score = signal_data.get('net_score', 0)
    
    # 使用signal_type判断（兼容详细信号）
    if signal_type == 'BUY' or signal in ['BUY', 'STRONG_BUY', 'CAUTIOUS_BUY']:
        # 根据信号类型显示不同的图标和文字
        if signal == 'STRONG_BUY':
            signal_text = "🟢 强烈买入信号"
        elif signal == 'CAUTIOUS_BUY':
            signal_text = "🟡 谨慎买入信号"
        else:
            signal_text = "🟢 买入信号"
        
        strength_text = f"强度: {strength}%"
        if strength_level:
            strength_text += f" ({strength_level})"
        if net_score:
            strength_text += f" | 净分数: {net_score:+d}"
        
        st.markdown(f"""
        <div class="signal-buy">
            <h4>{signal_text} ({strength_text})</h4>
            <p><strong>建议：</strong>{reason}</p>
        </div>
        """, unsafe_allow_html=True)
    elif signal_type == 'SELL' or signal in ['SELL', 'STRONG_SELL', 'CAUTIOUS_SELL']:
        # 根据信号类型显示不同的图标和文字
        if signal == 'STRONG_SELL':
            signal_text = "🔴 强烈卖出信号"
        elif signal == 'CAUTIOUS_SELL':
            signal_text = "🟡 谨慎卖出信号"
        else:
            signal_text = "🔴 卖出信号"
        
        strength_text = f"强度: {strength}%"
        if strength_level:
            strength_text += f" ({strength_level})"
        if net_score:
            strength_text += f" | 净分数: {net_score:+d}"
        
        st.markdown(f"""
        <div class="signal-sell">
            <h4>{signal_text} ({strength_text})</h4>
            <p><strong>建议：</strong>{reason}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="signal-hold">
            <h4>🟡 持有观望</h4>
            <p><strong>分析：</strong>{reason}</p>
        </div>
        """, unsafe_allow_html=True)

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    if 'scanning' in st.session_state:
        st.session_state.scanning = False
        st.session_state.stop_requested = True
    sys.exit(0)

def _load_ignored_stocks() -> set:
    """加载忽略股票列表（退市股票等）"""
    ignored_stocks = set()
    ignored_file = "ignored_stocks.txt"
    if os.path.exists(ignored_file):
        try:
            with open(ignored_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释行
                    if line and not line.startswith('#'):
                        ignored_stocks.add(line)
        except Exception as e:
            print(f"读取忽略股票列表失败: {e}")
    return ignored_stocks

def analyze_single_stock_for_trend_signal(symbol: str, period: str, strong_sector_names: list, skip_invalid_codes: bool = True):
    """分析单只股票的趋势启动信号（核心算法，不依赖Streamlit）
    
    Args:
        symbol: 股票代码（带后缀，如 '000001.SZ'）
        period: 数据周期
        strong_sector_names: 强势板块名称列表
        skip_invalid_codes: 是否跳过920/900开头的无效代码
    
    Returns:
        tuple: (should_skip, result)
            - should_skip: bool, 是否应该跳过（True表示是无效代码，应跳过）
            - result: dict or None, 如果是信号股票，返回结果字典；否则返回None
    """
    # 检查是否在忽略列表中（退市股票等）
    ignored_stocks = _load_ignored_stocks()
    if symbol in ignored_stocks:
        return True, None  # 应该跳过
    
    # 跳过920和900开头的无效代码（与app.py中的逻辑一致）
    if skip_invalid_codes:
        code = symbol.replace('.SS', '').replace('.SZ', '')
        if (code.startswith('920') or code.startswith('900')) and len(code) == 6:
            return True, None  # 应该跳过
    
    try:
        analyzer = StockAnalyzer(symbol, period)
        if analyzer.fetch_data():
            # 获取股票信息，检查是否为ST股票
            info = analyzer.get_current_info()
            stock_name = info.get('name', symbol)
            
            # 过滤掉ST股票（名字中包含"ST"的股票）
            if 'ST' in str(stock_name).upper():
                # ST股票，返回False, None（不跳过，但也没有信号，避免重复处理）
                return False, None
            
            df = analyzer.calculate_indicators()
            
            # 使用趋势启动信号检测器
            detector = TrendStartSignalDetector(period)
            is_signal, reason, details = detector.check_trend_start_signal(df, symbol, strong_sector_names)
            
            if is_signal:
                result = {
                    'symbol': symbol,
                    'name': stock_name,
                    'price': info.get('current_price', 0),
                    'change_percent': info.get('change_percent', 0),
                    'signal': 'TREND_START',
                    'signal_type': 'BUY',
                    'strength': details.get('signal_strength', 85),
                    'stop_loss': details.get('stop_loss', 0),
                    'reason': details.get('启动理由', reason),
                    'details': details
                }
                return False, result
            else:
                return False, None
        else:
            # 无法获取数据，返回False, None（不跳过，但也没有信号）
            return False, None
    except Exception as e:
        # 分析失败，返回False, None（不跳过，但也没有信号）
        return False, None

def scan_trend_start_signals(period: str, max_stocks: int = 100, scan_all_stocks: bool = False):
    """扫描趋势启动信号（3-5日策略）
    
    Args:
        period: 数据周期
        max_stocks: 最大扫描数量（0表示不限制）
        scan_all_stocks: 是否扫描全部A股（True=全盘扫描，False=仅扫描强势板块）
    """
    st.subheader("🚀 趋势启动信号扫描（3-5日策略）")
    
    # 初始化扫描缓存
    scan_cache = ScanCache()
    
    # 第一步：分析市场环境（一天只分析一次，结果保存到文件）
    st.markdown("### 📊 第一步：市场环境分析")
    
    # 检查是否有今天的分析结果文件（即使重启应用也能读取）
    market_env = scan_cache.get_market_environment()
    
    if market_env is None:
        # 没有文件记录，需要分析
        market_analyzer = MarketAnalyzer()
        
        with st.spinner("正在分析市场环境（首次分析，可能需要一些时间）..."):
            market_env = market_analyzer.analyze_market_environment()
        
        # 保存分析结果到文件（持久化存储，重启应用后仍可用）
        if market_env:
            scan_cache.save_market_environment(market_env)
            st.success("✅ 市场环境分析完成，结果已保存到文件（今天不再重复分析，重启应用后仍可用）")
    else:
        # 使用文件中的分析结果（即使重启应用也能读取）
        st.info(f"📋 使用已保存的市场环境分析结果（分析时间：{market_env.get('timestamp', '未知')}，重启应用后仍可用）")
        
        # 提供重新分析按钮
        if st.button("🔄 重新分析市场环境", help="强制重新分析市场环境（会覆盖缓存）"):
            scan_cache.clear_market_environment_cache()
            market_analyzer = MarketAnalyzer()
            with st.spinner("正在重新分析市场环境..."):
                market_env = market_analyzer.analyze_market_environment()
            if market_env:
                scan_cache.save_market_environment(market_env)
            st.rerun()
    
    # 显示市场环境
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
        return
    elif market_env['recommendation'] == "积极操作":
        st.success(f"✅ **建议：{market_env['recommendation']}** - 市场环境良好，可以积极寻找机会")
    else:
        st.info(f"ℹ️ **建议：{market_env['recommendation']}** - 市场环境中性，谨慎操作")
    
    # 显示强势板块
    if market_env['strong_sectors']:
        with st.expander(f"📈 强势板块列表（前{len(market_env['strong_sectors'])}个）"):
            sector_df = pd.DataFrame(market_env['strong_sectors'], columns=['板块名称', '强度得分'])
            sector_df = sector_df.sort_values('强度得分', ascending=False)
            st.dataframe(sector_df, hide_index=True, width='stretch')
    
    # 显示详细得分明细表（诊断功能）
    if 'sector_details_df' in market_env:
        # 确保sector_details_df是DataFrame且不为空
        if isinstance(market_env['sector_details_df'], pd.DataFrame) and not market_env['sector_details_df'].empty:
            with st.expander("🔍 板块强度得分明细表（诊断功能）", expanded=False):
                st.markdown("""
                **说明：** 此表显示每个板块的综合得分构成，帮助诊断算法判断是否合理。
                - **5日贡献/10日贡献/20日贡献**：各期涨跌幅的得分贡献
                - **资金贡献**：资金流向的得分贡献（权重30%）
                - **成交量贡献**：成交量因子的得分贡献
                - **趋势贡献**：长期趋势健康度的得分贡献
                - **基础调整**：板块逻辑合理性调整分（如房地产板块会扣除3分）
                
                **诊断要点：**
                - 如果某个板块的高分主要来自5日涨幅，可能是短期脉冲，需谨慎
                - 如果资金贡献为负或很小，但综合得分高，可能存在偏差
                - 如果基础调整为负（如房地产-3.0），说明算法已识别并降权
                """)
                
                detail_df = market_env['sector_details_df'].copy()
                
                # 高亮显示关键列
                st.dataframe(
                    detail_df.style.format({
                        '综合得分': '{:.2f}',
                        '5日涨幅(%)': '{:.2f}',
                        '5日贡献': '{:.2f}',
                        '10日涨幅(%)': '{:.2f}',
                        '10日贡献': '{:.2f}',
                        '20日涨幅(%)': '{:.2f}',
                        '20日贡献': '{:.2f}',
                        '资金流向得分': '{:.2f}',
                        '资金贡献': '{:.2f}',
                        '成交量因子': '{:.2f}',
                        '成交量贡献': '{:.2f}',
                        '趋势健康度': '{:.1f}',
                        '趋势贡献': '{:.2f}',
                        '基础调整': '{:.2f}',
                    }).background_gradient(subset=['综合得分'], cmap='RdYlGn'),
                    hide_index=True,
                    width='stretch',
                    height=400
                )
                
                # 添加筛选功能
                st.markdown("#### 🔎 筛选特定板块")
                search_sector = st.text_input("输入板块名称（支持模糊搜索）", "")
                if search_sector:
                    filtered_df = detail_df[detail_df['板块名称'].str.contains(search_sector, case=False, na=False)]
                    if not filtered_df.empty:
                        st.dataframe(filtered_df, hide_index=True, width='stretch')
                    else:
                        st.info(f"未找到包含 '{search_sector}' 的板块")
    
    st.markdown("---")
    
    # 第二步：在强势板块中扫描个股
    st.markdown("### 🔍 第二步：扫描趋势启动信号")
    
    # 初始化实时结果文件路径（根据扫描范围区分）
    today = datetime.now().strftime('%Y%m%d')
    scan_scope_suffix = "all_stocks" if scan_all_stocks else "strong_sectors"
    realtime_results_file = os.path.join("scan_results", f"trend_start_signal_realtime_{scan_scope_suffix}_{today}.txt")
    os.makedirs("scan_results", exist_ok=True)
    
    # 获取强势板块的股票列表
    strong_sector_names = [s[0] for s in market_env['strong_sectors']]
    
    # 确定扫描范围
    scan_scope = "all_stocks" if scan_all_stocks else "strong_sectors"
    
    # 初始化session state
    if 'trend_scanning' not in st.session_state:
        st.session_state.trend_scanning = False
    if 'trend_results' not in st.session_state:
        # 尝试从缓存加载今天已扫描的结果（使用对应的扫描范围）
        cached_results = scan_cache.get_cached_results('trend_start_signal', scan_scope=scan_scope)
        st.session_state.trend_results = cached_results if cached_results else []
    if 'trend_logs' not in st.session_state:
        st.session_state.trend_logs = []
    if 'trend_index' not in st.session_state:
        st.session_state.trend_index = 0
    if 'trend_stats' not in st.session_state:
        st.session_state.trend_stats = {
            'total_scanned': 0,
            'passed_trend': 0,
            'passed_volume': 0,
            'passed_kline': 0,
            'passed_indicator': 0,
            'final_passed': 0
        }
    
    # 检查扫描范围是否改变，如果改变则清除缓存
    if 'trend_scan_all_stocks' not in st.session_state:
        st.session_state.trend_scan_all_stocks = scan_all_stocks
    elif st.session_state.trend_scan_all_stocks != scan_all_stocks:
        # 扫描范围改变了，清除缓存
        st.session_state.trend_scan_all_stocks = scan_all_stocks
        if 'trend_filtered_stocks' in st.session_state:
            del st.session_state.trend_filtered_stocks
        if 'trend_total_stocks' in st.session_state:
            del st.session_state.trend_total_stocks
    
    # 显示缓存统计信息（使用对应的扫描范围）
    cache_stats = scan_cache.get_cache_stats('trend_start_signal', scan_scope=scan_scope)
    if cache_stats['scanned_count'] > 0:
        st.info(f"📋 今天已扫描 {cache_stats['scanned_count']} 只股票（{scan_scope_suffix}），已缓存 {cache_stats['cached_results_count']} 个结果")
    
    # 获取股票列表（只在第一次或需要重新获取时）
    if 'trend_filtered_stocks' not in st.session_state or st.session_state.trend_filtered_stocks is None or st.session_state.trend_filtered_stocks.empty:
        if scan_all_stocks:
            # 全盘扫描：获取全部A股
            with st.spinner("正在获取全部A股列表..."):
                filtered_stocks = get_all_a_stock_list()
                if filtered_stocks.empty:
                    st.error("无法获取A股列表，请检查网络连接或稍后重试")
                    return
                st.session_state.trend_total_stocks = len(filtered_stocks)
                st.success(f"✅ 成功获取 {len(filtered_stocks)} 只A股，将进行全盘扫描")
        else:
            # 强势板块扫描
            with st.spinner("正在获取强势板块中的股票列表..."):
                # 如果强势板块列表为空，使用全部A股
                if not strong_sector_names:
                    st.warning("⚠️ 未找到强势板块，将扫描全部A股")
                    filtered_stocks = get_all_a_stock_list()
                    st.session_state.trend_total_stocks = len(filtered_stocks)
                else:
                    # 真正获取强势板块中的股票
                    st.info(f"📊 强势板块：{', '.join(strong_sector_names[:5])}{'...' if len(strong_sector_names) > 5 else ''}")
                    st.info("🔄 正在获取板块成分股，可能需要一些时间...")
                    
                    # 调用函数获取板块成分股
                    filtered_stocks = get_stocks_by_sectors(strong_sector_names)
                    
                    if filtered_stocks.empty:
                        st.warning("⚠️ 无法获取板块成分股，将使用全部A股作为备选")
                        filtered_stocks = get_all_a_stock_list()
                        st.session_state.trend_total_stocks = len(filtered_stocks)
                        st.info(f"📋 备选方案：使用全部A股，共 {len(filtered_stocks)} 只")
                    else:
                        # 先保存原始股票列表（用于统计）
                        st.session_state.trend_total_stocks = len(filtered_stocks)
                        
                        # 获取今天已扫描的股票列表（使用对应的扫描范围）
                        scanned_stocks = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope=scan_scope)
                        # 强势板块扫描时，也检查全盘扫描缓存
                        if not scan_all_stocks:
                            all_stocks_scanned = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope='all_stocks')
                            if all_stocks_scanned:
                                scanned_stocks = scanned_stocks.union(all_stocks_scanned)
                        scanned_count = len(scanned_stocks) if scanned_stocks else 0
                        pending_count = len(filtered_stocks) - scanned_count
                        
                        st.success(f"✅ 成功获取 {len(filtered_stocks)} 只强势板块股票")
                        if scanned_count > 0:
                            st.info(f"📊 其中 {scanned_count} 只已扫描，{pending_count} 只股票待扫描")
                        else:
                            st.info(f"📊 全部 {len(filtered_stocks)} 只股票待扫描")
                        st.info(f"💡 提示：趋势启动信号条件严格，可能只有少数股票符合条件")
                        
                        # 显示板块来源信息（用于验证）
                        with st.expander("🔍 验证：板块股票来源", expanded=False):
                            st.markdown(f"""
                            **板块筛选验证：**
                            - 强势板块数量：{len(strong_sector_names)} 个
                            - 获取到的股票数量：{len(filtered_stocks)} 只
                            - 数据来源：`get_stocks_by_sectors()` 函数
                            - API调用：`ak.stock_board_industry_cons_em()`
                            
                            **说明：** 如果股票数量明显少于全部A股（5000+只），说明确实是在板块中筛选。
                            如果数量接近全部A股，可能是API调用失败，已回退到全部A股。
                            """)
        
        # 获取今天已扫描的股票列表（在过滤前先统计）
        # 根据扫描范围获取对应的缓存
        scanned_stocks = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope=scan_scope)
        
        # 全盘扫描时，也检查强势板块的缓存，跳过已扫描的股票
        if scan_all_stocks:
            strong_sectors_scanned = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope='strong_sectors')
            if strong_sectors_scanned:
                scanned_stocks = scanned_stocks.union(strong_sectors_scanned)
                st.info(f"ℹ️ 全盘扫描：已跳过强势板块中已扫描的 {len(strong_sectors_scanned)} 只股票")
        
        # 强势板块扫描时，先检查全盘扫描缓存，如果有就直接读取
        if not scan_all_stocks:
            all_stocks_scanned = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope='all_stocks')
            if all_stocks_scanned:
                # 检查强势板块中的股票是否在全盘扫描中已有结果
                strong_sector_stocks_in_all = set(filtered_stocks['symbol']).intersection(all_stocks_scanned)
                if strong_sector_stocks_in_all:
                    st.info(f"ℹ️ 强势板块扫描：发现 {len(strong_sector_stocks_in_all)} 只股票已在全盘扫描中，将直接读取全盘扫描结果")
                    # 从全盘扫描缓存中读取这些股票的结果
                    for symbol in strong_sector_stocks_in_all:
                        cached_result = scan_cache.get_cached_results_from_other_scope('trend_start_signal', symbol, other_scope='all_stocks')
                        if cached_result:
                            # 如果全盘扫描中有结果，直接使用
                            if symbol not in [r.get('symbol') for r in st.session_state.trend_results]:
                                st.session_state.trend_results.append(cached_result)
                    # 将这些股票也加入已扫描列表，避免重复扫描
                    scanned_stocks = scanned_stocks.union(strong_sector_stocks_in_all)
        
        total_stocks_before_filter = len(filtered_stocks)
        scanned_count = len(scanned_stocks) if scanned_stocks else 0
        
        # 确保trend_total_stocks已设置
        if 'trend_total_stocks' not in st.session_state or st.session_state.trend_total_stocks == 0:
            st.session_state.trend_total_stocks = total_stocks_before_filter
        
        # 过滤掉ST股票（名字中包含"ST"的股票）
        if 'name' in filtered_stocks.columns:
            st_stocks_count = filtered_stocks['name'].astype(str).str.contains('ST', case=False, na=False).sum()
            if st_stocks_count > 0:
                filtered_stocks = filtered_stocks[~filtered_stocks['name'].astype(str).str.contains('ST', case=False, na=False)]
                st.info(f"ℹ️ 已过滤 {st_stocks_count} 只ST股票（风险提示股票）")
        
        # 过滤掉ST股票（名字中包含"ST"的股票）
        if 'name' in filtered_stocks.columns:
            st_stocks_count = filtered_stocks['name'].astype(str).str.contains('ST', case=False, na=False).sum()
            if st_stocks_count > 0:
                filtered_stocks = filtered_stocks[~filtered_stocks['name'].astype(str).str.contains('ST', case=False, na=False)]
                st.info(f"ℹ️ 已过滤 {st_stocks_count} 只ST股票（风险提示股票）")
        
        # 过滤掉已扫描的股票
        if scanned_stocks:
            filtered_stocks = filtered_stocks[~filtered_stocks['symbol'].isin(scanned_stocks)]
        
        pending_count = len(filtered_stocks)
        
        # 限制扫描数量（如果max_stocks > 0，否则扫描全部）
        if max_stocks > 0 and pending_count > max_stocks:
            filtered_stocks = filtered_stocks.head(max_stocks)
            if scan_all_stocks:
                st.info(f"📊 限制扫描数量为 {max_stocks} 只（共 {pending_count} 只待扫描A股）")
            else:
                st.info(f"📊 限制扫描数量为 {max_stocks} 只（共 {pending_count} 只待扫描股票）")
        else:
            if scanned_count > 0:
                if scan_all_stocks:
                    st.info(f"📊 将扫描 {pending_count} 只待扫描A股（共 {total_stocks_before_filter} 只，已扫描 {scanned_count} 只）")
                else:
                    st.info(f"📊 将扫描 {pending_count} 只待扫描股票（共 {total_stocks_before_filter} 只，已扫描 {scanned_count} 只）")
            else:
                if scan_all_stocks:
                    st.info(f"📊 将扫描全部 {pending_count} 只A股")
                else:
                    st.info(f"📊 将扫描全部 {pending_count} 只强势板块股票")
        
        # 保存到session_state
        st.session_state.trend_filtered_stocks = filtered_stocks
    else:
        # 使用已保存的股票列表
        filtered_stocks = st.session_state.trend_filtered_stocks
    
    if filtered_stocks.empty:
        # 检查是否是因为全部已扫描
        scanned_stocks = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope=scan_scope)
        # 全盘扫描时，也统计强势板块的缓存
        if scan_all_stocks:
            strong_sectors_scanned = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope='strong_sectors')
            if strong_sectors_scanned:
                scanned_stocks = scanned_stocks.union(strong_sectors_scanned)
        total_stocks = st.session_state.get('trend_total_stocks', 0)
        if scanned_stocks and len(scanned_stocks) > 0 and total_stocks > 0:
            st.warning(f"⚠️ 全部股票已扫描完成（共 {total_stocks} 只，已扫描 {len(scanned_stocks)} 只）")
            st.info("💡 如需重新扫描，请点击下方的「清理当日扫描记录」按钮")
        else:
            st.error("无法获取股票列表")
        return
    
    # 显示扫描统计信息（每次rerun时重新读取，确保显示最新数据）
    scanned_stocks = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope=scan_scope)
    # 全盘扫描时，也统计强势板块的缓存
    if scan_all_stocks:
        strong_sectors_scanned = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope='strong_sectors')
        if strong_sectors_scanned:
            scanned_stocks = scanned_stocks.union(strong_sectors_scanned)
    scanned_count = len(scanned_stocks) if scanned_stocks else 0
    total_stocks = st.session_state.get('trend_total_stocks', len(filtered_stocks))
    pending_count = len(filtered_stocks)
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("总股票数", f"{total_stocks} 只")
    with col_stat2:
        st.metric("已扫描", f"{scanned_count} 只", delta=f"{scanned_count/total_stocks*100:.1f}%" if total_stocks > 0 else "0%")
    with col_stat3:
        st.metric("待扫描", f"{pending_count} 只", delta=f"{pending_count/total_stocks*100:.1f}%" if total_stocks > 0 else "0%")
    
    # 显示实时结果文件路径
    scan_scope_display = "全部A股" if scan_all_stocks else "强势板块"
    scan_scope_suffix = "all_stocks" if scan_all_stocks else "strong_sectors"
    st.info(f"💾 扫描结果将实时保存到: `scan_results/trend_start_signal_realtime_{scan_scope_suffix}_{today}.txt` (扫描范围: {scan_scope_display})")
    
    # 检查是否有被跳过的920开头股票
    skipped_file = os.path.join("scan_results", f"skipped_920_stocks_{today}.txt")
    if os.path.exists(skipped_file):
        try:
            with open(skipped_file, 'r', encoding='utf-8') as f:
                skipped_lines = f.readlines()
                if skipped_lines:
                    skipped_count = len(skipped_lines)
                    with st.expander(f"⚠️ 已跳过 {skipped_count} 只920开头的无效代码股票（点击查看详情）", expanded=False):
                        st.markdown("""
                        **说明：** 这些920开头的代码不是标准A股代码，可能是内部标识符或特殊证券代码。
                        请根据股票名称在主流股票软件（如东方财富、同花顺）中查询实际的标准A股代码。
                        """)
                        # 显示被跳过的股票列表
                        skipped_data = []
                        for line in skipped_lines:
                            parts = line.strip().split('\t')
                            if len(parts) >= 3:
                                skipped_data.append({
                                    '代码': parts[0],
                                    '原始代码': parts[1],
                                    '名称': parts[2]
                                })
                        if skipped_data:
                            skipped_df = pd.DataFrame(skipped_data)
                            st.dataframe(skipped_df, hide_index=True, width='stretch')
                            st.download_button(
                                label="📥 下载被跳过的股票列表（TXT）",
                                data='\n'.join([f"{row['代码']}\t{row['原始代码']}\t{row['名称']}" for row in skipped_data]),
                                file_name=f"skipped_920_stocks_{today}.txt",
                                mime="text/plain"
                            )
        except Exception as e:
            pass  # 如果文件不存在或读取失败，静默处理
    
    # 控制按钮
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if not st.session_state.trend_scanning:
            if st.button("🚀 开始扫描", type="primary", use_container_width=True):
                st.session_state.trend_scanning = True
                # 不清空已有结果，继续追加（这样可以看到之前扫描的结果）
                # st.session_state.trend_results = []
                # st.session_state.trend_logs = []
                st.session_state.trend_index = 0
                st.rerun()
        else:
            st.button("⏸️ 扫描中...", disabled=True, use_container_width=True)
    
    with col_btn2:
        if st.session_state.trend_scanning:
            if st.button("⏸️ 停止扫描", use_container_width=True):
                st.session_state.trend_scanning = False
                st.rerun()
        else:
            if st.button("🔄 清理当日扫描记录", help="清除今天的扫描记录，可以重新扫描全部股票", use_container_width=True):
                # 清除当前扫描范围的缓存
                scan_cache.clear_today_cache('trend_start_signal', scan_scope=scan_scope)
                # 清除session_state中的相关数据
                if 'trend_filtered_stocks' in st.session_state:
                    del st.session_state.trend_filtered_stocks
                if 'trend_total_stocks' in st.session_state:
                    del st.session_state.trend_total_stocks
                if 'trend_results' in st.session_state:
                    st.session_state.trend_results = []
                if 'trend_logs' in st.session_state:
                    st.session_state.trend_logs = []
                if 'trend_index' in st.session_state:
                    st.session_state.trend_index = 0
                st.success(f"✅ 已清理当日扫描记录（{scan_scope_suffix}），可以重新扫描")
                st.rerun()
    
    st.markdown("---")
    
    # 创建两列布局
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📊 扫描结果")
        results_placeholder = st.empty()
    
    with col2:
        st.markdown("### 📝 扫描日志")
        log_placeholder = st.empty()
        progress_placeholder = st.empty()
    
    # 执行扫描
    if st.session_state.trend_scanning:
        current_index = st.session_state.trend_index
        
        if current_index < len(filtered_stocks):
            row = filtered_stocks.iloc[current_index]
            symbol = row['symbol']
            name = row.get('name', symbol)
            
            # 跳过ST股票（名字中包含"ST"的股票）
            if 'ST' in str(name).upper():
                # ST股票，直接跳过，不尝试获取数据
                st.session_state.trend_index = current_index + 1
                st.session_state.trend_stats['total_scanned'] += 1
                
                # 记录到日志
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️ 跳过ST股票: {name} ({symbol}) - 风险提示股票"
                st.session_state.trend_logs.append(log_msg)
                if len(st.session_state.trend_logs) > 20:
                    st.session_state.trend_logs = st.session_state.trend_logs[-20:]
                
                time.sleep(0.01)  # 减少延迟
                st.rerun()
                return
            
            # 跳过920开头的无效代码（不是标准A股代码，可能是内部标识符或特殊证券代码）
            code = symbol.replace('.SS', '').replace('.SZ', '')
            if code.startswith('920') and len(code) == 6:
                # 920开头的无效代码，直接跳过，不尝试获取数据
                # 记录详细信息到日志和文件，方便后续查询实际编号
                st.session_state.trend_index = current_index + 1
                st.session_state.trend_stats['total_scanned'] += 1
                
                # 记录到日志
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️ 跳过无效代码（920开头）: {name} ({symbol}) - 请根据名称查询实际编号"
                st.session_state.trend_logs.append(log_msg)
                if len(st.session_state.trend_logs) > 20:
                    st.session_state.trend_logs = st.session_state.trend_logs[-20:]
                
                # 不再保存到文件（用户要求移除）
                
                time.sleep(0.01)  # 减少延迟
                st.rerun()
                return
            
            # 更新日志
            log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 正在分析: {name} ({symbol})"
            st.session_state.trend_logs.append(log_msg)
            if len(st.session_state.trend_logs) > 20:
                st.session_state.trend_logs = st.session_state.trend_logs[-20:]
            
            # 显示日志
            with log_placeholder.container():
                for log in reversed(st.session_state.trend_logs[-10:]):
                    st.text(log)
            
            # 更新进度
            progress = (current_index + 1) / len(filtered_stocks)
            progress_placeholder.progress(progress, text=f"进度: {current_index + 1}/{len(filtered_stocks)} ({progress*100:.1f}%)")
            
            # 检查是否已扫描过（从缓存，每次rerun时重新读取，确保获取最新数据）
            current_scanned_stocks = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope=scan_scope)
            # 全盘扫描时，也检查强势板块的缓存
            if scan_all_stocks:
                strong_sectors_scanned = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope='strong_sectors')
                if strong_sectors_scanned:
                    current_scanned_stocks = current_scanned_stocks.union(strong_sectors_scanned)
            # 强势板块扫描时，也检查全盘扫描缓存，如果有就直接读取
            elif not scan_all_stocks:
                all_stocks_scanned = scan_cache.get_scanned_stocks('trend_start_signal', scan_scope='all_stocks')
                if all_stocks_scanned and symbol in all_stocks_scanned:
                    # 从全盘扫描缓存中读取结果
                    cached_result = scan_cache.get_cached_results_from_other_scope('trend_start_signal', symbol, other_scope='all_stocks')
                    if cached_result:
                        # 如果全盘扫描中有结果，直接使用
                        if symbol not in [r.get('symbol') for r in st.session_state.trend_results]:
                            st.session_state.trend_results.append(cached_result)
                            st.session_state.trend_stats['final_passed'] += 1
                        # 保存到当前扫描范围的缓存
                        scan_cache.add_scanned_stock('trend_start_signal', symbol, cached_result, scan_scope=scan_scope)
                        st.session_state.trend_index = current_index + 1
                        time.sleep(0.01)
                        st.rerun()
                        return
            
            if symbol in current_scanned_stocks:
                # 已扫描过，跳过
                st.session_state.trend_index = current_index + 1
                time.sleep(0.01)  # 减少延迟
                st.rerun()
                return
            
            # 分析股票（添加小延迟，避免请求过快）
            try:
                # 分批处理策略：每批500只股票后，增加额外延迟
                batch_size = 500
                current_batch = (st.session_state.trend_stats['total_scanned'] // batch_size) + 1
                
                # 基础延迟：20毫秒
                base_delay = 0.02
                
                # 每批结束后，增加额外延迟（避免长时间运行后的限流）
                if st.session_state.trend_stats['total_scanned'] > 0 and st.session_state.trend_stats['total_scanned'] % batch_size == 0:
                    # 每500只股票后，休息1秒
                    time.sleep(1.0)
                    log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏸️ 已扫描 {st.session_state.trend_stats['total_scanned']} 只股票，批次 {current_batch} 完成，休息1秒..."
                    st.session_state.trend_logs.append(log_msg)
                else:
                    # 正常延迟：20毫秒
                    time.sleep(base_delay)
                
                # 调用核心算法函数（与验证程序使用相同的逻辑）
                should_skip, result = analyze_single_stock_for_trend_signal(symbol, period, strong_sector_names, skip_invalid_codes=True)
                
                if should_skip:
                    # 已经在上面处理了跳过逻辑，这里不应该到达
                    pass
                else:
                    # 更新统计信息
                    st.session_state.trend_stats['total_scanned'] += 1
                    
                    if result is not None:
                        # 有信号
                        st.session_state.trend_stats['final_passed'] += 1
                        st.session_state.trend_results.append(result)
                        
                        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {name}: 趋势启动信号"
                        st.session_state.trend_logs.append(log_msg)
                        
                        # 实时写入txt文件
                        try:
                            with open(realtime_results_file, 'a', encoding='utf-8') as f:
                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                f.write(f"\n{'='*80}\n")
                                f.write(f"时间: {timestamp}\n")
                                f.write(f"股票代码: {result['symbol']}\n")
                                f.write(f"股票名称: {result['name']}\n")
                                f.write(f"当前价格: {result['price']:.2f}\n")
                                f.write(f"涨跌幅: {result['change_percent']:.2f}%\n")
                                f.write(f"信号强度: {result['strength']}%\n")
                                f.write(f"止损位: {result['stop_loss']:.2f}\n")
                                f.write(f"启动理由: {result['reason']}\n")
                                f.write(f"{'='*80}\n")
                                f.flush()  # 立即刷新到磁盘
                        except Exception as e:
                            print(f"写入实时结果文件失败: {e}")
                    else:
                        # 没有信号，记录失败原因（用于统计）
                        # 注意：由于使用了核心函数，这里无法获取详细的失败原因
                        # 如果需要详细统计，可以修改核心函数返回更多信息
                        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⚪ {name}: 未符合条件"
                        st.session_state.trend_logs.append(log_msg)
                        
                        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {name}: 趋势启动信号"
                        st.session_state.trend_logs.append(log_msg)
                        
                        # 实时写入txt文件
                        try:
                            with open(realtime_results_file, 'a', encoding='utf-8') as f:
                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                f.write(f"\n{'='*80}\n")
                                f.write(f"时间: {timestamp}\n")
                                f.write(f"股票代码: {symbol}\n")
                                f.write(f"股票名称: {name}\n")
                                f.write(f"当前价格: {info.get('current_price', 0):.2f}\n")
                                f.write(f"涨跌幅: {info.get('change_percent', 0):.2f}%\n")
                                f.write(f"信号强度: {details.get('signal_strength', 85)}%\n")
                                f.write(f"止损位: {details.get('stop_loss', 0):.2f}\n")
                                f.write(f"启动理由: {details.get('启动理由', reason)}\n")
                                f.write(f"{'='*80}\n")
                                f.flush()  # 立即刷新到磁盘
                        except Exception as e:
                            print(f"写入实时结果文件失败: {e}")
                    
                    # 保存到缓存（无论是否有信号都保存，避免重复扫描）
                    scan_cache.add_scanned_stock('trend_start_signal', symbol, result, scan_scope=scan_scope)
                    
            except Exception as e:
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {name} 分析失败: {str(e)[:30]}"
                st.session_state.trend_logs.append(log_msg)
                # 即使失败也记录到缓存，避免重复尝试（但可以设置重试次数）
                scan_cache.add_scanned_stock('trend_start_signal', symbol, None, scan_scope=scan_scope)
            
            st.session_state.trend_index = current_index + 1
            
            # 更新结果显示
            update_trend_results_display(results_placeholder, st.session_state.trend_results)
            
            # 显示统计信息（每10只股票更新一次）
            if st.session_state.trend_stats['total_scanned'] % 10 == 0 and st.session_state.trend_stats['total_scanned'] > 0:
                stats = st.session_state.trend_stats
                total = stats['total_scanned']
                pass_rate = (stats['final_passed'] / total * 100) if total > 0 else 0
                
                # 在日志区域显示统计信息
                with log_placeholder.container():
                    st.markdown("#### 📊 扫描统计")
                    st.markdown(f"""
                    - **已扫描**: {total} 只
                    - **符合条件**: {stats['final_passed']} 只 ({pass_rate:.1f}%)
                    - **趋势条件通过**: {stats['passed_trend']} 只
                    - **量能条件通过**: {stats['passed_volume']} 只  
                    - **K线条件通过**: {stats['passed_kline']} 只
                    - **指标条件通过**: {stats['passed_indicator']} 只
                    """)
                    st.markdown("---")
                    for log in reversed(st.session_state.trend_logs[-10:]):
                        st.text(log)
            
            # 继续扫描（减少延迟以提高速度）
            time.sleep(0.02)  # 从0.05秒减少到0.02秒
            st.rerun()
        else:
            # 扫描完成
            st.session_state.trend_scanning = False
            progress_placeholder.progress(1.0, text="扫描完成！")
            
            # 显示最终统计信息
            stats = st.session_state.trend_stats
            total = stats['total_scanned']
            pass_rate = (stats['final_passed'] / total * 100) if total > 0 else 0
            
            if st.session_state.trend_results:
                st.success(f"✅ 扫描完成！找到 {len(st.session_state.trend_results)} 只趋势启动信号股票")
                
                # 保存到文件（供验证程序使用）
                try:
                    scan_cache.save_daily_results('trend_start_signal', st.session_state.trend_results)
                    st.info("💾 扫描结果已自动保存到 `scan_results/` 目录")
                except Exception as e:
                    st.warning(f"⚠️ 保存结果文件失败: {e}")
                
                # 下载按钮（只在有结果时显示）
                df_results = pd.DataFrame(st.session_state.trend_results)
                csv_bytes = df_results.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 下载结果 (CSV)",
                    data=csv_bytes,
                    file_name=f"trend_start_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv; charset=utf-8"
                )
            else:
                st.info(f"ℹ️ 扫描完成，但未找到符合条件的股票")
            
            # 显示详细统计（无论是否有结果都显示）
            with st.expander("📊 扫描统计详情", expanded=True):
                st.markdown(f"""
                **扫描结果统计：**
                - 总扫描数量：{total} 只
                - 符合条件：{stats['final_passed']} 只（通过率：{pass_rate:.1f}%）
                
                **各条件通过情况：**
                - 趋势条件（价格>MA10, MA5>MA10, MA10斜率>0）：{stats['passed_trend']} 只
                - 量能条件（成交量≥1.8倍20日均量）：{stats['passed_volume']} 只
                - K线条件（涨幅>2.5%，创近10日新高）：{stats['passed_kline']} 只
                - 指标条件（RSI在50-70或MACD零轴上金叉）：{stats['passed_indicator']} 只
                
                **说明：**
                - 趋势启动信号条件严格，需要**同时满足**所有4个条件
                - 在100只股票中只找到1只符合条件，这在某些市场环境下是**正常的**
                - 如果希望找到更多信号，可以：
                  1. 增加扫描数量（如500只或1000只）
                  2. 等待更好的市场环境（市场情绪积极时信号会更多）
                  3. 考虑使用"技术指标评分"功能，条件相对宽松
                """)
    else:
        # 显示已有结果
        if st.session_state.trend_results:
            update_trend_results_display(results_placeholder, st.session_state.trend_results)
        
        if st.session_state.trend_logs:
            with log_placeholder.container():
                for log in reversed(st.session_state.trend_logs[-10:]):
                    st.text(log)

def update_trend_results_display(placeholder, results):
    """更新趋势启动信号结果显示"""
    if not results:
        placeholder.info("暂无结果，等待扫描...")
        return
    
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('strength', ascending=False)
    
    # 格式化显示
    display_columns = ['name', 'symbol', 'price', 'change_percent', 'strength', 'stop_loss', 'reason']
    available_columns = [col for col in display_columns if col in df_results.columns]
    display_df = df_results[available_columns].copy()
    
    # 重命名列
    column_mapping = {
        'name': '股票名称',
        'symbol': '代码',
        'price': '当前价',
        'change_percent': '涨跌幅%',
        'strength': '信号强度',
        'stop_loss': '建议止损位',
        'reason': '启动理由'
    }
    display_df.columns = [column_mapping.get(col, col) for col in display_df.columns]
    
    # 格式化数值
    if '涨跌幅%' in display_df.columns:
        try:
            display_df['涨跌幅%'] = pd.to_numeric(display_df['涨跌幅%'], errors='coerce')
            display_df['涨跌幅%'] = display_df['涨跌幅%'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")
        except:
            pass
    
    if '当前价' in display_df.columns:
        try:
            display_df['当前价'] = pd.to_numeric(display_df['当前价'], errors='coerce')
            display_df['当前价'] = display_df['当前价'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        except:
            pass
    
    if '建议止损位' in display_df.columns:
        try:
            display_df['建议止损位'] = pd.to_numeric(display_df['建议止损位'], errors='coerce')
            display_df['建议止损位'] = display_df['建议止损位'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        except:
            pass
    
    with placeholder.container():
        st.dataframe(display_df, width='stretch', hide_index=True, height=400)
        st.caption(f"已找到 {len(df_results)} 只趋势启动信号股票")

def scan_all_stocks(period: str, max_stocks: int = 100):
    """批量扫描所有A股（实时更新）"""
    st.subheader("🔍 A股批量扫描")
    
    # 初始化扫描缓存
    scan_cache = ScanCache()
    
    # 初始化session state
    if 'scan_results' not in st.session_state:
        st.session_state.scan_results = []
    if 'scan_logs' not in st.session_state:
        st.session_state.scan_logs = []
    if 'scanning' not in st.session_state:
        st.session_state.scanning = False
    if 'scan_progress' not in st.session_state:
        st.session_state.scan_progress = 0
    if 'current_scan_index' not in st.session_state:
        st.session_state.current_scan_index = 0
    if 'stop_requested' not in st.session_state:
        st.session_state.stop_requested = False
    
    # 获取所有A股列表
    if 'stock_list' not in st.session_state or 'max_stocks_setting' not in st.session_state or st.session_state.max_stocks_setting != max_stocks:
        with st.spinner("正在获取A股列表..."):
            stock_list = get_all_a_stock_list()
            if stock_list.empty:
                st.error("无法获取A股列表，请检查网络连接或稍后重试")
                return
            
            # 过滤掉ST股票（名字中包含"ST"的股票）
            if 'name' in stock_list.columns:
                st_stocks_count = stock_list['name'].astype(str).str.contains('ST', case=False, na=False).sum()
                if st_stocks_count > 0:
                    stock_list = stock_list[~stock_list['name'].astype(str).str.contains('ST', case=False, na=False)]
                    st.info(f"ℹ️ 已过滤 {st_stocks_count} 只ST股票（风险提示股票）")
            
            if max_stocks >= len(stock_list):
                st.session_state.stock_list = stock_list
                st.session_state.max_stocks_setting = max_stocks
            else:
                st.session_state.stock_list = stock_list.head(max_stocks)
                st.session_state.max_stocks_setting = max_stocks
    
    stock_list = st.session_state.stock_list
    total_stocks = len(stock_list)
    scanned_count = len(st.session_state.scan_results)
    
    # 显示统计信息
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("总股票数", f"{total_stocks:,}")
    with col_info2:
        st.metric("已扫描", f"{scanned_count:,}")
    with col_info3:
        remaining = total_stocks - scanned_count
        st.metric("剩余", f"{remaining:,}")
    
    # 控制按钮区域
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if not st.session_state.scanning:
            if st.button("🚀 开始扫描", type="primary", use_container_width=True):
                # 如果是重新开始，清空结果
                if scanned_count == 0:
                    st.session_state.scan_results = []
                    st.session_state.scan_logs = []
                    st.session_state.current_scan_index = 0
                st.session_state.scanning = True
                st.rerun()
        else:
            st.button("⏸️ 扫描中...", disabled=True, use_container_width=True)
    
    with col_btn2:
        if st.session_state.scanning:
            if st.button("⏸️ 停止扫描", use_container_width=True, type="secondary"):
                st.session_state.scanning = False
                st.session_state.stop_requested = True  # 添加停止标志
                st.rerun()
        else:
            if scanned_count > 0 and scanned_count < total_stocks:
                if st.button("▶️ 继续扫描", type="primary", use_container_width=True):
                    st.session_state.scanning = True
                    st.rerun()
    
    with col_btn3:
        if scanned_count > 0:
            if st.button("🔄 重新开始", use_container_width=True):
                st.session_state.scan_results = []
                st.session_state.scan_logs = []
                st.session_state.scanning = False
                st.session_state.current_scan_index = 0
                st.session_state.scan_progress = 0
                st.rerun()
    
    st.markdown("---")
    
    # 检查是否有被跳过的920开头股票（在扫描前显示）
    today_scan = datetime.now().strftime('%Y%m%d')
    skipped_file_scan = os.path.join("scan_results", f"skipped_920_stocks_{today_scan}.txt")
    if os.path.exists(skipped_file_scan):
        try:
            with open(skipped_file_scan, 'r', encoding='utf-8') as f:
                skipped_lines = [line.strip() for line in f.readlines() if line.strip()]
                if skipped_lines:
                    skipped_count = len(skipped_lines)
                    with st.expander(f"⚠️ 已跳过 {skipped_count} 只920开头的无效代码股票（点击查看详情）", expanded=False):
                        st.markdown("""
                        **说明：** 这些920开头的代码不是标准A股代码，可能是内部标识符或特殊证券代码。
                        请根据股票名称在主流股票软件（如东方财富、同花顺）中查询实际的标准A股代码。
                        """)
                        # 显示被跳过的股票列表
                        skipped_data = []
                        for line in skipped_lines:
                            parts = line.split('\t')
                            if len(parts) >= 3:
                                skipped_data.append({
                                    '代码': parts[0],
                                    '原始代码': parts[1],
                                    '名称': parts[2]
                                })
                        if skipped_data:
                            skipped_df = pd.DataFrame(skipped_data)
                            st.dataframe(skipped_df, hide_index=True, width='stretch')
                            st.download_button(
                                label="📥 下载被跳过的股票列表（TXT）",
                                data='\n'.join([f"{row['代码']}\t{row['原始代码']}\t{row['名称']}" for row in skipped_data]),
                                file_name=f"skipped_920_stocks_{today_scan}.txt",
                                mime="text/plain"
                            )
        except Exception as e:
            pass  # 如果文件不存在或读取失败，静默处理
    
    # 创建两列布局：左侧结果，右侧日志
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📊 扫描结果（实时更新）")
        results_placeholder = st.empty()
    
    with col2:
        st.markdown("### 📝 扫描日志")
        log_placeholder = st.empty()
        progress_placeholder = st.empty()
    
    # 如果正在扫描，执行扫描逻辑
    if st.session_state.scanning:
        # 检查是否应该停止（在每次循环前检查）
        if st.session_state.stop_requested or not st.session_state.scanning:
            st.session_state.scanning = False
            st.session_state.stop_requested = False
            st.info("⏸️ 扫描已停止")
            st.stop()  # 使用 st.stop() 而不是 return，立即停止执行
            return
        
        # 获取当前扫描位置
        current_index = st.session_state.current_scan_index
        
        if current_index < len(stock_list):
            row = stock_list.iloc[current_index]
            symbol = row['symbol']
            name = row.get('name', symbol)
            
            # 跳过ST股票（名字中包含"ST"的股票）
            if 'ST' in str(name).upper():
                # ST股票，直接跳过，不尝试获取数据
                st.session_state.current_scan_index += 1
                
                # 记录到日志
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️ 跳过ST股票: {name} ({symbol}) - 风险提示股票"
                st.session_state.scan_logs.append(log_msg)
                if len(st.session_state.scan_logs) > 20:
                    st.session_state.scan_logs = st.session_state.scan_logs[-20:]
                
                time.sleep(0.01)  # 减少延迟
                st.rerun()
                return
            
            # 跳过920和900开头的无效代码
            # 920开头：不是标准A股代码，可能是内部标识符或特殊证券代码
            # 900开头.SZ：深圳B股，数据源支持不好，容易导致限流
            code = symbol.replace('.SS', '').replace('.SZ', '')
            if (code.startswith('920') or code.startswith('900')) and len(code) == 6:
                # 跳过这些无效代码，不尝试获取数据
                # 记录详细信息到日志和文件，方便后续查询实际编号
                st.session_state.current_scan_index += 1
                
                # 记录到日志
                code_type = "920开头" if code.startswith('920') else "900开头.SZ"
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️ 跳过无效代码（{code_type}）: {name} ({symbol}) - 请根据名称查询实际编号"
                st.session_state.scan_logs.append(log_msg)
                if len(st.session_state.scan_logs) > 20:
                    st.session_state.scan_logs = st.session_state.scan_logs[-20:]
                
                # 不再保存到文件（用户要求移除）
                
                time.sleep(0.01)  # 减少延迟
                st.rerun()
                return
            
            # 更新日志
            log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 正在分析: {name} ({symbol})"
            st.session_state.scan_logs.append(log_msg)
            if len(st.session_state.scan_logs) > 20:  # 只保留最近20条日志
                st.session_state.scan_logs = st.session_state.scan_logs[-20:]
            
            # 显示日志
            with log_placeholder.container():
                for log in reversed(st.session_state.scan_logs[-10:]):  # 显示最近10条
                    st.text(log)
            
            # 更新进度
            progress = (current_index + 1) / len(stock_list)
            st.session_state.scan_progress = progress
            elapsed_time = ""
            if current_index > 0:
                # 估算剩余时间（简单估算）
                estimated_total = len(stock_list) * 0.15  # 假设每只股票0.15秒
                estimated_remaining = (len(stock_list) - current_index) * 0.15
                if estimated_remaining > 60:
                    elapsed_time = f" | 预计剩余: {int(estimated_remaining/60)}分钟"
                else:
                    elapsed_time = f" | 预计剩余: {int(estimated_remaining)}秒"
            progress_placeholder.progress(progress, text=f"进度: {current_index + 1}/{len(stock_list)} ({progress*100:.1f}%){elapsed_time}")
            
            # 再次检查停止标志（在开始分析前）
            if st.session_state.stop_requested or not st.session_state.scanning:
                st.session_state.scanning = False
                st.session_state.stop_requested = False
                st.info("⏸️ 扫描已停止")
                return
            
            # 分析股票（使用超时控制，避免长时间阻塞）
            # 分批处理策略：每批500只股票后，增加额外延迟
            batch_size = 500
            scanned_count = len(st.session_state.scan_results)
            current_batch = (scanned_count // batch_size) + 1
            
            # 每批结束后，增加额外延迟（避免长时间运行后的限流）
            if scanned_count > 0 and scanned_count % batch_size == 0:
                # 每500只股票后，休息1秒
                time.sleep(1.0)
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏸️ 已扫描 {scanned_count} 只股票，批次 {current_batch} 完成，休息1秒..."
                st.session_state.scan_logs.append(log_msg)
                if len(st.session_state.scan_logs) > 20:
                    st.session_state.scan_logs = st.session_state.scan_logs[-20:]
            
            # 基础延迟：50毫秒（避免请求过快）
            time.sleep(0.05)
            
            try:
                analyzer = StockAnalyzer(symbol, period)
                if analyzer.fetch_data():
                    signals = analyzer.generate_signals()
                    info = analyzer.get_current_info()
                    
                    if signals and info:
                        # 确保所有字段都存在，兼容旧版本
                        signal_value = signals.get('signal', 'HOLD')
                        signal_type_value = signals.get('signal_type', 'HOLD')
                        
                        # 如果没有signal_type，根据signal推断
                        if signal_type_value == 'HOLD':
                            if signal_value in ['STRONG_BUY', 'BUY', 'CAUTIOUS_BUY']:
                                signal_type_value = 'BUY'
                            elif signal_value in ['STRONG_SELL', 'SELL', 'CAUTIOUS_SELL']:
                                signal_type_value = 'SELL'
                            elif signal_value == 'BUY':
                                signal_type_value = 'BUY'
                            elif signal_value == 'SELL':
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
                            'reason': signals.get('reason', '')
                        }
                        st.session_state.scan_results.append(result)
                        
                        # 更新日志
                        signal_type_for_log = result.get('signal_type', result.get('signal', 'HOLD'))
                        if signal_type_for_log == 'BUY':
                            signal_icon = "🟢"
                        elif signal_type_for_log == 'SELL':
                            signal_icon = "🔴"
                        else:
                            signal_icon = "🟡"
                        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {signal_icon} {name}: {result['signal']} (强度:{result['strength']}%)"
                        st.session_state.scan_logs.append(log_msg)
            except Exception as e:
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {name} 分析失败: {str(e)[:50]}"
                st.session_state.scan_logs.append(log_msg)
            
            # 更新扫描索引
            st.session_state.current_scan_index = current_index + 1
            
            # 更新结果显示
            update_results_display(results_placeholder, st.session_state.scan_results)
            
            # 再次检查是否应该停止
            if st.session_state.stop_requested or not st.session_state.scanning:
                st.session_state.scanning = False
                st.session_state.stop_requested = False
                st.info("⏸️ 扫描已停止")
                return
            
            # 添加小延迟（使用更短的延迟，提高响应性）
            # 将延迟拆分成多个小段，每段检查一次停止标志，提高Ctrl+C响应速度
            delay_segments = 10  # 将延迟分成10段
            segment_delay = 0.005  # 每段0.005秒，总共0.05秒
            for _ in range(delay_segments):
                # 每次小延迟前都检查停止标志
                if st.session_state.stop_requested or not st.session_state.scanning:
                    st.session_state.scanning = False
                    st.session_state.stop_requested = False
                    st.info("⏸️ 扫描已停止")
                    return
                time.sleep(segment_delay)
            
            # 继续扫描下一个（只有在没有停止请求时才继续）
            if not st.session_state.stop_requested and st.session_state.scanning:
                st.rerun()
            else:
                st.session_state.scanning = False
                st.session_state.stop_requested = False
                st.info("⏸️ 扫描已停止")
                return
        else:
            # 扫描完成
            st.session_state.scanning = False
            st.session_state.scan_progress = 1.0
            progress_placeholder.progress(1.0, text="扫描完成！")
            
            log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 扫描完成！共分析 {len(st.session_state.scan_results)} 只股票"
            st.session_state.scan_logs.append(log_msg)
            
            # 显示最终结果
            update_results_display(results_placeholder, st.session_state.scan_results)
            
            # 显示完成信息和下载按钮
            df_results = pd.DataFrame(st.session_state.scan_results)
            df_buy = df_results[df_results['signal'] == 'BUY'].copy() if not df_results.empty else pd.DataFrame()
            
            if not df_buy.empty:
                st.success(f"✅ 分析完成！找到 {len(df_buy)} 只具有买入信号的股票")
                
                # 保存到文件（供验证程序使用）
                try:
                    scan_cache.save_daily_results('signal_analysis', st.session_state.scan_results)
                    st.info("💾 扫描结果已自动保存到 `scan_results/` 目录")
                except Exception as e:
                    st.warning(f"⚠️ 保存结果文件失败: {e}")
                
                # 下载按钮（使用UTF-8 BOM编码，确保Excel正确显示中文）
                csv_bytes = df_buy.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 下载结果 (CSV)",
                    data=csv_bytes,
                    file_name=f"a_stock_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv; charset=utf-8"
                )
            else:
                st.info("扫描完成，但当前没有找到买入信号的股票")
            
            # 重置按钮
            if st.button("🔄 重新扫描", use_container_width=True):
                st.session_state.scan_results = []
                st.session_state.scan_logs = []
                st.session_state.scanning = False
                st.session_state.scan_progress = 0
                if 'stock_list' in st.session_state:
                    del st.session_state.stock_list
                st.rerun()
    else:
        # 显示已有结果（如果有）
        if st.session_state.scan_results:
            update_results_display(results_placeholder, st.session_state.scan_results)
        
        # 显示已有日志
        if st.session_state.scan_logs:
            with log_placeholder.container():
                for log in reversed(st.session_state.scan_logs[-10:]):
                    st.text(log)

def update_results_display(placeholder, results):
    """更新结果显示"""
    if not results:
        placeholder.info("暂无结果，等待扫描...")
        return
    
    # 转换为DataFrame并排序
    df_results = pd.DataFrame(results)
    
    # 只显示买入信号（包括所有买入类型）
    # 兼容旧数据：如果没有signal_type，使用signal字段判断
    if 'signal_type' not in df_results.columns:
        # 兼容旧版本数据
        df_buy = df_results[df_results['signal'] == 'BUY'].copy()
    else:
        df_buy = df_results[df_results['signal_type'] == 'BUY'].copy()
    if not df_buy.empty:
        # 按信号强度排序（更直观，0-100%的百分比）
        # 信号强度 = (买入分数 / 总分数) * 100，反映买入信号的相对强度
        df_buy = df_buy.sort_values('strength', ascending=False)
        
        # 格式化显示（信号强度在前，更突出）
        display_columns = ['name', 'symbol', 'price', 'change_percent', 'signal', 'strength', 'strength_level', 'buy_score', 'net_score', 'reason']
        # 只选择存在的列
        available_columns = [col for col in display_columns if col in df_buy.columns]
        if not available_columns:
            # 如果没有可用列，使用基本列
            available_columns = ['name', 'symbol', 'price', 'change_percent', 'strength', 'buy_score', 'reason']
            available_columns = [col for col in available_columns if col in df_buy.columns]
        display_df = df_buy[available_columns].copy()
        
        # 重命名列
        column_mapping = {
            'name': '股票名称',
            'symbol': '代码',
            'price': '当前价',
            'change_percent': '涨跌幅%',
            'signal': '信号类型',
            'strength': '信号强度%',
            'strength_level': '强度等级',
            'buy_score': '买入分数',
            'net_score': '净分数',
            'reason': '分析原因'
        }
        display_df.columns = [column_mapping.get(col, col) for col in display_df.columns]
        
        # 格式化数值（确保先转换为数值类型）
        if '涨跌幅%' in display_df.columns:
            # 如果已经是字符串格式，先提取数值
            try:
                # 检查是否已经是格式化后的字符串
                if display_df['涨跌幅%'].dtype == 'object':
                    # 尝试提取数值（去掉%号）
                    display_df['涨跌幅%'] = display_df['涨跌幅%'].astype(str).str.replace('%', '').str.strip()
                display_df['涨跌幅%'] = pd.to_numeric(display_df['涨跌幅%'], errors='coerce')
                display_df['涨跌幅%'] = display_df['涨跌幅%'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")
            except Exception as e:
                # 如果转换失败，保持原样
                pass
        
        if '当前价' in display_df.columns:
            try:
                if display_df['当前价'].dtype == 'object':
                    # 如果已经是字符串，尝试提取数值
                    display_df['当前价'] = pd.to_numeric(display_df['当前价'], errors='coerce')
                display_df['当前价'] = display_df['当前价'].apply(lambda x: f"{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else str(x) if pd.notna(x) else "N/A")
            except:
                pass
        
        if '信号强度%' in display_df.columns:
            try:
                # 如果已经是百分比格式，先提取数值
                if display_df['信号强度%'].dtype == 'object':
                    # 尝试提取数字部分
                    display_df['信号强度%'] = display_df['信号强度%'].astype(str).str.replace('%', '').str.replace(' ', '').str.strip()
                display_df['信号强度%'] = pd.to_numeric(display_df['信号强度%'], errors='coerce')
                display_df['信号强度%'] = display_df['信号强度%'].apply(lambda x: f"{x}%" if pd.notna(x) else "N/A")
            except:
                pass
        
        if '净分数' in display_df.columns:
            try:
                if display_df['净分数'].dtype == 'object':
                    # 如果已经是格式化字符串，提取数值
                    display_df['净分数'] = display_df['净分数'].astype(str).str.replace('+', '').str.strip()
                display_df['净分数'] = pd.to_numeric(display_df['净分数'], errors='coerce')
                display_df['净分数'] = display_df['净分数'].apply(lambda x: f"{x:+d}" if pd.notna(x) else "N/A")
            except:
                pass
        
        with placeholder.container():
            st.dataframe(
                display_df,
                width='stretch',
                hide_index=True,
                height=400
            )
            st.caption(f"已找到 {len(df_buy)} 只买入信号股票（共分析 {len(results)} 只）")
    else:
        placeholder.info(f"暂无买入信号（已分析 {len(results)} 只股票）")

def main():
    """主函数"""
    st.markdown('<h1 class="main-header"></h1>', unsafe_allow_html=True)
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")
        
        # 模式选择
        mode = st.radio(
            "选择模式",
            ["单个股票分析", "A股批量扫描"],
            help="选择分析单个股票或批量扫描所有A股"
        )
        
        # 数据周期选择
        period = st.selectbox(
            "数据周期",
            options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=2,
            help="选择要分析的时间周期"
        )
        
        if mode == "A股批量扫描":
            scan_type = st.radio(
                "扫描类型",
                ["趋势启动信号", "技术指标评分"],
                help="选择扫描类型：趋势启动信号（3-5日策略）或技术指标评分"
            )
            
            if scan_type == "趋势启动信号":
                # 趋势启动信号扫描
                st.info("📊 趋势启动信号：先分析市场环境，然后寻找启动个股")
                
                # 添加扫描范围选择
                scan_scope = st.radio(
                    "扫描范围",
                    ["强势板块", "全部A股"],
                    help="选择扫描范围：强势板块（仅在强势板块中扫描，效率高）或全部A股（全盘扫描，覆盖所有股票）"
                )
                
                scan_all_stocks_flag = (scan_scope == "全部A股")
                
                if scan_all_stocks_flag:
                    st.info("💡 **全盘扫描模式**：将扫描全部A股，不限制在强势板块中，可能需要较长时间")
                else:
                    st.info("💡 **强势板块模式**：仅在强势板块中扫描，提高效率")
                
                # 添加"扫描全部"选项
                scan_all_option = st.checkbox("扫描全部股票（不限制数量）", value=False, help="勾选后将扫描全部股票，可能需要较长时间")
                if scan_all_option:
                    max_stocks = 0  # 0表示不限制，扫描全部
                    if scan_all_stocks_flag:
                        st.info("💡 将扫描全部A股，可能需要较长时间")
                    else:
                        st.info("💡 将扫描全部强势板块股票，可能需要较长时间")
                else:
                    max_stocks = st.slider(
                        "扫描数量",
                        min_value=10,
                        max_value=5000,  # 提高最大值以支持1393只股票
                        value=100,
                        step=10,
                        help="限制扫描的股票数量（最大5000只）"
                    )
            else:
                # 技术指标评分扫描
                scan_option = st.radio(
                    "扫描范围",
                    ["全部A股", "指定数量"],
                    help="选择扫描全部A股或指定数量"
                )
                if scan_option == "全部A股":
                    max_stocks = 10000  # 设置一个足够大的数字
                else:
                    max_stocks = st.slider(
                        "扫描数量",
                        min_value=10,
                        max_value=1000,
                        value=100,
                        step=10,
                        help="限制扫描的股票数量"
                    )
            symbol = None  # 批量扫描模式下不需要symbol
        else:
            # 股票代码输入（仅在单个股票模式下显示）
            symbol = st.text_input(
                "股票代码",
                value="159652.SS",
                help="输入股票代码，例如：000001.SS（平安银行）、600519.SS（贵州茅台）、AAPL（苹果）、TSLA（特斯拉）等"
            )
            
            # 自动刷新选项
            auto_refresh = st.checkbox("自动刷新", value=False)
            refresh_interval = st.slider("刷新间隔（秒）", 10, 300, 60, disabled=not auto_refresh)
        
        st.markdown("---")
        st.markdown("### 📊 使用说明")
        st.markdown("""
        1. 选择分析模式
        2. 选择分析周期
        3. 查看技术指标和信号
        4. 根据提示做出投资决策
        
        **代码格式：**
        - 美股：`AAPL`、`TSLA`
        - A股：`000001.SS`（上海）或 `000001.SZ`（深圳）
        - 港股：`00700.HK`
        
        **注意：** 本系统仅供参考，不构成投资建议
        """)
    
    # 主内容区
    if mode == "A股批量扫描":
        # scan_type在侧边栏中定义，需要确保可用
        if 'scan_type' in locals() and scan_type == "趋势启动信号":
            scan_all_stocks_flag = scan_scope == "全部A股" if 'scan_scope' in locals() else False
            scan_trend_start_signals(period, max_stocks, scan_all_stocks_flag)
        else:
            scan_all_stocks(period, max_stocks)
    elif symbol:
        try:
            # 创建分析器
            analyzer = StockAnalyzer(symbol, period)
            
            # 显示加载状态
            with st.spinner(f"正在获取 {symbol} 的数据..."):
                if analyzer.fetch_data():
                    # 获取股票信息
                    info = analyzer.get_current_info()
                    
                    if not info:
                        st.error("无法获取股票信息，请检查股票代码是否正确")
                        return
                    
                    # 显示股票基本信息
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "当前价格",
                            f"{info['currency']} {info['current_price']:.2f}",
                            f"{info['change']:+.2f} ({info['change_percent']:+.2f}%)"
                        )
                    
                    with col2:
                        st.metric("成交量", format_number(info['volume']))
                    
                    with col3:
                        if info['market_cap']:
                            st.metric("市值", format_number(info['market_cap']))
                    
                    with col4:
                        st.metric("股票名称", info['name'])
                    
                    # 显示数据日期信息
                    if 'data_date' in info and info['data_date']:
                        today = datetime.now().strftime('%Y-%m-%d')
                        data_date = info['data_date']
                        if data_date == today:
                            st.success(f"✅ 数据日期：{data_date}（最新交易日）")
                        else:
                            st.info(f"ℹ️ 数据日期：{data_date}（当前非交易日，使用最近交易日数据）")
                    
                    st.markdown("---")
                    
                    # 计算指标和生成信号
                    df = analyzer.calculate_indicators()
                    signals = analyzer.generate_signals()
                    
                    # 显示交易信号
                    display_signal(signals)
                    
                    st.markdown("---")
                    
                    # 显示技术指标数值
                    col1, col2, col3, col4 = st.columns(4)
                    
                    indicators = signals.get('indicators', {})
                    with col1:
                        if indicators.get('RSI') is not None:
                            rsi = indicators['RSI']
                            rsi_color = "🟢" if rsi < 30 else "🔴" if rsi > 70 else "🟡"
                            st.metric("RSI", f"{rsi_color} {rsi:.2f}")
                    
                    with col2:
                        if indicators.get('MACD') is not None:
                            st.metric("MACD", f"{indicators['MACD']:.2f}")
                    
                    with col3:
                        if indicators.get('MA5') is not None:
                            st.metric("MA5", f"{indicators['MA5']:.2f}")
                    
                    with col4:
                        if indicators.get('MA20') is not None:
                            st.metric("MA20", f"{indicators['MA20']:.2f}")
                    
                    st.markdown("---")
                    
                    # 显示图表
                    st.subheader("📊 技术分析图表")
                    fig = create_price_chart(df, signals)
                    st.plotly_chart(fig, width='stretch')
                    
                    # 显示数据表格
                    with st.expander("查看详细数据"):
                        st.dataframe(df[['Close', 'Volume', 'MA5', 'MA20', 'RSI', 'MACD']].tail(20))
                    
                    # 自动刷新功能
                    if auto_refresh:
                        time.sleep(refresh_interval)
                        st.rerun()
                    
                else:
                    st.error(f"❌ 无法获取股票 {symbol} 的数据")
                    st.warning("**请检查以下几点：**")
                    
                    if '.SS' in symbol.upper() or '.SZ' in symbol.upper() or (len(symbol) == 6 and symbol.isdigit()):
                        st.info("""
                        **A股代码格式说明：**
                        - 上海股票：`000001.SS` 或 `600519.SS`（6开头）
                        - 深圳股票：`000001.SZ` 或 `002594.SZ`（0或2开头）
                        - 也可以直接输入6位数字，系统会自动识别
                        
                        **如果仍然无法获取，请尝试：**
                        1. 检查网络连接
                        2. 确认股票代码是否正确
                        3. 稍后重试（数据源可能暂时不可用）
                        """)
                    else:
                        st.info("""
                        **股票代码格式：**
                        - **美股**：直接输入代码，如 `AAPL`、`TSLA`
                        - **A股**：需要加后缀，如 `000001.SS`（上海）或 `000001.SZ`（深圳）
                        - **港股**：需要加 `.HK` 后缀，如 `00700.HK`
                        
                        **如果仍然无法获取，请检查：**
                        1. 股票代码是否正确
                        2. 网络连接是否正常
                        3. 数据源是否可用
                        """)
        
        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ 发生错误: {error_msg}")
            
            if 'SS' in symbol.upper() or 'SZ' in symbol.upper() or (len(symbol) == 6 and symbol.isdigit()):
                st.info("""
                **A股数据获取提示：**
                - 如果首次使用，请确保已安装 `akshare`：`pip install akshare`
                - A股代码格式：`000001.SS`（上海）或 `000001.SZ`（深圳）
                - 也可以尝试直接输入6位数字代码
                - 如果akshare不可用，系统会尝试使用yfinance
                """)
            else:
                st.info("""
                **常见问题：**
                - **美股**：直接输入代码（如 AAPL）
                - **A股**：需要加后缀（如 000001.SS 或 000001.SZ）
                - **港股**：需要加 .HK 后缀（如 00700.HK）
                """)
    else:
        st.info("请在左侧输入股票代码开始分析")

if __name__ == "__main__":
    main()
