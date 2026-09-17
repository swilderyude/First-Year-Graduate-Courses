"""
Phase 6: 约束管理与可行性过滤
集成ConstraintEngine实现真实约束评估
"""

from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constraint_engine import ConstraintEngine, Constraint
from utils.state_manager import get_state_manager

layout = dbc.Container([
    dcc.Interval(id='phase6-autoloader', interval=500, max_intervals=1),
    dcc.Store(id='phase6-feasible-store', data=None),
    dcc.Store(id='global-selection-store', data={'selected_ids': []}, storage_type='session'),  # P0-1: 全局选择状态

    html.H2([
        html.Span("🔍", className="me-2"),
        "Phase 6: 约束管理与可行性过滤"
    ], className="mb-4"),

    dbc.Alert([
        html.Span("ℹ️", className="me-2"),
        "本阶段使用预定义的约束条件。将自动读取Phase 5的计算结果进行可行性筛选。"
    ], color="info", className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("6.1 预定义约束", className="mb-0")),
                dbc.CardBody([
                    html.P([html.Strong("硬约束（必须满足）:")]),
                    html.Ul([
                        html.Li("预算限制: 总成本 ≤ 5000 M$"),
                        html.Li("最小速度增量: 速度增量 ≥ 3 km/s"),
                        html.Li("最小服务能力: 服务能力 ≥ 2")
                    ]),
                    html.P([html.Strong("软约束（期望满足）:")]),
                    html.Ul([
                        html.Li("快速响应: 响应时间 = 0 (Fast)")
                    ])
                ])
            ], className="shadow-sm mb-4")
        ], md=12),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("6.2 执行可行性过滤", className="mb-0")),
                dbc.CardBody([
                    dbc.Button([
                        html.Span("🔍", className="me-2"),
                        "应用约束过滤"
                    ], id="btn-filter-designs", color="success", size="lg", className="w-100 mb-3"),
                    html.Div(id="filter-status")
                ])
            ], className="shadow-sm mb-4")
        ], md=12)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("6.3 Kill分析", className="mb-0")),
                dbc.CardBody([
                    html.Div(id="kill-analysis-results")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 可行性对比分析
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("6.4 可行 vs 不可行设计对比", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "箱线图对比可行和不可行设计在多个指标上的分布差异"
                    ], color="info", className="mb-3"),
                    dcc.Graph(id="feasibility-comparison-boxplot", figure=go.Figure(),
                             config={'displayModeBar': True}),
                    dbc.Button([
                        html.Span("📊", className="me-2"),
                        "生成对比图表"
                    ], id="btn-generate-feasibility-comparison", color="info",
                       className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 约束敏感性分析 (P1-5)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("6.5 不确定性传播分析 (Uncertainty Propagation)", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        html.Strong("系统工程定量方法："),
                        "使用蒙特卡洛模拟分析输入变量的不确定性如何传播到输出结果",
                        html.Br(),
                        html.Small("量化设计方案的鲁棒性，支持风险决策")
                    ], color="info", className="mb-3"),

                    dbc.Label("选择目标指标"),
                    dcc.Dropdown(
                        id='select-uncertainty-target',
                        options=[],
                        placeholder="选择目标指标 (通常为MAU)...",
                        className="mb-3"
                    ),

                    dbc.Label("选择不确定变量"),
                    dcc.Dropdown(
                        id='select-uncertainty-vars',
                        options=[],
                        multi=True,
                        placeholder="选择具有不确定性的设计变量...",
                        className="mb-3"
                    ),

                    dbc.Label("不确定性分布类型"),
                    dbc.RadioItems(
                        id='radio-uncertainty-dist',
                        options=[
                            {'label': '正态分布 (±5%)', 'value': 'normal'},
                            {'label': '均匀分布 (±10%)', 'value': 'uniform'}
                        ],
                        value='normal',
                        className="mb-3"
                    ),

                    dbc.Label("模拟次数"),
                    dcc.Slider(
                        id='slider-monte-carlo-samples',
                        min=100,
                        max=5000,
                        step=100,
                        value=1000,
                        marks={i: str(i) for i in range(100, 5001, 1000)},
                        tooltip={"placement": "bottom", "always_visible": True},
                        className="mb-3"
                    ),

                    dbc.Button([
                        html.Span("🎲", className="me-2"),
                        "运行蒙特卡洛模拟"
                    ], id='btn-monte-carlo', color="warning", className="w-100 mb-3"),

                    html.Div(id='uncertainty-results', className="mb-3"),
                    
                    dcc.Graph(id='uncertainty-distribution-plot', figure=go.Figure(),
                             config={'displayModeBar': True})
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # P2-8: 交互式约束调整
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("6.6 交互式约束调整 (P2-8)", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "使用滑块实时调整约束条件，立即看到可行设计数量变化"
                    ], color="info", className="mb-3"),

                    # 实时可行性统计卡片
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.H2(id='realtime-feasible-count', children="---", className="mb-0 text-center text-success"),
                                html.P("可行设计数量", className="text-center text-muted mb-2"),
                                dbc.Progress(id='realtime-feasibility-progress', value=0, className="mb-2"),
                                html.P(id='realtime-feasibility-ratio', children="可行性: ---%", className="text-center text-muted mb-0")
                            ])
                        ])
                    ], color="light", className="mb-4"),

                    # 滑块控制区
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("💰 预算限制 (总成本 ≤ )"),
                            dcc.Slider(
                                id='slider-budget-limit',
                                min=0,
                                max=10000,
                                step=100,
                                value=5000,
                                marks={i: f'{i}M$' for i in range(0, 10001, 2000)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                        ], md=6),

                        dbc.Col([
                            dbc.Label("🚀 最小速度增量 (速度增量 ≥ )"),
                            dcc.Slider(
                                id='slider-min-deltav',
                                min=0,
                                max=12,
                                step=0.5,
                                value=3,
                                marks={i: f'{i}km/s' for i in range(0, 13, 2)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                        ], md=6)
                    ]),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("📦 最小服务能力 (服务能力 ≥ )"),
                            dcc.Slider(
                                id='slider-min-capability',
                                min=0,
                                max=4,
                                step=1,
                                value=2,
                                marks={i: f'{i}' for i in range(5)},
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="mb-3"
                            ),
                        ], md=6),

                        dbc.Col([
                            dbc.Label("⚡ 快速响应 (响应时间 = 0)"),
                            dcc.Dropdown(
                                id='dropdown-fast-response',
                                options=[
                                    {'label': '是 (Fast)', 'value': 0},
                                    {'label': '否 (Slow)', 'value': 1}
                                ],
                                value=0,
                                className="mb-3"
                            ),
                        ], md=6)
                    ]),

                    html.Hr(),

                    dbc.Button([
                        "✓",
                        "应用当前约束并重新过滤"
                    ], id='btn-apply-adjusted-constraints', color="success", className="w-100")
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
                            "保存Phase 6数据"
                        ], id="btn-save-phase6", color="success", className="me-2"),
                        dbc.Button([
                            html.Span("📤", className="me-2"),
                            "加载Phase 6数据"
                        ], id="btn-load-phase6", color="info")
                    ]),
                    html.Div(id="phase6-save-status", className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button("上一步: Phase 5", href="/phase5", color="secondary", outline=True),
                dbc.Button("下一步: Phase 7", href="/phase7", color="primary")
            ], className="w-100")
        ])
    ])
], fluid=True)

@callback(
    [Output('filter-status', 'children', allow_duplicate=True),
     Output('kill-analysis-results', 'children', allow_duplicate=True),
     Output('phase6-feasible-store', 'data', allow_duplicate=True)],
    [Input('btn-filter-designs', 'n_clicks')],
    prevent_initial_call=True
)
def apply_constraints(n_clicks):
    """应用约束 - 集成ConstraintEngine"""
    if not n_clicks:
        return no_update, no_update, no_update

    try:
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

        # 1. 从StateManager加载Phase 5数据
        state = get_state_manager()
        unified = state.load('phase5', 'unified_results')

        if not _has_valid_data(unified):  # DataFrame使用显式类型检查
            return dbc.Alert("请先在Phase 5运行批量计算！", color="warning"), no_update, None

        # 2. 创建约束引擎
        engine = ConstraintEngine()

        # 添加约束 (使用 JSON 数据中的实际列名)
        engine.add_constraint(Constraint('budget', '总成本 <= 5000', 'hard'))
        engine.add_constraint(Constraint('min_deltav', '速度增量 >= 3', 'hard'))
        engine.add_constraint(Constraint('min_capability', '服务能力 >= 2', 'hard'))
        engine.add_constraint(Constraint('fast_response', '响应时间 == 0', 'soft'))

        # 3. 应用约束
        unified_filtered = engine.apply_constraints(unified)
        n_feasible = unified_filtered['feasible'].sum()
        n_total = len(unified_filtered)
        feasibility_rate = n_feasible / n_total * 100

        # 4. 保存到StateManager
        state.save('phase6', 'constraints', [c.to_dict() for c in engine.constraints])
        feasible_df = unified_filtered[unified_filtered['feasible']]
        feasible_designs = feasible_df.to_dict('records')
        state.save('phase6', 'feasible_designs', feasible_designs)

        # 5. 状态显示
        if feasibility_rate >= 50:
            color = "success"
        elif feasibility_rate >= 20:
            color = "warning"
        else:
            color = "danger"

        status = dbc.Alert([
            html.H5(["✓", "过滤完成！"], className="alert-heading"),
            html.Hr(),
            html.H4(f"可行方案: {n_feasible} / {n_total}", className="mb-2"),
            html.P([
                dbc.Progress(value=feasibility_rate, label=f"{feasibility_rate:.1f}%",
                           color="success" if feasibility_rate >= 50 else "warning", className="mb-3")
            ]),
            html.P([
                html.Strong("约束数量: "), f"{len(engine.constraints)} (3硬+1软)", html.Br(),
                html.Strong("过滤率: "), f"{100-feasibility_rate:.1f}%"
            ])
        ], color=color)

        # 6. Kill分析
        analysis = engine.analyze_constraints()

        kill_display = dbc.Alert([
            html.H5("Kill分析 - 约束瓶颈识别", className="alert-heading"),
            html.Hr(),
            html.P("识别哪些约束导致了最多的设计被淘汰："),
            dbc.Table.from_dataframe(analysis, striped=True, bordered=True, hover=True)
        ], color="info")

        return status, kill_display, feasible_designs

    except Exception as e:
        error = dbc.Alert(f"过滤失败: {str(e)}", color="danger")
        return error, no_update, None

@callback(
    Output('feasibility-comparison-boxplot', 'figure'),
    Input('btn-generate-feasibility-comparison', 'n_clicks'),
    prevent_initial_call=True
)
def generate_feasibility_comparison(n_clicks):
    """生成可行 vs 不可行设计的箱线图对比 (P0-1功能)"""
    if not n_clicks:
        return no_update

    try:
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

        # 1. 从StateManager加载统一结果
        state = get_state_manager()
        unified = state.load('phase5', 'unified_results')

        if not _has_valid_data(unified):  # DataFrame使用显式类型检查
            # 返回空图表并提示
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_annotation(
                text="请先在Phase 5运行批量计算，再在Phase 6应用约束过滤！",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="red")
            )
            fig.update_layout(
                title="可行 vs 不可行设计对比",
                height=600,
                xaxis=dict(visible=False),
                yaxis=dict(visible=False)
            )
            return fig

        # 2. 检查是否有feasible列（Phase 6约束过滤后才有）
        if 'feasible' not in unified.columns:
            # 如果还没有过滤，创建一个临时约束引擎来添加feasible列
            from utils.constraint_engine import ConstraintEngine, Constraint
            engine = ConstraintEngine()
            engine.add_constraint(Constraint('budget', '总成本 <= 5000', 'hard'))
            engine.add_constraint(Constraint('min_deltav', '速度增量 >= 3', 'hard'))
            engine.add_constraint(Constraint('min_capability', '服务能力 >= 2', 'hard'))
            unified = engine.apply_constraints(unified)

        # 3. 分离可行和不可行设计
        feasible_designs = unified[unified['feasible']]
        infeasible_designs = unified[~unified['feasible']]

        n_feasible = len(feasible_designs)
        n_infeasible = len(infeasible_designs)

        # 4. 选择要对比的关键指标
        metrics = [
            {'col': '总成本', 'name': '总成本 (M$)'},
            {'col': '速度增量', 'name': '速度增量 (km/s)'},
            {'col': '服务能力', 'name': '服务能力'},
            {'col': 'MAU', 'name': 'MAU效用值'}
        ]

        # 5. 创建子图（2x2布局）
        from plotly.subplots import make_subplots
        import plotly.graph_objects as go

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[m['name'] for m in metrics],
            vertical_spacing=0.12,
            horizontal_spacing=0.10
        )

        # 6. 为每个指标添加箱线图
        positions = [(1, 1), (1, 2), (2, 1), (2, 2)]

        for metric, (row, col) in zip(metrics, positions):
            metric_col = metric['col']

            # 可行设计箱线图
            fig.add_trace(
                go.Box(
                    y=feasible_designs[metric_col],
                    name='可行',
                    marker=dict(color='rgb(46, 204, 113)'),
                    boxmean='sd',  # 显示均值和标准差
                    legendgroup='feasible',
                    showlegend=(row == 1 and col == 1)  # 只在第一个子图显示图例
                ),
                row=row, col=col
            )

            # 不可行设计箱线图
            fig.add_trace(
                go.Box(
                    y=infeasible_designs[metric_col],
                    name='不可行',
                    marker=dict(color='rgb(231, 76, 60)'),
                    boxmean='sd',
                    legendgroup='infeasible',
                    showlegend=(row == 1 and col == 1)
                ),
                row=row, col=col
            )

        # 7. 更新布局
        fig.update_layout(
            title=dict(
                text=f"可行 vs 不可行设计对比分析<br><sub>可行: {n_feasible} | 不可行: {n_infeasible} | 总计: {len(unified)}</sub>",
                x=0.5,
                xanchor='center'
            ),
            height=700,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            hovermode='closest'
        )

        # 8. 更新坐标轴标签
        fig.update_xaxes(title_text="", showticklabels=True)
        fig.update_yaxes(title_text=metrics[0]['name'], row=1, col=1)
        fig.update_yaxes(title_text=metrics[1]['name'], row=1, col=2)
        fig.update_yaxes(title_text=metrics[2]['name'], row=2, col=1)
        fig.update_yaxes(title_text=metrics[3]['name'], row=2, col=2)

        return fig

    except Exception as e:
        # 错误处理
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_annotation(
            text=f"生成图表失败: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(
            title="可行 vs 不可行设计对比（生成失败）",
            height=600
        )
        return fig

# ========== P2-8: 交互式约束调整回调 ==========

# 回调1: 实时可行性计算（监听滑块变化）
@callback(
    [Output('realtime-feasible-count', 'children'),
     Output('realtime-feasibility-progress', 'value'),
     Output('realtime-feasibility-progress', 'color'),
     Output('realtime-feasibility-ratio', 'children')],
    [Input('slider-budget-limit', 'value'),
     Input('slider-min-deltav', 'value'),
     Input('slider-min-capability', 'value'),
     Input('dropdown-fast-response', 'value')],
    prevent_initial_call=False
)
def update_realtime_feasibility(budget_limit, min_deltav, min_capability, fast_response):
    """实时更新可行性统计（P2-8核心功能）"""
    try:
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
        unified = state.load('phase5', 'unified_results')

        if not _has_valid_data(unified):  # DataFrame使用显式类型检查
            return "---", 0, "secondary", "请先运行Phase 5批量计算"

        # 2. 根据当前滑块值计算可行性 (使用 JSON 数据中的实际列名)
        # 硬约束（必须全部满足）
        feasible_mask = (
            (unified['总成本'] <= budget_limit) &
            (unified['速度增量'] >= min_deltav) &
            (unified['服务能力'] >= min_capability)
        )

        # 软约束（响应时间，不影响可行性，但用于排序）
        # 这里我们将软约束也纳入可行性判断（用于展示）
        feasible_mask = feasible_mask & (unified['响应时间'] == fast_response)

        n_feasible = feasible_mask.sum()
        n_total = len(unified)
        feasibility_ratio = n_feasible / n_total * 100

        # 3. 颜色编码
        if feasibility_ratio >= 60:
            progress_color = "success"
        elif feasibility_ratio >= 30:
            progress_color = "warning"
        else:
            progress_color = "danger"

        # 4. 返回更新的UI
        return (
            str(n_feasible),
            feasibility_ratio,
            progress_color,
            f"可行性: {feasibility_ratio:.1f}% ({n_feasible}/{n_total})"
        )

    except Exception as e:
        return "错误", 0, "danger", f"计算失败: {str(e)}"
    

# 回调2: 应用调整后的约束并重新过滤
@callback(
    [Output('filter-status', 'children', allow_duplicate=True),
     Output('kill-analysis-results', 'children', allow_duplicate=True),
     Output('phase6-feasible-store', 'data', allow_duplicate=True)],
    [Input('btn-apply-adjusted-constraints', 'n_clicks'),
     Input('btn-filter-designs', 'n_clicks')],
    [State('slider-budget-limit', 'value'),
     State('slider-min-deltav', 'value'),
     State('slider-min-capability', 'value'),
     State('dropdown-fast-response', 'value')],
    prevent_initial_call=True
)
def apply_adjusted_constraints(n_click_adjust, n_click_filter, budget_limit, min_deltav, min_capability, fast_response):
    """
    应用约束过滤逻辑
    功能：
    1. 计算可行性过滤。
    2. 生成 Kill Analysis。
    3. 立即持久化核心数据 (Constraints, Config, Feasible Designs)。
    """
    from dash import ctx
    if not (n_click_adjust or n_click_filter):
        return no_update, no_update, no_update

    try:
        state = get_state_manager()
        # 1. 加载 Phase 5 输入数据
        unified = state.load('phase5', 'unified_results')

        def _has_valid_data(data):
            if data is None: return False
            if isinstance(data, pd.DataFrame): return not data.empty
            if isinstance(data, list): return len(data) > 0
            return False

        if not _has_valid_data(unified):
            return dbc.Alert("请先在Phase 5运行批量计算！", color="warning"), no_update, None

        # 2. 创建约束引擎并应用 (使用 JSON 数据中的实际列名)
        engine = ConstraintEngine()
        engine.add_constraint(Constraint('budget', f'总成本 <= {budget_limit}', 'hard'))
        engine.add_constraint(Constraint('min_deltav', f'速度增量 >= {min_deltav}', 'hard'))
        engine.add_constraint(Constraint('min_capability', f'服务能力 >= {min_capability}', 'hard'))
        engine.add_constraint(Constraint('fast_response', f'响应时间 == {fast_response}', 'soft'))

        unified_filtered = engine.apply_constraints(unified)
        n_feasible = unified_filtered['feasible'].sum()
        n_total = len(unified_filtered)
        feasibility_rate = n_feasible / n_total * 100

        # 3. [Core Data] 立即持久化关键结果
        # 保存具体约束定义
        state.save('phase6', 'constraints', [c.to_dict() for c in engine.constraints])
        # 保存可行设计结果集 (转换为字典列表以便JSON序列化)
        feasible_df = unified_filtered[unified_filtered['feasible']]
        feasible_designs = feasible_df.to_dict('records')
        state.save('phase6', 'feasible_designs', feasible_designs)
        # 保存生效的配置参数 (用于下次加载恢复基准)
        constraint_config = {
            'budget_limit': budget_limit,
            'min_deltav': min_deltav,
            'min_capability': min_capability,
            'fast_response': fast_response
        }
        state.save('phase6', 'constraint_config', constraint_config)

        # 4. 生成分析报告
        analysis = engine.analyze_constraints()
        kill_display = dbc.Alert([
            html.H5("Kill分析 - 约束瓶颈识别", className="alert-heading"),
            html.Hr(),
            html.P("基于当前约束，识别导致最多设计被淘汰的条件："),
            dbc.Table.from_dataframe(analysis, striped=True, bordered=True, hover=True)
        ], color="info")

        # 5. 生成状态提示
        status = dbc.Alert([
            html.H5(["✓", "过滤完成 & 已保存"], className="alert-heading"),
            html.Hr(),
            html.P([
                dbc.Progress(value=feasibility_rate, label=f"{feasibility_rate:.1f}%",
                           color="success" if feasibility_rate >= 50 else "warning", className="mb-2"),
                f"可行方案: {n_feasible} / {n_total} (过滤率: {100-feasibility_rate:.1f}%)"
            ])
        ], color="success")

        return status, kill_display, feasible_designs

    except Exception as e:
        import traceback
        traceback.print_exc()
        error = dbc.Alert(f"应用约束失败: {str(e)}", color="danger")
        return error, no_update, None

# ========== P0-1: 全局刷选响应 (跨页面同步) ==========

@callback(
    Output('feasibility-comparison-boxplot', 'figure', allow_duplicate=True),
    Input('global-selection-store', 'data'),
    State('feasibility-comparison-boxplot', 'figure'),
    prevent_initial_call=True
)
def highlight_phase6_selection(selection_data, current_figure):
    """在Phase 6可行性对比图中高亮显示全局选中的设计 (P0-1跨页面同步)"""
    if not selection_data or not current_figure:
        return no_update

    selected_ids = selection_data.get('selected_ids', [])

    if not selected_ids:
        return no_update

    try:
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

        # 从StateManager加载统一结果
        state = get_state_manager()
        unified = state.load('phase5', 'unified_results')

        if not _has_valid_data(unified):  # DataFrame使用显式类型检查
            return no_update

        # 创建新图表（保留原有布局）
        import plotly.graph_objects as go
        fig = go.Figure(current_figure)

        # 添加选择统计注释
        # 计算选中设计的可行性状态
        selected_data = unified.iloc[selected_ids] if max(selected_ids) < len(unified) else None

        if selected_data is not None and 'feasible' in selected_data.columns:
            n_feasible_selected = selected_data['feasible'].sum()
            n_infeasible_selected = len(selected_data) - n_feasible_selected

            annotation_text = (
                f"✓ 已选中 {len(selected_ids)} 个设计<br>"
                f"  - {n_feasible_selected} 可行<br>"
                f"  - {n_infeasible_selected} 不可行"
            )
        else:
            annotation_text = f"✓ 已选中 {len(selected_ids)} 个设计"

        # 清除旧的选择注释
        fig.layout.annotations = [
            ann for ann in fig.layout.annotations
            if "已选中" not in ann.text
        ]

        # 添加新的选择统计注释
        fig.add_annotation(
            text=annotation_text,
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            bgcolor="rgba(255,0,0,0.1)",
            bordercolor="red",
            borderwidth=2,
            font=dict(size=10, color="red"),
            align="left",
            yanchor="top"
        )

        return fig

    except Exception as e:
        print(f"Phase 6全局刷选响应失败: {e}")
        import traceback
        traceback.print_exc()
        return no_update

# P1-5功能：不确定性传播分析
@callback(
    [Output('uncertainty-results', 'children'),
     Output('uncertainty-distribution-plot', 'figure')],
    Input('btn-monte-carlo', 'n_clicks'),
    [State('select-uncertainty-target', 'value'),
     State('select-uncertainty-vars', 'value'),
     State('radio-uncertainty-dist', 'value'),
     State('slider-monte-carlo-samples', 'value')],
    prevent_initial_call=True
)
def monte_carlo_uncertainty_analysis(n_clicks, target_var, uncertainty_vars, dist_type, n_samples):
    """蒙特卡洛不确定性传播分析"""
    if not n_clicks or not target_var or not uncertainty_vars:
        return dbc.Alert("请选择目标指标和不确定变量！", color="warning"), go.Figure()

    try:
        import numpy as np
        import pandas as pd
        import plotly.graph_objects as go

        state = get_state_manager()
        unified = state.load('phase5', 'unified_results')

        if unified is None:
            return dbc.Alert("请先在Phase 5运行批量计算！", color="warning"), go.Figure()
        
        if isinstance(unified, list):
            unified = pd.DataFrame(unified)
        
        if unified.empty:
            return dbc.Alert("数据为空", color="warning"), go.Figure()

        if target_var not in unified.columns:
            return dbc.Alert(f"目标指标 {target_var} 不存在", color="danger"), go.Figure()

        valid_vars = [v for v in uncertainty_vars if v in unified.columns]
        if not valid_vars:
            return dbc.Alert("选择的不确定变量都不存在", color="danger"), go.Figure()

        base_target_values = unified[target_var].values
        base_mean = np.mean(base_target_values)
        base_std = np.std(base_target_values)

        all_simulated_values = []

        for var in valid_vars:
            var_values = unified[var].values
            var_mean = np.mean(var_values)
            var_std = np.std(var_values)

            if dist_type == 'normal':
                uncertainty_pct = 0.05
                simulated_vars = np.random.normal(var_mean, var_std * uncertainty_pct, n_samples)
            else:
                uncertainty_pct = 0.10
                simulated_vars = np.random.uniform(var_mean * (1 - uncertainty_pct), 
                                               var_mean * (1 + uncertainty_pct), n_samples)

            correlation = np.corrcoef(var_values, base_target_values)[0, 1]
            
            simulated_targets = base_mean + correlation * (simulated_vars - var_mean) * (base_std / (var_std + 1e-6))
            all_simulated_values.extend(simulated_targets)

        all_simulated_values = np.array(all_simulated_values)
        simulated_mean = np.mean(all_simulated_values)
        simulated_std = np.std(all_simulated_values)
        
        percentiles = [5, 25, 50, 75, 95]
        percentile_values = np.percentile(all_simulated_values, percentiles)
        
        cv = (simulated_std / abs(simulated_mean)) * 100 if simulated_mean != 0 else 0
        
        results_html = dbc.Card([
            dbc.CardBody([
                html.H5("蒙特卡洛模拟结果", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Strong("基准均值:"),
                        html.P(f"{base_mean:.4f}", className="mb-0"),
                    ], md=4),
                    dbc.Col([
                        html.Strong("模拟均值:"),
                        html.P(f"{simulated_mean:.4f}", className="mb-0"),
                    ], md=4),
                    dbc.Col([
                        html.Strong("均值偏差:"),
                        html.P(f"{abs(simulated_mean - base_mean):.4f}", className="mb-0"),
                    ], md=4),
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Strong("基准标准差:"),
                        html.P(f"{base_std:.4f}", className="mb-0"),
                    ], md=4),
                    dbc.Col([
                        html.Strong("模拟标准差:"),
                        html.P(f"{simulated_std:.4f}", className="mb-0"),
                    ], md=4),
                    dbc.Col([
                        html.Strong("变异系数:"),
                        html.P(f"{cv:.2f}%", className="mb-0"),
                    ], md=4),
                ], className="mb-3"),
                html.H6("分位数分布:", className="mb-2"),
                dbc.Table([
                    html.Thead([
                        html.Tr([
                            html.Th("5%"),
                            html.Th("25%"),
                            html.Th("50%"),
                            html.Th("75%"),
                            html.Th("95%")
                        ])
                    ]),
                    html.Tbody([
                        html.Tr([
                            html.Td(f"{p:.4f}") for p in percentile_values
                        ])
                    ])
                ], striped=True, bordered=True, hover=True, size="sm"),
                html.P([
                    html.Strong("鲁棒性评估: "),
                    "高" if cv < 10 else "中" if cv < 20 else "低"
                ], className="mt-3 mb-0")
            ])
        ], className="shadow-sm")

        fig = go.Figure()

        fig.add_trace(go.Histogram(
            x=all_simulated_values,
            name='模拟分布',
            nbinsx=50,
            marker_color='rgba(52, 152, 219, 0.7)',
            opacity=0.75
        ))

        fig.add_vline(
            x=simulated_mean,
            line_dash="dash",
            line_color="red",
            annotation_text=f"均值: {simulated_mean:.4f}",
            annotation_position="top right"
        )

        for i, (p, val) in enumerate(zip(percentiles, percentile_values)):
            color = 'green' if p == 50 else 'orange'
            fig.add_vline(
                x=val,
                line_dash="dot" if p != 50 else "dash",
                line_color=color,
                line_width=1,
                annotation_text=f"{p}%: {val:.4f}",
                annotation_position="top left" if i % 2 == 0 else "bottom left",
                annotation_font_size=10
            )

        fig.update_layout(
            title=f"不确定性传播分析: {target_var}<br><sub>模拟次数: {n_samples} | 不确定变量: {len(valid_vars)}个</sub>",
            xaxis_title=f"{target_var} 值",
            yaxis_title="频数",
            height=500,
            showlegend=True,
            hovermode='x unified'
        )

        return results_html, fig

    except Exception as e:
        import traceback
        print(f"不确定性传播分析失败: {e}")
        print(traceback.format_exc())

        fig = go.Figure()
        fig.add_annotation(
            text=f"分析失败: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        return dbc.Alert(f"分析失败: {str(e)}", color="danger"), fig


# 更新不确定性分析的下拉选项
@callback(
    [Output('select-uncertainty-target', 'options'),
     Output('select-uncertainty-vars', 'options')],
    Input('phase6-autoloader', 'n_intervals')
)
def update_uncertainty_options(n_intervals):
    """更新不确定性分析的下拉选项"""
    if not n_intervals:
        return [], []
    
    try:
        state = get_state_manager()
        unified = state.load('phase5', 'unified_results')
        
        if unified is None:
            return [], []
        
        if isinstance(unified, list):
            unified = pd.DataFrame(unified)
        
        if unified.empty:
            return [], []
        
        numeric_cols = unified.select_dtypes(include=[np.number]).columns.tolist()
        
        target_options = [{'label': col, 'value': col} for col in numeric_cols if col in ['MAU', '总成本', '速度增量', '服务能力']]
        var_options = [{'label': col, 'value': col} for col in numeric_cols if col not in ['feasible', 'id']]
        
        return target_options, var_options
        
    except Exception as e:
        print(f"更新不确定性选项失败: {e}")
        return [], []




