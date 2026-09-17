"""
Phase 5: 多域建模
集成ComputationEngine实现真实计算
"""

from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import sys
import os
import re
import json
import sklearn
from typing import Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.computation_engine import CostModel, PerformanceModel, ValueModel, ResultAssembler
from utils.calculation_engine import CalculationEngine
from utils.state_manager import get_state_manager

# 名称清洗辅助函数 (必须与 Phase 4 保持一致)
def sanitize_name(name):
    """
    清洗变量名或属性名，生成合法的 Python 标识符。
    """
    if not name:
        return "unknown"
    clean = re.sub(r'\W', '_', str(name))
    if clean and clean[0].isdigit():
        clean = '_' + clean
    return clean

# ========== Phase 5 UI Layout ==========

layout = dbc.Container([
    dcc.Store(id='phase5-unified-results-store', data=None),
    dcc.Store(id='global-selection-store', data={'selected_ids': []}, storage_type='session'),
    dcc.Store(id='phase5-model-source-store', data=None),
    dcc.Store(id='phase5-ui-state', data={}),

    html.H2([
        html.Span("🧮", className="me-2"),
        "Phase 5: 多域建模"
    ], className="mb-4"),

    # 动态模型状态提示
    html.Div(id="model-source-alert", className="mb-4"),

    # ===== 5.1 执行批量评估 =====
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("▶️", className="me-2"),
                    "5.1 执行批量评估"
                ], className="mb-0")),
                dbc.CardBody([
                    dbc.Button([
                        html.Span("▶️", className="me-2"),
                        "运行批量计算"
                    ], id="btn-run-evaluation", color="success", size="lg", className="w-100 mb-3"),
                    html.Div(id="evaluation-status")
                ])
            ], className="shadow-sm mb-4")
        ], md=12)
    ]),

    # ===== 5.2 计算结果统计 =====
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("5.2 计算结果统计", className="mb-0")),
                dbc.CardBody([
                    html.Div(id="evaluation-stats") # 这里将包含 Top 50 列表和统计摘要
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("5.3 性能分布可视化", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id="performance-distribution", figure=go.Figure())
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 回归模型拟合功能
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("5.4 敏感性分析 (Sensitivity Analysis)", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        html.Strong("系统工程定量方法："),
                        "识别关键设计变量（Critical Design Variables），量化每个变量对最终MAU值的影响程度",
                        html.Br(),
                        html.Small("使用龙卷风图直观展示变量的敏感性排序，帮助决策者优先关注高敏感性变量")
                    ], color="info", className="mb-3"),

                    dbc.Label("选择目标指标（Y）"),
                    dcc.Dropdown(
                        id='select-sensitivity-target',
                        options=[],
                        placeholder="选择目标指标 (通常为MAU)...",
                        className="mb-3"
                    ),

                    dbc.Label("选择分析变量（X）- 可多选"),
                    dcc.Dropdown(
                        id='select-sensitivity-vars',
                        options=[],
                        multi=True,
                        placeholder="选择要分析的设计变量...",
                        className="mb-3"
                    ),

                    dbc.Button([
                        html.Span("📊", className="me-2"),
                        "运行敏感性分析"
                    ], id='btn-run-sensitivity', color="primary", className='w-100 mb-3'),

                    html.Div(id='sensitivity-results', className="mb-3"),
                    
                    dcc.Graph(
                        id='sensitivity-tornado-plot',
                        figure=go.Figure(),
                        config={'displayModeBar': True},
                        style={'height': '500px'}
                    )
                ])
            ], className="shadow-sm mb-4")
        ], md=12),

        # 箱线图对比功能
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("5.5 箱线图分析", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "箱线图显示数据分布的五数概括"
                    ], color="info", className="mb-3"),

                    dbc.Label("选择指标"),
                    dbc.Select(
                        id='select-metric-boxplot',
                        options=[], # 动态填充
                        placeholder="选择要分析的指标...",
                        className="mb-3"
                    ),

                    dbc.Button([
                        html.Span("📊", className="me-2"),
                        "生成箱线图"
                    ], id='btn-create-boxplot', color="success", className='w-100 mb-3'),

                    dcc.Graph(id='box-whisker-plot', figure=go.Figure())
                ])
            ], className="shadow-sm mb-4")
        ], md=12)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("5.6 回归拟合可视化", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='regression-plot', figure=go.Figure(),
                             style={'height': '500px'})
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 性能分布统计增强
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("5.7 性能分布统计分析", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "深度统计分析：百分位数、相关性矩阵、异常值检测"
                    ], color="info", className="mb-3"),

                    dbc.Button([
                        html.Span("📊", className="me-2"),
                        "生成统计报告"
                    ], id='btn-generate-stats-report', color="success", className="w-100 mb-3"),

                    html.Div(id='stats-report-output')
                ])
            ], className="shadow-sm mb-4")
        ], md=12),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("5.8 指标相关性热图", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='correlation-heatmap', figure=go.Figure())
                ])
            ], className="shadow-sm mb-4")
        ], md=12)
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
                            "保存Phase 5数据"
                        ], id="btn-save-phase5", color="success", className="me-2"),
                        dbc.Button([
                            html.Span("📤", className="me-2"),
                            "加载Phase 5数据"
                        ], id="btn-load-phase5", color="info")
                    ]),
                    html.Div(id="phase5-save-status", className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button("上一步: Phase 4", href="/phase4", color="secondary", outline=True),
                dbc.Button("下一步: Phase 6", href="/phase6", color="primary")
            ], className="w-100")
        ])
    ])
], fluid=True)

@callback(
    [Output('evaluation-status', 'children'),
     Output('evaluation-stats', 'children'),
     Output('performance-distribution', 'figure'),
     Output('phase5-unified-results-store', 'data', allow_duplicate=True)],
    [Input('btn-run-evaluation', 'n_clicks')],
    prevent_initial_call=True
)
def run_batch_evaluation(n_clicks):
    """
    批量评估 - 修复版执行流
    """
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    try:
        import pandas as pd
        state = get_state_manager()
        
        # --- 1. 加载数据源 ---
        alternatives = state.load('phase3', 'alternatives')
        
        df_inputs = pd.DataFrame()
        if isinstance(alternatives, list):
            df_inputs = pd.DataFrame(alternatives)
        elif isinstance(alternatives, dict) and 'data' in alternatives:
            df_inputs = pd.DataFrame(alternatives['data'])
        elif isinstance(alternatives, pd.DataFrame):
            df_inputs = alternatives
            
        if df_inputs.empty:
             return dbc.Alert("❌ Phase 3 设计空间为空！请先在 Phase 3 生成数据。", color="warning"), no_update, {}, None

        # --- 2. 加载 Phase 4 定义的所有模型 ---
        perf_models_dict = state.load("phase4", "perf_models_dict") or {}
        utility_funcs_dict = state.load("phase4", "utility_functions_dict") or {}
        weights_mau_code = state.load("phase4", "weights_mau_code")

        if not weights_mau_code:
             return dbc.Alert(f"❌ Phase 4 MAU模型未定义，无法执行计算。", color="danger"), no_update, {}, None

        # --- 3. 编译执行环境 ---
        exec_ctx = {}
        
        try:
            for code in perf_models_dict.values():
                exec(code, exec_ctx)
            for code in utility_funcs_dict.values():
                exec(code, exec_ctx)
            exec(weights_mau_code, exec_ctx)
            
            if 'calculate_mau' not in exec_ctx: 
                raise ValueError("MAU 模型代码中缺少 'calculate_mau' 函数定义")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return dbc.Alert(f"❌ 代码编译错误: {str(e)}", color="danger"), no_update, {}, None

        # --- 4. 批量执行计算循环 ---
        results = []
        calc_mau = exec_ctx['calculate_mau']
        
        metric_funcs = {}
        for metric in perf_models_dict.keys():
            safe_metric = sanitize_name(metric)
            func_name = f"calculate_{safe_metric}"
            if func_name in exec_ctx:
                metric_funcs[metric] = exec_ctx[func_name]

        for idx, row in df_inputs.iterrows():
            row_context = {k: v for k, v in row.to_dict().items() if k != 'design_id'}
            
            # Step 4.1: 属性计算
            for metric, func in metric_funcs.items():
                try:
                    val = func(**row_context)
                    row_context[metric] = val
                except Exception as e:
                    row_context[metric] = 0.0
            
            # Step 4.2: MAU 计算
            try:
                mau_val = float(calc_mau(**row_context))
            except Exception as e:
                mau_val = 0.0
            
            row_context['MAU'] = mau_val
            
            if 'design_id' in row:
                row_context['design_id'] = row['design_id']
            else:
                row_context['design_id'] = idx
            
            results.append(row_context)

        # --- 5. 结果处理 ---
        unified_df = pd.DataFrame(results)
        unified_records = unified_df.to_dict('records')
        state.save('phase5', 'unified_results', unified_records)

        # --- 6. 生成 UI 反馈 ---
        status = dbc.Alert([
            html.H5(["✓", "计算完成"], className="alert-heading"),
            html.P(f"成功评估了 {len(unified_df)} 个设计方案。结果已保存。")
        ], color="success")

        # === 新增功能：5.2 数据预览列表 (Top 50) ===
        # 将 design_id 移到第一列
        cols = unified_df.columns.tolist()
        if 'design_id' in cols:
            cols.insert(0, cols.pop(cols.index('design_id')))
            preview_df = unified_df[cols].head(50) # 取前50行
        else:
            preview_df = unified_df.head(50)

        # 生成 Table Header
        table_header = [html.Th(col) for col in preview_df.columns]
        
        # 生成 Table Rows
        table_rows = []
        for i in range(len(preview_df)):
            row_cells = []
            for col in preview_df.columns:
                val = preview_df.iloc[i][col]
                # 格式化数值
                if isinstance(val, (int, float)):
                    display_val = f"{val:.4f}"
                else:
                    display_val = str(val)
                row_cells.append(html.Td(display_val))
            table_rows.append(html.Tr(row_cells))

        preview_table_component = html.Div([
            html.H6(f"数据预览 (前 {len(preview_df)} 条)", className="text-primary mt-2"),
            dbc.Table(
                [html.Thead(html.Tr(table_header)), html.Tbody(table_rows)],
                bordered=True, hover=True, striped=True, responsive=True, size='sm',
                style={'maxHeight': '400px', 'overflowY': 'auto'} # 增加滚动条
            ),
            html.Hr()
        ])

        # === 统计摘要表 ===
        numeric_cols = unified_df.select_dtypes(include=['float64', 'int64']).columns
        stats_cols = [c for c in numeric_cols if c != 'design_id']
        sorted_cols = ['MAU'] + [c for c in stats_cols if c != 'MAU']
        
        stats_rows = []
        for col in sorted_cols[:15]: 
            if col in unified_df.columns:
                series = unified_df[col]
                stats_rows.append(html.Tr([
                    html.Td(col),
                    html.Td(f"{series.min():.4f}"),
                    html.Td(f"{series.max():.4f}"),
                    html.Td(f"{series.mean():.4f}")
                ]))
        
        stats_summary_component = html.Div([
            html.H6("关键指标统计摘要", className="text-info"),
            dbc.Table([
                html.Thead(html.Tr([html.Th("指标"), html.Th("Min"), html.Th("Max"), html.Th("Mean")])),
                html.Tbody(stats_rows)
            ], bordered=True, hover=True, size='sm')
        ])

        # 组合 5.2 的输出内容
        stats_output_container = html.Div([
            preview_table_component,
            stats_summary_component
        ])

        # 分布图
        fig = make_subplots(rows=1, cols=2, subplot_titles=("MAU 分布", "属性分布示例"))
        fig.add_trace(go.Histogram(x=unified_df['MAU'], name='MAU', marker_color='green'), row=1, col=1)
        second_col = next((c for c in sorted_cols if c != 'MAU'), None)
        if second_col:
            fig.add_trace(go.Histogram(x=unified_df[second_col], name=second_col), row=1, col=2)
            fig.update_xaxes(title_text=second_col, row=1, col=2)
        else:
            fig.add_annotation(text="无其他属性", row=1, col=2, showarrow=False)
        fig.update_layout(height=400, showlegend=False, margin_l=20, margin_r=20, margin_t=40, margin_b=20)

        return status, stats_output_container, fig, unified_records

    except Exception as e:
        import traceback
        traceback.print_exc()
        error = dbc.Alert([
            html.H4("计算流程崩溃", className="alert-heading"),
            html.Pre(str(e))
        ], color="danger")
        return error, no_update, {}, None
    

# P1-1 回归模型拟合回调
@callback(
    [Output('sensitivity-results', 'children'),
     Output('sensitivity-tornado-plot', 'figure')],
    [Input('btn-run-sensitivity', 'n_clicks')],
    [State('select-sensitivity-target', 'value'),
     State('select-sensitivity-vars', 'value')],
    prevent_initial_call=True
)
def run_sensitivity_analysis(n_clicks, target_var, sensitivity_vars):
    """运行敏感性分析 - 识别关键设计变量"""
    if not n_clicks or not target_var or not sensitivity_vars:
        return dbc.Alert("请选择目标指标和分析变量！", color="warning"), go.Figure()

    try:
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

        valid_vars = [v for v in sensitivity_vars if v in unified.columns]
        if not valid_vars:
            return dbc.Alert("选择的分析变量都不存在", color="danger"), go.Figure()

        base_value = unified[target_var].mean()
        sensitivities = []

        for var in valid_vars:
            var_data = unified[var]
            target_data = unified[target_var]
            
            correlation = var_data.corr(target_data)
            std_ratio = (var_data.std() / (var_data.mean() + 1e-6)) if var_data.mean() != 0 else 0
            sensitivity_score = abs(correlation) * std_ratio
            
            sensitivities.append({
                'variable': var,
                'correlation': correlation,
                'std_ratio': std_ratio,
                'sensitivity': sensitivity_score,
                'impact': (var_data.max() - var_data.min()) * abs(correlation)
            })

        sensitivities.sort(key=lambda x: x['sensitivity'], reverse=True)

        results_card = dbc.Card([
            dbc.CardHeader(html.H5("敏感性分析结果", className="mb-0")),
            dbc.CardBody([
                html.P([
                    html.Strong("目标指标: "), target_var, html.Br(),
                    html.Strong("基准值: "), f"{base_value:.4f}", html.Br(),
                    html.Strong("分析变量数: "), len(valid_vars)
                ], className="mb-3"),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("变量名"),
                        html.Th("相关性"),
                        html.Th("标准差比"),
                        html.Th("敏感性得分"),
                        html.Th("影响范围")
                    ])),
                    html.Tbody([
                        html.Tr([
                            html.Td(s['variable']),
                            html.Td(f"{s['correlation']:.4f}"),
                            html.Td(f"{s['std_ratio']:.4f}"),
                            html.Td(f"{s['sensitivity']:.4f}"),
                            html.Td(f"{s['impact']:.4f}")
                        ]) for s in sensitivities
                    ])
                ], striped=True, bordered=True, hover=True, size='sm')
            ])
        ], color="light")

        fig = go.Figure()

        sorted_sensitivities = sorted(sensitivities, key=lambda x: x['sensitivity'], reverse=True)
        y_values = [s['variable'] for s in sorted_sensitivities]
        x_values = [s['sensitivity'] for s in sorted_sensitivities]

        colors = ['rgba(255, 0, 0, 0.7)' if s['sensitivity'] > np.median(x_values) else 'rgba(0, 128, 255, 0.7)' for s in sorted_sensitivities]

        fig.add_trace(go.Bar(
            x=x_values,
            y=y_values,
            orientation='h',
            marker=dict(color=colors),
            text=[f"{s['sensitivity']:.4f}" for s in sorted_sensitivities],
            textposition='outside',
            hovertemplate='%{y}<br>敏感性: %{x:.4f}<extra></extra>'
        ))

        fig.update_layout(
            title="龙卷风图 - 设计变量敏感性排序",
            xaxis_title="敏感性得分",
            yaxis_title="设计变量",
            height=400 + len(valid_vars) * 30,
            margin=dict(l=150, r=50, t=50, b=50)
        )

        return results_card, fig

    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"敏感性分析失败: {str(e)}", color="danger"), go.Figure()

# P1-2 箱线图生成回调
@callback(
    Output('box-whisker-plot', 'figure'),
    Input('btn-create-boxplot', 'n_clicks'),
    State('select-metric-boxplot', 'value'),
    prevent_initial_call=True
)
def create_box_whisker_plot(n_clicks, metric):
    """创建箱线图 (已修复硬编码)"""
    if not n_clicks or not metric:
        return no_update

    try:
        import pandas as pd
        state = get_state_manager()
        unified = state.load('phase5', 'unified_results')

        if unified is None:
             return go.Figure()
        
        if isinstance(unified, list): unified = pd.DataFrame(unified)
        
        if metric not in unified.columns:
             fig = go.Figure(); fig.update_layout(title=f"指标 {metric} 不存在"); return fig

        data = unified[metric]
        
        fig = go.Figure()
        fig.add_trace(go.Box(
            y=data, name=metric, boxmean='sd',
            marker=dict(color='rgb(107, 174, 214)'),
            line=dict(color='rgb(31, 119, 180)', width=2)
        ))

        fig.update_layout(
            title=f"{metric} 箱线图 (N={len(data)})",
            yaxis_title=metric,
            height=450,
            showlegend=False
        )
        return fig

    except Exception as e:
        fig = go.Figure(); fig.update_layout(title='错误: {}'.format(str(e))); return fig

# P2-7: 性能分布统计增强
@callback(
    [Output('stats-report-output', 'children'),
     Output('correlation-heatmap', 'figure')],
    [Input('btn-generate-stats-report', 'n_clicks')],
    prevent_initial_call=True
)
def generate_statistics_report(n_clicks):
    """生成深度统计分析报告 (修复 dbc.Div 报错)"""
    if not n_clicks:
        return no_update, no_update

    try:
        import pandas as pd
        state = get_state_manager()
        unified = state.load('phase5', 'unified_results')

        if unified is None:
            return dbc.Alert("请先运行计算！", color="warning"), go.Figure()
        
        if isinstance(unified, list): unified = pd.DataFrame(unified)
        if unified.empty: return dbc.Alert("数据为空", color="warning"), go.Figure()

        # 动态获取数值列
        numeric_df = unified.select_dtypes(include=['float64', 'int64'])
        metric_cols = [c for c in numeric_df.columns if c != 'design_id']
        
        if not metric_cols:
             return dbc.Alert("未检测到数值型指标", color="warning"), go.Figure()

        # 生成统计表
        percentiles = [10, 25, 50, 75, 90]
        percentile_rows = []
        
        for col in metric_cols:
            row = [html.Td(col)]
            for p in percentiles:
                row.append(html.Td(f"{unified[col].quantile(p/100):.3f}"))
            percentile_rows.append(html.Tr(row))

        percentile_table = dbc.Table([
            html.Thead(html.Tr([html.Th("指标")] + [html.Th(f"P{p}") for p in percentiles])),
            html.Tbody(percentile_rows)
        ], bordered=True, size='sm', striped=True, hover=True)

        # 尝试进行正态性检验 (依赖 scipy)
        normality_content = html.Div()
        try:
            from scipy import stats
            normality_rows = []
            for col in metric_cols:
                clean_series = unified[col].dropna()
                if len(clean_series) < 3: continue
                
                # 根据样本量选择检验方法
                if len(unified) < 5000:
                    stat, p_value = stats.shapiro(clean_series)
                else:
                    stat, p_value = stats.kstest(clean_series, 'norm')

                is_normal = p_value > 0.05
                normality_rows.append(html.Tr([
                    html.Td(col),
                    html.Td(f"{stat:.4f}"),
                    html.Td(f"{p_value:.4f}"),
                    html.Td(dbc.Badge(
                        "是" if is_normal else "否", 
                        color="success" if is_normal else "warning"
                    ))
                ]))
            
            if normality_rows:
                normality_table = dbc.Table([
                    html.Thead(html.Tr([html.Th("指标"), html.Th("统计量"), html.Th("P值"), html.Th("正态分布?")])),
                    html.Tbody(normality_rows)
                ], bordered=True, size='sm', striped=True)
                
                normality_content = html.Div([
                    html.H6("📈 正态性检验 (Shapiro-Wilk/KS)", className="mt-4"),
                    normality_table
                ])
        except ImportError:
            normality_content = html.Div("提示: 安装 scipy 库可查看正态性检验结果", className="text-muted small mt-2")

        # 相关性热图
        corr_matrix = unified[metric_cols].corr()
        corr_fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=metric_cols,
            y=metric_cols,
            colorscale='RdBu_r', zmid=0,
            text=corr_matrix.values, texttemplate='%{text:.2f}',
            colorbar=dict(title="Corr")
        ))
        corr_fig.update_layout(title="指标相关性矩阵", height=500 + len(metric_cols)*10)

        stats_report = html.Div([
            dbc.Alert([
                html.H5("统计分析摘要", className="alert-heading"),
                html.Hr(),
                html.H6("📊 百分位数分布"),
                percentile_table,
                normality_content
            ], color="light", className="border")
        ])

        return stats_report, corr_fig

    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert('生成失败: {}'.format(str(e)), color='danger'), go.Figure()

# 全局刷选响应
@callback(
    Output('performance-distribution', 'figure', allow_duplicate=True),
    Input('global-selection-store', 'data'),
    State('performance-distribution', 'figure'),
    prevent_initial_call=True
)
def highlight_phase5_selection(selection_data, current_figure):
    """在Phase 5性能分布图中高亮显示全局选中的设计"""
    if not selection_data or not current_figure:
        return no_update

    selected_ids = selection_data.get('selected_ids', [])
    if not selected_ids:
        return no_update

    try:
        state = get_state_manager()
        unified = state.load('phase5', 'unified_results')

        if unified is None or (isinstance(unified, pd.DataFrame) and unified.empty):
            return no_update

        import plotly.graph_objects as go
        fig = go.Figure(current_figure)

        fig.data = [trace for trace in fig.data if trace.name != 'Selected']

        selected_indices = [i for i in selected_ids if i < len(unified)]

        if selected_indices and len(fig.data) > 0:
            main_trace = fig.data[0]
            if hasattr(main_trace, 'x') and hasattr(main_trace, 'y'):
                selected_x = [main_trace.x[i] if i < len(main_trace.x) else None for i in selected_indices]
                selected_y = [main_trace.y[i] if i < len(main_trace.y) else None for i in selected_indices]

                valid_points = [(x, y) for x, y in zip(selected_x, selected_y) if x is not None and y is not None]

                if valid_points:
                    selected_x_clean, selected_y_clean = zip(*valid_points)
                    fig.add_trace(go.Scatter(
                        x=selected_x_clean,
                        y=selected_y_clean,
                        mode='markers',
                        name='Selected',
                        marker=dict(
                            size=15,
                            color='rgba(255,0,0,0.7)',
                            symbol='circle-open',
                            line=dict(width=3, color='red')
                        ),
                        hovertemplate='<b>选中设计 #%{text}</b><extra></extra>',
                        text=[str(i) for i in selected_indices]
                    ))

        fig.add_annotation(
            text=f"✓ 已选中 {len(selected_ids)} 个设计",
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            bgcolor="rgba(255,0,0,0.1)",
            bordercolor="red",
            borderwidth=2,
            font=dict(size=12, color="red"),
            align="left"
        )

        return fig

    except Exception as e:
        print(f"Phase 5全局刷选高亮失败: {e}")
        return no_update

# 模型来源检测
@callback(
    Output('model-source-alert', 'children'),
    Input('url', 'pathname'),
    prevent_initial_call=False
)
def display_model_source_status(pathname):
    """检测并显示当前使用的模型来源 (适配 Phase 4 统一模型存储架构)"""
    from dash import no_update
    
    if pathname != '/phase5':
        return no_update

    try:
        import pandas as pd
        state = get_state_manager()

        def _has_valid_data(data):
            if data is None: return False
            if isinstance(data, pd.DataFrame): return not data.empty
            if isinstance(data, dict): return len(data) > 0
            if isinstance(data, str): return len(data.strip()) > 0
            return bool(data)

        # [核心修改] Phase 4 已将所有属性计算（含成本）统一存入 perf_models_dict
        perf_models_dict = state.load('phase4', 'perf_models_dict')

        has_models = _has_valid_data(perf_models_dict)

        if has_models:
            model_names = list(perf_models_dict.keys())
            model_count = len(model_names)
            
            model_details = [
                f"✅ 已加载 {model_count} 个属性计算模型 (来自 Phase 4 4.1):",
                html.Br(),
                html.Span(", ".join(model_names), className="text-muted small")
            ]

            return dbc.Alert([
                html.H5([
                    "✓",
                    "模型加载就绪"
                ], className="alert-heading mb-3"),
                html.P([
                    html.Strong("当前模型状态:"), html.Br(),
                    *model_details
                ], className="mb-2"),
                html.Hr(),
                html.P([
                    html.Span("ℹ️", className="me-2"),
                    "如需修改计算逻辑，请返回 ",
                    html.A("Phase 4", href="/phase4", className="alert-link"),
                    " 进行编辑。"
                ], className="mb-0 small")
            ], color="success", className="mb-4")

        else:
            return dbc.Alert([
                html.H5([
                    "❌",
                    "未检测到计算模型"
                ], className="alert-heading mb-3"),
                html.P([
                    html.Strong("当前无法进行评估计算。"), html.Br(),
                    "系统未在 Phase 4 中检测到任何有效的属性计算模型（成本或性能）。"
                ], className="mb-2"),
                html.Hr(),
                html.P([
                    html.Span("➡️", className="me-2"),
                    "请前往 ",
                    html.A("Phase 4: 效用与偏好建模", href="/phase4", className="alert-link fw-bold"),
                    " (4.1 步骤) 定义计算逻辑并点击\"保存函数\"。"
                ], className="mb-0")
            ], color="danger", className="mb-4")

    except Exception as e:
        import traceback
        return dbc.Alert([
            "⚠️",
            f"模型状态检测失败: {str(e)}"
        ], color="danger", className="mb-4")