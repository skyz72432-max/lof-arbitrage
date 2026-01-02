# 实时溢价率警报系统设计

## 🎯 系统目标

基于交易需求，设计一套实时溢价率监控系统，用于：
1. **盘中实时监测** LOF溢价率异常
2. **智能预警** 当溢价率偏离历史均值时发出交易信号
3. **多维度分析** 结合市场情绪、成交量等指标
4. **分层提醒** 不同级别的交易机会

## 📊 需求拆解

### 1. 核心功能需求

#### 1.1 实时数据获取
- **当前限制**: 无法获取盘中实时数据（需会员权限）
- **解决方案**: 
  - 使用定时轮询（每15-30分钟）
  - 监控集思录API变化
  - 考虑第三方数据源（如雪球、同花顺）

#### 1.2 溢价率计算
- **当前**: 基于收盘价计算
- **目标**: 盘中实时计算
- **公式**: `溢价率 = (市场价格 - 基金净值) / 基金净值 * 100%`

#### 1.3 历史基准
- **7日平均**: 短期交易信号
- **14日平均**: 中期趋势判断
- **21日平均**: 长期均值回归

### 2. 交易决策逻辑

#### 2.1 信号分级
| 信号级别 | 触发条件 | 操作建议 | 置信度 |
|---------|----------|----------|---------|
| **强烈卖出** | 溢价率 > 21日均值 + 2σ | 立即卖出 | 90%+ |
| **卖出** | 溢价率 > 21日均值 + 1.5σ | 分批卖出 | 70-90% |
| **观望** | 溢价率在 ±1σ 内 | 持有观察 | 50-70% |
| **买入** | 折价率 < -21日均值 - 1.5σ | 分批买入 | 70-90% |
| **强烈买入** | 折价率 < -21日均值 - 2σ | 立即买入 | 90%+ |

#### 2.2 风险控制
- **止损设置**: 基于目标价格的2%止损
- **仓位管理**: 单只LOF不超过总仓位10%
- **时间限制**: 信号有效期24小时

### 3. 系统架构设计

#### 3.1 数据流架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据源        │────│   数据处理器    │────│   信号生成器    │
│   (集思录API)   │    │   (清洗计算)    │    │   (策略引擎)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   警报推送      │◄───│   决策引擎      │◄───│   历史基准      │
│   (微信/邮件)   │    │   (规则匹配)    │    │   (统计分析)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### 3.2 技术实现分层

##### 数据层 (Data Layer)
```python
class RealTimeDataFetcher:
    def __init__(self):
        self.api_endpoints = [
            "https://www.jisilu.cn/data/lof/hist_list/{code}",  # 历史数据
            "https://www.jisilu.cn/data/lof/detail/{code}"     # 实时数据
        ]
    
    async def fetch_realtime_data(self, code: str) -> dict:
        """获取实时溢价数据"""
        # 实现实时数据获取逻辑
        pass
    
    async def fetch_nav_data(self, code: str) -> dict:
        """获取实时净值数据"""
        # 实现净值数据获取逻辑
        pass
```

##### 计算层 (Calculation Layer)
```python
class PremiumCalculator:
    def __init__(self):
        self.historical_data = HistoricalData()
    
    def calculate_realtime_premium(self, market_price: float, nav: float) -> float:
        """计算实时溢价率"""
        return (market_price - nav) / nav * 100
    
    def get_baseline_stats(self, code: str, days: int) -> dict:
        """获取历史基准"""
        return {
            'mean': self.historical_data.get_mean(code, days),
            'std': self.historical_data.get_std(code, days),
            'percentiles': self.historical_data.get_percentiles(code, days)
        }
```

##### 决策层 (Decision Layer)
```python
class TradingStrategy:
    def __init__(self):
        self.thresholds = {
            'strong_sell': 2.0,    # 2σ
            'sell': 1.5,          # 1.5σ
            'buy': -1.5,          # -1.5σ
            'strong_buy': -2.0    # -2σ
        }
    
    def generate_signal(self, code: str, current_premium: float) -> dict:
        """生成交易信号"""
        baseline = self.get_baseline_stats(code, 21)
        z_score = (current_premium - baseline['mean']) / baseline['std']
        
        return self._evaluate_signal(z_score, current_premium, baseline)
```

##### 通知层 (Notification Layer)
```python
class AlertManager:
    def __init__(self):
        self.notifiers = [
            WeChatNotifier(),
            EmailNotifier(),
            SMSNotifier()
        ]
    
    async def send_alert(self, signal: dict, priority: str):
        """发送警报"""
        for notifier in self.notifiers:
            await notifier.send(signal, priority)
```

### 4. 会员权限问题解决方案

#### 4.1 当前可行方案
1. **定时轮询** (每30分钟)
   - 使用现有API获取最新数据
   - 计算近似盘中溢价率
   - 适合低频交易

2. **替代数据源**
   - 雪球LOF板块
   - 天天基金网
   - 券商APP数据

3. **会员权限升级路径**
   - 免费版：日终数据 + 模拟盘
   - 基础版：盘中30分钟更新
   - 专业版：实时数据 + API

#### 4.2 成本控制策略
| 方案 | 成本 | 更新频率 | 适用场景 |
|------|------|----------|----------|
| **免费方案** | ¥0/月 | 日终 | 长期配置 |
| **基础方案** | ¥50/月 | 30分钟 | 波段交易 |
| **专业方案** | ¥200/月 | 实时 | 日内交易 |

### 5. 实施路线图

#### 阶段1: 基础框架 (已完成)
- ✅ 历史数据分析系统
- ✅ 7/14/21日计算
- ✅ 交易信号生成

#### 阶段2: 实时模拟 (当前)
- 🔄 定时轮询系统
- 🔄 基础警报机制
- 🔄 模拟盘验证

#### 阶段3: 实时升级 (未来)
- ⏳ 会员权限申请
- ⏳ 实时数据源接入
- ⏳ 高级策略优化

### 6. 当前可用工具

#### 6.1 CLI工具
```bash
# 查看交易信号
python simple_trading_cli.py

# 查看特定LOF分析
python trading_framework.py
```

#### 6.2 数据输出格式
```json
{
  "LOF161126": {
    "current_premium": 1.29,
    "7d_avg": 0.85,
    "14d_avg": 0.92,
    "21d_avg": 1.01,
    "signal": "SELL",
    "confidence": 0.75,
    "reason": "溢价率高于21日均值+1.5σ"
  }
}
```

### 7. 下一步行动计划

#### 7.1 短期 (1-2周)
1. **完善CLI工具**
   - 添加更多筛选条件
   - 支持批量分析
   - 输出格式化报告

2. **模拟盘验证**
   - 基于历史数据回测
   - 记录信号准确率
   - 优化阈值参数

#### 7.2 中期 (1个月)
1. **定时轮询系统**
   - 每30分钟更新数据
   - 基础邮件/微信通知
   - 信号有效期管理

2. **会员权限评估**
   - 测试不同数据源
   - 评估成本效益
   - 制定升级计划

#### 7.3 长期 (2-3个月)
1. **实时系统上线**
   - 会员权限申请
   - 实时数据接入
   - 高级策略部署

### 8. 风险控制建议

#### 8.1 使用前验证
- **回测验证**: 使用历史数据验证信号准确率
- **模拟盘**: 先用模拟资金测试3个月
- **小仓位**: 初期使用小仓位实盘验证

#### 8.2 信号过滤
- **成交量过滤**: 剔除低成交量LOF
- **规模过滤**: 剔除规模过小基金
- **流动性检查**: 确保有足够的买卖盘

### 9. 快速开始指南

#### 9.1 立即使用
```bash
# 1. 查看所有LOF交易信号
python simple_trading_cli.py

# 2. 获取详细分析
python trading_framework.py

# 3. 查看JSON格式输出
cat trading_analysis.json
```

#### 9.2 每日监控
```bash
# 添加到crontab (每30分钟)
*/30 * * * * cd /path/to/get_jisilu && python simple_trading_cli.py >> trading_log.txt
```

### 10. 联系方式
- **技术支持**: 基于当前开源框架
- **升级咨询**: 会员权限申请指导
- **策略优化**: 根据实际交易需求调整

---

**总结**: 当前系统已具备基础的交易分析能力，可通过定时轮询实现近似实时功能。建议先使用免费方案验证策略有效性，再考虑会员升级。