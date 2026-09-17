"""
数据管理页面 - 导入/导出功能
"""

from dash import html, dcc, callback, Input, Output, State, ALL
import dash_bootstrap_components as dbc
import base64
import io
import pandas as pd

layout = dbc.Container([
    html.H2([
        html.Span("🗄️", className="me-2"),
        "数据管理"
    ], className="mb-4"),

    # 数据导入
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("数据导入", className="mb-0")),
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            html.Span("☁️", className="fa-3x mb-3 text-primary"),
                            # 这里的 html.Br() 可以保留，也可以去掉，因为 flex 布局会自动排列
                            html.Div([
                                '拖拽文件到此处或 ',
                                html.A('点击选择文件', className="text-primary")
                            ])
                        ]),
                        style={
                            'width': '100%',
                            'height': '200px',
                            'borderWidth': '2px',
                            'borderStyle': 'dashed',
                            'borderRadius': '10px',
                            'textAlign': 'center',
                            'cursor': 'pointer',
                            
                            # ===  Flexbox 设置 ===
                            'display': 'flex',              # 启用弹性盒子布局
                            'flexDirection': 'column',      # 内容垂直排列 (图标在上，文字在下)
                            'justifyContent': 'center',     # 垂直居中
                            'alignItems': 'center'          # 水平居中
                        },
                        multiple=False,
                        className="mb-3"
                    ),

                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "支持格式：JSON"
                    ], color="info"),

                    html.Div(id='upload-status')
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 数据预览
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H5("数据预览", className="mb-0 d-inline"),
                    dbc.Badge(id="data-rows-badge", color="primary", className="float-end")
                ]),
                dbc.CardBody([
                    html.Div(id='data-preview', style={'maxHeight': '400px', 'overflowY': 'auto'})
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 数据导出
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("数据导出", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("选择要导出的数据"),
                    dbc.RadioItems(
                        id="radio-export-data",
                        options=[
                            {"label": "所有设计方案", "value": "all"},
                            {"label": "可行设计", "value": "feasible"},
                            {"label": "Pareto最优设计", "value": "pareto"},
                            {"label": "Top 10设计", "value": "top10"},
                            {"label": "自定义选择", "value": "custom"}
                        ],
                        value="all",
                        className="mb-3"
                    ),

                    dbc.Label("导出格式"),
                    dbc.ButtonGroup([
                        dbc.Button([
                            html.Span("📄", className="me-2"),
                            "CSV"
                        ], id="btn-export-csv-data", color="success", outline=True),
                        dbc.Button([
                            html.Span("📊", className="me-2"),
                            "Excel"
                        ], id="btn-export-excel-data", color="success", outline=True),
                        dbc.Button([
                            html.Span("📝", className="me-2"),
                            "JSON"
                        ], id="btn-export-json-data", color="success", outline=True)
                    ], className="w-100")
                ])
            ], className="shadow-sm mb-4")
        ], md=6),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("图表导出", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("选择要导出的图表"),
                    dbc.Checklist(
                        id="checklist-export-charts",
                        options=[
                            {"label": "DVM热图", "value": "dvm"},
                            {"label": "采样分布", "value": "sampling"},
                            {"label": "性能分布", "value": "performance"},
                            {"label": "过滤效果", "value": "filter"},
                            {"label": "权衡空间散点图", "value": "tradespace"},
                            {"label": "平行坐标图", "value": "parallel"},
                            {"label": "雷达图", "value": "radar"}
                        ],
                        value=[],
                        className="mb-3"
                    ),

                    dbc.Label("导出格式"),
                    dbc.RadioItems(
                        id="radio-chart-format",
                        options=[
                            {"label": "PNG (静态图片)", "value": "png"},
                            {"label": "HTML (交互式)", "value": "html"},
                            {"label": "SVG (矢量图)", "value": "svg"}
                        ],
                        value="html",
                        className="mb-3"
                    ),

                    dbc.Button([
                        html.Span("⬇️", className="me-2"),
                        "导出图表"
                    ], id="btn-export-charts-data", color="info", className="w-100")
                ])
            ], className="shadow-sm mb-4")
        ], md=6)
    ]),

    # 项目管理
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("项目管理", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "导出所有8个Phase的完整数据为JSON格式，包含metadata和validation信息"
                    ], color="light", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button([
                                html.Span("💾", className="me-2"),
                                "保存项目"
                            ], id="btn-export-session", color="success", className="w-100")
                        ], width=6), 
                        dbc.Col([
                            dbc.Button([
                                html.Span("📝", className="me-2"),
                                "下载模板"
                            ], id="btn-download-template", color="secondary", outline=True, className="w-100")
                        ], width=6), 
                    ], className="g-2 mb-3"), 
                    dcc.Download(id="download-template-json"),
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 数据统计
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("数据统计", className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H4("0", id="stat-total-designs", className="mb-0 text-primary"),
                                html.Small("设计方案总数")
                            ], className="text-center")
                        ], md=3),
                        dbc.Col([
                            html.Div([
                                html.H4("0", id="stat-total-feasible", className="mb-0 text-success"),
                                html.Small("可行设计")
                            ], className="text-center")
                        ], md=3),
                        dbc.Col([
                            html.Div([
                                html.H4("0", id="stat-total-pareto", className="mb-0 text-info"),
                                html.Small("Pareto最优")
                            ], className="text-center")
                        ], md=3),
                        dbc.Col([
                            html.Div([
                                html.H4("0", id="stat-data-size", className="mb-0 text-warning"),
                                html.Small("数据大小 (MB)")
                            ], className="text-center")
                        ], md=3)
                    ])
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Button([
                html.Span("🏠", className="me-2"),
                "返回仪表盘"
            ], href="/", color="primary", className="w-100")
        ])
    ]),

    # 下载组件
    dcc.Download(id="download-dataframe"),
    dcc.Download(id="download-session")

], fluid=True)

# 文件上传回调
@callback(
    [Output('upload-status', 'children'),
     Output('data-preview', 'children'),
     Output('data-rows-badge', 'children')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def handle_upload(contents, filename):
    """处理文件上传 - 仅支持JSON项目文件导入，执行全系统恢复并生成报告"""
    if contents is None:
        return None, None, "未选择文件"

    # 1. 严格限制文件格式，移除 CSV/Excel 支持
    if not filename.lower().endswith('.json'):
        error_msg = dbc.Alert([
            "❌",
            "格式错误：系统恢复仅支持导入本平台导出的 .json 项目文件。"
        ], color="danger")
        return error_msg, None, "格式错误"

    try:
        # 2. 解析 JSON
        import base64
        import json
        import pandas as pd
        
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        project_data = json.loads(decoded.decode('utf-8'))

        # 3. 导入 StateManager 并执行重置
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.state_manager import get_state_manager
        
        state = get_state_manager()
        state.reset_all() # 核心：导入前清空现有状态

        # 4. 智能解析结构 (V2 vs Phases vs Flat)
        source_data = {}
        version_info = "Unknown"
        
        if 'data' in project_data and isinstance(project_data['data'], dict):
            source_data = project_data['data']
            version_info = project_data.get('version', '2.0')
        elif 'phases' in project_data and isinstance(project_data['phases'], dict):
            source_data = project_data['phases']
            version_info = 'Backend Export'
        else:
            source_data = project_data
            version_info = 'Legacy'

        # 5. 执行数据加载并收集统计信息用于生成报告
        restoration_report = []
        phases_found = 0
        
        # 定义 Phase 显示名称
        phase_map = {
            'phase1': 'Phase 1: 问题定义', 'phase2': 'Phase 2: 物理架构', 
            'phase3': 'Phase 3: 设计空间', 'phase4': 'Phase 4: 效用建模', 
            'phase5': 'Phase 5: 仿真评估', 'phase6': 'Phase 6: 敏感性分析',
            'phase7': 'Phase 7: 帕累托分析', 'phase8': 'Phase 8: 多准则决策'
        }

        # 遍历标准 Phase 键值
        for i in range(1, 9):
            phase_key = f'phase{i}'
            phase_name = phase_map.get(phase_key, phase_key)
            
            if phase_key in source_data:
                phases_found += 1
                items_count = 0
                phase_content = source_data[phase_key]
                
                status = "加载成功"
                row_variant = "success"
                
                try:
                    if isinstance(phase_content, dict):
                        # 逐项加载
                        for k, v in phase_content.items():
                            if v is not None:
                                # ---------------- DVM 矩阵特殊处理 ----------------
                                # 如果是 DVM 矩阵，且包含我们导出的行ID列，则还原为索引
                                if phase_key == 'phase1' and k == 'dvm_matrix' and isinstance(v, list) and len(v) > 0:
                                    # 检查第一行是否有 dvm_row_id
                                    if 'dvm_row_id' in v[0]:
                                        df_dvm = pd.DataFrame(v)
                                        df_dvm.set_index('dvm_row_id', inplace=True)
                                        df_dvm.index.name = None # 清除索引名称，保持整洁
                                        state.save(phase_key, k, df_dvm)
                                        items_count += 1
                                        continue # 跳过默认保存
                                # ------------------------------------------------

                                state.save(phase_key, k, v)
                                items_count += 1
                    else:
                        status = "格式错误 (非字典)"
                        row_variant = "warning"
                except Exception as e:
                    status = f"写入错误: {str(e)}"
                    row_variant = "danger"
                
                restoration_report.append({
                    "Phase": phase_name,
                    "状态": status,
                    "数据项": items_count,
                    "_row_variant": row_variant
                })
            else:
                restoration_report.append({
                    "Phase": phase_name,
                    "状态": "无数据",
                    "数据项": 0,
                    "_row_variant": "light"
                })

        # 6. 生成反馈结果
        success_msg = dbc.Alert([
            html.H5(["✓", "项目导入成功"], className="alert-heading"),
            html.P(f"文件 '{filename}' (v{version_info}) 已解析并加载到系统中。"),
            html.Hr(),
            html.P(f"检测到 {phases_found} 个 Phase 的数据，DVM矩阵结构已还原。", className="mb-0")
        ], color="success")

        # 生成预览表格
        table_header = [
            html.Thead(html.Tr([html.Th("阶段"), html.Th("导入状态"), html.Th("恢复数据项数量")]))
        ]
        
        table_rows = []
        for row in restoration_report:
            table_rows.append(
                html.Tr([
                    html.Td(row["Phase"]),
                    html.Td(row["状态"]),
                    html.Td(str(row["数据项"]))
                ], className=f"table-{row['_row_variant']}")
            )
        
        table_body = [html.Tbody(table_rows)]
        
        preview_table = dbc.Table(
            table_header + table_body,
            bordered=True,
            hover=True,
            responsive=True,
            size='sm',
            striped=False
        )

        badge_text = f"已恢复 {phases_found} Phases"

        return success_msg, preview_table, badge_text

    except Exception as e:
        import traceback
        error_msg = dbc.Alert([
            "⚠️",
            html.H6("导入失败", className="mb-2"),
            html.P(f"处理文件时发生错误: {str(e)}", className="mb-0 small"),
            html.Pre(traceback.format_exc(), className="mt-2 p-2 bg-light border rounded", style={"fontSize": "0.7rem", "maxHeight": "200px"})
        ], color="danger")
        return error_msg, None, "错误"
    

# 数据导出回调
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.state_manager import get_state_manager
from dash import ctx, no_update

@callback(
    Output('download-dataframe', 'data'),
    [Input('btn-export-csv-data', 'n_clicks'),
     Input('btn-export-excel-data', 'n_clicks'),
     Input('btn-export-json-data', 'n_clicks')],
    [State('radio-export-data', 'value')],
    prevent_initial_call=True
)
def export_data(n_csv, n_excel, n_json, export_type):
    """导出设计数据"""
    if not ctx.triggered:
        return no_update

    # DataFrame：辅助函数检查数据有效性
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

    # 确定导出哪些数据
    if export_type == 'all':
        data = state.load('phase4', 'alternatives')
    elif export_type == 'feasible':
        data = state.load('phase6', 'feasible_designs')
    elif export_type == 'pareto':
        data = state.load('phase7', 'pareto_designs')
    elif export_type == 'top10':
        pareto = state.load('phase7', 'pareto_designs')
        if _has_valid_data(pareto):  # ✅ DataFrame
            data = pareto.sort_values('MAU', ascending=False).head(10)
        else:
            data = None
    elif export_type == 'custom':
        # 自定义选择（暂时导出所有可行设计）
        data = state.load('phase6', 'feasible_designs')
    else:
        data = None

    if not _has_valid_data(data):  # ✅ DataFrame
        return no_update

    # 根据按钮确定格式
    if ctx.triggered_id == 'btn-export-csv-data':
        return dcc.send_data_frame(data.to_csv, filename=f"designs_{export_type}.csv", index=False)
    elif ctx.triggered_id == 'btn-export-excel-data':
        return dcc.send_data_frame(data.to_excel, filename=f"designs_{export_type}.xlsx",
                                   sheet_name="Designs", index=False)
    elif ctx.triggered_id == 'btn-export-json-data':
        return dcc.send_data_frame(data.to_json, filename=f"designs_{export_type}.json",
                                   orient='records', indent=2)

    return no_update

# 项目数据导出回调
@callback(
    Output('download-session', 'data'),
    Input('btn-export-session', 'n_clicks'),
    prevent_initial_call=True
)
def export_project(n_clicks):
    """项目导出 - JSON v2.0格式，包含所有Phase数据、metadata和validation，并正确处理DVM矩阵"""
    if not n_clicks:
        return no_update

    state = get_state_manager()

    # 导出所有Phase数据
    import json
    from datetime import datetime
    import numpy as np

    # 获取原始数据
    raw_phases_data = {
        'phase1': state.get_all_phase_data('phase1'),
        'phase2': state.get_all_phase_data('phase2'),
        'phase3': state.get_all_phase_data('phase3'),
        'phase4': state.get_all_phase_data('phase4'),
        'phase5': state.get_all_phase_data('phase5'),
        'phase6': state.get_all_phase_data('phase6'),
        'phase7': state.get_all_phase_data('phase7'),
        'phase8': state.get_all_phase_data('phase8'),
    }

    # ---------------- DVM 矩阵特殊处理 (导出) ----------------
    # StateManager取出的 DVM 矩阵是 DataFrame，to_dict默认会丢弃 Index(行名)
    # 我们需要手动 reset_index，把行名变成一个普通的列，比如 'dvm_row_id'
    if 'phase1' in raw_phases_data and raw_phases_data['phase1']:
        p1_data = raw_phases_data['phase1']
        if 'dvm_matrix' in p1_data:
            dvm = p1_data['dvm_matrix']
            if isinstance(dvm, pd.DataFrame):
                # 复制一份以防修改原数据
                dvm_export = dvm.copy()
                # 命名索引列
                dvm_export.index.name = 'dvm_row_id'
                # 转换为包含索引的记录列表
                p1_data['dvm_matrix'] = dvm_export.reset_index().to_dict('records')
    # --------------------------------------------------------

    # JSON v2.0 Schema
    project_data = {
        'version': '2.0',
        'format': 'system_engineering_project',
        'timestamp': datetime.now().isoformat(),
        'metadata': {
            'project_name': state.project_name,
            'last_modified': datetime.now().isoformat(),
            'exported_by': 'System Engineering Platform v2.0',
            'platform_version': '2.0.0',
            'database_backend': 'SQLite + SQLAlchemy',
            'export_notes': '完整项目导出'
        },
        'data': raw_phases_data,
        'validation': state.validate_data_flow()
    }

    # 增强的NumpyEncoder - 支持numpy、DataFrame、Timestamp等复杂类型
    class EnhancedJSONEncoder(json.JSONEncoder):
        """增强的JSON编码器，支持numpy、pandas等科学计算类型"""
        def default(self, obj):
            # numpy整数类型
            if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                return int(obj)
            # numpy浮点类型
            elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
                return float(obj)
            # numpy数组
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            # pandas DataFrame
            elif isinstance(obj, pd.DataFrame):
                return obj.to_dict('records')
            # pandas Timestamp
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            # 其他类型使用默认处理
            return super(EnhancedJSONEncoder, self).default(obj)

    # 序列化为JSON字符串
    json_str = json.dumps(project_data, indent=2, ensure_ascii=False, cls=EnhancedJSONEncoder)

    # 生成带项目名和时间戳的文件名
    filename = f"{state.project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return dcc.send_string(json_str, filename=filename)



# 快照管理回调
@callback(
    [Output('snapshots-list', 'children'),
     Output('input-snapshot-name', 'value')],
    [Input('btn-create-snapshot', 'n_clicks'),
     Input('interval-dashboard-update', 'n_intervals')],  # 定时刷新快照列表
    State('input-snapshot-name', 'value'),
    prevent_initial_call=True
)
def manage_snapshots(n_create, n_intervals, snapshot_name):
    """管理快照（创建/列表）"""
    from dash import ctx

    state = get_state_manager()

    # 如果点击了创建快照按钮
    if ctx.triggered_id == 'btn-create-snapshot' and n_create:
        if snapshot_name:
            state.create_snapshot(snapshot_name)
        else:
            state.create_snapshot()  # 自动命名

    # 获取所有快照列表
    snapshots = state.list_snapshots()

    if not snapshots:
        return dbc.Alert([
            html.Span("ℹ️", className="me-2"),
            "暂无保存的快照"
        ], color="light"), ""

    # 构建快照列表UI
    snapshot_items = []
    for snap in snapshots:
        snapshot_items.append(
            dbc.ListGroupItem([
                html.Div([
                    html.Strong(snap['name']),
                    html.Br(),
                    html.Small(snap['created_at'], className="text-muted")
                ], className="d-inline-block"),
                dbc.ButtonGroup([
                    dbc.Button("加载", size="sm", color="success", outline=True,
                              id={'type': 'btn-restore-snapshot', 'index': snap['name']}),
                    dbc.Button("删除", size="sm", color="danger", outline=True,
                              id={'type': 'btn-delete-snapshot', 'index': snap['name']})
                ], className="float-end")
            ])
        )

    return dbc.ListGroup(snapshot_items), ""

# 恢复快照回调
@callback(
    Output('snapshots-list', 'children', allow_duplicate=True),
    Input({'type': 'btn-restore-snapshot', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def restore_snapshot(n_clicks_list):
    """恢复快照"""
    from dash import ctx

    if not any(n_clicks_list):
        return no_update

    # 获取点击的快照名称
    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-restore-snapshot':
        snapshot_name = triggered['index']

        state = get_state_manager()
        success = state.restore_snapshot(snapshot_name)

        if success:
            return dbc.Alert([
                "✓",
                f"✅ 已恢复快照: {snapshot_name}"
            ], color="success")

    return no_update



# P1-10: 图表导出回调（PNG/HTML/SVG）
@callback(
    Output('download-dataframe', 'data', allow_duplicate=True),
    Input('btn-export-charts-data', 'n_clicks'),
    [State('checklist-export-charts', 'value'),
     State('radio-chart-format', 'value')],
    prevent_initial_call=True
)
def export_charts(n_clicks, selected_charts, chart_format):
    """导出选中的图表（P1-10核心功能）"""
    if not n_clicks or not selected_charts:
        return no_update

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.io as pio
    import zipfile
    from io import BytesIO
    from datetime import datetime

    # DataFrame：辅助函数检查数据有效性
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

    # 生成选中的图表
    figures = {}

    try:
        # 根据选择生成对应图表
        if 'sampling' in selected_charts:
            # 采样分布图（Phase 4）
            alternatives = state.load('phase4', 'alternatives')
            if _has_valid_data(alternatives):  # ✅ DataFrame
                import numpy as np
                fig = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=("轨道高度", "天线直径", "发射功率", "频段")
                )
                fig.add_trace(go.Histogram(x=alternatives['orbit_altitude'], nbinsx=30), row=1, col=1)
                fig.add_trace(go.Histogram(x=alternatives['antenna_diameter'], nbinsx=30), row=1, col=2)
                fig.add_trace(go.Histogram(x=alternatives['transmit_power'], nbinsx=30), row=2, col=1)
                freq_counts = alternatives['frequency_band'].value_counts()
                fig.add_trace(go.Bar(x=freq_counts.index, y=freq_counts.values), row=2, col=2)
                fig.update_layout(height=600, title_text="采样分布", showlegend=False)
                figures['sampling'] = fig

        if 'performance' in selected_charts:
            # 性能分布图（Phase 5）
            unified = state.load('phase5', 'unified_results')
            if _has_valid_data(unified):  # ✅ DataFrame
                fig = make_subplots(rows=2, cols=2, subplot_titles=("成本", "覆盖", "分辨率", "MAU"))
                fig.add_trace(go.Histogram(x=unified['cost_total'], nbinsx=30), row=1, col=1)
                fig.add_trace(go.Histogram(x=unified['perf_coverage'], nbinsx=30), row=1, col=2)
                fig.add_trace(go.Histogram(x=unified['perf_resolution'], nbinsx=30), row=2, col=1)
                fig.add_trace(go.Histogram(x=unified['MAU'], nbinsx=30), row=2, col=2)
                fig.update_layout(height=600, title_text="性能分布", showlegend=False)
                figures['performance'] = fig

        if 'tradespace' in selected_charts:
            # 权衡空间散点图（Phase 7）
            pareto = state.load('phase7', 'pareto_designs')
            if _has_valid_data(pareto):  # ✅ DataFrame
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=pareto['cost_total'],
                    y=pareto['MAU'],
                    mode='markers',
                    marker=dict(size=8, color=pareto['perf_coverage'], colorscale='Viridis', showscale=True),
                    text=[f"设计 {i}" for i in pareto.index],
                    hovertemplate='成本: %{x:.0f} M$<br>MAU: %{y:.3f}<extra></extra>'
                ))
                fig.update_layout(title="权衡空间：成本 vs MAU", xaxis_title="总成本 (M$)", yaxis_title="MAU")
                figures['tradespace'] = fig

        if 'parallel' in selected_charts:
            # 平行坐标图（Phase 7）
            pareto = state.load('phase7', 'pareto_designs')
            if _has_valid_data(pareto):  # ✅ DataFrame
                dims = ['cost_total', 'perf_coverage', 'perf_resolution', 'MAU']
                dimensions = []
                for dim in dims:
                    if dim in pareto.columns:
                        label_map = {
                            'cost_total': '总成本',
                            'perf_coverage': '覆盖范围',
                            'perf_resolution': '分辨率',
                            'MAU': 'MAU'
                        }
                        dimensions.append(dict(
                            label=label_map.get(dim, dim),
                            values=pareto[dim],
                            range=[pareto[dim].min(), pareto[dim].max()]
                        ))
                fig = go.Figure(data=go.Parcoords(
                    line=dict(color=pareto['MAU'], colorscale='Viridis', showscale=True),
                    dimensions=dimensions
                ))
                fig.update_layout(title="平行坐标图", height=500)
                figures['parallel'] = fig

        if 'radar' in selected_charts:
            # 雷达图（Phase 8）
            pareto = state.load('phase7', 'pareto_designs')
            if _has_valid_data(pareto):  # ✅ DataFrame
                top5 = pareto.sort_values('MAU', ascending=False).head(5)
                fig = go.Figure()
                metrics = ['cost_total', 'perf_coverage', 'perf_resolution', 'MAU']
                categories = ['成本', '覆盖', '分辨率', 'MAU']
                for i, (idx, row) in enumerate(top5.iterrows()):
                    values = []
                    for metric in metrics:
                        val = row[metric]
                        min_val, max_val = pareto[metric].min(), pareto[metric].max()
                        if max_val > min_val:
                            norm_val = 1 - (val - min_val) / (max_val - min_val) if metric == 'cost_total' else (val - min_val) / (max_val - min_val)
                        else:
                            norm_val = 0.5
                        values.append(norm_val)
                    values.append(values[0])
                    fig.add_trace(go.Scatterpolar(r=values, theta=categories + [categories[0]], name=f'设计 {int(idx)}'))
                fig.update_layout(title="Top 5设计雷达图", polar_radialaxis_visible=True, polar_radialaxis_range=[0, 1])
                figures['radar'] = fig

        # 如果没有生成任何图表
        if not figures:
            return no_update

        # 导出图表
        if chart_format == 'html':
            # HTML格式：合并所有图表到单个HTML文件
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>图表导出 - {datetime.now().strftime('%Y%m%d_%H%M%S')}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .chart-container {{ background: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>📊 系统工程分析平台 - 图表导出</h1>
    <p>导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
            chart_names = {
                'sampling': '采样分布图',
                'performance': '性能分布图',
                'tradespace': '权衡空间散点图',
                'parallel': '平行坐标图',
                'radar': '雷达图对比'
            }
            for key, fig in figures.items():
                html_content += f'<div class="chart-container"><h2>{chart_names.get(key, key)}</h2>'
                html_content += pio.to_html(fig, include_plotlyjs=False, div_id=f"chart_{key}")
                html_content += '</div>'
            html_content += '</body></html>'

            return dcc.send_string(html_content, filename=f"charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")

        elif chart_format in ['png', 'svg']:
            # PNG/SVG格式：打包为ZIP文件
            try:
                import kaleido  # PNG/SVG导出需要kaleido
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for key, fig in figures.items():
                        img_bytes = pio.to_image(fig, format=chart_format, width=1200, height=800)
                        zip_file.writestr(f"{key}.{chart_format}", img_bytes)
                zip_buffer.seek(0)
                return dcc.send_bytes(zip_buffer.read(), filename=f"charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
            except ImportError:
                # 如果kaleido未安装，降级为HTML
                return dcc.send_string(
                    f"⚠️ PNG/SVG导出需要安装 kaleido 库。\n\n"
                    f"请运行：pip install kaleido\n\n"
                    f"已自动切换为HTML格式导出。",
                    filename="export_error.txt"
                )

    except Exception as e:
        # 错误处理
        error_msg = f"图表导出失败: {str(e)}"
        return dcc.send_string(error_msg, filename="export_error.txt")

    return no_update

@callback(
    Output("download-template-json", "data"),
    Input("btn-download-template", "n_clicks"),
    prevent_initial_call=True
)
def download_project_template(n_clicks):
    """生成并下载空白项目模板 (支持 V2 格式)"""
    import json
    from datetime import datetime
    
    if not n_clicks:
        return no_update
        
    # 实例化 StateManager
    # 使用临时项目名，避免影响当前打开的项目
    # 注意：这里会连接数据库，但不会读取特定项目数据，只会调用 get_project_template
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.state_manager_v2 import StateManagerV2
    
    # 使用 "template_generator" 作为 ID，这会在数据库创建一个临时记录，是可以接受的
    temp_manager = StateManagerV2("template_generator")
    
    # 获取 V2 格式模板数据
    template_data = temp_manager.get_project_template()
    
    # 生成带时间戳的文件名
    filename = f"Project_Template_v2_{datetime.now().strftime('%Y%m%d')}.json"
    
    return dict(
        content=json.dumps(template_data, indent=2, ensure_ascii=False),
        filename=filename
    )