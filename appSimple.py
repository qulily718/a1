"""
A股全盘扫描系统 - Streamlit Web应用
仅用于全盘A股扫描，基于技术指标评分
"""
import streamlit as st
import pandas as pd
from stock_analyzer import (
    StockAnalyzer, 
    get_all_a_stock_list, 
    PredictiveSignalModel,
    scan_sector_and_generate_recommendations,
    get_stocks_by_sectors
)
from scan_cache import ScanCache
from datetime import datetime, date, timedelta
from typing import Tuple, Optional, List, Dict
import time
import os
import json
# 已移除并发扫描，改回串行扫描以降低资源消耗

def get_all_a_stock_list_cached() -> Tuple[pd.DataFrame, bool]:
    """
    获取所有A股股票列表（带当日缓存）
    当天首次获取时从网络获取并保存到文件，后续直接从文件读取
    
    Returns:
        tuple: (DataFrame, is_cached)
            - DataFrame: 包含股票代码和名称的DataFrame
            - is_cached: 是否从缓存读取（True=从缓存，False=从网络获取）
    """
    today = datetime.now().strftime('%Y%m%d')
    cache_dir = "scan_cache"
    cache_file = os.path.join(cache_dir, f"a_stock_list_{today}.csv")
    
    # 确保缓存目录存在
    os.makedirs(cache_dir, exist_ok=True)
    
    # 检查是否有当日的缓存文件
    if os.path.exists(cache_file):
        try:
            # 从缓存文件读取
            cached_df = pd.read_csv(cache_file, encoding='utf-8')
            if not cached_df.empty:
                return cached_df, True
        except Exception as e:
            print(f"读取股票列表缓存失败: {e}，将重新获取")
    
    # 没有缓存或读取失败，从网络获取
    stock_list = get_all_a_stock_list()
    
    # 保存到缓存文件（如果获取成功）
    if not stock_list.empty:
        try:
            stock_list.to_csv(cache_file, index=False, encoding='utf-8')
        except Exception as e:
            print(f"保存股票列表缓存失败: {e}")
    
    return stock_list, False

# 页面配置
# st.set_page_config(
#     page_title="",
#     page_icon="",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 1rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    /* 将所有标题改为正文字体大小 */
    h1, h2, h3, h4, h5, h6 {
        font-size: 1rem !important;
    }
    
    .stSubheader {
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
</style>
""", unsafe_allow_html=True)

def scan_all_stocks(period: str, max_stocks: int = 100, end_date: Optional[date] = None):
    """
    批量扫描所有A股（实时更新），支持历史日期查询
    
    Args:
        period: 数据周期
        max_stocks: 最大扫描股票数
        end_date: 结束日期（date对象），None表示今天
    """
    # 将date对象转换为字符串格式（如果提供）
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    
    # 转换为缓存使用的日期格式（YYYYMMDD）
    cache_date = end_date.strftime('%Y%m%d') if end_date else datetime.now().strftime('%Y%m%d')
    
    # 显示当前查询日期
    if end_date_str:
        st.markdown(f"🔍 **A股全盘扫描** (历史日期: {end_date_str})")
    else:
        st.markdown("🔍 **A股全盘扫描** (实时数据)")
    
    # 初始化扫描缓存
    scan_cache = ScanCache()
    
    # 初始化实时结果文件路径
    today = datetime.now().strftime('%Y%m%d')
    realtime_results_file = os.path.join("scan_results", f"trend_start_signal_realtime_all_stocks_{today}.txt")
    os.makedirs("scan_results", exist_ok=True)
    
    # 初始化session state
    if 'scan_results' not in st.session_state:
        # 尝试从缓存加载已扫描的结果
        # 注意：get_cached_results 只支持今天的缓存，历史日期需要单独处理
        if end_date_str:
            # 历史日期查询，尝试从历史日期缓存加载
            cache_file = scan_cache._get_cache_file_path('signal_analysis', date=cache_date, scan_scope='all_stocks', period=period)
            cached_results = []
            if os.path.exists(cache_file):
                try:
                    import json
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('date') == cache_date and data.get('period') == period:
                            results = data.get('results', {})
                            cached_results = list(results.values())
                            if cached_results:
                                st.info(f"ℹ️ 从缓存恢复 {len(cached_results)} 个扫描结果（日期: {end_date_str}, period={period}）")
                except:
                    pass
            st.session_state.scan_results = cached_results if cached_results else []
        else:
            # 实时数据查询，使用标准方法
            cached_results = scan_cache.get_cached_results('signal_analysis', scan_scope='all_stocks', period=period)
            if cached_results:
                st.info(f"ℹ️ 从缓存恢复 {len(cached_results)} 个扫描结果（period={period}）")
            st.session_state.scan_results = cached_results if cached_results else []
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
    
    # 检查period或end_date是否改变，如果改变则清除相关缓存
    if 'last_period' not in st.session_state:
        st.session_state.last_period = period
    if 'last_end_date' not in st.session_state:
        st.session_state.last_end_date = end_date_str
    
    period_changed = st.session_state.last_period != period
    end_date_changed = st.session_state.last_end_date != end_date_str
    
    if period_changed or end_date_changed:
        # period或end_date改变了，清除扫描缓存和session_state，强制重新扫描
        # 注意：不同period和end_date使用不同的缓存文件，所以不需要清除旧缓存
        # 只需要清除session_state即可
        
        # 清除session_state中的相关数据
        if 'scan_results' in st.session_state:
            st.session_state.scan_results = []
        if 'scan_logs' in st.session_state:
            st.session_state.scan_logs = []
        if 'stock_list' in st.session_state:
            del st.session_state.stock_list
        if 'max_stocks_setting' in st.session_state:
            del st.session_state.max_stocks_setting
        if 'current_scan_index' in st.session_state:
            st.session_state.current_scan_index = 0
        if 'scan_progress' in st.session_state:
            st.session_state.scan_progress = 0
        if 'scanning' in st.session_state:
            st.session_state.scanning = False
        
        st.session_state.last_period = period
        st.session_state.last_end_date = end_date_str
        
        change_msg = []
        if period_changed:
            change_msg.append(f"数据周期: {period}")
        if end_date_changed:
            if end_date_str:
                change_msg.append(f"查询日期: {end_date_str}")
            else:
                change_msg.append("查询日期: 今天")
        
        st.info(f"ℹ️ {'，'.join(change_msg)}，已清除之前的扫描缓存和结果，请重新开始扫描")
    
    # 获取所有A股列表
    if 'stock_list' not in st.session_state or 'max_stocks_setting' not in st.session_state or st.session_state.max_stocks_setting != max_stocks:
        with st.spinner("正在获取A股列表..."):
            stock_list, is_cached = get_all_a_stock_list_cached()
            if stock_list.empty:
                st.error("无法获取A股列表，请检查网络连接或稍后重试")
                return
            if is_cached:
                st.info(f"ℹ️ 从缓存读取A股列表（今日已获取，无需重新下载）")
            
            # 保存原始股票总数（过滤ST和退市前）
            original_total = len(stock_list)
            
            # 过滤掉ST股票（名字中包含"ST"的股票）
            if 'name' in stock_list.columns:
                st_stocks_count = stock_list['name'].astype(str).str.contains('ST', case=False, na=False).sum()
                if st_stocks_count > 0:
                    stock_list = stock_list[~stock_list['name'].astype(str).str.contains('ST', case=False, na=False)]
                    st.info(f"ℹ️ 已过滤 {st_stocks_count} 只ST股票（风险提示股票）")
            
            # 过滤掉退市股票（名字中包含"退市"的股票）
            if 'name' in stock_list.columns:
                delisted_stocks_count = stock_list['name'].astype(str).str.contains('退市', case=False, na=False).sum()
                if delisted_stocks_count > 0:
                    stock_list = stock_list[~stock_list['name'].astype(str).str.contains('退市', case=False, na=False)]
                    st.info(f"ℹ️ 已过滤 {delisted_stocks_count} 只退市股票")
            
            # 保存过滤ST和退市后的总数（这是实际可扫描的A股总数）
            total_after_st_filter = len(stock_list)
            st.session_state.original_stock_count = total_after_st_filter  # 保存原始总数（过滤ST和退市后）
            
            # 获取已扫描的股票列表，过滤掉已扫描的股票（使用当前period和日期）
            scanned_stocks = scan_cache.get_scanned_stocks('signal_analysis', date=cache_date, scan_scope='all_stocks', period=period)
            if scanned_stocks:
                total_before = len(stock_list)
                stock_list = stock_list[~stock_list['symbol'].isin(scanned_stocks)]
                scanned_count = len(scanned_stocks)
                skipped_count = total_before - len(stock_list)
                if skipped_count > 0:
                    st.info(f"ℹ️ 已跳过 {skipped_count} 只今日已扫描的股票（从缓存读取）")
            
            if max_stocks >= len(stock_list) or max_stocks == 0:
                st.session_state.stock_list = stock_list
                st.session_state.max_stocks_setting = max_stocks
            else:
                st.session_state.stock_list = stock_list.head(max_stocks)
                st.session_state.max_stocks_setting = max_stocks
    
    stock_list = st.session_state.stock_list
    
    # 获取原始A股总数（过滤ST和退市后，但不过滤已扫描和max_stocks）
    # 缓存原始股票列表的symbol集合，避免重复计算
    if 'original_stock_symbols' not in st.session_state or 'original_stock_count' not in st.session_state:
        # 如果没有保存原始总数，重新计算（过滤ST和退市后）
        original_list, _ = get_all_a_stock_list_cached()
        if 'name' in original_list.columns:
            # 过滤ST股票
            original_list = original_list[~original_list['name'].astype(str).str.contains('ST', case=False, na=False)]
            # 过滤退市股票
            original_list = original_list[~original_list['name'].astype(str).str.contains('退市', case=False, na=False)]
        st.session_state.original_stock_count = len(original_list)
        st.session_state.original_stock_symbols = set(original_list['symbol'].tolist())
    
    total_stocks = st.session_state.original_stock_count  # 总股票数（原始A股总数，已过滤ST和退市，包含已扫描的）
    original_stock_symbols = st.session_state.original_stock_symbols  # 原始股票代码集合
    
    # 从缓存获取已扫描的股票列表（使用正确的日期参数）
    scanned_stocks_from_cache = scan_cache.get_scanned_stocks('signal_analysis', date=cache_date, scan_scope='all_stocks', period=period)
    
    # 计算已扫描数量（基于原始股票列表）
    if scanned_stocks_from_cache:
        # 统计在原始列表中的已扫描股票（这是真实的已扫描数量）
        scanned_in_original = scanned_stocks_from_cache.intersection(original_stock_symbols)
        scanned_count = len(scanned_in_original)
    else:
        scanned_count = 0
    
    # 计算剩余数量
    remaining = total_stocks - scanned_count
    remaining = max(0, remaining)  # 确保不为负
    
    # 显示统计信息（使用占位符，以便在扫描过程中实时更新）
    # 每次页面执行时都重新计算，确保显示最新数据
    stats_placeholder = st.empty()
    
    # 定义更新统计信息的函数
    def update_stats_display():
        # 每次更新时都从缓存重新读取最新数据
        current_scanned_stocks = scan_cache.get_scanned_stocks('signal_analysis', date=cache_date, scan_scope='all_stocks', period=period)
        if current_scanned_stocks:
            # 使用缓存的原始股票代码集合
            original_stock_symbols_cached = st.session_state.get('original_stock_symbols', set())
            scanned_in_original = current_scanned_stocks.intersection(original_stock_symbols_cached)
            current_scanned_count = len(scanned_in_original)
        else:
            current_scanned_count = 0
        
        current_remaining = max(0, total_stocks - current_scanned_count)
        
        with stats_placeholder.container():
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("总股票数", f"{total_stocks:,}", 
                         help="A股总数（已过滤ST和退市股票，包含已扫描的股票）")
            with col_info2:
                st.metric("已扫描", f"{current_scanned_count:,}",
                         help="已扫描的股票数量（基于原始A股列表）")
            with col_info3:
                st.metric("剩余", f"{current_remaining:,}",
                         help=f"剩余未扫描的股票数 = 总股票数({total_stocks:,}) - 已扫描({current_scanned_count:,})")
    
    # 初始显示统计信息
    update_stats_display()
    
    # 已移除并发扫描设置，使用串行扫描以降低资源消耗
    st.markdown("---")
    
    # 控制按钮区域
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    
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
                st.session_state.stop_requested = True
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
    
    with col_btn4:
        if st.button("🗑️ 清除当日记录", use_container_width=True, help="清除今天的扫描缓存和推荐股票信息，可以重新扫描全部股票"):
            # 清除扫描缓存（使用当前period，清除当前period的缓存）
            scan_cache.clear_today_cache('signal_analysis', scan_scope='all_stocks', period=period)
            
            # 清除推荐股票实时TXT文件
            realtime_txt_file = os.path.join("scan_results", f"trend_start_signal_realtime_all_stocks_{today}.txt")
            if os.path.exists(realtime_txt_file):
                try:
                    os.remove(realtime_txt_file)
                except Exception as e:
                    print(f"清除实时结果文件失败: {e}")
            
            # 清除推荐股票JSON文件（scan_cache目录）
            trend_json_file = os.path.join("scan_cache", f"trend_start_signal_all_stocks_{today}.json")
            if os.path.exists(trend_json_file):
                try:
                    os.remove(trend_json_file)
                except Exception as e:
                    print(f"清除推荐股票JSON文件失败: {e}")
            
            # 清除scan_results目录下的CSV和JSON文件（save_daily_results保存的文件）
            signal_csv_file = os.path.join("scan_results", f"signal_analysis_results_{today}.csv")
            signal_json_file = os.path.join("scan_results", f"signal_analysis_results_{today}.json")
            for file_path in [signal_csv_file, signal_json_file]:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"清除结果文件失败: {e}")
            
            # 清除session_state中的相关数据
            if 'scan_results' in st.session_state:
                st.session_state.scan_results = []
            if 'scan_logs' in st.session_state:
                st.session_state.scan_logs = []
            if 'stock_list' in st.session_state:
                del st.session_state.stock_list
            if 'max_stocks_setting' in st.session_state:
                del st.session_state.max_stocks_setting
            if 'current_scan_index' in st.session_state:
                st.session_state.current_scan_index = 0
            if 'scan_progress' in st.session_state:
                st.session_state.scan_progress = 0
            if 'scanning' in st.session_state:
                st.session_state.scanning = False
            
            st.success("✅ 已清除当日扫描记录和推荐股票信息，可以重新扫描全部股票")
            st.rerun()
    
    # 显示实时结果文件路径
    st.info(f"💾 扫描结果将实时保存到: `scan_results/trend_start_signal_realtime_all_stocks_{today}.txt`")
    
    st.markdown("---")
    
    # 创建两列布局：左侧结果，右侧日志
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("📊 **扫描结果（实时更新）**")
        results_placeholder = st.empty()
    
    with col2:
        st.markdown("📝 **扫描日志**")
        log_placeholder = st.empty()
        progress_placeholder = st.empty()
    
    # 如果正在扫描，执行扫描逻辑（串行扫描）
    if st.session_state.scanning:
        # 检查是否应该停止（在每次循环前检查）
        if st.session_state.stop_requested or not st.session_state.scanning:
            st.session_state.scanning = False
            st.session_state.stop_requested = False
            st.info("⏸️ 扫描已停止")
            st.stop()
            return
        
        # 串行扫描逻辑
        # 获取当前扫描位置
        current_index = st.session_state.current_scan_index
        
        if current_index < len(stock_list):
            row = stock_list.iloc[current_index]
            symbol = row['symbol']
            name = row.get('name', symbol)
            
            # 检查是否已扫描过（从缓存，每次rerun时重新读取，确保获取最新数据，使用当前period和日期）
            current_scanned_stocks = scan_cache.get_scanned_stocks('signal_analysis', date=cache_date, scan_scope='all_stocks', period=period)
            if symbol in current_scanned_stocks:
                # 已扫描过，跳过
                st.session_state.current_scan_index = current_index + 1
                # 更新统计信息
                update_stats_display()
                time.sleep(0.01)
                st.rerun()
                return
            
            # 跳过ST股票（名字中包含"ST"的股票）
            if 'ST' in str(name).upper():
                st.session_state.current_scan_index += 1
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️ 跳过ST股票: {name} ({symbol}) - 风险提示股票"
                st.session_state.scan_logs.append(log_msg)
                if len(st.session_state.scan_logs) > 20:
                    st.session_state.scan_logs = st.session_state.scan_logs[-20:]
                # 更新统计信息
                update_stats_display()
                time.sleep(0.01)
                st.rerun()
                return
            
            # 跳过退市股票（名字中包含"退市"的股票）
            if '退市' in str(name):
                st.session_state.current_scan_index += 1
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️ 跳过退市股票: {name} ({symbol})"
                st.session_state.scan_logs.append(log_msg)
                if len(st.session_state.scan_logs) > 20:
                    st.session_state.scan_logs = st.session_state.scan_logs[-20:]
                # 更新统计信息
                update_stats_display()
                time.sleep(0.01)
                st.rerun()
                return
            
            # 跳过920和900开头的无效代码
            code = symbol.replace('.SS', '').replace('.SZ', '')
            if (code.startswith('920') or code.startswith('900')) and len(code) == 6:
                st.session_state.current_scan_index += 1
                code_type = "920开头" if code.startswith('920') else "900开头.SZ"
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️ 跳过无效代码（{code_type}）: {name} ({symbol})"
                st.session_state.scan_logs.append(log_msg)
                if len(st.session_state.scan_logs) > 20:
                    st.session_state.scan_logs = st.session_state.scan_logs[-20:]
                # 更新统计信息
                update_stats_display()
                time.sleep(0.01)
                st.rerun()
                return
            
            # 更新日志
            log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 正在分析: {name} ({symbol})"
            st.session_state.scan_logs.append(log_msg)
            if len(st.session_state.scan_logs) > 20:
                st.session_state.scan_logs = st.session_state.scan_logs[-20:]
            
            # 显示日志
            with log_placeholder.container():
                for log in reversed(st.session_state.scan_logs[-10:]):
                    st.text(log)
            
            # 更新进度（确保在 [0.0, 1.0] 范围内）
            if len(stock_list) > 0:
                progress = min(1.0, (current_index + 1) / len(stock_list))
            else:
                progress = 1.0
            st.session_state.scan_progress = progress
            elapsed_time = ""
            if current_index > 0:
                estimated_total = len(stock_list) * 0.15
                estimated_remaining = (len(stock_list) - current_index) * 0.15
                if estimated_remaining > 60:
                    elapsed_time = f" | 预计剩余: {int(estimated_remaining/60)}分钟"
                else:
                    elapsed_time = f" | 预计剩余: {int(estimated_remaining)}秒"
            progress_placeholder.progress(progress, text=f"进度: {current_index + 1}/{len(stock_list)} ({progress*100:.1f}%){elapsed_time}")
            
            # 再次检查停止标志
            if st.session_state.stop_requested or not st.session_state.scanning:
                st.session_state.scanning = False
                st.session_state.stop_requested = False
                st.info("⏸️ 扫描已停止")
                return
            
            # 分批处理策略：每批500只股票后，增加额外延迟
            batch_size = 500
            # 从缓存获取已扫描的股票数量（更准确，使用正确的日期）
            current_scanned_stocks_for_batch = scan_cache.get_scanned_stocks('signal_analysis', date=cache_date, scan_scope='all_stocks', period=period)
            scanned_count_for_batch = len(current_scanned_stocks_for_batch) if current_scanned_stocks_for_batch else 0
            current_batch = (scanned_count_for_batch // batch_size) + 1
            
            # 每批结束后，增加额外延迟（避免长时间运行后的限流）
            if scanned_count_for_batch > 0 and scanned_count_for_batch % batch_size == 0:
                time.sleep(1.0)
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⏸️ 已扫描 {scanned_count_for_batch} 只股票，批次 {current_batch} 完成，休息1秒..."
                st.session_state.scan_logs.append(log_msg)
                if len(st.session_state.scan_logs) > 20:
                    st.session_state.scan_logs = st.session_state.scan_logs[-20:]
            
            # 基础延迟：50毫秒（避免请求过快）
            time.sleep(0.05)
            
            try:
                # 将end_date转换为字符串格式（如果提供）
                end_date_for_analyzer = end_date_str if end_date_str else None
                analyzer = StockAnalyzer(symbol, period, end_date=end_date_for_analyzer)
                # 调试信息：显示使用的period和end_date（只在第一次扫描时显示）
                scanned_count_before = len(st.session_state.scan_results)
                if scanned_count_before == 0:
                    if end_date_str:
                        print(f"🔍 开始扫描，使用数据周期: {period}，查询日期: {end_date_str}")
                    else:
                        print(f"🔍 开始扫描，使用数据周期: {period}，查询日期: 今天")
                if analyzer.fetch_data():
                    signals = analyzer.generate_signals()
                    info = analyzer.get_current_info()
                    
                    # 计算预测因子（用于预测模型）
                    predictive_factors = {}
                    predictive_recommendation = {}
                    try:
                        predictive_factors = analyzer.calculate_predictive_factors()
                        
                        # 初始化预测模型（如果还没有初始化）
                        if 'predictive_model' not in st.session_state:
                            st.session_state.predictive_model = PredictiveSignalModel()
                        
                        # 获取市场趋势评分（简化版，后续可以优化）
                        market_trend_score = st.session_state.predictive_model.get_market_trend_score()
                        
                        # 生成预测推荐（板块共识度暂时设为0，后续可以添加板块功能）
                        sector_consensus = 0.0  # 全盘扫描时暂时不使用板块共识度
                        
                        # 准备信号字典（包含current_price）
                        signal_dict = signals.copy()
                        signal_dict['current_price'] = info.get('current_price', 0)
                        
                        # 生成预测推荐
                        predictive_recommendation = st.session_state.predictive_model.generate_recommendation_strength(
                            stock_factors=predictive_factors,
                            sector_consensus=sector_consensus,
                            market_trend_score=market_trend_score,
                            stock_signal=signal_dict
                        )
                    except Exception as e:
                        print(f"计算预测因子失败 {symbol}: {e}")
                        predictive_factors = {}
                        predictive_recommendation = {}
                    
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
                            'reason': signals.get('reason', ''),
                            # 添加预测模型相关字段
                            'predictive_score': predictive_recommendation.get('final_score', 0),
                            'predictive_recommendation': predictive_recommendation.get('recommendation', ''),
                            'predictive_stop_loss': predictive_recommendation.get('stop_loss', 0),
                            'predictive_stop_loss_type': predictive_recommendation.get('stop_loss_type', ''),
                            'predictive_time_stop': predictive_recommendation.get('time_stop_loss', ''),
                            'predictive_position': predictive_recommendation.get('position_suggestion', ''),
                            'original_signal': predictive_recommendation.get('original_signal', signal_value),
                            'original_reason': predictive_recommendation.get('original_reason', signals.get('reason', '')),
                            'suggested_stop_loss': signals.get('suggested_stop_loss', 0),
                            'position_suggestion': signals.get('position_suggestion', '')
                        }
                        st.session_state.scan_results.append(result)
                        
                        # 如果是买入信号，实时写入txt文件
                        if signal_type_value == 'BUY':
                            try:
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
                                    f.flush()  # 立即刷新到磁盘
                            except Exception as e:
                                print(f"写入实时结果文件失败: {e}")
                        
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
                        
                        # 保存到缓存（无论是否有信号都保存，避免重复扫描，使用当前period和日期）
                        scan_cache.add_scanned_stock('signal_analysis', symbol, result, date=cache_date, scan_scope='all_stocks', period=period)
                    else:
                        # 没有信号，也保存到缓存（避免重复扫描，使用当前period和日期）
                        scan_cache.add_scanned_stock('signal_analysis', symbol, None, date=cache_date, scan_scope='all_stocks', period=period)
            except Exception as e:
                log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {name} 分析失败: {str(e)[:50]}"
                st.session_state.scan_logs.append(log_msg)
                # 即使失败也记录到缓存，避免重复尝试（使用当前period和日期）
                scan_cache.add_scanned_stock('signal_analysis', symbol, None, date=cache_date, scan_scope='all_stocks', period=period)
            
            # 更新扫描索引
            st.session_state.current_scan_index = current_index + 1
            
            # 更新统计信息显示（从缓存重新读取最新数据）
            update_stats_display()
            
            # 更新结果显示
            update_results_display(results_placeholder, st.session_state.scan_results)
            
            # 再次检查是否应该停止
            if st.session_state.stop_requested or not st.session_state.scanning:
                st.session_state.scanning = False
                st.session_state.stop_requested = False
                st.info("⏸️ 扫描已停止")
                return
            
            # 添加小延迟（将延迟拆分成多个小段，每段检查一次停止标志）
            delay_segments = 10
            segment_delay = 0.005
            for _ in range(delay_segments):
                if st.session_state.stop_requested or not st.session_state.scanning:
                    st.session_state.scanning = False
                    st.session_state.stop_requested = False
                    st.info("⏸️ 扫描已停止")
                    return
                time.sleep(segment_delay)
            
            # 继续扫描下一个（在rerun前更新统计信息）
            if not st.session_state.stop_requested and st.session_state.scanning:
                # 更新统计信息（确保显示最新数据）
                update_stats_display()
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
                
                # 保存到文件（保存买入信号的股票，使用trend_start_signal类型以保持格式一致）
                try:
                    # 保存所有扫描结果（signal_analysis类型）
                    scan_cache.save_daily_results('signal_analysis', st.session_state.scan_results)
                    
                    # 保存买入信号的股票（trend_start_signal类型，格式与原来一致）
                    buy_results = [r for r in st.session_state.scan_results if r.get('signal_type') == 'BUY' or r.get('signal') == 'BUY']
                    if buy_results:
                        # 保存到scan_cache目录，文件名包含all_stocks（格式：trend_start_signal_all_stocks_YYYYMMDD.json）
                        import json
                        cache_file = os.path.join("scan_cache", f"trend_start_signal_all_stocks_{today}.json")
                        os.makedirs("scan_cache", exist_ok=True)
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(buy_results, f, ensure_ascii=False, indent=2)
                    
                    st.info("💾 扫描结果已自动保存到 `scan_results/` 和 `scan_cache/` 目录")
                except Exception as e:
                    st.warning(f"⚠️ 保存结果文件失败: {e}")
                
                # 下载按钮
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
    if 'signal_type' not in df_results.columns:
        df_buy = df_results[df_results['signal'] == 'BUY'].copy()
    else:
        df_buy = df_results[df_results['signal_type'] == 'BUY'].copy()
    
    if not df_buy.empty:
        # 按信号强度排序
        df_buy = df_buy.sort_values('strength', ascending=False)
        
        # 格式化显示（添加预测评分相关列）
        display_columns = ['name', 'symbol', 'price', 'change_percent', 'signal', 'strength', 'strength_level', 
                          'predictive_score', 'predictive_recommendation', 'predictive_stop_loss', 
                          'predictive_stop_loss_type', 'predictive_time_stop', 'predictive_position',
                          'buy_score', 'net_score', 'reason']
        available_columns = [col for col in display_columns if col in df_buy.columns]
        if not available_columns:
            available_columns = ['name', 'symbol', 'price', 'change_percent', 'strength', 'buy_score', 'reason']
            available_columns = [col for col in available_columns if col in df_buy.columns]
        display_df = df_buy[available_columns].copy()
        
        # 如果有预测评分，按预测评分排序（优先），否则按信号强度排序
        if 'predictive_score' in display_df.columns:
            display_df = display_df.sort_values('predictive_score', ascending=False)
        else:
            display_df = display_df.sort_values('strength', ascending=False)
        
        # 重命名列
        column_mapping = {
            'name': '股票名称',
            'symbol': '代码',
            'price': '当前价',
            'change_percent': '涨跌幅%',
            'signal': '信号类型',
            'strength': '信号强度%',
            'strength_level': '强度等级',
            'predictive_score': '预测评分',
            'predictive_recommendation': '预测建议',
            'predictive_stop_loss': '预测止损',
            'predictive_stop_loss_type': '止损类型',
            'predictive_time_stop': '时间止损',
            'predictive_position': '预测仓位',
            'buy_score': '买入分数',
            'net_score': '净分数',
            'reason': '分析原因'
        }
        display_df.columns = [column_mapping.get(col, col) for col in display_df.columns]
        
        # 格式化数值
        if '涨跌幅%' in display_df.columns:
            try:
                if display_df['涨跌幅%'].dtype == 'object':
                    display_df['涨跌幅%'] = display_df['涨跌幅%'].astype(str).str.replace('%', '').str.strip()
                display_df['涨跌幅%'] = pd.to_numeric(display_df['涨跌幅%'], errors='coerce')
                display_df['涨跌幅%'] = display_df['涨跌幅%'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")
            except:
                pass
        
        if '当前价' in display_df.columns:
            try:
                if display_df['当前价'].dtype == 'object':
                    display_df['当前价'] = pd.to_numeric(display_df['当前价'], errors='coerce')
                display_df['当前价'] = display_df['当前价'].apply(lambda x: f"{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else str(x) if pd.notna(x) else "N/A")
            except:
                pass
        
        if '信号强度%' in display_df.columns:
            try:
                if display_df['信号强度%'].dtype == 'object':
                    display_df['信号强度%'] = display_df['信号强度%'].astype(str).str.replace('%', '').str.replace(' ', '').str.strip()
                display_df['信号强度%'] = pd.to_numeric(display_df['信号强度%'], errors='coerce')
                display_df['信号强度%'] = display_df['信号强度%'].apply(lambda x: f"{x}%" if pd.notna(x) else "N/A")
            except:
                pass
        
        if '净分数' in display_df.columns:
            try:
                if display_df['净分数'].dtype == 'object':
                    display_df['净分数'] = display_df['净分数'].astype(str).str.replace('+', '').str.strip()
                display_df['净分数'] = pd.to_numeric(display_df['净分数'], errors='coerce')
                display_df['净分数'] = display_df['净分数'].apply(lambda x: f"{x:+d}" if pd.notna(x) else "N/A")
            except:
                pass
        
        # 格式化预测评分
        if '预测评分' in display_df.columns:
            try:
                if display_df['预测评分'].dtype == 'object':
                    display_df['预测评分'] = display_df['预测评分'].astype(str).str.replace('%', '').str.strip()
                display_df['预测评分'] = pd.to_numeric(display_df['预测评分'], errors='coerce')
                display_df['预测评分'] = display_df['预测评分'].apply(lambda x: f"{x:.1f}" if pd.notna(x) and x > 0 else "N/A")
            except:
                pass
        
        # 格式化预测止损
        if '预测止损' in display_df.columns:
            try:
                if display_df['预测止损'].dtype == 'object':
                    display_df['预测止损'] = pd.to_numeric(display_df['预测止损'], errors='coerce')
                display_df['预测止损'] = display_df['预测止损'].apply(lambda x: f"{x:.2f}" if pd.notna(x) and x > 0 else "N/A")
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
    st.markdown('<div class="main-header"></div>', unsafe_allow_html=True)
    
    # 侧边栏配置
    with st.sidebar:
        st.markdown("⚙️ **配置**")
        
        # 数据周期选择
        period = st.selectbox(
            "数据周期",
            options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=3,
            help="选择要分析的时间周期"
        )
        
        # 查询日期选择（历史日期查询）
        st.markdown("---")
        use_historical_date = st.checkbox(
            "📅 使用历史日期查询",
            value=False,
            help="勾选后可以查询历史日期的数据，用于回测和历史分析"
        )
        
        end_date = None
        if use_historical_date:
            # 默认选择30天前的日期（避免选择未来日期）
            default_date = date.today() - timedelta(days=30)
            max_date = date.today()  # 不能选择今天之后的日期
            
            end_date = st.date_input(
                "查询日期",
                value=default_date,
                max_value=max_date,
                help="选择要查询的历史日期（不能选择未来日期）"
            )
            
            if end_date > date.today():
                st.warning("⚠️ 不能选择未来日期，已自动调整为今天")
                end_date = date.today()
            
            if end_date == date.today():
                st.info("ℹ️ 选择的日期是今天，将使用实时数据")
                end_date = None  # 今天的话，不使用end_date，使用实时数据
            else:
                st.info(f"📅 将查询 {end_date} 的历史数据")
        
        st.markdown("---")
        
        # 扫描数量选择
        scan_option = st.radio(
            "扫描范围",
            ["全部A股", "指定数量"],
            help="选择扫描全部A股或指定数量"
        )
        
        if scan_option == "全部A股":
            max_stocks = 0  # 0表示不限制，扫描全部
            st.info("💡 将扫描全部A股，可能需要较长时间")
        else:
            max_stocks = st.slider(
                "扫描数量",
                min_value=10,
                max_value=5000,
                value=100,
                step=10,
                help="限制扫描的股票数量（最大5000只）"
            )
        
        st.markdown("---")
        st.markdown("📊 **使用说明**")
        st.markdown("""
        1. 选择数据周期
        2. （可选）勾选"使用历史日期查询"并选择日期
        3. 选择扫描范围（全部A股或指定数量）
        4. 点击"开始扫描"按钮
        5. 查看扫描结果和买入信号
        
        **功能说明：**
        - 基于技术指标评分系统
        - 支持历史日期查询（用于回测）
        - 自动过滤ST股票和无效代码
        - 实时显示扫描进度和结果
        - 支持暂停、继续、重新开始
        
        **历史日期查询：**
        - 勾选"使用历史日期查询"可以分析过去任意日期的数据
        - 用于回测策略和验证模型准确性
        - 选择今天将使用实时数据
        
        **注意：** 本系统仅供参考，不构成投资建议
        """)
    
    # 主内容区 - 直接调用全盘扫描
    scan_all_stocks(period, max_stocks, end_date=end_date)

if __name__ == "__main__":
    main()
