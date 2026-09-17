"""
Phase 7: 权衡空间探索
"""

from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import json
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.state_manager import get_state_manager

layout = dbc.Container([
    # 仅当Phase 7页面渲染时触发，替代全局URL触发
    dcc.Interval(id='phase7-autoloader', interval=500, max_intervals=1),

    # 全局刷选状态存储 (P0-3)
    dcc.Store(id='global-selection-store', data={'selected_ids': []}, storage_type='session'),

    #Phase 6 数据存储组件
    dcc.Store(id='phase6-feasible-store', data=[]),
    
    # Phase 7 核心数据存储
    dcc.Store(id='pareto-designs-store', data=[]),

    html.H2([
        html.Span("📈", className="me-2"),
        "Phase 7: 权衡空间探索"
    ], className="mb-4"),

    # 视图配置区域
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("7.1 视图配置 (ViewDataMapper)", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("视图名称"),
                    dbc.Input(id="input-view-name", placeholder="例如：cost_vs_resolution", className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("X轴字段"),
                            dbc.Select(id="select-x-field", className="mb-2")
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Y轴字段"),
                            dbc.Select(id="select-y-field", className="mb-2")
                        ], md=6)
                    ]),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("颜色字段"),
                            dbc.Select(id="select-color-field", className="mb-2")
                        ], md=6),
                        dbc.Col([
                            dbc.Label("尺寸字段"),
                            dbc.Select(id="select-size-field", className="mb-2")
                        ], md=6)
                    ]),

                    dbc.Button("创建视图", id="btn-create-view", color="primary", className="mt-2"),

                    html.Hr(),

                    dbc.Label("已创建的视图"),
                    html.Div(id="views-list", children=[
                        dbc.Alert("尚未创建视图", color="light")
                    ])
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("7.2 Pareto优化配置", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("选择优化目标"),
                    dbc.Checklist(
                        id="checklist-objectives",
                        options=[],
                        value=[],
                        className="mb-3"
                    ),

                    dbc.Label("优化方向"),
                    html.Div(id="objectives-directions"),

                    dbc.Label("ε-容差"),
                    dbc.Input(id="input-epsilon", type="number", value=0.0, min=0, max=0.1, step=0.01, className="mb-3"),

                    dbc.Button("识别Pareto前沿", id="btn-run-pareto", color="success")
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("7.3 多目标权衡决策支持", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        html.Strong("系统工程定量方法："),
                        "决策区域划分和偏好锥分析，支持多目标权衡决策",
                        html.Br(),
                        html.Small("通过决策空间可视化理解不同偏好的最优方案选择")
                    ], color="info", className="mb-3"),

                    dbc.Label("选择决策目标"),
                    dbc.Checklist(
                        id="checklist-decision-objectives",
                        options=[
                            {"label": "MAU效用值", "value": "MAU"},
                            {"label": "总成本 (M$)", "value": "总成本"},
                            {"label": "速度增量 (km/s)", "value": "速度增量"},
                            {"label": "服务能力", "value": "服务能力"}
                        ],
                        value=["MAU", "总成本"],
                        className="mb-3"
                    ),

                    dbc.Label("决策方法"),
                    dbc.RadioItems(
                        id="radio-decision-method",
                        options=[
                            {"label": "加权求和法", "value": "weighted"},
                            {"label": "ε-约束法", "value": "epsilon"},
                            {"label": "TOPSIS法", "value": "topsis"}
                        ],
                        value="weighted",
                        className="mb-3"
                    ),

                    dbc.Label("权重分配"),
                    html.Div(id="weight-sliders", children=[
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("MAU权重"),
                                dcc.Slider(id='slider-weight-mau', min=0, max=1, step=0.1, value=0.5, marks={round(i, 1): str(round(i, 1)) for i in [0, 0.2, 0.4, 0.6, 0.8, 1.0]}, className="mb-2")
                            ], md=6),
                            dbc.Col([
                                dbc.Label("成本权重"),
                                dcc.Slider(id='slider-weight-cost', min=0, max=1, step=0.1, value=0.5, marks={round(i, 1): str(round(i, 1)) for i in [0, 0.2, 0.4, 0.6, 0.8, 1.0]}, className="mb-2")
                            ], md=6)
                        ])
                    ]),

                    dbc.Label("偏好锥角度"),
                    dcc.Slider(
                        id='slider-preference-cone',
                        min=10,
                        max=90,
                        step=5,
                        value=45,
                        marks={i: str(i) + '°' for i in range(10, 91, 20)},
                        className="mb-3"
                    ),

                    dbc.Label("决策区域划分"),
                    dbc.RadioItems(
                        id="radio-decision-region",
                        options=[
                            {"label": "四象限划分", "value": "quadrant"},
                            {"label": "六区域划分", "value": "hexagon"},
                            {"label": "偏好锥划分", "value": "cone"}
                        ],
                        value="cone",
                        className="mb-3"
                    ),

                    dbc.Button([
                        html.Span("🎯", className="me-2"),
                        "生成决策支持分析"
                    ], id="btn-generate-decision-support", color="success", className="w-100 mb-3"),

                    html.Div(id='decision-support-results', className="mb-3"),
                    
                    dcc.Graph(
                        id='decision-support-plot',
                        figure=go.Figure(),
                        config={'displayModeBar': True},
                        style={'height': '600px'}
                    )
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
    ]),

    # 主要可视化区域
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("7.4 权衡空间可视化", className="mb-0 d-inline"),
                    dbc.ButtonGroup([
                        dbc.Button([html.Span("⬇️")], id="btn-download-chart", color="secondary", size="sm", outline=True),
                        dbc.Button([html.Span("⛶")], id="btn-fullscreen", color="secondary", size="sm", outline=True)
                    ], className="float-end")
                ]),
                dbc.CardBody([
                    dcc.Graph(
                        id="tradespace-plot",
                        figure=go.Figure(),
                        config={'displayModeBar': True},
                        style={'height': '600px'}
                    )
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # P2-9: 3D权衡空间可视化
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("7.4.1 3D权衡空间可视化 (P2-9)", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "使用3D散点图展示三个关键指标之间的权衡关系，支持交互式旋转和缩放"
                    ], color="info", className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("🔵 X轴指标"),
                            dbc.Select(
                                id='select-3d-x-axis',
                                options=[
                                    {'label': '总成本 (M$)', 'value': '总成本'},
                                    {'label': '覆盖范围 (°)', 'value': '覆盖范围'},
                                    {'label': '分辨率 (m)', 'value': '分辨率'},
                                    {'label': 'MAU效用值', 'value': 'MAU'},
                                    {'label': '发射功率 (W)', 'value': '发射功率'},
                                    {'label': '性价比', 'value': '性价比'}
                                ],
                                value='总成本',
                                className="mb-3"
                            ),
                        ], md=4),

                        dbc.Col([
                            dbc.Label("🟢 Y轴指标"),
                            dbc.Select(
                                id='select-3d-y-axis',
                                options=[
                                    {'label': '总成本 (M$)', 'value': '总成本'},
                                    {'label': '覆盖范围 (°)', 'value': '覆盖范围'},
                                    {'label': '分辨率 (m)', 'value': '分辨率'},
                                    {'label': 'MAU效用值', 'value': 'MAU'},
                                    {'label': '发射功率 (W)', 'value': '发射功率'},
                                    {'label': '性价比', 'value': '性价比'}
                                ],
                                value='覆盖范围',
                                className="mb-3"
                            ),
                        ], md=4),

                        dbc.Col([
                            dbc.Label("🔴 Z轴指标"),
                            dbc.Select(
                                id='select-3d-z-axis',
                                options=[
                                    {'label': '总成本 (M$)', 'value': '总成本'},
                                    {'label': '覆盖范围 (°)', 'value': '覆盖范围'},
                                    {'label': '分辨率 (m)', 'value': '分辨率'},
                                    {'label': 'MAU效用值', 'value': 'MAU'},
                                    {'label': '发射功率 (W)', 'value': '发射功率'},
                                    {'label': '性价比', 'value': '性价比'}
                                ],
                                value='MAU',
                                className="mb-3"
                            ),
                        ], md=4)
                    ]),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("颜色编码"),
                            dbc.Select(
                                id='select-3d-color',
                                options=[
                                    {'label': 'MAU效用值', 'value': 'MAU'},
                                    {'label': '总成本 (M$)', 'value': '总成本'},
                                    {'label': '覆盖范围 (°)', 'value': '覆盖范围'},
                                    {'label': '分辨率 (m)', 'value': '分辨率'},
                                    {'label': '性价比', 'value': '性价比'}
                                ],
                                value='MAU',
                                className="mb-3"
                            ),
                        ], md=6),

                        dbc.Col([
                            dbc.Label("数据来源"),
                            dbc.RadioItems(
                                id='radio-3d-data-source',
                                options=[
                                    {'label': 'Pareto最优设计', 'value': 'pareto'},
                                    {'label': '所有可行设计', 'value': 'feasible'},
                                    {'label': '所有设计（含不可行）', 'value': 'all'}
                                ],
                                value='pareto',
                                className="mb-3"
                            ),
                        ], md=6)
                    ]),

                    dbc.Button([
                        html.Span("📦", className="me-2"),
                        "生成3D权衡空间图"
                    ], id='btn-generate-3d-tradespace', color="primary", className="w-100 mb-3"),

                    dcc.Graph(
                        id='3d-tradespace-plot',
                        figure=go.Figure(),
                        config={'displayModeBar': True},
                        style={'height': '700px'}
                    )
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 散点图矩阵
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("7.5 散点图矩阵 (SPLOM)", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("选择维度（最多6个）"),
                    dbc.Checklist(id="checklist-splom-dims", options=[], value=[], className="mb-3"),
                    dbc.Button("生成SPLOM", id="btn-generate-splom", color="primary", className="mb-3"),
                    dcc.Graph(id="splom-plot", figure=go.Figure())
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 平行坐标图
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("7.6 平行坐标图 (Parallel Coordinates)", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("选择维度（建议7-10个）"),
                    dbc.Checklist(id="checklist-pcp-dims", options=[], value=[], className="mb-3"),

                    dbc.Label("颜色编码"),
                    dbc.Select(id="select-pcp-color", className="mb-3"),

                    dbc.Button("生成平行坐标图", id="btn-generate-pcp", color="primary", className="mb-3"),
                    dcc.Graph(id="pcp-plot", figure=go.Figure(), style={'height': '500px'})
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # Pareto前沿统计
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("7.7 Pareto前沿分析", className="mb-0")),
                dbc.CardBody([
                    html.Div(id="pareto-result-display", className="mb-3"),
                    
                    html.Div(id="pareto-stats", children=[
                        dbc.Table([
                            html.Thead([html.Tr([html.Th("指标"), html.Th("值")])]),
                            html.Tbody([
                                html.Tr([html.Td("Pareto最优设计数量"), html.Td("-", id="stat-pareto-count")]),
                                html.Tr([html.Td("占总设计比例"), html.Td("-", id="stat-pareto-ratio")]),
                                html.Tr([html.Td("支配层级"), html.Td("-", id="stat-dominance-layers")])
                            ])
                        ], bordered=True, striped=True)
                    ])
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("7.8 设计空间覆盖", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id="coverage-plot", figure=go.Figure(), style={'height': '200px'})
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
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
                            "保存Phase 7数据"
                        ], id="btn-save-phase7", color="success", className="me-2"),
                        dbc.Button([
                            html.Span("📤", className="me-2"),
                            "加载Phase 7数据"
                        ], id="btn-load-phase7", color="info")
                    ]),
                    html.Div(id="phase7-save-status", className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button("上一步: Phase 6", href="/phase6", color="secondary", outline=True),
                dbc.Button("下一步: Phase 8", href="/phase8", color="primary")
            ], className="w-100")
        ])
    ])
], fluid=True)


# ==================== 回调函数 ====================

# 7.1 视图配置 - 填充字段选项
@callback(
    [Output('select-x-field', 'options'),
     Output('select-y-field', 'options'),
     Output('select-color-field', 'options'),
     Output('select-size-field', 'options'),
     Output('select-x-field', 'value'),
     Output('select-y-field', 'value'),
     Output('select-color-field', 'value')],
    Input('phase6-feasible-store', 'data')
)
def populate_view_fields(feasible_data):
    """填充视图配置中的字段选项"""
    if not feasible_data:
        return [], [], [], [], None, None, None
    
    try:
        import pandas as pd
        
        if isinstance(feasible_data, list):
            df = pd.DataFrame(feasible_data)
        else:
            df = pd.DataFrame(feasible_data)
        
        if df.empty:
            return [], [], [], [], None, None, None
        
        # 提取数值型列作为可选字段
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        excluded = ['design_id', 'feasible', 'kills']
        numeric_cols = [col for col in numeric_cols if col not in excluded]
        
        # 列名映射到中文标签
        label_map = {
            'cost_total': '总成本 (M$)',
            'perf_coverage': '覆盖范围 (°)',
            'perf_resolution': '分辨率 (m)',
            'transmit_power': '发射功率 (W)',
            'MAU': 'MAU效用值',
            '总成本': '总成本 (M$)',
            '速度增量': '速度增量 (km/s)',
            '服务能力': '服务能力',
            '响应时间': '响应时间',
            '推进系统类型': '推进系统类型',
            '推进剂类型': '推进剂类型',
            '初始质量': '初始质量 (kg)',
            '载荷质量': '载荷质量 (kg)'
        }
        
        options = [
            {'label': label_map.get(col, col), 'value': col}
            for col in numeric_cols
        ]
        
        # 设置默认值
        default_x = '总成本' if '总成本' in numeric_cols else (numeric_cols[0] if numeric_cols else None)
        default_y = '覆盖范围' if '覆盖范围' in numeric_cols else (numeric_cols[1] if len(numeric_cols) > 1 else None)
        default_color = 'MAU' if 'MAU' in numeric_cols else None
        
        return options, options, options, options, default_x, default_y, default_color
        
    except Exception as e:
        print(f"填充视图字段选项失败: {e}")
        return [], [], [], [], None, None, None

# 7.2 Pareto优化配置 - 填充优化目标选项
@callback(
    [Output('checklist-objectives', 'options'),
     Output('objectives-directions', 'children')],
    Input('phase6-feasible-store', 'data')
)
def populate_objectives(feasible_data):
    """填充优化目标选项"""
    if not feasible_data:
        return [], html.P("请先完成Phase 6约束过滤", className="text-muted")
    
    try:
        import pandas as pd
        
        if isinstance(feasible_data, list):
            df = pd.DataFrame(feasible_data)
        else:
            df = pd.DataFrame(feasible_data)
        
        if df.empty:
            return [], html.P("无可用数据", className="text-muted")
        
        # 提取数值型列作为优化目标
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        excluded = ['design_id', 'feasible', 'kills']
        numeric_cols = [col for col in numeric_cols if col not in excluded]
        
        # 列名映射到中文标签
        label_map = {
            'cost_total': '总成本 (M$)',
            'perf_coverage': '覆盖范围 (°)',
            'perf_resolution': '分辨率 (m)',
            'transmit_power': '发射功率 (W)',
            'MAU': 'MAU效用值',
            '总成本': '总成本 (M$)',
            '速度增量': '速度增量 (km/s)',
            '服务能力': '服务能力',
            '响应时间': '响应时间'
        }
        
        options = [
            {'label': label_map.get(col, col), 'value': col}
            for col in numeric_cols
        ]
        
        # 生成优化方向说明
        directions = dbc.Row([
            dbc.Col([
                html.Small("💰 成本类指标: 越小越好 (Minimize)", className="text-muted")
            ], md=6),
            dbc.Col([
                html.Small("📈 性能类指标: 越大越好 (Maximize)", className="text-muted")
            ], md=6)
        ])
        
        return options, directions
        
    except Exception as e:
        print(f"填充优化目标选项失败: {e}")
        return [], html.P(f"加载失败: {e}", className="text-danger")

# 更新2D权衡图
@callback(
    Output('tradespace-plot', 'figure'), 
    [Input('select-x-field', 'value'),
     Input('select-y-field', 'value'),
     Input('select-color-field', 'value'),
     Input('select-size-field', 'value'),
     Input('phase6-feasible-store', 'data'),
     Input('global-selection-store', 'data'),
     Input('phase7-autoloader', 'n_intervals')]
)
def update_tradeoff_plot(x_field, y_field, color_field, size_field, feasible_data, selection_data, n_intervals):
    """更新2D散点图"""
    if not feasible_data or not x_field or not y_field:
        fig = go.Figure()
        fig.update_layout(
            title="请选择X轴和Y轴字段以生成图表",
            xaxis={'visible': False}, yaxis={'visible': False},
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig

    try:
        import pandas as pd
        import plotly.express as px
        
        # 1. 准备数据
        df = pd.DataFrame(feasible_data)
        
        # 处理全局选择状态
        selected_ids = selection_data.get('selected_ids', []) if selection_data else []
        df['selected'] = df['design_id'].apply(lambda x: 'Selected' if x in selected_ids else 'Normal')
        
        # 2. 生成图表
        color_arg = color_field if color_field else None
        size_arg = size_field if size_field else None
        
        # 检查列是否存在
        if x_field not in df.columns or y_field not in df.columns:
            fig = go.Figure()
            fig.update_layout(
                title=f"列不存在: {x_field} 或 {y_field}",
                xaxis={'visible': False}, yaxis={'visible': False}
            )
            return fig
        
        fig = px.scatter(
            df, 
            x=x_field, 
            y=y_field,
            color=color_arg,
            size=size_arg,
            hover_data=['design_id'],
            title=f"2D权衡分析: {x_field} vs {y_field}",
            template="plotly_white",
            opacity=0.7
        )
        
        # 高亮选中点
        if selected_ids:
            selected_df = df[df['design_id'].isin(selected_ids)]
            if not selected_df.empty:
                fig.add_trace(go.Scatter(
                    x=selected_df[x_field],
                    y=selected_df[y_field],
                    mode='markers',
                    marker_symbol='circle-open', marker_size=15, marker_color='red', marker_line_width=2,
                    name='已选中',
                    showlegend=False
                ))

        fig.update_layout(
            height=600,
            hovermode='closest',
            margin=dict(l=20, r=20, t=50, b=20)
        )

        return fig

    except Exception as e:
        import traceback
        print(f"生成2D权衡图失败: {e}")
        return go.Figure()

# P0-2功能：散点图矩阵 (SPLOM) - 维度填充
@callback(
    Output('checklist-splom-dims', 'options'),
    [Input('phase6-feasible-store', 'data'),
     Input('pareto-designs-store', 'data')]  # 当数据更新时触发
)
def populate_splom_dimensions(feasible_data, pareto_data):
    """填充SPLOM维度选项"""
    try:
        import pandas as pd

        # 优先使用 Pareto 设计数据
        data = pareto_data if pareto_data else feasible_data
        
        if not data:
            return []
            
        if isinstance(data, list):
            data = pd.DataFrame(data)

        # 提取数值型列作为可选维度
        numeric_cols = data.select_dtypes(include=['float64', 'int64']).columns.tolist()
        excluded = ['design_id', 'feasible', 'kills']
        numeric_cols = [col for col in numeric_cols if col not in excluded]

        label_map = {
            'cost_total': '总成本 (M$)',
            'perf_coverage': '覆盖范围 (°)',
            'perf_resolution': '分辨率 (m)',
            'transmit_power': '发射功率 (W)',
            'MAU': 'MAU效用值',
            '总成本': '总成本 (M$)',
            '覆盖范围': '覆盖范围 (°)',
            '分辨率': '分辨率 (m)',
            '发射功率': '发射功率 (W)',
            '性价比': '性价比',
            '速度增量': '速度增量 (km/s)',
            '服务能力': '服务能力',
            '响应时间': '响应时间',
            '推进系统类型': '推进系统类型',
            '推进剂类型': '推进剂类型',
            '初始质量': '初始质量 (kg)',
            '载荷质量': '载荷质量 (kg)'
        }

        options = [
            {'label': label_map.get(col, col), 'value': col}
            for col in numeric_cols[:10]  # 限制最多10个选项
        ]

        return options

    except Exception as e:
        print(f"填充SPLOM维度失败: {e}")
        return []

# 生成SPLOM图表
@callback(
    Output('splom-plot', 'figure'),
    [Input('btn-generate-splom', 'n_clicks'),
     Input('pareto-designs-store', 'data'),
     Input('phase6-feasible-store', 'data')],
    [State('checklist-splom-dims', 'value')],
    prevent_initial_call=False
)
def generate_splom(n_clicks, pareto_data, feasible_data, selected_dims):
    """生成散点图矩阵 (SPLOM)"""
    from dash import ctx
    import plotly.graph_objects as go
    
    # 只有在点击按钮或数据更新时才生成
    triggered_id = ctx.triggered_id
    if triggered_id not in ['btn-generate-splom', 'pareto-designs-store', 'phase6-feasible-store']:
        return go.Figure()
    
    # 如果是数据更新触发，但没有数据，返回空图
    if triggered_id in ['pareto-designs-store', 'phase6-feasible-store']:
        if not pareto_data and not feasible_data:
            return go.Figure()
    
    # 如果没有选择维度，自动选择前4个可用维度
    if not selected_dims:
        try:
            import pandas as pd
            data = pareto_data if pareto_data else feasible_data
            if not data:
                return go.Figure()
            if isinstance(data, list):
                data = pd.DataFrame(data)
            numeric_cols = data.select_dtypes(include=['float64', 'int64']).columns.tolist()
            excluded = ['design_id', 'feasible', 'kills']
            numeric_cols = [col for col in numeric_cols if col not in excluded]
            selected_dims = numeric_cols[:4] if len(numeric_cols) >= 4 else numeric_cols
        except:
            return go.Figure()
    
    if not selected_dims:
        return go.Figure()

    try:
        import pandas as pd
        import plotly.graph_objects as go

        state = get_state_manager()
        
        if pareto_data:
            pareto_designs = pareto_data
        elif feasible_data:
            pareto_designs = feasible_data
        else:
            pareto_designs = state.load('phase7', 'pareto_designs')
            if not pareto_designs:
                pareto_designs = state.load('phase6', 'feasible_designs')

        if not pareto_designs:
            return go.Figure()
            
        if isinstance(pareto_designs, dict) and 'data' in pareto_designs:
            pareto_designs = pd.DataFrame(pareto_designs['data'])
        elif isinstance(pareto_designs, list):
            pareto_designs = pd.DataFrame(pareto_designs)

        if len(selected_dims) > 6:
            selected_dims = selected_dims[:6]

        available_cols = [col for col in selected_dims if col in pareto_designs.columns]
        if not available_cols:
            return go.Figure()

        plot_data = pareto_designs[available_cols].copy()

        label_map = {
            'cost_total': '总成本',
            'perf_coverage': '覆盖',
            'perf_resolution': '分辨率',
            'transmit_power': '功率',
            'MAU': 'MAU',
            '总成本': '总成本',
            '覆盖范围': '覆盖',
            '分辨率': '分辨率',
            '发射功率': '功率',
            '性价比': '性价比',
            '速度增量': '速度增量',
            '服务能力': '服务能力',
            '响应时间': '响应时间'
        }

        dimensions = [
            dict(label=label_map.get(dim, dim), values=plot_data[dim])
            for dim in available_cols
        ]

        color_col = 'MAU' if 'MAU' in pareto_designs.columns else None

        fig = go.Figure(data=go.Splom(
            dimensions=dimensions,
            marker=dict(
                size=5,
                color=pareto_designs[color_col] if color_col else None,
                colorscale='Viridis',
                showscale=bool(color_col),
                line=dict(width=0.5, color='rgba(0,0,0,0.2)')
            ),
            diagonal_visible=False,
            showupperhalf=False
        ))

        fig.update_layout(
            title="散点图矩阵 (SPLOM)",
            height=150 * len(available_cols) + 100,
            width=150 * len(available_cols) + 100,
            hovermode='closest',
            dragmode='select'
        )

        return fig

    except Exception as e:
        print(f"生成SPLOM失败: {e}")
        return go.Figure()

# P0-3功能：全局刷选 (Global Brushing) 
@callback(
    Output('global-selection-store', 'data'),
    [Input('splom-plot', 'selectedData'),
     Input('tradespace-plot', 'selectedData')],
    prevent_initial_call=True
)
def update_global_selection(splom_selection, tradespace_selection):
    """更新全局选择状态"""
    from dash import ctx
    triggered_id = ctx.triggered_id
    selected_ids = []

    if triggered_id == 'splom-plot' and splom_selection:
        if 'points' in splom_selection:
            selected_ids = [p.get('pointIndex', p.get('pointNumber', -1)) for p in splom_selection['points']]
    elif triggered_id == 'tradespace-plot' and tradespace_selection:
        if 'points' in tradespace_selection:
            selected_ids = [p.get('pointIndex', p.get('pointNumber', -1)) for p in tradespace_selection['points']]

    selected_ids = [idx for idx in selected_ids if idx >= 0]
    source_val = str(triggered_id) if triggered_id else ''
    return {'selected_ids': list(selected_ids), 'source': source_val}

@callback(
    Output('splom-plot', 'figure', allow_duplicate=True),
    Input('global-selection-store', 'data'),
    State('splom-plot', 'figure'),
    State('checklist-splom-dims', 'value'),
    prevent_initial_call=True
)
def highlight_splom_selection(selection_data, current_figure, selected_dims):
    """在SPLOM中高亮显示"""
    if not selection_data or not current_figure:
        return no_update
    # 简化逻辑
    return no_update 

@callback(
    Output('tradespace-plot', 'figure', allow_duplicate=True),
    Input('global-selection-store', 'data'),
    State('tradespace-plot', 'figure'),
    prevent_initial_call=True
)
def highlight_tradespace_selection(selection_data, current_figure):
    """在主散点图中高亮显示"""
    return no_update

# 添加选择统计显示
@callback(
    Output('pareto-stats', 'children', allow_duplicate=True),
    Input('global-selection-store', 'data'),
    prevent_initial_call=True
)
def update_selection_stats(selection_data):
    """更新选择统计信息"""
    if not selection_data:
        return html.P("当前无选择", className="text-muted")

    selected_ids = selection_data.get('selected_ids', [])
    source = selection_data.get('source', '未知')

    if not selected_ids:
        return html.P("当前无选择", className="text-muted")

    return dbc.Alert([
        html.H6([html.Span("👆", className="me-2"), "全局刷选激活"], className="alert-heading"),
        html.Hr(),
        html.P([
            html.Strong("选中数量: "), f"{len(selected_ids)}", html.Br(),
            html.Strong("来源: "), source
        ]),
        dbc.Button([html.Span("✖️", className="me-2"), "清除"], id="btn-clear-selection", size="sm", color="secondary")
    ], color="info")

@callback(
    Output('global-selection-store', 'data', allow_duplicate=True),
    Input('btn-clear-selection', 'n_clicks'),
    prevent_initial_call=True
)
def clear_global_selection(n_clicks):
    if n_clicks: return {'selected_ids': [], 'source': 'manual_clear'}
    return no_update

# P1-3功能：平行坐标图维度填充
@callback(
    [Output('checklist-pcp-dims', 'options'),
     Output('select-pcp-color', 'options')],
    [Input('phase6-feasible-store', 'data'),
     Input('pareto-designs-store', 'data')]  # 当数据更新时触发
)
def populate_pcp_dimensions(feasible_data, pareto_data):
    """填充PCP维度选项"""
    try:
        import pandas as pd

        # 优先使用 Pareto 设计数据
        data = pareto_data if pareto_data else feasible_data
        
        if not data:
            return [], []
            
        if isinstance(data, list):
            data = pd.DataFrame(data)

        # 提取数值型列作为可选维度
        numeric_cols = data.select_dtypes(include=['float64', 'int64']).columns.tolist()
        excluded = ['design_id', 'feasible', 'kills']
        numeric_cols = [col for col in numeric_cols if col not in excluded]

        label_map = {
            'cost_total': '总成本 (M$)',
            'perf_coverage': '覆盖范围 (°)',
            'perf_resolution': '分辨率 (m)',
            'transmit_power': '发射功率 (W)',
            'MAU': 'MAU效用值',
            '总成本': '总成本 (M$)',
            '覆盖范围': '覆盖范围 (°)',
            '分辨率': '分辨率 (m)',
            '发射功率': '发射功率 (W)',
            '性价比': '性价比',
            '速度增量': '速度增量 (km/s)',
            '服务能力': '服务能力',
            '响应时间': '响应时间',
            '推进系统类型': '推进系统类型',
            '推进剂类型': '推进剂类型',
            '初始质量': '初始质量 (kg)',
            '载荷质量': '载荷质量 (kg)'
        }

        options = [
            {'label': label_map.get(col, col), 'value': col}
            for col in numeric_cols
        ]

        return options, options

    except Exception as e:
        print(f"填充PCP维度失败: {e}")
        return [], []

# 生成平行坐标图
@callback(
    Output('pcp-plot', 'figure'),
    Input('btn-generate-pcp', 'n_clicks'),
    [State('checklist-pcp-dims', 'value'),
     State('select-pcp-color', 'value')],
    prevent_initial_call=True
)
def generate_parallel_coordinates(n_clicks, selected_dims, color_metric):
    """生成平行坐标图"""
    if not n_clicks or not selected_dims:
        return go.Figure()

    try:
        import pandas as pd
        state = get_state_manager()
        pareto_designs = state.load('phase7', 'pareto_designs')
        
        if not pareto_designs:
            pareto_designs = state.load('phase6', 'feasible_designs')
            
        if not pareto_designs:
            return go.Figure()
            
        if isinstance(pareto_designs, list):
            pareto_designs = pd.DataFrame(pareto_designs)

        if len(selected_dims) > 10: selected_dims = selected_dims[:10]
        
        plot_data = pareto_designs[selected_dims].copy()
        
        dimensions = []
        for dim in selected_dims:
            dimensions.append(dict(
                label=dim,
                values=plot_data[dim],
                range=[plot_data[dim].min(), plot_data[dim].max()]
            ))

        fig = go.Figure(data=go.Parcoords(
            line=dict(
                color=pareto_designs[color_metric] if color_metric else 'blue',
                colorscale='Viridis' if color_metric else None,
                showscale=bool(color_metric)
            ),
            dimensions=dimensions
        ))
        
        fig.update_layout(title="平行坐标图", height=500)
        return fig

    except Exception as e:
        print(f"PCP生成失败: {e}")
        return go.Figure()

# ========== P2-9: 3D权衡空间可视化回调 ==========

@callback(
    Output('3d-tradespace-plot', 'figure'),
    [Input('btn-generate-3d-tradespace', 'n_clicks'),
     Input('pareto-designs-store', 'data'),
     Input('phase6-feasible-store', 'data')],
    [State('select-3d-x-axis', 'value'),
     State('select-3d-y-axis', 'value'),
     State('select-3d-z-axis', 'value'),
     State('select-3d-color', 'value'),
     State('radio-3d-data-source', 'value')],
    prevent_initial_call=False
)
def generate_3d_tradespace(n_clicks, pareto_data, feasible_data, x_axis, y_axis, z_axis, color_metric, data_source):
    """生成3D权衡空间可视化"""
    from dash import ctx
    
    # 只有在点击按钮或数据更新时才生成
    triggered_id = ctx.triggered_id
    if triggered_id not in ['btn-generate-3d-tradespace', 'pareto-designs-store', 'phase6-feasible-store']:
        return go.Figure()
    
    # 如果是数据更新触发，但没有数据，返回空图
    if triggered_id in ['pareto-designs-store', 'phase6-feasible-store']:
        if not pareto_data and not feasible_data:
            return go.Figure()
    
    try:
        import pandas as pd
        state = get_state_manager()

        if data_source == 'pareto':
            data = pareto_data if pareto_data else state.load('phase7', 'pareto_designs')
            label = 'Pareto设计'
        elif data_source == 'feasible':
            data = feasible_data if feasible_data else state.load('phase6', 'feasible_designs')
            label = '可行设计'
        else:
            data = state.load('phase5', 'unified_results')
            label = '所有设计'

        if not data:
            return go.Figure()
            
        if isinstance(data, list):
            data = pd.DataFrame(data)

        # 列名映射（兼容旧列名）
        col_mapping = {
            'cost_total': '总成本',
            'perf_coverage': '覆盖范围',
            'perf_resolution': '分辨率',
            'transmit_power': '发射功率',
            'cost_effectiveness': '性价比'
        }
        
        # 如果选择的是旧列名，映射到新列名
        x_axis = col_mapping.get(x_axis, x_axis)
        y_axis = col_mapping.get(y_axis, y_axis)
        z_axis = col_mapping.get(z_axis, z_axis)
        color_metric = col_mapping.get(color_metric, color_metric)
        
        required = [x_axis, y_axis, z_axis, color_metric]
        if not all(col in data.columns for col in required):
            return go.Figure()

        fig = go.Figure(data=[go.Scatter3d(
            x=data[x_axis],
            y=data[y_axis],
            z=data[z_axis],
            mode='markers',
            marker=dict(
                size=5,
                color=data[color_metric],
                colorscale='Viridis',
                colorbar=dict(title=color_metric),
                opacity=0.8
            ),
            text=data.index,
            hovertemplate='%{x}<br>%{y}<br>%{z}<extra></extra>'
        )])

        fig.update_layout(
            title=f"3D权衡空间 ({label})",
            scene=dict(xaxis_title=x_axis, yaxis_title=y_axis, zaxis_title=z_axis),
            height=700
        )
        return fig

    except Exception as e:
        print(f"3D图生成失败: {e}")
        return go.Figure()


# ===== 1. 自动保存 UI 状态 =====
@callback(
    Output('phase7-save-status', 'children', allow_duplicate=True),
    [Input('input-view-name', 'value'),
     Input('select-x-field', 'value'),
     Input('select-y-field', 'value'),
     Input('select-color-field', 'value'),
     Input('select-size-field', 'value'),
     Input('checklist-objectives', 'value'),
     Input('input-epsilon', 'value'),
     Input('select-3d-x-axis', 'value'),
     Input('select-3d-y-axis', 'value'),
     Input('select-3d-z-axis', 'value'),
     Input('select-3d-color', 'value'),
     Input('radio-3d-data-source', 'value'),
     Input('checklist-splom-dims', 'value'),
     Input('checklist-pcp-dims', 'value'),
     Input('select-pcp-color', 'value')],
    prevent_initial_call=True
)
def auto_save_phase7_ui(view_name, x_axis, y_axis, color_field, size_field, 
                       objectives, epsilon,
                       x3d, y3d, z3d, c3d, src3d, splom_dims, pcp_dims, pcp_color):
    """
    自动保存所有视图配置控件的状态
    """
    from dash import ctx
    if not ctx.triggered: return no_update
    
    state = get_state_manager()
    current_ui = state.load('phase7', 'ui_state') or {}
    
    current_ui.update({
        'view_name': view_name,
        'x_axis': x_axis, 'y_axis': y_axis,
        'color_field': color_field, 'size_field': size_field,
        'pareto_objectives': objectives, 'epsilon': epsilon,
        'x_axis_3d': x3d, 'y_axis_3d': y3d, 'z_axis_3d': z3d, 
        'color_field_3d': c3d, 'data_source_3d': src3d,
        'splom_dims': splom_dims, 'pcp_dims': pcp_dims, 'pcp_color': pcp_color
    })
    
    state.save('phase7', 'ui_state', current_ui)
    return no_update

# ===== 2. 手动保存 Phase 7 数据 =====
@callback(
    Output('phase7-save-status', 'children', allow_duplicate=True),
    Input('btn-save-phase7', 'n_clicks'),
    [State('pareto-designs-store', 'data'),
     State('input-view-name', 'value'),
     State('select-x-field', 'value'),
     State('select-y-field', 'value'),
     State('select-color-field', 'value'),
     State('select-size-field', 'value'),
     State('checklist-objectives', 'value'),
     State('input-epsilon', 'value'),
     State('select-3d-x-axis', 'value'),
     State('select-3d-y-axis', 'value'),
     State('select-3d-z-axis', 'value'),
     State('select-3d-color', 'value'),
     State('radio-3d-data-source', 'value'),
     State('checklist-splom-dims', 'value'),
     State('checklist-pcp-dims', 'value'),
     State('select-pcp-color', 'value')],
    prevent_initial_call=True
)
def save_phase7_data(n_clicks, pareto_data, view_name, x_axis, y_axis, color_field, size_field,
                    objectives, epsilon,
                    x3d, y3d, z3d, c3d, src3d, splom_dims, pcp_dims, pcp_color):
    """
    手动保存 Phase 7 所有数据
    """
    if not n_clicks: return no_update
    
    state = get_state_manager()
    
    # 1. 保存 Core Data (如果有)
    if pareto_data:
        state.save('phase7', 'pareto_designs', pareto_data)
        
    # 2. 保存 UI State
    ui_state = {
        'view_name': view_name,
        'x_axis': x_axis, 'y_axis': y_axis,
        'color_field': color_field, 'size_field': size_field,
        'pareto_objectives': objectives, 'epsilon': epsilon,
        'x_axis_3d': x3d, 'y_axis_3d': y3d, 'z_axis_3d': z3d, 
        'color_field_3d': c3d, 'data_source_3d': src3d,
        'splom_dims': splom_dims, 'pcp_dims': pcp_dims, 'pcp_color': pcp_color
    }
    state.save('phase7', 'ui_state', ui_state)
    
    return dbc.Alert([
        "✓",
        "Phase 7 数据与视图配置已保存"
    ], color="success")



@callback(
    [Output('pareto-result-display', 'children'),
     Output('pareto-designs-store', 'data', allow_duplicate=True)],
    [Input('btn-run-pareto', 'n_clicks')],
    [State('checklist-objectives', 'value'),
     State('input-epsilon', 'value'),
     State('phase6-feasible-store', 'data')], 
    prevent_initial_call=True
)
def run_pareto_analysis(n_clicks, objectives, epsilon, feasible_data):
    """
    执行帕累托分析并保存结果
    """
    if not n_clicks:
        return no_update, no_update

    try:
        import pandas as pd
        
        # 1. 准备数据
        state = get_state_manager()
        
        # 如果前端 Store 没数据，尝试从 StateManager 加载 Phase 6 数据
        if not feasible_data:
            feasible_data = state.load('phase6', 'feasible_designs')
            
        def _to_df(data):
            if data is None: return pd.DataFrame()
            if isinstance(data, pd.DataFrame): return data
            if isinstance(data, list): return pd.DataFrame(data)
            if isinstance(data, dict) and 'data' in data: return pd.DataFrame(data['data'])
            return pd.DataFrame()

        df = _to_df(feasible_data)

        if df.empty:
            return dbc.Alert("数据不足: 请先在 Phase 6 完成约束过滤。", color="warning"), no_update

        if not objectives or len(objectives) < 2:
            return dbc.Alert("请至少选择 2 个优化目标。", color="warning"), no_update

        # 2. 执行计算 (简单的帕累托过滤逻辑示例)
        # 假设所有目标都是"越小越好" (Minimize)，如果有些是Maximize需要预处理
        # 这里为了演示，使用简单的非支配排序逻辑
        subset = df[objectives].copy()
        
        # 简单的 O(N^2) 帕累托过滤 (生产环境建议使用 pymoo 或 pareto.py)
        is_efficient = lambda row: not any(
            all(r <= row[objectives]) and any(r < row[objectives])
            for _, r in subset.iterrows()
        )
        # 注意：这里仅为演示，实际计算量大时需优化
        mask = subset.apply(is_efficient, axis=1)
        pareto_front = df[mask].to_dict('records')
        dominated = df[~mask].to_dict('records')

        # 3. [Core Data] 立即持久化
        analysis_result = {
            'pareto_front': pareto_front,
            'dominated_solutions': dominated,
            'objectives': objectives,
            'epsilon': epsilon
        }
        
        # 保存到 StateManager
        state.save('phase7', 'pareto_analysis', analysis_result)
        # 同时更新 Store 供前端绘图使用
        state.save('phase7', 'pareto_designs', pareto_front) # 冗余存储方便前端直接取用

        # 4. 生成报告
        report = dbc.Alert([
            html.H5([html.Span("🏆", className="me-2"), "帕累托分析完成"], className="alert-heading"),
            html.Hr(),
            html.P([
                html.Strong("非支配解数量: "), f"{len(pareto_front)}", html.Br(),
                html.Strong("被支配解数量: "), f"{len(dominated)}", html.Br(),
                html.Strong("优化目标: "), ", ".join(objectives)
            ])
        ], color="success")

        return report, pareto_front

    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"分析失败: {str(e)}", color="danger"), no_update


@callback(
    [Output('phase6-feasible-store', 'data', allow_duplicate=True), 
     Output('pareto-designs-store', 'data', allow_duplicate=True), 
     Output('input-view-name', 'value'),
     Output('select-size-field', 'value'),
     Output('checklist-objectives', 'value'),
     Output('input-epsilon', 'value'),
     Output('select-3d-x-axis', 'value'),
     Output('select-3d-y-axis', 'value'),
     Output('select-3d-z-axis', 'value'),
     Output('select-3d-color', 'value'),
     Output('radio-3d-data-source', 'value'),
     Output('checklist-splom-dims', 'value'),
     Output('checklist-pcp-dims', 'value'),
     Output('select-pcp-color', 'value'),
     Output('phase7-save-status', 'children', allow_duplicate=True)],
    [Input('btn-load-phase7', 'n_clicks'),
     Input('phase7-autoloader', 'n_intervals')], 
    prevent_initial_call=True
)
def load_phase7_data(n_clicks, n_intervals):
    """
    统一加载：恢复输入数据、分析结果和视图配置
    """
    from dash import ctx
    
    # 逻辑：点击按钮 或 页面加载(Interval触发)
    triggered_id = ctx.triggered_id
    
    # 如果没有触发源（初始加载）或不是这两个ID触发的，直接返回
    if not triggered_id:
        return tuple([no_update] * 15)

    try:
        state = get_state_manager()
        
        # 1. 恢复 Phase 6 输入数据 (关键依赖)
        feasible_data = state.load('phase6', 'feasible_designs')
        final_feasible = []
        if feasible_data is not None:
            if isinstance(feasible_data, dict) and 'data' in feasible_data:
                final_feasible = feasible_data['data']
            elif hasattr(feasible_data, 'to_dict'):
                final_feasible = feasible_data.to_dict('records')
            elif isinstance(feasible_data, list):
                final_feasible = feasible_data

        # 2. 恢复 Phase 7 分析结果
        pareto_designs = state.load('phase7', 'pareto_designs')
        final_pareto = []
        if pareto_designs:
             if isinstance(pareto_designs, list): final_pareto = pareto_designs
             elif hasattr(pareto_designs, 'to_dict'): final_pareto = pareto_designs.to_dict('records')

        # 3. 恢复 UI State
        ui = state.load('phase7', 'ui_state') or {}
        
        # 4. 生成状态提示
        status_msg = no_update
        # 只有在明确点击按钮时才显示"加载成功"的提示，自动加载保持静默（或根据需求显示）
        if triggered_id == 'btn-load-phase7' or (n_intervals and n_intervals > 0):
            msg = []
            if final_feasible: msg.append(f"输入数据({len(final_feasible)})")
            if final_pareto: msg.append(f"帕累托解({len(final_pareto)})")
            
            if msg:
                status_msg = dbc.Alert([
                    "✓",
                    f"数据已同步: {' + '.join(msg)}"
                ], color="success")
            elif triggered_id == 'btn-load-phase7':
                status_msg = dbc.Alert("未找到相关数据，请先完成前序步骤", color="warning")

        # 返回所有 Output
        return (
            final_feasible or no_update,
            final_pareto or no_update,
            ui.get('view_name', ''),
            ui.get('size_field') if 'size_field' in ui else None,
            ui.get('pareto_objectives', []),
            ui.get('epsilon', 0.0),
            ui.get('x_axis_3d', '总成本'),
            ui.get('y_axis_3d', '覆盖范围'),
            ui.get('z_axis_3d', 'MAU'),
            ui.get('color_field_3d', 'MAU'),
            ui.get('data_source_3d', 'pareto'),
            ui.get('splom_dims', []),
            ui.get('pcp_dims', []),
            ui.get('pcp_color', 'MAU'),
            status_msg
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        error = dbc.Alert(f"加载异常: {str(e)}", color="danger")
        return tuple([no_update] * 15) + (error,)

# 更新Pareto统计信息
@callback(
    [Output('stat-pareto-count', 'children'),
     Output('stat-pareto-ratio', 'children'),
     Output('stat-dominance-layers', 'children')],
    [Input('pareto-designs-store', 'data'),
     Input('phase6-feasible-store', 'data')]
)
def update_pareto_stats(pareto_data, feasible_data):
    """更新Pareto前沿统计信息"""
    try:
        if not pareto_data:
            return "-", "-", "-"
        
        pareto_count = len(pareto_data) if isinstance(pareto_data, list) else len(pareto_data.get('data', []))
        
        total_count = 0
        if feasible_data:
            total_count = len(feasible_data) if isinstance(feasible_data, list) else len(feasible_data.get('data', []))
        
        ratio = f"{pareto_count/total_count:.1%}" if total_count > 0 else "-"
        
        return pareto_count, ratio, "2层 (Pareto + Dominated)"
        
    except Exception as e:
        print(f"更新Pareto统计失败: {e}")
        return "-", "-", "-"

# 更新设计空间覆盖图
@callback(
    Output('coverage-plot', 'figure'),
    [Input('pareto-designs-store', 'data'),
     Input('phase6-feasible-store', 'data')]
)
def update_coverage_plot(pareto_data, feasible_data):
    """更新设计空间覆盖可视化"""
    try:
        import plotly.graph_objects as go
        
        if not feasible_data:
            fig = go.Figure()
            fig.update_layout(
                title="无数据",
                xaxis={'visible': False}, yaxis={'visible': False},
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            return fig
        
        total_count = len(feasible_data) if isinstance(feasible_data, list) else len(feasible_data.get('data', []))
        pareto_count = len(pareto_data) if isinstance(pareto_data, list) else len(pareto_data.get('data', []))
        
        fig = go.Figure(data=[
            go.Bar(
                x=['可行设计', 'Pareto最优'],
                y=[total_count, pareto_count],
                marker_color=['#636EFA', '#00CC96'],
                text=[total_count, pareto_count],
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title="设计空间覆盖统计",
            yaxis_title="数量",
            showlegend=False,
            height=200,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return fig
        
    except Exception as e:
        print(f"更新覆盖图失败: {e}")
        return go.Figure()

# 创建视图功能
@callback(
    Output('views-list', 'children'),
    [Input('btn-create-view', 'n_clicks')],
    [State('input-view-name', 'value'),
     State('select-x-field', 'value'),
     State('select-y-field', 'value'),
     State('select-color-field', 'value'),
     State('select-size-field', 'value')],
    prevent_initial_call=True
)
def create_view(n_clicks, view_name, x_field, y_field, color_field, size_field):
    """创建并保存自定义视图"""
    if not n_clicks or not view_name:
        return dbc.Alert("请输入视图名称", color="warning")
    
    try:
        state = get_state_manager()
        views = state.load('phase7', 'saved_views') or {}
        
        views[view_name] = {
            'x_field': x_field,
            'y_field': y_field,
            'color_field': color_field,
            'size_field': size_field
        }
        
        state.save('phase7', 'saved_views', views)
        
        return dbc.Alert([
            "✓",
            f"视图 '{view_name}' 已创建"
        ], color="success")
        
    except Exception as e:
        return dbc.Alert(f"创建视图失败: {e}", color="danger")

# 更新图表功能
@callback(
    Output('tradespace-plot', 'figure', allow_duplicate=True),
    Input('btn-update-chart', 'n_clicks'),
    [State('select-x-field', 'value'),
     State('select-y-field', 'value'),
     State('select-color-field', 'value'),
     State('select-size-field', 'value'),
     State('phase6-feasible-store', 'data')],
    prevent_initial_call=True
)
def update_chart_with_options(n_clicks, x_field, y_field, color_field, size_field, 
                            feasible_data):
    """根据可视化选项更新图表"""
    if not n_clicks:
        return no_update
    
    try:
        import pandas as pd
        import plotly.express as px
        
        if not feasible_data or not x_field or not y_field:
            return go.Figure()
        
        df = pd.DataFrame(feasible_data)
        
        if x_field not in df.columns or y_field not in df.columns:
            return go.Figure()
        
        fig = px.scatter(
            df, 
            x=x_field, 
            y=y_field,
            color=color_field if color_field in df.columns else None,
            size=size_field if size_field in df.columns else None,
            hover_data=['design_id'],
            title=f"权衡分析: {x_field} vs {y_field}",
            template="plotly_white",
            opacity=0.7
        )
        
        show_grid = 'grid' in viz_options
        show_legend = 'legend' in viz_options
        
        fig.update_layout(
            height=600,
            hovermode='closest',
            showlegend=show_legend,
            xaxis_showgrid=show_grid,
            yaxis_showgrid=show_grid,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        
        return fig
        
    except Exception as e:
        print(f"更新图表失败: {e}")
        return go.Figure()

# 下载图表功能
@callback(
    Output('tradespace-plot', 'figure', allow_duplicate=True),
    Input('btn-download-chart', 'n_clicks'),
    State('tradespace-plot', 'figure'),
    prevent_initial_call=True
)
def download_chart(n_clicks, figure):
    """下载当前图表"""
    if not n_clicks or not figure:
        return no_update
    
    try:
        import plotly.io as pio
        import os
        
        # 创建下载目录
        download_dir = os.path.join(os.path.dirname(__file__), '..', 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        
        # 保存图表
        filepath = os.path.join(download_dir, f'tradespace_plot_{n_clicks}.png')
        pio.write_image(figure, filepath)
        
        return figure
        
    except Exception as e:
        print(f"下载图表失败: {e}")
        return figure

# 全屏功能
@callback(
    Output('tradespace-plot', 'style', allow_duplicate=True),
    Input('btn-fullscreen', 'n_clicks'),
    State('tradespace-plot', 'style'),
    prevent_initial_call=True
)
def toggle_fullscreen(n_clicks, current_style):
    """切换图表全屏模式"""
    if not n_clicks:
        return no_update
    
    if current_style and current_style.get('height') == '90vh':
        return {'height': '600px'}
    else:
        return {'height': '90vh', 'position': 'fixed', 'top': '0', 'left': '0', 'right': '0', 'zIndex': '9999', 'background': 'white'}


# P1-5功能：多目标权衡决策支持
@callback(
    [Output('decision-support-results', 'children'),
     Output('decision-support-plot', 'figure')],
    Input('btn-generate-decision-support', 'n_clicks'),
    [State('checklist-decision-objectives', 'value'),
     State('radio-decision-method', 'value'),
     State('slider-weight-mau', 'value'),
     State('slider-weight-cost', 'value'),
     State('slider-preference-cone', 'value'),
     State('radio-decision-region', 'value')],
    prevent_initial_call=True
)
def generate_decision_support(n_clicks, objectives, method, weight_mau, weight_cost, cone_angle, region_type):
    """生成多目标权衡决策支持分析"""
    if not n_clicks or not objectives or len(objectives) < 2:
        return dbc.Alert("请至少选择两个决策目标！", color="warning"), go.Figure()

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

        valid_objectives = [obj for obj in objectives if obj in unified.columns]
        if len(valid_objectives) < 2:
            return dbc.Alert("选择的目标指标不存在", color="danger"), go.Figure()

        obj1, obj2 = valid_objectives[0], valid_objectives[1]
        
        x_data = unified[obj1].values
        y_data = unified[obj2].values

        x_mean, y_mean = np.mean(x_data), np.mean(y_data)
        x_std, y_std = np.std(x_data), np.std(y_data)

        normalized_x = (x_data - x_mean) / (x_std + 1e-6)
        normalized_y = (y_data - y_mean) / (y_std + 1e-6)

        if method == 'weighted':
            decision_scores = weight_mau * normalized_x + weight_cost * normalized_y
        elif method == 'epsilon':
            threshold = np.percentile(normalized_x, 75)
            decision_scores = np.where(normalized_x >= threshold, normalized_y, -np.inf)
        else:
            ideal_point = np.array([np.max(normalized_x), np.max(normalized_y)])
            negative_ideal = np.array([np.min(normalized_x), np.min(normalized_y)])
            
            distances_to_ideal = np.sqrt(np.sum((np.column_stack([normalized_x, normalized_y]) - ideal_point) ** 2, axis=1))
            distances_to_negative = np.sqrt(np.sum((np.column_stack([normalized_x, normalized_y]) - negative_ideal) ** 2, axis=1))
            decision_scores = distances_to_negative / (distances_to_ideal + distances_to_negative + 1e-6)

        best_idx = np.argmax(decision_scores)
        best_design = unified.iloc[best_idx]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=x_data,
            y=y_data,
            mode='markers',
            name='设计方案',
            marker=dict(
                size=8,
                color=decision_scores,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='决策得分')
            ),
            text=[f"设计ID: {i}<br>{obj1}: {x:.2f}<br>{obj2}: {y:.2f}<br>得分: {s:.3f}" 
                  for i, x, y, s in zip(range(len(x_data)), x_data, y_data, decision_scores)],
            hovertemplate='%{text}<extra></extra>'
        ))

        fig.add_trace(go.Scatter(
            x=[x_data[best_idx]],
            y=[y_data[best_idx]],
            mode='markers',
            name='最优方案',
            marker=dict(size=20, color='red', symbol='star', line=dict(width=2, color='white'))
        ))

        if region_type == 'quadrant':
            fig.add_vline(x=x_mean, line_dash="dash", line_color="gray", annotation_text="均值X")
            fig.add_hline(y=y_mean, line_dash="dash", line_color="gray", annotation_text="均值Y")
        elif region_type == 'hexagon':
            for angle in range(0, 360, 60):
                rad = np.radians(angle)
                fig.add_shape(type="line",
                             x0=x_mean, y0=y_mean,
                             x1=x_mean + np.cos(rad) * x_std * 2,
                             y1=y_mean + np.sin(rad) * y_std * 2,
                             line=dict(color="gray", dash="dot"))
        elif region_type == 'cone':
            cone_rad = np.radians(cone_angle)
            cone_length = max(x_std, y_std) * 3
            
            fig.add_shape(type="line",
                         x0=x_mean, y0=y_mean,
                         x1=x_mean + np.cos(cone_rad) * cone_length,
                         y1=y_mean + np.sin(cone_rad) * cone_length,
                         line=dict(color="red", dash="dash", width=2))
            
            fig.add_shape(type="line",
                         x0=x_mean, y0=y_mean,
                         x1=x_mean + np.cos(-cone_rad) * cone_length,
                         y1=y_mean + np.sin(-cone_rad) * cone_length,
                         line=dict(color="red", dash="dash", width=2))

        fig.update_layout(
            title=f"多目标权衡决策支持: {obj1} vs {obj2}<br><sub>方法: {method} | 偏好锥角度: {cone_angle}°</sub>",
            xaxis_title=obj1,
            yaxis_title=obj2,
            height=600,
            hovermode='closest',
            showlegend=True
        )

        results_html = dbc.Card([
            dbc.CardBody([
                html.H5("决策支持分析结果", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Strong("决策方法:"),
                        html.P({
                            'weighted': '加权求和法',
                            'epsilon': 'ε-约束法',
                            'topsis': 'TOPSIS法'
                        }.get(method, method), className="mb-0"),
                    ], md=4),
                    dbc.Col([
                        html.Strong("决策区域:"),
                        html.P({
                            'quadrant': '四象限划分',
                            'hexagon': '六区域划分',
                            'cone': '偏好锥划分'
                        }.get(region_type, region_type), className="mb-0"),
                    ], md=4),
                    dbc.Col([
                        html.Strong("偏好锥角度:"),
                        html.P(f"{cone_angle}°", className="mb-0"),
                    ], md=4),
                ], className="mb-3"),
                html.H6("推荐最优方案:", className="mb-2"),
                dbc.Table([
                    html.Thead([
                        html.Tr([
                            html.Th("指标"),
                            html.Th("值")
                        ])
                    ]),
                    html.Tbody([
                        html.Tr([html.Td("设计ID"), html.Td(str(best_idx))]),
                        html.Tr([html.Td(obj1), html.Td(f"{best_design[obj1]:.4f}")]),
                        html.Tr([html.Td(obj2), html.Td(f"{best_design[obj2]:.4f}")]),
                        html.Tr([html.Td("决策得分"), html.Td(f"{decision_scores[best_idx]:.4f}")])
                    ])
                ], striped=True, bordered=True, hover=True, size="sm"),
                html.P([
                    html.Strong("决策建议: "),
                    "该方案在当前决策方法和偏好设置下表现最优，建议作为首选方案。"
                ], className="mt-3 mb-0")
            ])
        ], className="shadow-sm")

        return results_html, fig

    except Exception as e:
        import traceback
        print(f"决策支持分析失败: {e}")
        print(traceback.format_exc())

        fig = go.Figure()
        fig.add_annotation(
            text=f"分析失败: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        return dbc.Alert(f"分析失败: {str(e)}", color="danger"), fig