#!/usr/bin/env python3
"""
交易决策框架
基于历史溢价率数据提供交易信号和风险管理
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

@dataclass
class TradingSignal:
    """交易信号数据类"""
    code: str
    signal: str  # BUY, SELL, HOLD
    confidence: float  # 0-1
    current_premium: float
    target_price: float
    stop_loss: float
    take_profit: float
    analysis: Dict
    timestamp: datetime

@dataclass
class MarketContext:
    """市场环境"""
    overall_market_sentiment: str  # BULL, BEAR, NEUTRAL
    volatility_level: str  # HIGH, MEDIUM, LOW
    volume_trend: str  # INCREASING, DECREASING, STABLE

class TradingFramework:
    """交易框架核心类"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.lof_data = {}
        self.trading_config = self._load_config()
        self.load_all_data()
    
    def _load_config(self) -> Dict:
        """加载交易配置"""
        return {
            "thresholds": {
                "extreme_premium": 2.0,      # 极端溢价阈值
                "extreme_discount": -2.0,   # 极端折价阈值
                "confidence_threshold": 0.6,
                "volume_threshold": 10000   # 成交量阈值
            },
            "risk_management": {
                "max_position_size": 0.1,   # 最大仓位10%
                "stop_loss_pct": 0.02,      # 2%止损
                "take_profit_pct": 0.05     # 5%止盈
            }
        }
    
    def load_all_data(self):
        """加载所有LOF数据"""
        csv_files = [f for f in os.listdir(self.data_dir) 
                    if f.startswith('lof_') and f.endswith('.csv')]
        
        for file in csv_files:
            code = file.replace('lof_', '').replace('.csv', '')
            file_path = os.path.join(self.data_dir, file)
            try:
                df = pd.read_csv(file_path)
                df['price_dt'] = pd.to_datetime(df['price_dt'])
                df['discount_rt'] = pd.to_numeric(df['discount_rt'], errors='coerce')
                df['price'] = pd.to_numeric(df['price'], errors='coerce')
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                self.lof_data[code] = df.sort_values('price_dt')
            except Exception as e:
                print(f"加载 {code} 数据失败: {e}")
    
    def calculate_market_context(self, code: str) -> MarketContext:
        """计算市场环境"""
        if code not in self.lof_data:
            return MarketContext("NEUTRAL", "MEDIUM", "STABLE")
        
        df = self.lof_data[code]
        recent_7d = df.tail(7)
        
        # 市场趋势
        premium_trend = recent_7d['discount_rt'].iloc[-1] - recent_7d['discount_rt'].iloc[0]
        if premium_trend > 0.5:
            sentiment = "BULL"
        elif premium_trend < -0.5:
            sentiment = "BEAR"
        else:
            sentiment = "NEUTRAL"
        
        # 波动率
        volatility = recent_7d['discount_rt'].std()
        if volatility > 1.5:
            vol_level = "HIGH"
        elif volatility < 0.5:
            vol_level = "LOW"
        else:
            vol_level = "MEDIUM"
        
        # 成交量趋势
        volume_trend = recent_7d['amount'].iloc[-1] / recent_7d['amount'].iloc[0] - 1
        if volume_trend > 0.2:
            volume_trend = "INCREASING"
        elif volume_trend < -0.2:
            volume_trend = "DECREASING"
        else:
            volume_trend = "STABLE"
        
        return MarketContext(sentiment, vol_level, volume_trend)
    
    def analyze_premium_distribution(self, code: str, days: int) -> Dict:
        """分析溢价率分布"""
        if code not in self.lof_data:
            return {}
        
        df = self.lof_data[code]
        cutoff_date = datetime.now() - timedelta(days=days)
        data = df[df['price_dt'] >= cutoff_date].copy()
        
        if data.empty:
            return {}
        
        premiums = data['discount_rt'].dropna()
        
        return {
            'percentiles': {
                '5%': float(np.percentile(premiums, 5)),
                '25%': float(np.percentile(premiums, 25)),
                '50%': float(np.percentile(premiums, 50)),
                '75%': float(np.percentile(premiums, 75)),
                '95%': float(np.percentile(premiums, 95))
            },
            'quartiles': {
                'Q1': float(np.percentile(premiums, 25)),
                'Q2': float(np.percentile(premiums, 50)),
                'Q3': float(np.percentile(premiums, 75))
            },
            'outliers': {
                'lower_fence': float(np.percentile(premiums, 25) - 1.5 * (np.percentile(premiums, 75) - np.percentile(premiums, 25))),
                'upper_fence': float(np.percentile(premiums, 75) + 1.5 * (np.percentile(premiums, 75) - np.percentile(premiums, 25)))
            }
        }
    
    def generate_trading_signal(self, code: str) -> Optional[TradingSignal]:
        """生成交易信号"""
        if code not in self.lof_data:
            return None
        
        df = self.lof_data[code]
        
        # 获取最新数据
        latest = df.iloc[-1]
        current_premium = latest['discount_rt']
        current_price = latest['price']
        
        # 计算各期统计
        stats_7d = self.calculate_premium_stats(code, 7)
        stats_14d = self.calculate_premium_stats(code, 14)
        stats_21d = self.calculate_premium_stats(code, 21)
        
        if not all([stats_7d, stats_14d, stats_21d]):
            return None
        
        # 市场环境
        market_context = self.calculate_market_context(code)
        
        # 溢价率分布分析
        distribution = self.analyze_premium_distribution(code, 21)
        
        # 信号生成逻辑
        signal, confidence, reasons = self._generate_signal_logic(
            current_premium, stats_7d, stats_14d, stats_21d, distribution, market_context
        )
        
        if signal == "HOLD":
            return None
        
        # 计算目标价格
        target_price, stop_loss, take_profit = self._calculate_targets(
            current_price, current_premium, signal, confidence
        )
        
        return TradingSignal(
            code=code,
            signal=signal,
            confidence=confidence,
            current_premium=current_premium,
            target_price=target_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            analysis={
                'stats_7d': stats_7d,
                'stats_14d': stats_14d,
                'stats_21d': stats_21d,
                'distribution': distribution,
                'market_context': market_context.__dict__,
                'reasons': reasons
            },
            timestamp=datetime.now()
        )
    
    def _generate_signal_logic(self, current: float, stats_7d: Dict, stats_14d: Dict, 
                             stats_21d: Dict, distribution: Dict, market: MarketContext) -> Tuple[str, float, List[str]]:
        """信号生成核心逻辑"""
        reasons = []
        
        # 基础信号
        signal = "HOLD"
        confidence = 0.0
        
        # 相对于7日均值
        z_score_7d = (current - stats_7d['mean']) / stats_7d['std'] if stats_7d['std'] > 0 else 0
        
        # 相对于分布
        if distribution:
            upper_fence = distribution['outliers']['upper_fence']
            lower_fence = distribution['outliers']['lower_fence']
            median = distribution['percentiles']['50%']
        else:
            upper_fence = stats_7d['mean'] + 2 * stats_7d['std']
            lower_fence = stats_7d['mean'] - 2 * stats_7d['std']
            median = stats_7d['mean']
        
        # 卖出信号
        if current > upper_fence:
            signal = "SELL"
            confidence = min(0.9, abs(current - median) / stats_7d['std'] * 0.2)
            reasons.append(f"当前溢价率{current:.2f}%高于历史95%分位数")
        
        # 买入信号
        elif current < lower_fence:
            signal = "BUY"
            confidence = min(0.9, abs(current - median) / stats_7d['std'] * 0.2)
            reasons.append(f"当前折价率{current:.2f}%低于历史5%分位数")
        
        # 增强信号
        if abs(z_score_7d) > 1.5:
            confidence *= 1.2
            reasons.append(f"Z-Score: {z_score_7d:.2f}")
        
        # 市场环境调整
        if market.overall_market_sentiment == "BULL" and signal == "BUY":
            confidence *= 1.1
        elif market.overall_market_sentiment == "BEAR" and signal == "SELL":
            confidence *= 1.1
        
        return signal, min(1.0, confidence), reasons
    
    def _calculate_targets(self, current_price: float, current_premium: float, 
                         signal: str, confidence: float) -> Tuple[float, float, float]:
        """计算目标价格"""
        config = self.trading_config['risk_management']
        
        if signal == "SELL":
            # 卖出信号：预期价格回落
            target_price = current_price * (1 - abs(current_premium) * 0.5 * confidence)
            stop_loss = current_price * (1 + config['stop_loss_pct'])
            take_profit = current_price * (1 - config['take_profit_pct'])
        else:  # BUY
            # 买入信号：预期价格回升
            target_price = current_price * (1 + abs(current_premium) * 0.5 * confidence)
            stop_loss = current_price * (1 - config['stop_loss_pct'])
            take_profit = current_price * (1 + config['take_profit_pct'])
        
        return round(target_price, 3), round(stop_loss, 3), round(take_profit, 3)
    
    def calculate_premium_stats(self, code: str, days: int) -> Dict:
        """计算溢价率统计"""
        if code not in self.lof_data:
            return {}
        
        df = self.lof_data[code]
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_data = df[df['price_dt'] >= cutoff_date].copy()
        
        if recent_data.empty:
            return {}
        
        return {
            'mean': float(recent_data['discount_rt'].mean()),
            'std': float(recent_data['discount_rt'].std()),
            'current': float(recent_data['discount_rt'].iloc[-1]) if not recent_data.empty else 0,
            'count': len(recent_data)
        }
    
    def get_all_signals(self) -> List[TradingSignal]:
        """获取所有交易信号"""
        signals = []
        for code in self.lof_data.keys():
            signal = self.generate_trading_signal(code)
            if signal and signal.confidence > self.trading_config['thresholds']['confidence_threshold']:
                signals.append(signal)
        
        # 按置信度排序
        return sorted(signals, key=lambda x: x.confidence, reverse=True)
    
    def export_signals_json(self, output_file: str = "trading_signals.json"):
        """导出交易信号为JSON"""
        signals = self.get_all_signals()
        
        export_data = {
            "generated_at": datetime.now().isoformat(),
            "signals": [
                {
                    "code": s.code,
                    "signal": s.signal,
                    "confidence": s.confidence,
                    "current_premium": s.current_premium,
                    "target_price": s.target_price,
                    "stop_loss": s.stop_loss,
                    "take_profit": s.take_profit,
                    "timestamp": s.timestamp.isoformat()
                } for s in signals
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return export_data

def main():
    """主函数"""
    framework = TradingFramework()
    
    print("🎯 LOF交易框架启动")
    print("=" * 50)
    
    # 获取所有交易信号
    signals = framework.get_all_signals()
    
    print(f"📊 发现 {len(signals)} 个交易机会")
    
    if signals:
        print("\n🚨 交易信号:")
        for signal in signals[:10]:  # 显示前10个
            print(f"\n📈 {signal.code}")
            print(f"   信号: {signal.signal}")
            print(f"   置信度: {signal.confidence}")
            print(f"   当前溢价率: {signal.current_premium:.2f}%")
            print(f"   目标价格: {signal.target_price}")
            print(f"   止损: {signal.stop_loss}")
            print(f"   止盈: {signal.take_profit}")
    
    # 导出信号
    export_data = framework.export_signals_json()
    print(f"\n✅ 交易信号已导出到 trading_signals.json")
    
    return framework

if __name__ == "__main__":
    framework = main()