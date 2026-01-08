"""
生成AI操作建议Prompt脚本
从当天的趋势启动信号扫描结果文件中提取股票信息，生成用于询问AI操作建议的prompt
"""
import os
import re
from datetime import datetime
from typing import List, Dict


def parse_result_file(file_path: str) -> List[Dict]:
    """
    解析扫描结果文件，提取股票信息
    
    Args:
        file_path: 结果文件路径
        
    Returns:
        List[Dict]: 股票信息列表
    """
    stocks = []
    
    if not os.path.exists(file_path):
        print(f"[错误] 文件不存在: {file_path}")
        return stocks
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则表达式提取每个股票的信息块
        pattern = r'={80}\n时间: (.*?)\n股票代码: (.*?)\n股票名称: (.*?)\n当前价格: (.*?)\n涨跌幅: (.*?)\n信号强度: (.*?)\n止损位: (.*?)\n启动理由: (.*?)\n={80}'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            stock_info = {
                '时间': match[0].strip(),
                '股票代码': match[1].strip(),
                '股票名称': match[2].strip(),
                '当前价格': match[3].strip(),
                '涨跌幅': match[4].strip(),
                '信号强度': match[5].strip(),
                '止损位': match[6].strip(),
                '启动理由': match[7].strip()
            }
            stocks.append(stock_info)
        
        print(f"[成功] 成功解析 {len(stocks)} 只股票")
        return stocks
        
    except Exception as e:
        print(f"[错误] 解析文件失败: {e}")
        return stocks


def calculate_recommendation_strength(stock: Dict) -> float:
    """
    计算明日操作推荐强度（0-100）
    综合考虑：涨跌幅、信号强度、放量倍数、RSI、MACD等因素
    
    Args:
        stock: 股票信息字典
        
    Returns:
        float: 推荐强度分数
    """
    strength = 0.0
    
    # 1. 信号强度（权重40%）
    signal_strength = float(stock['信号强度'].replace('%', ''))
    strength += signal_strength * 0.4
    
    # 2. 涨跌幅（权重30%，但涨幅过大可能降低推荐强度，避免追高）
    change_pct = float(stock['涨跌幅'].replace('%', ''))
    if change_pct <= 5:
        # 涨幅适中，加分
        change_score = change_pct * 2
    elif change_pct <= 10:
        # 涨幅较大，适度加分
        change_score = 10 + (change_pct - 5) * 1
    else:
        # 涨幅过大，可能追高风险，降低分数
        change_score = 15 - (change_pct - 10) * 0.5
    strength += min(change_score, 30) * 0.3
    
    # 3. 从启动理由中提取放量倍数（权重15%）
    reason = stock['启动理由']
    volume_match = re.search(r'放量([\d.]+)倍', reason)
    if volume_match:
        volume_ratio = float(volume_match.group(1))
        # 放量1.5-3倍为最佳，超过3倍可能过热
        if 1.5 <= volume_ratio <= 3:
            volume_score = 20
        elif volume_ratio > 3:
            volume_score = 20 - (volume_ratio - 3) * 2
        else:
            volume_score = volume_ratio * 10
        strength += min(volume_score, 20) * 0.15
    
    # 4. RSI指标（权重10%）
    rsi_match = re.search(r'RSI\(([\d.]+)\)', reason)
    if rsi_match:
        rsi = float(rsi_match.group(1))
        # RSI在60-70为最佳强势区
        if 60 <= rsi <= 70:
            rsi_score = 20
        elif 50 <= rsi < 60:
            rsi_score = 15
        elif 70 < rsi <= 75:
            rsi_score = 15
        else:
            rsi_score = 10
        strength += rsi_score * 0.1
    
    # 5. MACD金叉（权重5%）
    if 'MACD零轴上方金叉' in reason:
        strength += 20 * 0.05
    
    return min(strength, 100)


def generate_ai_prompt(stocks: List[Dict], date: str) -> str:
    """
    生成AI操作建议的prompt
    
    Args:
        stocks: 股票信息列表
        date: 日期字符串（YYYYMMDD）
        
    Returns:
        str: 生成的prompt文本
    """
    if not stocks:
        return "未找到股票数据"
    
    # 计算每只股票的推荐强度并排序（从高到低）
    stocks_with_strength = []
    for stock in stocks:
        recommendation_strength = calculate_recommendation_strength(stock)
        stock['推荐强度'] = recommendation_strength
        stocks_with_strength.append(stock)
    
    # 按推荐强度排序（从高到低）
    sorted_stocks = sorted(stocks_with_strength, key=lambda x: x['推荐强度'], reverse=True)
    
    # 生成prompt
    prompt = f"""# A股趋势启动信号分析 - {date}

## 背景信息

我使用量化算法扫描了A股市场，发现了 {len(stocks)} 只符合"趋势启动信号"条件的股票。
这些股票都满足以下技术条件：
- 价格位于MA10之上，MA5>MA10，MA10斜率向上（趋势向上）
- 放量上涨（成交量放大）
- 实体阳线，创近10日新高（K线形态良好）
- RSI处于强势区（动量指标良好）
- 部分股票MACD零轴上方金叉（动能确认）

所有股票的信号强度均为85%，说明技术面条件较为一致。

**重要说明**：以下股票已按"明日操作推荐强度"排序（从高到低），推荐强度综合考虑了信号强度、涨跌幅、放量倍数、RSI、MACD等因素。涨幅过大的股票可能因追高风险而降低推荐强度。

## 股票列表（按明日操作推荐强度排序）

"""
    
    # 添加每只股票的详细信息（按推荐强度排序）
    for idx, stock in enumerate(sorted_stocks, 1):
        prompt += f"""
### {idx}. {stock['股票名称']} ({stock['股票代码']}) - 推荐强度: {stock['推荐强度']:.1f}分

- **当前价格**: {stock['当前价格']} 元
- **涨跌幅**: {stock['涨跌幅']}
- **信号强度**: {stock['信号强度']}
- **明日操作推荐强度**: {stock['推荐强度']:.1f}分（满分100分）
- **建议止损位**: {stock['止损位']} 元
- **启动理由**: {stock['启动理由']}
- **检测时间**: {stock['时间']}

"""
    
    # 添加分析请求
    prompt += f"""
## 分析请求

请作为专业的股票投资顾问，对以上 {len(stocks)} 只股票进行综合分析，并提供操作建议。

### 请从以下维度进行分析：

1. **市场环境评估**
   - 当前市场整体趋势如何？
   - 这些股票集中在哪些板块？板块轮动情况如何？
   - 市场情绪和资金流向如何？

2. **个股分析**（请对所有股票进行分析，按推荐强度从高到低排序）
   - 每只股票的基本面情况（行业、主营业务、财务状况）
   - 技术面分析（结合提供的技术指标）
   - 风险提示（包括但不限于：高涨幅风险、止损位设置是否合理、是否存在追高风险）
   - 明日操作建议（买入/持有/观望，以及具体操作策略）

3. **操作建议**（按推荐强度排序）
   - 所有股票的明日操作建议（买入/持有/观望），按推荐强度从高到低排列
   - 建议的买入时机和仓位配置（推荐强度高的股票可以适当提高仓位）
   - 止损策略和风险控制建议
   - 是否需要分批建仓？建议的建仓节奏
   - 推荐强度高的股票优先考虑，但也要注意风险控制

4. **风险提示**
   - 整体市场风险
   - 个股风险（特别关注高涨幅股票的回调风险）
   - 止损策略的重要性

### 注意事项：

- 所有股票的信号强度均为85%，技术面条件相似，需要结合基本面进行筛选
- 部分股票涨幅较大（如20%），可能存在追高风险
- 建议止损位已提供，请评估是否合理
- 请综合考虑市场环境、板块轮动、个股基本面等因素
- 投资有风险，建议仅供参考

### 输出格式：

请按照以下格式输出分析结果：

```
## 市场环境分析
[你的分析]

## 所有股票分析（按推荐强度排序）

请对所有 {len(stocks)} 只股票进行分析，按推荐强度从高到低排列：

1. [股票名称] ([股票代码]) - 推荐强度：[分数]分
   - 基本面分析：[分析]
   - 技术面分析：[分析]
   - 明日操作建议：[买入/持有/观望，具体策略]
   - 风险提示：[风险]
   - 仓位建议：[建议仓位比例]

2. [股票名称] ([股票代码]) - 推荐强度：[分数]分
   ...

（请继续列出所有股票，按推荐强度从高到低排序）

## 操作建议总结
[整体操作建议]

## 风险提示
[风险提示]
```

请开始分析。
"""
    
    return prompt


def main():
    """主函数"""
    # 获取今天的日期
    today = datetime.now().strftime('%Y%m%d')
    
    # 结果文件路径
    result_file = os.path.join("scan_results", f"trend_start_signal_realtime_{today}.txt")
    
    # 如果文件不存在，尝试使用用户指定的日期
    if not os.path.exists(result_file):
        print(f"[警告] 今天的文件不存在: {result_file}")
        print("[提示] 可以手动指定日期，格式：YYYYMMDD")
        date_input = input("请输入日期（直接回车使用今天）: ").strip()
        if date_input:
            today = date_input
            result_file = os.path.join("scan_results", f"trend_start_signal_realtime_{today}.txt")
        else:
            print("[错误] 未指定日期，退出")
            return
    
    # 解析结果文件
    print(f"[读取] 正在读取文件: {result_file}")
    stocks = parse_result_file(result_file)
    
    if not stocks:
        print("[错误] 未找到股票数据，请检查文件格式")
        return
    
    # 生成prompt
    print("[生成] 正在生成AI操作建议prompt...")
    prompt = generate_ai_prompt(stocks, today)
    
    # 保存prompt到文件
    prompt_file = os.path.join("scan_results", f"ai_prompt_{today}.txt")
    try:
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"[成功] Prompt已保存到: {prompt_file}")
        print(f"[统计] 共包含 {len(stocks)} 只股票")
        
        # 显示统计信息
        print("\n[统计] 股票统计信息：")
        print(f"   - 总数量: {len(stocks)} 只")
        
        # 统计涨跌幅分布
        changes = [float(s['涨跌幅'].replace('%', '')) for s in stocks]
        print(f"   - 最高涨幅: {max(changes):.2f}%")
        print(f"   - 最低涨幅: {min(changes):.2f}%")
        print(f"   - 平均涨幅: {sum(changes)/len(changes):.2f}%")
        
        # 统计涨跌幅超过10%的股票
        high_gain = [s for s in stocks if float(s['涨跌幅'].replace('%', '')) >= 10]
        print(f"   - 涨幅≥10%: {len(high_gain)} 只")
        
        # 显示推荐强度前10只股票
        print("\n[推荐强度前10] 明日操作推荐强度前10只股票：")
        stocks_with_strength = []
        for stock in stocks:
            recommendation_strength = calculate_recommendation_strength(stock)
            stocks_with_strength.append((stock, recommendation_strength))
        sorted_by_strength = sorted(stocks_with_strength, key=lambda x: x[1], reverse=True)
        for idx, (stock, strength) in enumerate(sorted_by_strength[:10], 1):
            print(f"   {idx}. {stock['股票名称']} ({stock['股票代码']}) - 推荐强度: {strength:.1f}分, 涨跌幅: {stock['涨跌幅']}")
        
    except Exception as e:
        print(f"[错误] 保存prompt文件失败: {e}")


if __name__ == "__main__":
    main()
