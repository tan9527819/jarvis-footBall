# Football Orchestrator - 足球总控 Skill

## 概述
Football Orchestrator 是足球分析系统的总控 Skill，负责协调所有子 Skill 的调用流程、数据流转、风险控制和输出可追溯性。

## 调用流程

```
football-data
    ↓
odds-analysis
    ↓
historical-matching
    ↓
football-ai
    ↓
match-review
```

## 流程详解

### 1. football-data（足球数据收集）
- 收集赛事基本信息（主客队、赛事级别、日期、时间）
- 获取球队基础数据（历史战绩、主客场表现、伤病情况）
- 收集天气、场地等外部条件
- **输出**：标准化的数据集 (`data_payload`)

### 2. odds-analysis（赔率分析）
- 分析初盘赔率（欧洲盘、亚洲盘）
- 追踪赔率变化趋势
- 识别资金流向异常
- **输出**：赔率数据包 (`odds_payload`)

### 3. historical-matching（历史匹配）
- 检索类似赛事历史记录
- 分析历史战绩对比
- 识别球队之间的战术特性
- **输出**：历史参考数据包 (`history_payload`)

### 4. football-ai（AI 预测引擎）
- 综合前三步数据进行模型预测
- 生成多个预测维度（胜平负、进球数、让球等）
- 计算预测置信度
- **输出**：预测结果包 (`prediction_payload`)

### 5. match-review（比赛评审）
- 风险门槛检查
- 证据充分度评估
- 最终判断输出
- **输出**：最终结论 (`review_payload`)

## 统一数据结构

### 输入格式 (match_input)
```
{
  "match_id": "string",           // 赛事唯一标识
  "league": "string",             // 赛事联赛
  "home_team": "string",          // 主队
  "away_team": "string",          // 客队
  "match_date": "ISO8601",        // 比赛日期时间
  "analysis_time": "ISO8601"      // 分析时间
}
```

### Evidence Ledger（证据账本）
```
{
  "match_id": "string",
  "evidence_entries": [
    {
      "entry_id": "string",
      "source": "string",                  // 数据来源（football-data/odds-analysis/historical-matching/football-ai）
      "evidence_type": "string",           // 证据类型（data/odds/history/prediction）
      "timestamp": "ISO8601",
      "content": "object",                 // 具体证据内容
      "confidence": "number (0-1)",       // 置信度
      "supporting_claim": "string"        // 支撑的论点
    }
  ]
}
```

### 输出格式 (prediction_output)
```
{
  "match_id": "string",
  "prediction": {
    "recommendation": "string",           // 推荐（支持/反对/暂不推荐）
    "primary_outcome": "string",          // 主要预测（胜/平/负）
    "confidence_level": "string",         // 置信度（高/中/低）
    "key_factors": ["string"],            // 关键因素列表
  },
  "evidence_summary": "object",           // Evidence Ledger 摘要
  "risk_assessment": "object",            // 风险评估结果
  "trace_id": "string",                   // 可追溯性 ID
  "analysis_timestamp": "ISO8601"
}
```

## Risk Gate（风险控制门）

### 风险门槛 1: 数据充分度
```
if total_evidence_count < minimum_threshold:
  output: "暂不推荐 / 证据不足"
  stop_processing: true
```

### 风险门槛 2: 置信度要求
```
if average_confidence < 0.65:
  output: "暂不推荐 / 证据不足"
  stop_processing: true
```

### 风险门槛 3: 多维度一致性
```
if prediction_inconsistency_rate > 0.4:  // 预测维度间差异过大
  output: "暂不推荐 / 证据不足"
  reduce_confidence: true
```

### 风险门槛 4: 异常赔率检测
```
if odds_movement_suspicious:
  flag: "潜在操控风险"
  reduce_confidence: true
```

## 核心规则

### 规则 1: 不为多串改变单场判断
```
/**
 * 单场判断独立进行
 * 不因为需要组成"3串1"、"5串1"、"8串1"而改变单场的评估
 * 每场比赛的推荐基于独立的数据分析
 */
```

### 规则 2: 平局独立评估
```
/**
 * 平局不能作为其他判断的附属结论
 * 平局必须有独立的证据支撑：
 * - 球队风格特点（防线稳健）
 * - 历史对阵平局倾向
 * - 赔率市场平局价值认可
 * - AI 模型明确的平局预测
 */
```

### 规则 3: 冷门判断独立证据
```
/**
 * 冷门（客队胜或低倍数判断）需要独立证据支撑
 * 单纯因为"赔率便宜"不足以推荐冷门
 * 必须满足：
 * - 至少 2 个独立维度的数据支持
 * - 历史战绩或交手记录支持
 * - 球队状态或伤病对比有利
 */
```

### 规则 4: 赛前预测 vs 赛后信息
```
/**
 * 严格隔离时间线
 * 赛前分析：只使用 analysis_time 之前的信息
 * 禁止使用：
 * - 赛后球队阵容调整信息
 * - 赛后伤病更新
 * - 赛后情报
 * - 赛后赔率变化
 * 
 * 每个 Evidence Entry 必须带时间戳
 * 时间戳必须 <= analysis_time
 */
```

## 输出可追溯性

### 可追溯性要求
```
{
  "trace_id": "UUID",                     // 唯一追踪 ID
  "full_evidence_chain": [                // 完整证据链
    {
      "step": "number",
      "skill": "string",
      "evidence_id": "string",
      "timestamp": "ISO8601",
      "summary": "string"
    }
  ],
  "decision_logic": "string",             // 决策逻辑说明
  "alternative_scenarios": [              // 备选场景
    {
      "scenario": "string",
      "probability": "number",
      "supporting_evidence": "string"
    }
  ],
  "limitations": ["string"]               // 已知限制
}
```

### 记录要求
- 每个推荐都必须关联唯一的 `trace_id`
- 用户可通过 `trace_id` 追溯完整的分析过程
- 记录中间过程的所有关键决策点
- 记录被排除的证据和原因

## "暂不推荐 / 证据不足" 的触发条件

| 条件 | 说明 |
|------|------|
| 数据缺失 | 基础赛事信息不完整 |
| 置信度低 | 各 Skill 平均置信度 < 65% |
| 证据矛盾 | 多个数据源的结论相互矛盾 |
| 异常检测 | 赔率操控、数据异常等风险标志 |
| 无独立证据 | 冷门/平局判断缺乏独立支撑 |
| 时间污染 | 检测到赛后信息混入赛前分析 |

## 实现检查清单

- [ ] 所有 Skill 调用按顺序执行
- [ ] Evidence Ledger 完整记录每个数据来源
- [ ] Risk Gate 在输出前进行完整检查
- [ ] 输出中包含完整的 trace_id 和证据链
- [ ] 单场判断独立，不受多串形式影响
- [ ] 平局/冷门有独立证据支撑
- [ ] 时间戳检查无赛后污染
- [ ] 可追溯性完整

## 版本信息
- 创建日期：2026-10-02
- 状态：活跃
- 维护者：足球分析系统团队
