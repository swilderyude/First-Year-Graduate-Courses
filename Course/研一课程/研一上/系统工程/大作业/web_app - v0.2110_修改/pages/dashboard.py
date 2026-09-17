"""
仪表盘页面 - 项目概览和快速开始
"""

import dash
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# 页面布局
layout = dbc.Container([
    # 页面跳转组件（用于Dashboard->Phase1联动）
    dcc.Location(id='url-redirect', refresh=True),

    # 欢迎横幅
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H2([
                        html.Span("🚀", className="me-3"),
                        "欢迎使用系统工程分析平台"
                    ], className="mb-3"),
                    html.P(
                        "本平台提供完整的8阶段系统工程分析工作流，从问题定义到决策推荐。",
                        className="lead"
                    ),
                    html.Hr(),
                    html.Div([
                        dbc.Button([
                            html.Span("➕", className="me-2"),
                            "新建项目"
                        ], id="btn-new-project", color="primary", size="lg", className="me-2"),
                        dbc.Button([
                            html.Span("📂", className="me-2"),
                            "打开项目"
                        ], id="btn-load-project", color="secondary", size="lg", className="me-2"),
                        html.A([
                            dbc.Button([
                                html.Span("📖", className="me-2"),
                                "查看教程"
                            ], color="info", size="lg", outline=True)
                        ], href="/tutorial", target="_blank", style={"textDecoration": "none"})
                    ])
                ])
            ], className="shadow-sm border-0 bg-light")
        ])
    ], className="mb-4"),

    # 项目状态
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("ℹ️", className="me-2"),
                    "当前项目状态"
                ], className="mb-0")),
                dbc.CardBody([
                    html.Div(id='project-status-display', children=[
                        dbc.Alert([
                            "⚠️",
                            "暂无项目。请新建或加载项目。"
                        ], color="warning")
                    ])
                ])
            ], className="shadow-sm")
        ], md=6),

        # 快速统计
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("📊", className="me-2"),
                    "快速统计"
                ], className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H3("0", className="mb-0 text-primary", id="stat-designs"),
                                html.Small("设计方案", className="text-muted")
                            ], className="text-center")
                        ], md=4),
                        dbc.Col([
                            html.Div([
                                html.H3("0", className="mb-0 text-success", id="stat-feasible"),
                                html.Small("可行设计", className="text-muted")
                            ], className="text-center")
                        ], md=4),
                        dbc.Col([
                            html.Div([
                                html.H3("0", className="mb-0 text-info", id="stat-pareto"),
                                html.Small("Pareto最优", className="text-muted")
                            ], className="text-center")
                        ], md=4)
                    ])
                ])
            ], className="shadow-sm")
        ], md=6)
    ], className="mb-4"),

    # 工作流进度 (P1-7增强)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("📋", className="me-2"),
                    "工作流进度",
                    dbc.Badge("0%", id="badge-overall-progress", color="secondary", className="ms-2")
                ], className="mb-0")),
                dbc.CardBody([
                    html.Div(id='workflow-progress', children=[
                        # Phase进度条（动态更新）
                        *[
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.Span(f"{icon}", className="me-2"),
                                        f"Phase {i}: {name}"
                                    ], className="fw-bold", id=f"phase{i}-label")
                                ], md=4),
                                dbc.Col([
                                    dbc.Progress(
                                        value=0,
                                        id=f"progress-phase{i}",
                                        className="mb-0",
                                        striped=True,
                                        animated=True
                                    )
                                ], md=8)
                            ], className="mb-3")
                            for i, (name, icon) in enumerate([
                                ("问题定义", "🎯"),
                                ("物理架构", "🔧"),
                                ("效用建模", "⚙️"),
                                ("设计空间", "📐"),
                                ("多域建模", "🧮"),
                                ("约束过滤", "🔍"),
                                ("权衡空间", "📈"),
                                ("决策分析", "🏆")
                            ], start=1)
                        ]
                    ])
                ])
            ], className="shadow-sm")
        ])
    ], className="mb-4"),

    # 实时数据监控卡片 (P1-6增强)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("🗄️", className="me-2"),
                    "实时数据监控"
                ], className="mb-0")),
                dbc.CardBody([
                    html.Div(id='real-time-data-monitor', children=[
                        dbc.Alert("等待数据更新...", color="light", className="text-center")
                    ])
                ])
            ], className="shadow-sm")
        ])
    ], className="mb-4"),

    # 快速操作卡片
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Span("📥", className="fa-3x mb-3 text-primary"),
                    html.H5("导入数据", className="card-title"),
                    html.P("从CSV/Excel文件导入设计数据", className="card-text text-muted"),
                    dbc.Button("导入", id="btn-import-data", color="primary", outline=True, size="sm", href="/data")
                ], className="text-center")
            ], className="shadow-sm h-100")
        ], md=3),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Span("📦", className="fa-3x mb-3 text-success"),
                    html.H5("示例项目", className="card-title"),
                    html.P("加载卫星雷达系统示例项目", className="card-text text-muted"),
                    dbc.Button("加载", color="success", outline=True, size="sm", id="btn-load-example")
                ], className="text-center")
            ], className="shadow-sm h-100")
        ], md=3),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Span("▶️", className="fa-3x mb-3 text-info"),
                    html.H5("运行分析", className="card-title"),
                    html.P("执行完整的8阶段工作流", className="card-text text-muted"),
                    dbc.Button("运行", id="btn-run-analysis", color="info", outline=True, size="sm")
                ], className="text-center")
            ], className="shadow-sm h-100")
        ], md=3),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Span("📤", className="fa-3x mb-3 text-warning"),
                    html.H5("导出结果", className="card-title"),
                    html.P("导出分析结果和可视化图表", className="card-text text-muted"),
                    dbc.Button("导出", id="btn-export-results", color="warning", outline=True, size="sm", href="/data")
                ], className="text-center")
            ], className="shadow-sm h-100")
        ], md=3)
    ], className="mb-4"),

    # P2-11: 最近活动日志（增强）
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("📜", className="me-2"),
                    "最近活动日志",
                    dbc.Badge("实时更新", color="info", className="ms-2", pill=True)
                ], className="mb-0")),
                dbc.CardBody([
                    html.Div(id='activity-log', children=[
                        dbc.ListGroup([
                            dbc.ListGroupItem([
                                html.Div([
                                    html.Span("ℹ️", className="text-secondary me-2"),
                                    "暂无活动记录。开始工作流后，活动将在此处显示。"
                                ])
                            ])
                        ], flush=True)
                    ]),
                    html.Hr(),
                    html.Div([
                        dbc.Button([
                            html.Span("🔄", className="me-2"),
                            "手动刷新"
                        ], id='btn-refresh-activity-log', size="sm", color="secondary", outline=True, className="me-2"),
                        dbc.Button([
                            html.Span("🗑️", className="me-2"),
                            "清空日志"
                        ], id='btn-clear-activity-log', size="sm", color="danger", outline=True)
                    ], className="text-end")
                ])
            ], className="shadow-sm")
        ])
    ]),

    # 新建项目模态框
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("新建项目")),
        dbc.ModalBody([
            dbc.Label("项目名称"),
            dbc.Input(id="input-project-name", placeholder="例如：卫星雷达系统设计", className="mb-3"),
            dbc.Label("项目描述"),
            dbc.Textarea(id="input-project-desc", placeholder="简要描述项目目标...", rows=3)
        ]),
        dbc.ModalFooter([
            dbc.Button("取消", id="btn-cancel-new-project", color="secondary", className="me-2"),
            dbc.Button("创建", id="btn-create-project", color="primary")
        ])
    ], id="modal-new-project", size="lg", is_open=False),

    # P1-1: 打开项目模态框
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("打开项目")),
        dbc.ModalBody([
            dbc.Alert([
                html.Span("ℹ️", className="me-2"),
                "请选择之前保存的项目文件（.json格式）"
            ], color="info", className="mb-3"),

            dcc.Upload(
                id='upload-project-file',
                children=html.Div([
                    html.Span("☁️", className="fa-3x mb-3 text-primary"),
                    html.H5("点击或拖拽文件到此处", className="mb-2"),
                    html.P("支持.json格式，最大10MB", className="text-muted small")
                ], className="text-center py-4"),
                style={
                    'width': '100%',
                    'height': '150px',
                    'lineHeight': '150px',
                    'borderWidth': '2px',
                    'borderStyle': 'dashed',
                    'borderRadius': '10px',
                    'borderColor': '#007bff',
                    'textAlign': 'center',
                    'cursor': 'pointer'
                },
                accept='.json',
                max_size=10*1024*1024
            ),

            html.Div(id='upload-status-display', className="mt-3")
        ]),
        dbc.ModalFooter([
            dbc.Button("关闭", id="btn-close-load-project", color="secondary")
        ])
    ], id="modal-load-project", size="lg", is_open=False),

    # 定时刷新组件（每5秒更新统计）
    dcc.Interval(
        id='interval-dashboard-update',
        interval=5000,  # 5秒
        n_intervals=0
    )

], fluid=True)

# 加载示例项目回调
@callback(
    [Output('project-status-display', 'children', allow_duplicate=True),
     Output('url-redirect', 'href', allow_duplicate=True)],
    [Input('btn-load-example', 'n_clicks')],
    prevent_initial_call=True
)
def load_example_project(n_clicks):
    """加载示例项目（示例项目_卫星雷达.json）"""
    if n_clicks:
        try:
            import sys, os, json
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from utils.state_manager import get_state_manager

            # 加载示例JSON文件
            example_file = os.path.join(os.path.dirname(__file__), '..', 'docs', '示例项目_卫星雷达.json')
            with open(example_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 恢复所有Phase的数据到StateManager
            state = get_state_manager()
            phases_loaded = []
            for phase_key, phase_data in project_data.items():
                if phase_key.startswith('phase'):
                    for data_key, data_value in phase_data.items():
                        state.save(phase_key, data_key, data_value)
                    phases_loaded.append(phase_key)

            # 验证数据完整性
            validation = state.validate_data_flow()
            complete_phases = [p for p, v in validation.items() if v['status'] == 'complete']

            project_name = project_data.get('phase1', {}).get('project_name', '卫星雷达系统设计')
            project_desc = project_data.get('phase1', {}).get('project_description', '未提供描述')

            project_status = dbc.Alert([
                html.H5([
                    html.Span("🛰️", className="me-2"),
                    f"已加载项目: {project_name}"
                ], className="alert-heading"),
                html.P(project_desc),
                html.Hr(),
                html.Div([
                    dbc.Badge(f"✓ {len(complete_phases)}/{len(validation)} Phases 数据完整", color="success", className="me-2"),
                    dbc.Badge(f"已恢复 {len(phases_loaded)} Phases", color="info")
                ])
            ], color="success")

            return project_status, "/phase1"

        except Exception as e:
            import traceback
            error_msg = dbc.Alert([
                html.Span("⚠️", className="me-2"),
                html.H6("❌ 加载失败", className="mb-2"),
                html.P(f"错误: {str(e)}", className="mb-0 small")
            ], color="danger")
            return error_msg, ""

    return no_update, no_update

# 控制新建项目模态框
@callback(
    Output("modal-new-project", "is_open"),
    [Input("btn-new-project", "n_clicks"),
     Input("btn-cancel-new-project", "n_clicks"),
     Input("btn-create-project", "n_clicks")],
    [State("modal-new-project", "is_open")],
    prevent_initial_call=True
)
def toggle_modal(n_new, n_cancel, n_create, is_open):
    """控制新建项目模态框的显示/隐藏"""
    if n_new or n_cancel or n_create:
        return not is_open
    return is_open

# 创建新项目（修复1.1：Dashboard-Phase1联动）
@callback(
    [Output('project-status-display', 'children', allow_duplicate=True),
     Output('url-redirect', 'href'),
     Output('phase1-auto-load-trigger', 'data')],  # 新增：触发Phase 1自动加载
    [Input('btn-create-project', 'n_clicks')],
    [State('input-project-name', 'value'),
     State('input-project-desc', 'value')],
    prevent_initial_call=True
)
def create_new_project(n_clicks, project_name, project_desc):
    """创建新项目 - 重置状态并保存到StateManager,然后跳转到Phase 1"""
    if n_clicks and project_name:
        # 1. 导入StateManager
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.state_manager import get_state_manager
        import time

        # 2. 重置StateManager到初始状态（清空所有已加载的用户数据）
        state = get_state_manager()
        state.reset_all()
        print("新建项目: {}".format(project_name))
        print("描述: {}".format(project_desc or "无描述"))

        # 3. 保存项目基本信息到StateManager
        # 修复：只保存mission字典（StateManagerV2只支持mission，不支持单独的project_name/description）
        state.save('phase1', 'mission', {
            'title': project_name,
            'description': project_desc or '',
            'key_objectives': [],
            'value_proposition': ''
        })

        # 4. 创建提示消息
        status_display = dbc.Alert([
            html.H5([
                "✓",
                "项目已创建：" + project_name
            ], className="alert-heading"),
            html.P(project_desc or "暂无描述"),
            html.Hr(),
            html.Div([
                dbc.Badge("✓ 状态已重置", color="success", className="me-2"),
                dbc.Badge("✓ 数据已保存", color="success", className="me-2"),
                dbc.Badge("→ 跳转到Phase 1", color="info")
            ])
        ], color="success")

        # 5. 返回跳转URL + 触发Phase 1自动加载
        return status_display, "/phase1", {'timestamp': str(time.time()), 'source': 'dashboard'}

    return no_update, no_update, no_update

# 打开项目（P1-1修复：实现加载功能）
@callback(
    Output('modal-load-project', 'is_open'),
    [Input('btn-load-project', 'n_clicks'),
     Input('btn-close-load-project', 'n_clicks')],
    [State('modal-load-project', 'is_open')],
    prevent_initial_call=True
)
def toggle_load_project_modal(n_load, n_close, is_open):
    """控制打开项目模态框"""
    if n_load or n_close:
        return not is_open
    return is_open

# P1-1: 处理上传的项目文件
@callback(
    [Output('upload-status-display', 'children'),
     Output('project-status-display', 'children', allow_duplicate=True),
     Output('url-redirect', 'href', allow_duplicate=True)],
    [Input('upload-project-file', 'contents')],
    [State('upload-project-file', 'filename')],
    prevent_initial_call=True
)
def load_uploaded_project(contents, filename):
    """加载上传的项目JSON文件（修复版：支持V2格式、全量恢复及DVM矩阵还原）"""
    if contents is None:
        return no_update, no_update, no_update

    try:
        # 1. 解码base64内容
        import base64
        import json
        import pandas as pd
        
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        project_data = json.loads(decoded.decode('utf-8'))

        # 2. 导入StateManager
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.state_manager import get_state_manager
        
        state = get_state_manager()

        # 3. 重置StateManager到初始状态
        state.reset_all()
        print("打开项目: {}".format(filename))

        # 4. 智能解析 JSON 结构
        source_data = {}
        meta_name = None
        meta_desc = None

        if 'data' in project_data and isinstance(project_data['data'], dict):
            # V2 格式
            source_data = project_data['data']
            meta_name = project_data.get('metadata', {}).get('project_name')
            meta_desc = project_data.get('metadata', {}).get('export_notes')
        elif 'phases' in project_data and isinstance(project_data['phases'], dict):
            # 后端格式
            source_data = project_data['phases']
            meta_name = project_data.get('project_name')
        else:
            # 兼容旧格式
            source_data = project_data

        # 5. 恢复所有Phase的数据到StateManager
        phases_loaded = []
        for phase_key, phase_data in source_data.items():
            if phase_key.startswith('phase') and isinstance(phase_data, dict):
                has_data = False
                for data_key, data_value in phase_data.items():
                    try:
                        if data_value is not None:
                            # ---------------- DVM 矩阵特殊处理 (导入) ----------------
                            if phase_key == 'phase1' and data_key == 'dvm_matrix' and isinstance(data_value, list) and len(data_value) > 0:
                                if 'dvm_row_id' in data_value[0]:
                                    df_dvm = pd.DataFrame(data_value)
                                    df_dvm.set_index('dvm_row_id', inplace=True)
                                    df_dvm.index.name = None
                                    state.save(phase_key, data_key, df_dvm)
                                    has_data = True
                                    continue
                            # --------------------------------------------------------

                            state.save(phase_key, data_key, data_value)
                            has_data = True
                    except Exception as e:
                        print("Warning loading {}.{}: {}".format(phase_key, data_key, e))
                
                if has_data:
                    phases_loaded.append(phase_key)

        # 6. 验证数据完整性
        validation = state.validate_data_flow()
        complete_phases = [p for p, v in validation.items() if v['status'] == 'complete']
        
        # 7. 生成详细结果列表
        validation_items = []
        for phase, result in validation.items():
            phase_num = phase.replace('phase', '')
            if result['status'] == 'complete':
                validation_items.append(
                    html.Li([
                        html.Span("✓", className="text-success me-2"),
                        f"Phase {phase_num}: ",
                        html.Strong("数据完整", className="text-success")
                    ])
                )
            else:
                missing = result.get('missing', [])
                validation_items.append(
                    html.Li([
                        html.Span("⚠️", className="text-warning me-2"),
                        f"Phase {phase_num}: ",
                        html.Strong("数据不完整", className="text-warning"),
                        html.Small(f" (缺少: {', '.join(missing)})", className="text-muted")
                    ])
                )

        upload_status = dbc.Alert([
            "✓",
            html.H6(f"✅ 文件已解析: {filename}", className="mb-2"),
            html.P(f"已恢复 {len(phases_loaded)} 个Phase的数据", className="mb-1 small"),
            html.Hr(className="my-2"),
            html.H6("📊 数据完整性检查:", className="mb-2 small"),
            html.Ul(validation_items, className="small mb-0", style={"listStyle": "none", "paddingLeft": "0"})
        ], color="success")

        # 8. 更新项目状态显示
        p1_mission = state.load('phase1', 'mission') or {}
        project_name = meta_name or p1_mission.get('title', '未命名项目')
        project_desc = meta_desc or p1_mission.get('description', '无描述')

        project_status = dbc.Alert([
            html.H5([
                html.Span("📂", className="me-2"),
                f"已加载项目: {project_name}"
            ], className="alert-heading"),
            html.P(project_desc),
            html.Hr(),
            html.Div([
                dbc.Badge(f"✓ {len(complete_phases)}/{len(validation)} Phases 数据完整", color="success", className="me-2"),
                dbc.Badge(f"已恢复 {len(phases_loaded)} Phases", color="info")
            ])
        ], color="success")

        return upload_status, project_status, "/phase1"

    except Exception as e:
        import traceback
        error_msg = dbc.Alert([
            html.Span("⚠️", className="me-2"),
            html.H6("❌ 加载失败", className="mb-2"),
            html.P(f"错误: {str(e)}", className="mb-0 small"),
            html.Details([
                html.Summary("详细错误信息", style={"cursor": "pointer"}),
                html.Pre(traceback.format_exc(), className="small mt-2", style={"fontSize": "0.7rem"})
            ])
        ], color="danger")

        return error_msg, no_update, no_update
    



# 运行分析（占位功能）
@callback(
    Output('project-status-display', 'children', allow_duplicate=True),
    [Input('btn-run-analysis', 'n_clicks')],
    prevent_initial_call=True
)
def run_analysis(n_clicks):
    """运行完整8阶段分析"""
    if n_clicks:
        return dbc.Alert([
            html.Span("⚙️", className="me-2"),
            "分析功能开发中：请先完成Phase 1-8各阶段的配置"
        ], color="info")
    return no_update

# 实时统计和工作流进度更新（P1-6 + P1-7综合回调）
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.state_manager import get_state_manager

@callback(
    [Output('stat-designs', 'children'),
     Output('stat-feasible', 'children'),
     Output('stat-pareto', 'children'),
     # P1-7: 8个Phase进度条
     Output('progress-phase1', 'value'),
     Output('progress-phase2', 'value'),
     Output('progress-phase3', 'value'),
     Output('progress-phase4', 'value'),
     Output('progress-phase5', 'value'),
     Output('progress-phase6', 'value'),
     Output('progress-phase7', 'value'),
     Output('progress-phase8', 'value'),
     # P1-7: 整体进度徽章
     Output('badge-overall-progress', 'children'),
     Output('badge-overall-progress', 'color'),
     # P1-6: 实时数据监控
     Output('real-time-data-monitor', 'children')],
    [Input('interval-dashboard-update', 'n_intervals')]
)
def update_dashboard_realtime(n):
    """实时更新仪表盘统计数据和工作流进度（P1-6 + P1-7）"""
    import pandas as pd

    # DataFrame修复：辅助函数检查数据有效性
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

    # === P1-6: 快速统计 ===
    alternatives = state.load('phase4', 'alternatives')
    feasible_designs = state.load('phase6', 'feasible_designs')
    pareto_designs = state.load('phase7', 'pareto_designs')

    n_designs = len(alternatives) if _has_valid_data(alternatives) else 0  # ✅ DataFrame修复
    n_feasible = len(feasible_designs) if _has_valid_data(feasible_designs) else 0  # ✅ DataFrame修复
    n_pareto = len(pareto_designs) if _has_valid_data(pareto_designs) else 0  # ✅ DataFrame修复

    # === P1-7: 工作流进度计算（改进版 - 使用validate_data_flow） ===
    # 使用StateManager的标准验证方法，确保数据完整性
    validation = state.validate_data_flow()

    phase_progress = []
    for i in range(1, 9):
        phase_key = f'phase{i}'
        phase_status = validation[phase_key]['status']

        # 根据验证状态计算进度
        if phase_status == 'complete':
            progress = 100  # 数据完整
        elif phase_status == 'incomplete':
            # 计算部分完整度（已有字段数 / 必需字段数）
            phase_data = state.get_all_phase_data(phase_key)
            required_fields = validation[phase_key]['required']
            missing_fields = validation[phase_key].get('missing', [])
            filled_fields = len(required_fields) - len(missing_fields)
            progress = int((filled_fields / len(required_fields)) * 100) if required_fields else 0
        else:
            progress = 0  # 未知状态

        phase_progress.append(progress)

    # 整体进度
    overall_progress = sum(phase_progress) / 8
    badge_text = f"{overall_progress:.0f}%"
    badge_color = "success" if overall_progress == 100 else "warning" if overall_progress >= 50 else "secondary"

    # === P1-6: 实时数据监控（显示各Phase关键指标）===
    monitoring_cards = []

    # Phase 4: 设计空间
    if phase_progress[3] > 0:  # phase_progress[3] = Phase 4
        monitoring_cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6([html.Span("📐", className="me-2 text-primary"), "Phase 4: 设计空间"], className="mb-2"),
                        html.H4(str(n_designs), className="mb-1 text-primary"),
                        html.Small("设计方案已生成", className="text-muted")
                    ], className="text-center p-2")
                ], className="shadow-sm h-100")
            ], md=3)
        )

    # Phase 5: 多域建模（安全加载DataFrame数据）
    if phase_progress[4] > 0:  # phase_progress[4] = Phase 5
        try:
            unified = state.load('phase5', 'unified_results')
            avg_mau = unified['MAU'].mean() if _has_valid_data(unified) and 'MAU' in unified.columns else 0  # ✅ DataFrame修复
            monitoring_cards.append(
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6([html.Span("🧮", className="me-2 text-danger"), "Phase 5: 多域建模"], className="mb-2"),
                            html.H4(f"{avg_mau:.3f}", className="mb-1 text-danger"),
                            html.Small("平均MAU效用", className="text-muted")
                        ], className="text-center p-2")
                    ], className="shadow-sm h-100")
                ], md=3)
            )
        except (KeyError, TypeError, AttributeError):
            # 跳过格式错误的数据
            pass

    # Phase 6: 约束过滤
    if phase_progress[5] > 0:  # phase_progress[5] = Phase 6
        feasibility_rate = (n_feasible / n_designs * 100) if n_designs > 0 else 0
        monitoring_cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6([html.Span("🔍", className="me-2 text-success"), "Phase 6: 约束过滤"], className="mb-2"),
                        html.H4(f"{feasibility_rate:.1f}%", className="mb-1 text-success"),
                        html.Small(f"{n_feasible}/{n_designs} 可行方案", className="text-muted")
                    ], className="text-center p-2")
                ], className="shadow-sm h-100")
            ], md=3)
        )

    # Phase 7: Pareto前沿
    if phase_progress[6] > 0:  # phase_progress[6] = Phase 7
        pareto_rate = (n_pareto / n_feasible * 100) if n_feasible > 0 else 0
        monitoring_cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6([html.Span("📈", className="me-2 text-info"), "Phase 7: Pareto前沿"], className="mb-2"),
                        html.H4(f"{pareto_rate:.1f}%", className="mb-1 text-info"),
                        html.Small(f"{n_pareto}/{n_feasible} Pareto最优", className="text-muted")
                    ], className="text-center p-2")
                ], className="shadow-sm h-100")
            ], md=3)
        )

    if not monitoring_cards:
        monitoring_cards = [
            dbc.Col([
                dbc.Alert([
                    html.Span("ℹ️", className="me-2"),
                    "暂无数据。请先完成Phase 4-8的分析。"
                ], color="light", className="text-center mb-0")
            ])
        ]

    real_time_monitor = dbc.Row(monitoring_cards, className="g-3")

    # 返回所有更新
    return (
        str(n_designs), str(n_feasible), str(n_pareto),  # 快速统计
        *phase_progress,  # 8个Phase进度条
        badge_text, badge_color,  # 整体进度徽章
        real_time_monitor  # 实时监控卡片
    )

# ========== P2-11: 最近活动日志回调 ==========

@callback(
    Output('activity-log', 'children'),
    [Input('interval-dashboard-update', 'n_intervals'),
     Input('btn-refresh-activity-log', 'n_clicks')],
    prevent_initial_call=False
)
def update_activity_log(n_intervals, n_refresh):
    """生成活动日志（P2-11核心功能）

    基于StateManager中的数据推断最近的操作活动。
    """
    try:
        import datetime
        import pandas as pd

        # DataFrame修复：辅助函数检查数据有效性
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

        # 收集各Phase的数据状态
        activities = []

        # Phase 1: 问题定义
        phase1_dv = state.load('phase1', 'design_variables')
        phase1_va = state.load('phase1', 'value_attributes')
        if _has_valid_data(phase1_dv) or _has_valid_data(phase1_va):  # ✅ DataFrame修复
            activities.append({
                'icon': 'fa-bullseye',
                'color': 'primary',
                'phase': 'Phase 1',
                'action': '完成问题定义',
                'detail': f"定义了{len(phase1_dv) if phase1_dv is not None else 0}个设计变量" if phase1_dv is not None else "定义了价值属性",
                'time': '最近'
            })

        # Phase 2: 物理架构
        phase2_comp = state.load('phase2', 'components')
        phase2_intf = state.load('phase2', 'interfaces')
        if _has_valid_data(phase2_comp) and _has_valid_data(phase2_intf):  # ✅ DataFrame修复
            activities.append({
                'icon': 'fa-project-diagram',
                'color': 'success',
                'phase': 'Phase 2',
                'action': '构建物理架构',
                'detail': f"{len(phase2_comp)}个组件, {len(phase2_intf)}个接口",
                'time': '最近'
            })

        # Phase 3: 效用建模
        phase3_uf = state.load('phase3', 'utility_functions')
        if _has_valid_data(phase3_uf):  # ✅ DataFrame修复
            activities.append({
                'icon': 'fa-sliders-h',
                'color': 'info',
                'phase': 'Phase 3',
                'action': '定义效用函数',
                'detail': f"配置了{len(phase3_uf)}个效用函数" if isinstance(phase3_uf, list) else "配置了效用模型",
                'time': '最近'
            })

        # Phase 4: 设计空间
        alternatives = state.load('phase4', 'alternatives')
        if _has_valid_data(alternatives):  # ✅ DataFrame修复
            activities.append({
                'icon': 'fa-th',
                'color': 'warning',
                'phase': 'Phase 4',
                'action': '生成设计空间',
                'detail': f"生成了{len(alternatives)}个设计方案",
                'time': '最近'
            })

        # Phase 5: 多域建模（安全加载DataFrame数据）
        try:
            unified = state.load('phase5', 'unified_results')
            if _has_valid_data(unified):  # ✅ DataFrame修复
                avg_mau = unified['MAU'].mean() if 'MAU' in unified.columns else 0
                activities.append({
                    'icon': 'fa-calculator',
                    'color': 'danger',
                    'phase': 'Phase 5',
                    'action': '完成多域建模',
                    'detail': f"评估了{len(unified)}个方案, 平均MAU: {avg_mau:.3f}",
                    'time': '最近'
                })
        except (KeyError, TypeError, AttributeError):
            # 跳过格式错误的数据
            pass

        # Phase 6: 约束过滤（安全加载DataFrame数据）
        try:
            feasible = state.load('phase6', 'feasible_designs')
            if _has_valid_data(feasible):  # ✅ DataFrame修复
                feasibility_rate = (len(feasible) / len(alternatives) * 100) if _has_valid_data(alternatives) else 0  # ✅ DataFrame修复
                activities.append({
                    'icon': 'fa-filter',
                    'color': 'primary',
                    'phase': 'Phase 6',
                    'action': '应用约束过滤',
                    'detail': f"{len(feasible)}个可行方案 (可行性: {feasibility_rate:.1f}%)",
                    'time': '最近'
                })
        except (KeyError, TypeError, AttributeError):
            # 跳过格式错误的数据
            pass

        # Phase 7: 权衡空间（安全加载DataFrame数据）
        try:
            pareto = state.load('phase7', 'pareto_designs')
            if _has_valid_data(pareto):  # ✅ DataFrame修复
                pareto_rate = (len(pareto) / len(feasible) * 100) if _has_valid_data(feasible) else 0  # ✅ DataFrame修复
                activities.append({
                    'icon': 'fa-chart-scatter',
                    'color': 'info',
                    'phase': 'Phase 7',
                    'action': '识别Pareto前沿',
                    'detail': f"{len(pareto)}个Pareto最优设计 ({pareto_rate:.1f}%)",
                    'time': '最近'
                })
        except (KeyError, TypeError, AttributeError):
            # 跳过格式错误的数据
            pass

        # Phase 8: 决策分析
        recommended = state.load('phase8', 'recommended_design')
        if _has_valid_data(recommended):  # ✅ DataFrame修复
            activities.append({
                'icon': 'fa-trophy',
                'color': 'success',
                'phase': 'Phase 8',
                'action': '完成决策分析',
                'detail': "已生成推荐设计方案",
                'time': '最近'
            })

        # 如果没有活动
        if not activities:
            return dbc.ListGroup([
                dbc.ListGroupItem([
                    html.Div([
                        html.Span("ℹ️", className="text-secondary me-2"),
                        "暂无活动记录。开始工作流后，活动将在此处显示。"
                    ])
                ])
            ], flush=True)

        # 倒序排列（最新的在最上面）
        activities.reverse()

        # 限制显示最多10条
        activities = activities[:10]

        # 生成活动列表
        activity_items = []
        for activity in activities:
            activity_items.append(
                dbc.ListGroupItem([
                    dbc.Row([
                        dbc.Col([
                            html.I(className=f"fas {activity['icon']} text-{activity['color']} me-2"),
                            html.Strong(activity['phase'], className="me-2"),
                            activity['action']
                        ], width=12, className="mb-1"),
                        dbc.Col([
                            html.Small(activity['detail'], className="text-muted")
                        ], width=12)
                    ]),
                    html.Div([
                        html.Small([
                            html.Span("🕐", className="me-1"),
                            activity['time']
                        ], className="text-muted float-end")
                    ])
                ])
            )

        return dbc.ListGroup(activity_items, flush=True)

    except Exception as e:
        import traceback
        print(f"生成活动日志失败: {e}")
        print(traceback.format_exc())

        return dbc.ListGroup([
            dbc.ListGroupItem([
                html.Div([
                    html.Span("⚠️", className="text-warning me-2"),
                    f"加载活动日志失败: {str(e)}"
                ])
            ], color="light")
        ], flush=True)

@callback(
    Output('activity-log', 'children', allow_duplicate=True),
    [Input('btn-clear-activity-log', 'n_clicks')],
    prevent_initial_call=True
)
def clear_activity_log(n_clicks):
    """清空活动日志（P2-11功能）"""
    if n_clicks:
        return dbc.ListGroup([
            dbc.ListGroupItem([
                html.Div([
                    html.Span("✓", className="text-success me-2"),
                    "活动日志已清空。新的活动将在此处显示。"
                ])
            ], color="light")
        ], flush=True)
    return no_update

