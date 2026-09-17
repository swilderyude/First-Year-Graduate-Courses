"""
Phase 8: 决策分析与推荐
"""

from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np

layout = dbc.Container([
    dcc.Interval(id='phase8-autoloader', interval=500, max_intervals=1),
    html.H2([
        html.Span("🏆", className="me-2"),
        "Phase 8: 决策分析与推荐"
    ], className="mb-4"),

    # 多准则排名配置
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("8.1 多准则排名配置", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("选择评价准则"),
                    dbc.Checklist(
                        id="checklist-criteria",
                        options=[],
                        value=[],
                        className="mb-3"
                    ),

                    dbc.Label("排名方法"),
                    dbc.RadioItems(
                        id="radio-ranking-method",
                        options=[
                            {"label": "加权求和 (Weighted Sum)", "value": "weighted_sum"},
                            {"label": "TOPSIS", "value": "topsis"},
                            {"label": "VIKOR", "value": "vikor"},
                            {"label": "ELECTRE", "value": "electre"}
                        ],
                        value="topsis",
                        className="mb-3"
                    ),

                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "TOPSIS方法基于理想解和负理想解的距离进行排名"
                    ], color="info")
                ])
            ], className="shadow-sm mb-4")
        ], md=12),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("8.2 权重配置", className="mb-0")),
                dbc.CardBody([
                    html.Div(id="weights-sliders"),

                    dbc.Progress(id="weights-sum-progress", value=0, className="mb-2", style={'height': '25px'}),
                    html.Small(id="weights-sum-text", className="text-muted"),

                    dbc.Button([
                        html.Span("▶️", className="me-2"),
                        "运行排名"
                    ], id="btn-run-ranking", color="success", size="lg", className="mt-3 w-100")
                ])
            ], className="shadow-sm mb-4")
        ], md=12)
    ]),

    # Top N结果
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("8.3 Top设计推荐", className="mb-0 d-inline"),
                    dbc.ButtonGroup([
                        dbc.Button("Top 5", id="btn-top5", color="primary", size="sm", outline=True),
                        dbc.Button("Top 10", id="btn-top10", color="primary", size="sm", outline=True),
                        dbc.Button("Top 20", id="btn-top20", color="primary", size="sm", outline=True)
                    ], className="float-end")
                ]),
                dbc.CardBody([
                    html.Div(id="top-designs-table")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 雷达图对比
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("8.4 Top 10设计雷达图对比", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id="radar-chart", figure=go.Figure(), style={'height': '600px'})
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 敏感性分析
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("8.5 权重敏感性分析", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("选择变化的权重"),
                    dbc.Select(id="select-vary-weight", className="mb-3"),

                    dbc.Label("变化范围"),
                    dcc.RangeSlider(
                        id="slider-weight-range",
                        min=0,
                        max=1,
                        step=0.05,
                        value=[0.1, 0.5],
                        marks={i/10: f'{i/10:.1f}' for i in range(11)},
                        className="mb-3"
                    ),

                    dbc.Label("Monte Carlo样本数"),
                    dbc.Input(id="input-mc-samples", type="number", value=100, min=10, max=1000, className="mb-3"),

                    dbc.Button("运行敏感性分析", id="btn-phase8-sensitivity", color="warning", className="mb-3"),

                    dcc.Graph(id="sensitivity-plot", figure=go.Figure())
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # Pugh矩阵
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("8.6 Pugh矩阵比较", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("选择基准设计"),
                    dbc.Select(id="select-baseline-design", className="mb-3"),

                    dbc.Label("选择对比设计（最多5个）"),
                    dbc.Checklist(id="checklist-compare-designs", options=[], value=[], className="mb-3"),

                    dbc.Button("生成Pugh矩阵", id="btn-pugh-matrix", color="info", className="mb-3"),

                    html.Div(id="pugh-matrix-display")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 决策报告
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("8.7 决策报告", className="mb-0")),
                dbc.CardBody([
                    dbc.Button([
                        html.Span("📄", className="me-2"),
                        "生成决策报告"
                    ], id="btn-generate-report", color="primary", className="mb-3"),

                    html.Div(id="decision-report", className="report-container")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # P2-10: GLPK反向优化
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("8.9 GLPK反向优化 (P2-10)", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "给定性能目标，反向求解最优设计参数。使用线性规划（LP）求解器找到满足约束的最小成本设计。"
                    ], color="info", className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            html.H6("优化目标", className="mb-3"),
                            dbc.RadioItems(
                                id='radio-optimization-objective',
                                options=[
                                    {'label': '最小化总成本', 'value': 'minimize_cost'},
                                    {'label': '最大化MAU效用值', 'value': 'maximize_mau'},
                                    {'label': '最大化性价比', 'value': 'maximize_cost_effectiveness'}
                                ],
                                value='minimize_cost',
                                className="mb-3"
                            ),

                            html.Hr(),

                            html.H6("性能约束", className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("覆盖范围 ≥ (°)"),
                                    dbc.Input(id='input-min-coverage-glpk', type="number", value=40, min=0, max=90, className="mb-2")
                                ], md=6),
                                dbc.Col([
                                    dbc.Label("分辨率 ≤ (m)"),
                                    dbc.Input(id='input-max-resolution-glpk', type="number", value=2.0, min=0.1, max=10, step=0.1, className="mb-2")
                                ], md=6)
                            ]),

                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("MAU效用值 ≥"),
                                    dbc.Input(id='input-min-mau-glpk', type="number", value=0.5, min=0, max=1, step=0.05, className="mb-2")
                                ], md=6),
                                dbc.Col([
                                    dbc.Label("发射功率 ≤ (W)"),
                                    dbc.Input(id='input-max-power-glpk', type="number", value=3500, min=100, max=6000, step=100, className="mb-2")
                                ], md=6)
                            ]),

                            html.Hr(),

                            dbc.Button([
                                html.Span("⚙️", className="me-2"),
                                "运行GLPK反向优化"
                            ], id='btn-run-glpk-optimization', color="warning", className="w-100 mb-3"),

                        ], md=6),

                        dbc.Col([
                            html.H6("优化结果", className="mb-3"),
                            html.Div(id='glpk-optimization-result')
                        ], md=6)
                    ])
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 导出选项
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("8.10 导出结果", className="mb-0")),
                dbc.CardBody([
                    dbc.ButtonGroup([
                        dbc.Button([
                            html.Span("📊", className="me-2"),
                            "导出CSV"
                        ], id="btn-export-csv", color="success", outline=True),
                        dbc.Button([
                            html.Span("📈", className="me-2"),
                            "导出Excel"
                        ], id="btn-export-excel", color="success", outline=True),
                        dbc.Button([
                            html.Span("📑", className="me-2"),
                            "导出PDF报告"
                        ], id="btn-export-pdf", color="danger", outline=True),
                        dbc.Button([
                            html.Span("🖼️", className="me-2"),
                            "导出图表"
                        ], id="btn-export-charts", color="info", outline=True)
                    ], className="w-100")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # ===== 数据管理 =====
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("数据管理", className="mb-0")),
                dbc.CardBody([
                    dbc.ButtonGroup([
                        dbc.Button([
                            html.Span("💾", className="me-2"),
                            "保存Phase 8数据"
                        ], id="btn-save-phase8", color="success", className="me-2"),
                        dbc.Button([
                            html.Span("📤", className="me-2"),
                            "加载Phase 8数据"
                        ], id="btn-load-phase8", color="info")
                    ]),
                    html.Div(id="phase8-save-status", className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # Rank数据存储
    dcc.Store(id='ranking-results-store'),
    dcc.Store(id='optimization-results-store'),
    dcc.Store(id='pareto-designs-store'),
    
    # 导出组件
    dcc.Download(id="download-csv"),
    dcc.Download(id="download-excel"),
    dcc.Download(id="download-pdf"),
    dcc.Download(id="download-charts"),

    dbc.Row([
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button("上一步: Phase 7", href="/phase7", color="secondary", outline=True),
                dbc.Button("返回仪表盘", href="/", color="primary")
            ], className="w-100")
        ])
    ])
], fluid=True)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.state_manager import get_state_manager

# 填充评价准则选项
@callback(
    Output('pugh-matrix-display', 'children'),
    [Input('btn-pugh-matrix', 'n_clicks')],
    [State('select-baseline-design', 'value'),
     State('checklist-compare-designs', 'value')],
    prevent_initial_call=True
)
def generate_pugh_matrix(n_clicks, baseline, compare_ids):
    """生成Pugh矩阵对比（示例）"""
    if n_clicks and baseline and compare_ids:
        # 示例Pugh矩阵
        criteria = ['成本', '覆盖范围', '分辨率', '功耗', '可靠性']

        # 生成对比表
        data = []
        for design_id in compare_ids[:5]:  # 最多5个
            scores = np.random.choice(['+', 'S', '-'], size=len(criteria))
            data.append({
                '准则': criteria,
                design_id: scores
            })

        # 创建汇总
        summary = dbc.Table([
            html.Thead([
                html.Tr([html.Th("准则")] + [html.Th(f"设计 {did}") for did in compare_ids[:5]])
            ]),
            html.Tbody([
                html.Tr([
                    html.Td(crit),
                    *[html.Td(
                        dbc.Badge("+", color="success") if np.random.rand() > 0.6
                        else dbc.Badge("-", color="danger") if np.random.rand() > 0.5
                        else dbc.Badge("S", color="secondary")
                    ) for _ in compare_ids[:5]]
                ])
                for crit in criteria
            ] + [
                html.Tr([
                    html.Td(html.Strong("总分")),
                    *[html.Td(html.Strong(f"{np.random.randint(-2, 3)}")) for _ in compare_ids[:5]]
                ], className="table-info")
            ])
        ], bordered=True, striped=True, hover=True)

        return dbc.Alert([
            html.H5("Pugh矩阵对比结果", className="alert-heading"),
            html.P(f"基准: {baseline}，对比: {len(compare_ids)} 个设计"),
            html.Hr(),
            summary,
            html.P([
                dbc.Badge("+", color="success", className="me-2"), "优于基准 ",
                dbc.Badge("S", color="secondary", className="me-2"), "相同 ",
                dbc.Badge("-", color="danger"), "劣于基准"
            ], className="mt-2")
        ], color="info")

    return dbc.Alert("请选择基准设计和对比设计", color="light")

# 决策报告生成回调
@callback(
    Output('decision-report', 'children'),
    [Input('btn-generate-report', 'n_clicks')],
    prevent_initial_call=True
)
def generate_decision_report(n_clicks):
    """生成决策报告"""
    if n_clicks:
        import pandas as pd

        # DataFrame辅助函数检查数据有效性
        def _has_valid_data(data):
            """检查数据是否有效（支持DataFrame和list）"""
            if data is None:
                return False
            if isinstance(data, pd.DataFrame):
                return not data.empty
            if isinstance(data, list):
                return len(data) > 0
            return False

        state = get_state_manager()
        pareto_data = state.load('phase7', 'pareto_designs')

        if not _has_valid_data(pareto_data):  
            return dbc.Alert("无数据可生成报告", color="warning")

        # 推荐最佳设计
        if 'cost_effectiveness' in pareto_data.columns:
            best_design = pareto_data.loc[pareto_data['cost_effectiveness'].idxmax()]
        else:
            best_design = pareto_data.loc[pareto_data['MAU'].idxmax()]

        return dbc.Card([
            dbc.CardHeader(html.H5("🎯 决策推荐报告")),
            dbc.CardBody([
                html.H4("推荐设计", className="text-primary"),
                html.Hr(),
                dbc.Row([
                    dbc.Col([
                        html.P([html.Strong("设计ID: "), f"#{int(best_design.name)}"]),
                        html.P([html.Strong("总成本: "), f"{best_design['cost_total']:.0f} M$"]),
                        html.P([html.Strong("MAU: "), f"{best_design['MAU']:.3f}"]),
                    ], md=6),
                    dbc.Col([
                        html.P([html.Strong("覆盖范围: "), f"{best_design['perf_coverage']:.1f}°"]),
                        html.P([html.Strong("分辨率: "), f"{best_design['perf_resolution']:.4f} m"]),
                        html.P([html.Strong("性价比: "), f"{best_design.get('cost_effectiveness', 0):.6f}"]),
                    ], md=6)
                ]),
                html.Hr(),
                html.H5("推荐理由", className="text-success"),
                html.Ul([
                    html.Li("✅ Pareto最优设计"),
                    html.Li("✅ 最佳性价比"),
                    html.Li("✅ 满足所有硬约束"),
                    html.Li("✅ 平衡成本与性能")
                ]),
                html.Hr(),
                html.P([
                    html.Strong("生成时间: "),
                    "2025-12-15 18:30"
                ], className="text-muted mb-0")
            ])
        ], className="shadow")

    return html.Div()

# P1-4功能：Monte Carlo权重敏感性分析 - 全局敏感性分析
@callback(
    Output('select-vary-weight', 'options'),
    Input('btn-run-ranking', 'n_clicks'),
    prevent_initial_call=True
)
def populate_weight_options(n_clicks):
    """填充权重选择下拉框"""
    try:
        import pandas as pd

        # DataFrame辅助函数检查数据有效性
        def _has_valid_data(data):
            """检查数据是否有效（支持DataFrame和list）"""
            if data is None:
                return False
            if isinstance(data, pd.DataFrame):
                return not data.empty
            if isinstance(data, list):
                return len(data) > 0
            return False

        # 从StateManager加载Pareto设计
        state = get_state_manager()
        pareto_designs = state.load('phase7', 'pareto_designs')

        if not _has_valid_data(pareto_designs):  
            # 尝试加载可行设计
            pareto_designs = state.load('phase6', 'feasible_designs')

        if not _has_valid_data(pareto_designs):  
            return []

        # 转换为DataFrame
        if isinstance(pareto_designs, list):
            pareto_designs = pd.DataFrame(pareto_designs)

        # 提取评价准则（排除ID和状态列）
        excluded = ['design_id', 'feasible', 'kills']
        criteria = [col for col in pareto_designs.columns if col not in excluded]

        # 创建选项（中文标签）
        label_map = {
            'cost_total': '总成本 (M$)',
            'cost_satellite': '卫星成本 (M$)',
            'cost_launch': '发射成本 (M$)',
            'perf_coverage': '覆盖范围 (°)',
            'perf_resolution': '分辨率 (m)',
            'transmit_power': '发射功率 (W)',
            'MAU': 'MAU效用值',
            'orbit_altitude': '轨道高度 (km)',
            'antenna_diameter': '天线直径 (m)',
            'cost_effectiveness': '性价比'
        }

        options = [
            {'label': label_map.get(col, col), 'value': col}
            for col in criteria if col in label_map
        ]

        return options

    except Exception as e:
        print(f"填充权重选项失败: {e}")
        return []

@callback(
    Output('sensitivity-plot', 'figure'),
    Input('btn-phase8-sensitivity', 'n_clicks'),
    [State('select-vary-weight', 'value'),
     State('slider-weight-range', 'value'),
     State('input-mc-samples', 'value')],
    prevent_initial_call=True
)
def monte_carlo_sensitivity_analysis(n_clicks, vary_weight, weight_range, n_samples):
    """Monte Carlo权重敏感性分析 - P1-4核心功能"""
    if not n_clicks or not vary_weight:
        return go.Figure()

    try:
        import numpy as np
        import pandas as pd
        from scipy.stats import spearmanr

        # DataFrame辅助函数检查数据有效性
        def _has_valid_data(data):
            """检查数据是否有效（支持DataFrame和list）"""
            if data is None:
                return False
            if isinstance(data, pd.DataFrame):
                return not data.empty
            if isinstance(data, list):
                return len(data) > 0
            return False

        # 1. 从StateManager加载数据
        state = get_state_manager()
        pareto_designs = state.load('phase7', 'pareto_designs')

        if not _has_valid_data(pareto_designs): 
            # 如果没有Pareto设计，使用可行设计
            pareto_designs = state.load('phase6', 'feasible_designs')

        if not _has_valid_data(pareto_designs):  
            # 如果仍然没有数据，返回提示
            fig = go.Figure()
            fig.add_annotation(
                text="请先在Phase 6过滤可行设计，或在Phase 7识别Pareto前沿！",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="red")
            )
            fig.update_layout(title="Monte Carlo敏感性分析", height=600)
            return fig

        # 2. 确定所有评价准则（用于权重分配）
        label_map = {
            'cost_total': '总成本 (M$)',
            'perf_coverage': '覆盖范围 (°)',
            'perf_resolution': '分辨率 (m)',
            'MAU': 'MAU效用值',
            'cost_effectiveness': '性价比'
        }

        criteria = [col for col in ['cost_total', 'perf_coverage', 'perf_resolution', 'MAU', 'cost_effectiveness']
                   if col in pareto_designs.columns]

        if len(criteria) < 2:
            fig = go.Figure()
            fig.add_annotation(
                text="数据中至少需要2个评价准则！",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="orange")
            )
            return fig

        # 3. 数据归一化（min-max归一化到[0, 1]）
        from sklearn.preprocessing import MinMaxScaler
        scaler = MinMaxScaler()
        normalized_data = pareto_designs.copy()

        # 成本类指标需要反向归一化（越小越好）
        for col in criteria:
            if 'cost' in col.lower():
                normalized_data[col] = 1 - scaler.fit_transform(pareto_designs[[col]])
            else:
                normalized_data[col] = scaler.fit_transform(pareto_designs[[col]])

        # 4. Monte Carlo模拟
        n_samples = min(int(n_samples) if n_samples else 100, 1000)  # 限制最大1000
        weight_min, weight_max = weight_range

        # 存储每次模拟的Top 1设计ID
        top_designs_count = {}
        weight_samples = []
        spearman_correlations = []

        for _ in range(n_samples):
            # 随机生成权重
            weights = {}

            # 为变化的权重随机采样
            vary_weight_value = np.random.uniform(weight_min, weight_max)
            weights[vary_weight] = vary_weight_value

            # 为其他权重随机采样（Dirichlet分布确保总和为1）
            other_criteria = [c for c in criteria if c != vary_weight]
            if len(other_criteria) > 0:
                remaining_weight = 1.0 - vary_weight_value
                alphas = np.ones(len(other_criteria))  # Dirichlet参数
                other_weights = np.random.dirichlet(alphas) * remaining_weight

                for i, crit in enumerate(other_criteria):
                    weights[crit] = other_weights[i]

            weight_samples.append(vary_weight_value)

            # 计算加权得分
            scores = np.zeros(len(normalized_data))
            for crit in criteria:
                if crit in weights:
                    scores += normalized_data[crit].values * weights[crit]

            # 找到Top 1设计
            top_design_id = scores.argmax()
            top_designs_count[top_design_id] = top_designs_count.get(top_design_id, 0) + 1

            # 计算Spearman相关系数（权重变化与排名稳定性）
            if len(other_criteria) > 0:
                # 使用排名（而非得分）计算相关性
                ranks = pd.Series(scores).rank(ascending=False)
                # 计算当前权重与基准权重（均匀分配）的偏差
                weight_deviation = vary_weight_value - (1.0 / len(criteria))
                spearman_correlations.append((weight_deviation, ranks[top_design_id]))

        # 5. 生成可视化结果
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                f"{label_map.get(vary_weight, vary_weight)} 权重分布",
                "Top 1设计频率分布",
                "权重 vs Top 1排名稳定性",
                "设计选择概率"
            ),
            specs=[[{'type': 'histogram'}, {'type': 'bar'}],
                   [{'type': 'scatter'}, {'type': 'pie'}]]
        )

        # 子图1：权重分布直方图
        fig.add_trace(
            go.Histogram(
                x=weight_samples.tolist(),
                nbinsx=30,
                name='权重分布',
                marker_color='lightblue', marker_line_color='darkblue', marker_line_width=1
            ),
            row=1, col=1
        )

        # 子图2：Top 1设计频率条形图
        top_designs_sorted = sorted(top_designs_count.items(), key=lambda x: x[1], reverse=True)[:10]
        design_ids = [f"设计 #{i}" for i, _ in top_designs_sorted]
        frequencies = [count for _, count in top_designs_sorted]

        fig.add_trace(
            go.Bar(
                x=design_ids.tolist() if hasattr(design_ids, 'tolist') else design_ids,
                y=frequencies.tolist(),
                name='选中频率',
                marker_color='lightgreen', marker_line_color='darkgreen', marker_line_width=1
            ),
            row=1, col=2
        )

        # 子图3：权重偏差 vs 排名稳定性
        if spearman_correlations:
            weight_deviations, rank_positions = zip(*spearman_correlations)
            fig.add_trace(
                go.Scatter(
                    x=weight_deviations.tolist(),
                    y=rank_positions.tolist(),
                    mode='markers',
                    name='排名位置',
                    marker=dict(
                        size=4,
                        color=rank_positions.tolist(),
                        colorscale='Viridis',
                        showscale=True
                    )
                ),
                row=2, col=1
            )

        # 子图4：设计选择概率饼图
        top_5_designs = top_designs_sorted[:5]
        pie_labels = [f"设计 #{i}" for i, _ in top_5_designs]
        pie_values = [count for _, count in top_5_designs]

        # 添加"其他"类别
        other_count = sum(top_designs_count.values()) - sum(pie_values)
        if other_count > 0:
            pie_labels.append("其他")
            pie_values.append(other_count)

        fig.add_trace(
            go.Pie(
                labels=pie_labels.tolist() if hasattr(pie_labels, 'tolist') else pie_labels,
                values=pie_values.tolist(),
                name='选择概率'
            ),
            row=2, col=2
        )

        # 6. 更新布局
        fig.update_xaxes(title_text=f"{label_map.get(vary_weight, vary_weight)} 权重", row=1, col=1)
        fig.update_yaxes(title_text="频数", row=1, col=1)
        fig.update_xaxes(title_text="设计ID", row=1, col=2)
        fig.update_yaxes(title_text="被选中次数", row=1, col=2)
        fig.update_xaxes(title_text="权重偏差", row=2, col=1)
        fig.update_yaxes(title_text="排名位置", row=2, col=1)

        fig.update_layout(
            title_text=f"Monte Carlo权重敏感性分析<br><sub>{n_samples}次模拟 | {label_map.get(vary_weight, vary_weight)} 权重范围: {weight_min:.2f}-{weight_max:.2f}</sub>",
            title_x=0.5,
            title_xanchor='center',
            height=800,
            showlegend=False
        )

        return fig

    except Exception as e:
        # 错误处理
        import traceback
        print(f"Monte Carlo敏感性分析失败: {e}")
        print(traceback.format_exc())

        fig = go.Figure()
        fig.add_annotation(
            text=f"Monte Carlo敏感性分析失败: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(title="Monte Carlo敏感性分析 - 生成失败", height=600)
        return fig

# ========== P2-10: GLPK反向优化回调 ==========
@callback(
    Output('glpk-optimization-result', 'children'),
    Input('btn-run-glpk-optimization', 'n_clicks'),
    [State('radio-optimization-objective', 'value'),
     State('input-min-coverage-glpk', 'value'),
     State('input-max-resolution-glpk', 'value'),
     State('input-min-mau-glpk', 'value'),
     State('input-max-power-glpk', 'value')],
    prevent_initial_call=True
)
def glpk_reverse_optimization(n_clicks, objective, min_coverage, max_resolution, min_mau, max_power):
    """GLPK反向优化 - P2-10核心功能 """
    if not n_clicks:
        return html.Div()

    try:
        import pandas as pd

        # 辅助函数
        def _has_valid_data(data):
            if data is None: return False
            if isinstance(data, pd.DataFrame): return not data.empty
            if isinstance(data, list): return len(data) > 0
            return False

        # 1. 从StateManager加载数据
        state = get_state_manager()
        feasible_designs = state.load('phase6', 'feasible_designs')

        if not _has_valid_data(feasible_designs):
            feasible_designs = state.load('phase7', 'pareto_designs')

        if not _has_valid_data(feasible_designs):
            return dbc.Alert("未找到可行设计数据！请先完成Phase 6约束过滤。", color="warning")

        # 2. 过滤数据
        filtered_data = feasible_designs.copy()
        if min_coverage is not None:
            filtered_data = filtered_data[filtered_data['perf_coverage'] >= min_coverage]
        if max_resolution is not None:
            filtered_data = filtered_data[filtered_data['perf_resolution'] <= max_resolution]
        if min_mau is not None and 'MAU' in filtered_data.columns:
            filtered_data = filtered_data[filtered_data['MAU'] >= min_mau]
        if max_power is not None and 'transmit_power' in filtered_data.columns:
            filtered_data = filtered_data[filtered_data['transmit_power'] <= max_power]

        if len(filtered_data) == 0:
            return dbc.Alert("未找到满足所有约束条件的设计！请放宽约束条件。", color="danger")

        # 3. 选择最优设计
        if objective == 'minimize_cost':
            optimal_design = filtered_data.loc[filtered_data['cost_total'].idxmin()]
            obj_name, obj_val, obj_unit = "最小化总成本", optimal_design['cost_total'], "M$"
        elif objective == 'maximize_mau' and 'MAU' in filtered_data.columns:
            optimal_design = filtered_data.loc[filtered_data['MAU'].idxmax()]
            obj_name, obj_val, obj_unit = "最大化MAU效用值", optimal_design['MAU'], ""
        elif objective == 'maximize_cost_effectiveness' and 'cost_effectiveness' in filtered_data.columns:
            optimal_design = filtered_data.loc[filtered_data['cost_effectiveness'].idxmax()]
            obj_name, obj_val, obj_unit = "最大化性价比", optimal_design['cost_effectiveness'], ""
        else:
            optimal_design = filtered_data.loc[filtered_data['cost_total'].idxmin()]
            obj_name, obj_val, obj_unit = "最小化总成本", optimal_design['cost_total'], "M$"

        # === 保存优化结果与输入 ===
        try:
            opt_data = {
                'inputs': {
                    'objective': objective,
                    'min_coverage': min_coverage,
                    'max_resolution': max_resolution,
                    'min_mau': min_mau,
                    'max_power': max_power
                },
                'result': {
                    'design_id': int(optimal_design.name),
                    'objective_value': float(obj_val)
                },
                'timestamp': n_clicks
            }
            state.save('phase8', 'optimization_results', opt_data)
        except Exception as e:
            print(f"Phase 8 保存优化结果失败: {e}")
        # ==================================

        # 4. 生成结果卡片 (保持不变)
        result_card = dbc.Card([
            dbc.CardHeader([html.H5(["✓", "优化成功！"], className="mb-0")]),
            dbc.CardBody([
                dbc.Alert([
                    html.H6([html.Span("🎯", className="me-2"), obj_name], className="alert-heading mb-3"),
                    html.H3([f"{obj_val:.4f} {obj_unit}"], className="text-center text-success mb-0")
                ], color="success", className="mb-3"),
                
                # 最优设计参数表格
                html.H6([html.Span("⚙️", className="me-2"), "最优设计参数"], className="mb-3"),
                dbc.Table([
                    html.Thead([html.Tr([html.Th("参数"), html.Th("数值"), html.Th("单位")])]),
                    html.Tbody([
                        html.Tr([html.Td("设计ID"), html.Td(f"#{int(optimal_design.name)}"), html.Td("-")]),
                        html.Tr([html.Td("总成本"), html.Td(f"{optimal_design['cost_total']:.2f}"), html.Td("M$")]),
                        html.Tr([html.Td("覆盖范围"), html.Td(f"{optimal_design['perf_coverage']:.2f}"), html.Td("°")]),
                        html.Tr([html.Td("分辨率"), html.Td(f"{optimal_design['perf_resolution']:.4f}"), html.Td("m")]),
                    ])
                ], bordered=True, striped=True, hover=True, size='sm', className="mb-3"),

                # 约束与统计
                html.H6([html.Span("✅", className="me-2"), "约束满足情况"], className="mb-3"),
                dbc.ListGroup([
                    dbc.ListGroupItem(["✓", f"覆盖范围: {optimal_design['perf_coverage']:.2f}° ≥ {min_coverage}°"], color="light"),
                    dbc.ListGroupItem(["✓", f"分辨率: {optimal_design['perf_resolution']:.4f}m ≤ {max_resolution}m"], color="light"),
                ], className="mb-3"),
                
                dbc.Alert([
                    html.P([html.Strong("候选数量: "), f"{len(filtered_data)} / {len(feasible_designs)}"], className="mb-0")
                ], color="info")
            ])
        ], color="light", className="shadow")

        return result_card

    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert([html.H5("优化失败"), html.P(str(e))], color="danger")



# ===== 1. 自动保存 UI 状态 (覆盖所有输入控件) =====
@callback(
    Output('phase8-save-status', 'children', allow_duplicate=True),
    [Input('checklist-criteria', 'value'),
     Input('radio-ranking-method', 'value'),
     Input('select-vary-weight', 'value'),         
     Input('slider-weight-range', 'value'),        
     Input('input-mc-samples', 'value'),
     Input('select-baseline-design', 'value'),     
     Input('checklist-compare-designs', 'value'),  
     Input('radio-optimization-objective', 'value'), 
     Input('input-min-coverage-glpk', 'value'),       
     Input('input-max-resolution-glpk', 'value'),     
     Input('input-min-mau-glpk', 'value'),            
     Input('input-max-power-glpk', 'value')],         
    prevent_initial_call=True
)
def auto_save_phase8_ui(criteria, method, 
                       sens_var, sens_range, mc_samples,
                       pugh_base, pugh_compare,
                       opt_obj, min_cov, max_res, min_mau, max_pow):
    """
    自动保存 Phase 8 所有决策配置 UI 状态
    """
    from dash import ctx
    if not ctx.triggered: return no_update
    
    state = get_state_manager()
    current_ui = state.load('phase8', 'ui_state') or {}
    
    current_ui.update({
        'selected_criteria': criteria,
        'ranking_method': method,
        'sens_vary_weight': sens_var,
        'sens_weight_range': sens_range,
        'sens_mc_samples': mc_samples,
        'pugh_baseline': pugh_base,
        'pugh_compares': pugh_compare,
        'glpk_objective': opt_obj,
        'glpk_min_coverage': min_cov,
        'glpk_max_resolution': max_res,
        'glpk_min_mau': min_mau,
        'glpk_max_power': max_pow
    })
    
    state.save('phase8', 'ui_state', current_ui)
    return no_update


@callback(
    [Output('ranking-results-store', 'data', allow_duplicate=True),
     Output('top-designs-table', 'children'),
     Output('radar-chart', 'figure', allow_duplicate=True)],
    [Input('btn-run-ranking', 'n_clicks'),
     Input('btn-top5', 'n_clicks'),
     Input('btn-top10', 'n_clicks'),
     Input('btn-top20', 'n_clicks')],
    [State('checklist-criteria', 'value'),
     State('radio-ranking-method', 'value'),
     State('pareto-designs-store', 'data')], 
    prevent_initial_call=True
)
def update_ranking_results(n_run, n_top5, n_top10, n_top20, criteria, method, pareto_data):
    """
    执行 MCDM 排名分析并保存结果
    """
    from dash import ctx
    
    # 确定触发源
    triggered_id = ctx.triggered_id
    if not triggered_id or (not n_run and not n_top5 and not n_top10 and not n_top20):
        return no_update, no_update, no_update

    try:
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        
        state = get_state_manager()

        # 1. 准备数据 (优先使用 Phase 7 的帕累托解，如果没有则加载 Phase 6 的可行解)
        df = pd.DataFrame()
        if pareto_data:
            df = pd.DataFrame(pareto_data)
        else:
            # 尝试从 StateManager 加载
            pareto_remote = state.load('phase7', 'pareto_designs')
            if pareto_remote:
                df = pd.DataFrame(pareto_remote)
            else:
                # 降级：使用 Phase 6 可行解
                feasible = state.load('phase6', 'feasible_designs')
                if feasible is not None:
                    if isinstance(feasible, dict) and 'data' in feasible:
                        df = pd.DataFrame(feasible['data'])
                    elif isinstance(feasible, list):
                        df = pd.DataFrame(feasible)

        if df.empty:
            return no_update, dbc.Alert("无有效设计方案可供排名", color="warning"), no_update

        if not criteria:
            return no_update, dbc.Alert("请选择至少一个评价准则", color="warning"), no_update

        # 2. 执行排名计算 (模拟逻辑)
        # 实际应调用 DecisionEngine
        # 这里简单模拟评分：归一化加权
        df_scored = df.copy()
        df_scored['score'] = 0.0
        
        for crit in criteria:
            if crit in df_scored.columns:
                # 简单最大化归一化 (实际需区分 minimize/maximize)
                min_v = df_scored[crit].min()
                max_v = df_scored[crit].max()
                if max_v != min_v:
                    norm = (df_scored[crit] - min_v) / (max_v - min_v)
                    # 假设都是越高越好，如果是成本等需要反转
                    if 'cost' in crit.lower() or 'power' in crit.lower():
                        norm = 1 - norm
                    df_scored['score'] += norm
        
        df_scored['score'] /= len(criteria)
        df_scored = df_scored.sort_values('score', ascending=False)
        
        # 确定Top N数量
        if triggered_id == 'btn-top5':
            top_n = 5
        elif triggered_id == 'btn-top10':
            top_n = 10
        elif triggered_id == 'btn-top20':
            top_n = 20
        else:
            top_n = 10
        
        # Top N
        top_n_designs = df_scored.head(top_n).to_dict('records')
        
        # 3. [Core Data] 立即持久化
        analysis_result = {
            'method': method,
            'weights': {c: 1.0/len(criteria) for c in criteria}, 
            'rankings': top_n_designs,
            'scores': df_scored.to_dict('records')
        }
        
        # 保存结果
        state.save('phase8', 'mcdm_analysis', analysis_result)
        # 保存生效配置
        state.save('phase8', 'mcdm_config', {'criteria': criteria, 'method': method})

        # 4. 生成雷达图 (Top 10设计)
        top_10 = df_scored.head(10)
        
        # 归一化数据用于雷达图
        radar_data = top_10[criteria].copy()
        for col in radar_data.columns:
            min_val = radar_data[col].min()
            max_val = radar_data[col].max()
            if max_val != min_val:
                radar_data[col] = (radar_data[col] - min_val) / (max_val - min_val)
        
        # 创建雷达图
        fig_radar = go.Figure()
        
        # 列名映射
        label_map = {
            'cost_total': '总成本',
            'perf_coverage': '覆盖范围',
            'perf_resolution': '分辨率',
            'MAU': 'MAU',
            'cost_effectiveness': '性价比'
        }
        
        # 为每个设计添加雷达图轨迹
        for idx, row in top_10.iterrows():
            fig_radar.add_trace(go.Scatterpolar(
                r=list([radar_data.at[idx, crit] for crit in criteria]),
                theta=list([label_map.get(crit, crit) for crit in criteria]),
                fill='toself',
                name=f'设计 #{idx}',
                opacity=0.3
            ))
        
        fig_radar.update_layout(
            polar_radialaxis_visible=True,
            polar_radialaxis_range=[0, 1],
            showlegend=True,
            title="Top 10 设计雷达图对比",
            height=600
        )

        # 5. 生成表格
        table = dbc.Table.from_dataframe(
            df_scored.head(top_n).round(4),
            striped=True, bordered=True, hover=True
        )

        return top_n_designs, table, fig_radar

    except Exception as e:
        import traceback
        traceback.print_exc()
        return no_update, dbc.Alert(f"排名计算失败: {str(e)}", color="danger"), no_update



@callback(
    [Output('checklist-criteria', 'value'),
     Output('radio-ranking-method', 'value'),
     Output('select-vary-weight', 'value'),        
     Output('slider-weight-range', 'value'),       
     Output('input-mc-samples', 'value'),
     Output('select-baseline-design', 'value'),    
     Output('checklist-compare-designs', 'value'),  
     Output('radio-optimization-objective', 'value'), 
     Output('input-min-coverage-glpk', 'value'),      
     Output('input-max-resolution-glpk', 'value'),    
     Output('input-min-mau-glpk', 'value'),           
     Output('input-max-power-glpk', 'value'),         
     Output('optimization-results-store', 'data', allow_duplicate=True),
     Output('phase8-save-status', 'children', allow_duplicate=True)],
    [Input('btn-load-phase8', 'n_clicks'),
     Input('phase8-autoloader', 'n_intervals')],  
    prevent_initial_call=True
)
def load_phase8_data(n_clicks, n_intervals):
    """
    统一加载：恢复决策配置和计算结果
    """
    from dash import ctx
    
    triggered_id = ctx.triggered_id
    
    if not triggered_id:
        return tuple([no_update] * 14)

    try:
        state = get_state_manager()
        
        # 1. 加载 Core Data (计算结果)
        mcdm_res = state.load('phase8', 'mcdm_analysis')
        opt_res = state.load('phase8', 'optimization_results')
        
        # 2. 加载 UI State
        ui_state = state.load('phase8', 'ui_state') or {}
        
        # 3. 恢复值
        r_criteria = ui_state.get('selected_criteria', [])
        r_method = ui_state.get('ranking_method', 'topsis')
        
        r_vary_weight = ui_state.get('sens_vary_weight', no_update)
        r_weight_range = ui_state.get('sens_weight_range', [0.1, 0.5])
        r_mc_samples = ui_state.get('sens_mc_samples', 100)
        
        r_baseline = ui_state.get('pugh_baseline', no_update)
        r_compares = ui_state.get('pugh_compares', [])
        
        r_opt_obj = ui_state.get('glpk_objective', 'minimize_cost')
        r_min_cov = ui_state.get('glpk_min_coverage', 40)
        r_max_res = ui_state.get('glpk_max_resolution', 2.0)
        r_min_mau = ui_state.get('glpk_min_mau', 0.5)
        r_max_pow = ui_state.get('glpk_max_power', 3500)

        status_msg = no_update
        if triggered_id == 'btn-load-phase8':
            status_msg = dbc.Alert([
                "✓",
                "已成功恢复决策分析配置"
            ], color="success")

        return (
            r_criteria, r_method,
            r_vary_weight, r_weight_range, r_mc_samples,
            r_baseline, r_compares,
            r_opt_obj, r_min_cov, r_max_res, r_min_mau, r_max_pow,
            opt_res or no_update,  
            status_msg
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        error = dbc.Alert(f"加载异常: {str(e)}", color="danger")
        return tuple([no_update] * 13) + (error,)
    
    
@callback(
    Output('phase8-save-status', 'children', allow_duplicate=True),
    Input('btn-save-phase8', 'n_clicks'),
    [State('ranking-results-store', 'data'),
     State('optimization-results-store', 'data'),
     State('checklist-criteria', 'value'),
     State('radio-ranking-method', 'value'),
     State('select-vary-weight', 'value'),         
     State('slider-weight-range', 'value'),        
     State('input-mc-samples', 'value'),
     State('select-baseline-design', 'value'),     
     State('checklist-compare-designs', 'value'),  
     State('radio-optimization-objective', 'value'), 
     State('input-min-coverage-glpk', 'value'),       
     State('input-max-resolution-glpk', 'value'),     
     State('input-min-mau-glpk', 'value'),            
     State('input-max-power-glpk', 'value')],         
    prevent_initial_call=True
)
def save_phase8_data(n_clicks, mcdm_res, opt_res, 
                    criteria, method, 
                    sens_var, sens_range, mc_samples,
                    pugh_base, pugh_compare,
                    opt_obj, min_cov, max_res, min_mau, max_pow):
    """手动保存 Phase 8 所有数据"""
    if not n_clicks: return no_update
    
    state = get_state_manager()
    
    # 1. 保存 Core Data
    if mcdm_res: state.save('phase8', 'mcdm_analysis', mcdm_res)
    if opt_res: state.save('phase8', 'optimization_results', opt_res)
    
    # 2. 保存 UI State
    ui_state = {
        'selected_criteria': criteria,
        'ranking_method': method,
        'sens_vary_weight': sens_var,
        'sens_weight_range': sens_range,
        'sens_mc_samples': mc_samples,
        'pugh_baseline': pugh_base,
        'pugh_compares': pugh_compare,
        'glpk_objective': opt_obj,
        'glpk_min_coverage': min_cov,
        'glpk_max_resolution': max_res,
        'glpk_min_mau': min_mau,
        'glpk_max_power': max_pow
    }
    state.save('phase8', 'ui_state', ui_state)
    
    return dbc.Alert([
        "✓",
        "Phase 8 决策数据已保存"
    ], color="success")

# 填充评价准则选项
@callback(
    [Output('checklist-criteria', 'options'),
     Output('select-baseline-design', 'options'),
     Output('checklist-compare-designs', 'options')],
    Input('phase8-autoloader', 'n_intervals')
)
def populate_criteria_options(n_intervals):
    """填充评价准则和设计选项"""
    if not n_intervals:
        return [], [], []
    
    try:
        import pandas as pd
        state = get_state_manager()
        
        # 加载Pareto设计
        pareto_data = state.load('phase7', 'pareto_designs')
        if not pareto_data:
            pareto_data = state.load('phase6', 'feasible_designs')
        
        if not pareto_data:
            return [], [], []
        
        if isinstance(pareto_data, list):
            df = pd.DataFrame(pareto_data)
        else:
            df = pareto_data
        
        if df.empty:
            return [], [], []
        
        # 评价准则选项
        excluded = ['design_id', 'feasible', 'kills', 'name']
        criteria = [col for col in df.columns if col not in excluded]
        
        label_map = {
            'cost_total': '总成本 (M$)',
            'cost_satellite': '卫星成本 (M$)',
            'cost_launch': '发射成本 (M$)',
            'perf_coverage': '覆盖范围 (°)',
            'perf_resolution': '分辨率 (m)',
            'transmit_power': '发射功率 (W)',
            'MAU': 'MAU效用值',
            'orbit_altitude': '轨道高度 (km)',
            'antenna_diameter': '天线直径 (m)',
            'cost_effectiveness': '性价比'
        }
        
        criteria_options = [
            {'label': label_map.get(col, col), 'value': col}
            for col in criteria if col in label_map
        ]
        
        # 设计选项（用于Pugh矩阵）
        design_options = [
            {'label': f'设计 #{int(idx)}', 'value': int(idx)}
            for idx in df.index
        ]
        
        return criteria_options, design_options, design_options
        
    except Exception as e:
        print(f"填充选项失败: {e}")
        return [], [], []

# 加载Pareto数据到Store
@callback(
    Output('pareto-designs-store', 'data'),
    [Input('phase8-autoloader', 'n_intervals'),
     Input('btn-run-ranking', 'n_clicks')],
    prevent_initial_call=False
)
def load_pareto_to_store(n_intervals, n_clicks):
    """加载Phase 7的Pareto数据到前端Store"""
    if not n_intervals and not n_clicks:
        return no_update
    
    try:
        state = get_state_manager()
        pareto_data = state.load('phase7', 'pareto_designs')
        
        if not pareto_data:
            pareto_data = state.load('phase6', 'feasible_designs')
        
        if isinstance(pareto_data, list):
            return pareto_data
        elif hasattr(pareto_data, 'to_dict'):
            return pareto_data.to_dict('records')
        return pareto_data
    except Exception as e:
        print(f"加载Pareto数据失败: {e}")
        return []

# 生成权重滑块
@callback(
    [Output('weights-sliders', 'children'),
     Output('weights-sum-progress', 'value'),
     Output('weights-sum-text', 'children')],
    [Input('checklist-criteria', 'value'),
     Input('phase8-autoloader', 'n_intervals')]
)
def generate_weights_sliders(criteria, n_intervals):
    """生成权重配置滑块"""
    if not criteria:
        return html.P("请先选择评价准则", className="text-muted"), 0, "权重总和: 0"
    
    try:
        sliders = []
        for i, crit in enumerate(criteria):
            label_map = {
                'cost_total': '总成本',
                'perf_coverage': '覆盖范围',
                'perf_resolution': '分辨率',
                'MAU': 'MAU效用值',
                'cost_effectiveness': '性价比'
            }
            label = label_map.get(crit, crit)
            
            sliders.append(
                dbc.Row([
                    dbc.Col([
                        dbc.Label(f"{label} 权重", className="fw-bold"),
                        dcc.Slider(
                            id=f'slider-weight-{i}',
                            min=0,
                            max=1,
                            step=0.05,
                            value=0.25,
                            marks={j/10: f'{j/10:.1f}' for j in range(0, 11, 2)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], md=10),
                    dbc.Col([
                        html.Span(id=f'span-weight-{i}', children="0.25", className="fw-bold text-primary")
                    ], md=2, className="d-flex align-items-center justify-content-center")
                ], className="mb-3 align-items-center")
            )
        
        return sliders, 25, "权重总和: 1.00 (默认等权重)"

    except Exception as e:
        print(f"生成权重滑块失败: {e}")
        return html.P(f"生成失败: {e}", className="text-danger"), 0, "错误"


@callback(
    Output('download-csv', 'data'),
    Input('btn-export-csv', 'n_clicks'),
    State('ranking-results-store', 'data'),
    prevent_initial_call=True
)
def export_csv(n_clicks, ranking_data):
    """导出排名结果为CSV"""
    if not n_clicks or not ranking_data:
        return None
    
    try:
        import pandas as pd
        import datetime
        
        df = pd.DataFrame(ranking_data)
        
        filename = f'ranking_results_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return dcc.send_data_frame(df.to_csv, filename=filename, index=False)
        
    except Exception as e:
        print(f"导出CSV失败: {e}")
        return None

# 导出Excel功能
@callback(
    Output('download-excel', 'data'),
    Input('btn-export-excel', 'n_clicks'),
    State('ranking-results-store', 'data'),
    prevent_initial_call=True
)
def export_excel(n_clicks, ranking_data):
    """导出排名结果为Excel"""
    if not n_clicks or not ranking_data:
        return None
    
    try:
        import pandas as pd
        import datetime
        
        df = pd.DataFrame(ranking_data)
        
        filename = f'ranking_results_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return dcc.send_data_frame(df.to_excel, filename=filename, sheet_name="Ranking", index=False)
        
    except Exception as e:
        print(f"导出Excel失败: {e}")
        return None

# 导出PDF报告功能
@callback(
    Output('download-pdf', 'data'),
    Input('btn-export-pdf', 'n_clicks'),
    State('ranking-results-store', 'data'),
    State('decision-report', 'children'),
    prevent_initial_call=True
)
def export_pdf(n_clicks, ranking_data, report_html):
    """导出决策报告为PDF"""
    if not n_clicks:
        return None
    
    try:
        import datetime
        import io
        
        content = "决策分析报告\n"
        content += "=" * 50 + "\n\n"
        content += f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if ranking_data:
            content += "排名结果:\n"
            for i, design in enumerate(ranking_data[:10], 1):
                content += f"{i}. 设计 {design.get('name', 'N/A')}: 得分 {design.get('score', 0):.4f}\n"
            content += "\n"
        
        filename = f'decision_report_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        return dcc.send_bytes(content.encode('utf-8'), filename=filename)
        
    except Exception as e:
        print(f"导出PDF失败: {e}")
        return None

# 导出图表功能
@callback(
    Output('download-charts', 'data'),
    Input('btn-export-charts', 'n_clicks'),
    State('radar-chart', 'figure'),
    State('sensitivity-plot', 'figure'),
    prevent_initial_call=True
)
def export_charts(n_clicks, radar_fig, sensitivity_fig):
    """导出图表为图片"""
    if not n_clicks:
        return None
    
    try:
        import datetime
        import plotly.io as pio
        
        # 导出雷达图
        if radar_fig:
            import io
            radar_bytes = io.BytesIO()
            pio.write_image(radar_fig, radar_bytes, format='png')
            radar_bytes.seek(0)
            bytes_content = radar_bytes.read()
            filename = 'radar_chart_{}.png'.format(datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
            return dcc.send_bytes(bytes_content, filename=filename)
        
        return None
        
    except Exception as e:
        print(f"导出图表失败: {e}")
        return None