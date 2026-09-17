"""
Phase 1: 问题定义与价值映射
"""

from dash import html, dcc, callback, Input, Output, State, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import dash # 确保导入 dash

# 导入必要模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.state_manager import get_state_manager
from dash import no_update

def _fetch_full_phase1_data():
    """从数据库读取 Phase 1 的完整数据（内部通用函数）"""
    state = get_state_manager()
    
    # 辅助转换函数
    def _to_list(data):
        if isinstance(data, pd.DataFrame): return data.to_dict('records')
        return data if data else []

    def _dvm_to_dict(dvm_df):
        if isinstance(dvm_df, pd.DataFrame) and not dvm_df.empty:
            return {
                'design_vars': list(dvm_df.index), 
                'value_attrs': list(dvm_df.columns), 
                'matrix': dvm_df.values.tolist()
            }
        return {'design_vars': [], 'value_attrs': [], 'matrix': []}

    try:
        # 1. 核心数据
        mission = state.load('phase1', 'mission') or {}
        val_attrs = _to_list(state.load('phase1', 'value_attributes'))
        des_vars = _to_list(state.load('phase1', 'design_variables'))
        
        # 2. DVM 矩阵 (必须同步加载，否则会导致 UI 渲染错位)
        dvm_raw = state.load('phase1', 'dvm_matrix')
        dvm_matrix = _dvm_to_dict(dvm_raw)
        
        objectives = mission.get('key_objectives', [])
        
        # 3. UI 状态
        ui_state = state.load('phase1', 'ui_state') or {}
        title = ui_state.get('mission_title') or mission.get('title', '')
        desc = ui_state.get('mission_desc') or mission.get('description', '')
        thresh = ui_state.get('threshold', 0.65)
        
        return title, desc, val_attrs, des_vars, dvm_matrix, objectives, thresh, ui_state
        
    except Exception as e:
        print(f"❌ Phase 1 Data Fetch Error: {e}")
        return "", "", [], [], {'matrix':[]}, [], 0.65, {}
    


layout = dbc.Container([
    # 数据存储组件（用于保持UI状态）
    dcc.Store(id='phase1-value-attrs-store', data=[]),
    dcc.Store(id='phase1-design-vars-store', data=[]),
    dcc.Store(id='phase1-dvm-matrix-store', data={'design_vars': [], 'value_attrs': [], 'matrix': []}),
    dcc.Store(id='phase1-objectives-store', data=[]),
    # P0-3修复：编辑模式索引存储
    dcc.Store(id='editing-value-attr-index', data=None),
    dcc.Store(id='editing-design-var-index', data=None),
    # 刷新触发器（用于自动刷新1.3设计变量列表）
    dcc.Store(id='phase1-refresh-trigger', data=0),
    dcc.Store(id='phase1-ui-state', data={}),

    html.H2([
        html.Span("🎯", className="me-2"),
        "Phase 1: 问题定义与价值映射"
    ], className="mb-4"),

    # 任务意图定义
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("1.1 任务意图定义", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("项目名称"),
                    dbc.Input(id="input-mission-title", placeholder="例如：卫星雷达系统设计", className="mb-3"),

                    dbc.Label("项目描述"),
                    dbc.Textarea(id="input-mission-desc", placeholder="详细描述项目背景和目标...", rows=3, className="mb-3"),

                    dbc.Label("关键目标"),
                    dbc.InputGroup([
                        dbc.Input(id="input-objective", placeholder="输入目标并按回车添加"),
                        dbc.Button("添加", id="btn-add-objective", color="primary")
                    ], className="mb-3"),

                    html.Div(id="objectives-list", children=[
                        dbc.Alert("尚未添加目标", color="light", className="mb-0")
                    ])
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 价值属性定义
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("1.2 价值属性定义 (Y_val)", className="mb-0")),
                dbc.CardBody([
                    dbc.Button([
                        html.Span("➕", className="me-2"),
                        "添加价值属性"
                    ], id="btn-open-value-attr-modal", color="success", className="mb-3"),

                    # 价值属性列表
                    html.Div(id="value-attrs-list", className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 价值属性添加模态框
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("添加价值属性")),
        dbc.ModalBody([
            dbc.Label("属性名称"),
            dbc.Input(id="input-value-attr-name", placeholder="例如：resolution", className="mb-3"),

            dbc.Label("单位"),
            dbc.Input(id="input-value-attr-unit", placeholder="例如：m", className="mb-3"),

            dbc.Label("优化方向"),
            dbc.Select(
                id="select-value-attr-direction",
                options=[
                    {"label": "最小化 (越小越好)", "value": "minimize"},
                    {"label": "最大化 (越大越好)", "value": "maximize"}
                ],
                value="minimize",
                className="mb-3"
            ),

            dbc.Label("目标值 (可选)"),
            dbc.Input(id="input-value-attr-target", type="number", placeholder="例如：1.0", className="mb-3")
        ]),
        dbc.ModalFooter([
            dbc.Button("取消", id="btn-cancel-value-attr", color="secondary", className="me-2"),
            dbc.Button("确认添加", id="btn-confirm-value-attr", color="primary")
        ])
    ], id="modal-value-attr", size="lg", is_open=False),

    # 设计变量定义
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("1.3 设计变量注册 (X)", className="mb-0")),
                dbc.CardBody([
                    dbc.Button([
                        html.Span("➕", className="me-2"),
                        "添加设计变量"
                    ], id="btn-open-design-var-modal", color="info", className="mb-3"),

                    # 设计变量列表
                    html.Div(id="design-vars-list", className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 设计变量添加模态框
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("添加设计变量")),
        dbc.ModalBody([
            dbc.Label("变量名称"),
            dbc.Input(id="input-design-var-name", placeholder="例如：orbit_altitude", className="mb-3"),

            dbc.Label("变量类型"),
            dbc.Select(
                id="select-design-var-type",
                options=[
                    {"label": "连续 (Continuous)", "value": "continuous"},
                    {"label": "离散 (Discrete)", "value": "discrete"},
                    {"label": "分类 (Categorical)", "value": "categorical"}
                ],
                value="continuous",
                className="mb-3"
            ),

            dbc.Label("范围/选项"),
            dbc.Input(id="input-design-var-range", placeholder="连续：400-800；分类：L,S,C,X", className="mb-3"),

            dbc.Label("单位 (可选)"),
            dbc.Input(id="input-design-var-unit", placeholder="例如：km", className="mb-3")
        ]),
        dbc.ModalFooter([
            dbc.Button("取消", id="btn-cancel-design-var", color="secondary", className="me-2"),
            dbc.Button("确认添加", id="btn-confirm-design-var", color="primary")
        ])
    ], id="modal-design-var", size="lg", is_open=False),

    # DVM矩阵编辑器
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("1.4 DVM矩阵编辑 (设计-价值映射)", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "DVM矩阵评估每个设计变量对每个价值属性的影响程度。",
                        html.Br(),
                        "评分: 0=无影响, 1=弱影响, 3=中等影响, 9=强影响"
                    ], color="info", className="mb-3"),

                    html.Div(id="dvm-matrix-editor"),

                    dbc.Button([
                        html.Span("📊", className="me-2"),
                        "生成DVM热图"
                    ], id="btn-generate-dvm", color="primary", className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # DVM可视化
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("1.5 DVM热图可视化", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id="dvm-heatmap", figure=go.Figure())
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 关键变量识别
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("1.6 关键设计变量识别", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("影响阈值"),
                    dbc.Input(
                        id="input-threshold",
                        type="number",
                        value=0.65,
                        min=0,
                        max=1,
                        step=0.05,
                        className="mb-3"
                    ),
                    dbc.Button("识别关键变量", id="btn-identify-key-vars", color="warning"),
                    html.Hr(),
                    html.Div(id="key-vars-result")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 变量相关性分析 (P2-2)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("1.7 设计变量相关性分析", className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "散点矩阵可视化设计变量之间的相关性模式，帮助识别变量间的依赖关系"
                    ], color="info", className="mb-3"),

                    dbc.Button([
                        html.Span("📈", className="me-2"),
                        "生成变量相关性散点矩阵"
                    ], id="btn-generate-variable-correlation", color="primary", className="w-100 mb-3"),

                    dcc.Graph(id="variable-correlation-splom", figure=go.Figure())
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 数据保存/加载
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("数据管理", className="mb-0")),
                dbc.CardBody([
                    dbc.ButtonGroup([
                        dbc.Button([
                            html.Span("💾", className="me-2"),
                            "保存Phase 1数据"
                        ], id="btn-save-phase1", color="success", className="me-2"),
                        dbc.Button([
                            html.Span("📤", className="me-2"),
                            "加载Phase 1数据"
                        ], id="btn-load-phase1", color="info")
                    ]),
                    html.Div(id="phase1-save-status", className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ])
    ]),

    # 导航按钮
    dbc.Row([
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button([
                    html.Span("⬅️", className="me-2"),
                    "返回仪表盘"
                ], href="/", color="secondary", outline=True),
                dbc.Button([
                    "下一步: Phase 2",
                    html.Span("➡️", className="ms-2")
                ], href="/phase2", color="primary")
            ], className="w-100")
        ])
    ])
], fluid=True)




# ========== 数据自动加载回调 (新增修复) ==========

# [重要] 保留此函数以维持 1.2/1.3 与 3.2/3.3 的同步
@callback(
    [Output('phase1-value-attrs-store', 'data', allow_duplicate=True),
     Output('phase1-design-vars-store', 'data', allow_duplicate=True),
     Output('phase1-dvm-matrix-store', 'data', allow_duplicate=True)], # 同步 DVM 以防覆盖
    [Input('phase1-auto-load-trigger', 'data')],
    prevent_initial_call=True
)
def auto_load_phase1_data(trigger):
    """
    当外部模块（如 Phase 3）修改了设计变量时，自动同步 Phase 1 的 Store。
    必须同时刷新 DVM Matrix Store，否则旧的 Matrix Store 与新的变量列表不匹配，
    会导致 Render 函数渲染出空表格，进而触发 Update 保存空值。
    """
    if not trigger:
        return no_update, no_update, no_update
        
    # 复用读取逻辑，只取相关部分
    _, _, val_attrs, des_vars, dvm_matrix, _, _, _ = _fetch_full_phase1_data()
    
    print(f"🔄 Phase 1 Auto-Sync: Vars={len(des_vars)}, Attrs={len(val_attrs)}")
    return val_attrs, des_vars, dvm_matrix



# 控制价值属性模态框的开关
@callback(
    Output('modal-value-attr', 'is_open'),
    [Input('btn-open-value-attr-modal', 'n_clicks'),
     Input('btn-cancel-value-attr', 'n_clicks'),
     Input('btn-confirm-value-attr', 'n_clicks')],
    [State('modal-value-attr', 'is_open')],
    prevent_initial_call=True
)
def toggle_value_attr_modal(n_open, n_cancel, n_confirm, is_open):
    """控制价值属性模态框的显示/隐藏"""
    return not is_open

# 添加价值属性到Store
@callback(
    [Output('phase1-value-attrs-store', 'data'),
     Output('input-value-attr-name', 'value'),
     Output('input-value-attr-unit', 'value'),
     Output('select-value-attr-direction', 'value'),
     Output('input-value-attr-target', 'value'),
     Output('editing-value-attr-index', 'data', allow_duplicate=True)],
    [Input('btn-confirm-value-attr', 'n_clicks')],
    [State('phase1-value-attrs-store', 'data'),
     State('input-value-attr-name', 'value'),
     State('input-value-attr-unit', 'value'),
     State('select-value-attr-direction', 'value'),
     State('input-value-attr-target', 'value'),
     State('editing-value-attr-index', 'data')],
    prevent_initial_call=True
)
def add_or_edit_value_attr(n_clicks, current_data, name, unit, direction, target, editing_index):
    """添加或编辑价值属性（修复：同步到StateManager，且支持目标值为0）"""
    if n_clicks and name:
        # [核心修复] 允许 target 为 0，仅当为空字符串或None时才设为None
        final_target = None
        if target is not None and str(target).strip() != "":
            try:
                final_target = float(target)
            except ValueError:
                final_target = None

        new_attr = {
            'name': name,
            'unit': unit or '',
            'direction': direction,
            'target': final_target
        }

        # 判断是编辑模式还是新增模式
        if editing_index is not None and 0 <= editing_index < len(current_data):
            # 编辑模式：更新现有数据
            current_data[editing_index] = new_attr
            print(f"✅ Phase 1编辑价值属性: {name}, 索引={editing_index}")
        else:
            # 新增模式：追加新数据
            current_data.append(new_attr)
            print(f"✅ Phase 1新增价值属性: {name}")

        # 修复：同步保存到StateManager，确保Phase 4能读取到
        state = get_state_manager()
        state.save('phase1', 'value_attributes', current_data)
        print(f"📝 Phase 1已保存价值属性到StateManager: {len(current_data)}个")

        # 清空输入框并重置编辑索引
        return current_data, "", "", "minimize", "", None

    return no_update, no_update, no_update, no_update, no_update, no_update



# 从Store渲染价值属性列表
@callback(
    Output('value-attrs-list', 'children'),
    [Input('phase1-value-attrs-store', 'data')]
)
def render_value_attrs_list(value_attrs):
    """从Store渲染价值属性列表（支持标准JSON格式: name, unit, direction, weight）"""
    if not value_attrs:
        return dbc.Alert([
            html.Span("ℹ️", className="me-2"),
            "尚未添加价值属性"
        ], color="light")

    # 构建表格
    table_rows = []
    for i, attr in enumerate(value_attrs):
        direction_badge = dbc.Badge(
            "最小化" if attr.get('direction') == 'minimize' else "最大化",
            color="warning" if attr.get('direction') == 'minimize' else "success"
        )

        # 兼容两种格式：标准JSON使用weight，旧版使用target
        weight_or_target = attr.get('weight') or attr.get('target')
        weight_display = f"{weight_or_target:.2f}" if weight_or_target is not None else "N/A"

        table_rows.append(
            html.Tr([
                html.Td(html.Strong(attr.get('name', '未命名'))),
                html.Td(attr.get('unit', 'N/A')),
                html.Td(direction_badge),
                html.Td(weight_display),  # 显示权重或目标值
                html.Td(dbc.ButtonGroup([
                    dbc.Button(
                        "修改",
                        id={'type': 'btn-edit-value-attr', 'index': i},
                        color="info",
                        size="sm",
                        outline=True
                    ),
                    dbc.Button(
                        "转变量",
                        id={'type': 'btn-convert-attr-to-var', 'index': i},
                        color="warning",
                        size="sm",
                        outline=True
                    ),
                    dbc.Button(
                        "删除",
                        id={'type': 'btn-delete-value-attr', 'index': i},
                        color="danger",
                        size="sm",
                        outline=True
                    )
                ], size="sm"))
            ])
        )

    return dbc.Table([
        html.Thead([
            html.Tr([
                html.Th("属性名称"),
                html.Th("单位"),
                html.Th("优化方向"),
                html.Th("目标值"),
                html.Th("操作")
            ])
        ]),
        html.Tbody(table_rows)
    ], bordered=True, striped=True, hover=True, size='sm')

# Pattern-matching回调：删除价值属性
@callback(
    Output('phase1-value-attrs-store', 'data', allow_duplicate=True),
    [Input({'type': 'btn-delete-value-attr', 'index': ALL}, 'n_clicks')],
    [State('phase1-value-attrs-store', 'data')],
    prevent_initial_call=True
)
def delete_value_attr(n_clicks_list, current_data):
    """删除价值属性（修复：同步到StateManager）"""
    from dash import ctx

    if not any(n_clicks_list):
        return no_update

    # 获取点击的按钮索引
    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-delete-value-attr':
        index = triggered['index']
        current_data.pop(index)

        # 修复：同步保存到StateManager，确保Phase 4能读取到
        state = get_state_manager()
        state.save('phase1', 'value_attributes', current_data)

        return current_data

    return no_update

# P0-3修复 + P0-问题1修复：Pattern-matching回调 - 修改价值属性（从StateManager读取数据）
@callback(
    [Output('modal-value-attr', 'is_open', allow_duplicate=True),
     Output('input-value-attr-name', 'value', allow_duplicate=True),
     Output('input-value-attr-unit', 'value', allow_duplicate=True),
     Output('select-value-attr-direction', 'value', allow_duplicate=True),
     Output('input-value-attr-target', 'value', allow_duplicate=True),
     Output('editing-value-attr-index', 'data', allow_duplicate=True)],
    [Input({'type': 'btn-edit-value-attr', 'index': ALL}, 'n_clicks')],
    [State('phase1-value-attrs-store', 'data')],
    prevent_initial_call=True
)
def edit_value_attr(n_clicks_list, value_attrs_from_store):
    """修改价值属性 - 打开模态框并预填充数据（P0-问题1修复：从StateManager读取实时数据）"""
    from dash import ctx

    if not any(n_clicks_list):
        return no_update, no_update, no_update, no_update, no_update, no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-edit-value-attr':
        index = triggered['index']

        # P0-问题1修复：从StateManager读取最新数据，而不是依赖Store（可能过时）
        state = get_state_manager()
        value_attrs = state.load('phase1', 'value_attributes')

        # 如果StateManager没有数据，回退到Store
        # DataFrame修复：显式检查空数据
        if value_attrs is None or (isinstance(value_attrs, pd.DataFrame) and value_attrs.empty):
            value_attrs = value_attrs_from_store

        # DataFrame修复：显式检查数据有效性
        if value_attrs is not None and (not isinstance(value_attrs, pd.DataFrame) or not value_attrs.empty) and 0 <= index < len(value_attrs):
            # DataFrame修复：统一索引访问方式
            if isinstance(value_attrs, pd.DataFrame):
                attr = value_attrs.iloc[index].to_dict()  # 使用 .iloc[index] 访问 DataFrame 行
            else:
                attr = value_attrs[index]  # list 直接索引

            # 打开模态框，预填充数据，记录编辑索引
            return (
                True,  # 打开模态框
                attr['name'],
                attr['unit'],
                attr['direction'],
                str(attr.get('target')) if attr.get('target') is not None else '',
                index  # 记录编辑索引
            )

    return no_update, no_update, no_update, no_update, no_update, no_update

# P0-3修复：Pattern-matching回调 - 价值属性转设计变量
@callback(
    [Output('phase1-value-attrs-store', 'data', allow_duplicate=True),
     Output('phase1-design-vars-store', 'data', allow_duplicate=True)],
    [Input({'type': 'btn-convert-attr-to-var', 'index': ALL}, 'n_clicks')],
    [State('phase1-value-attrs-store', 'data'),
     State('phase1-design-vars-store', 'data')],
    prevent_initial_call=True
)
def convert_attr_to_var(n_clicks_list, value_attrs, design_vars):
    """价值属性转设计变量（DataFrame修复版 + StateManager同步）"""
    from dash import ctx

    if not any(n_clicks_list):
        return no_update, no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-convert-attr-to-var':
        index = triggered['index']

        # DataFrame修复：先转换为统一的list格式
        if isinstance(value_attrs, pd.DataFrame):
            value_attrs_list = value_attrs.to_dict('records')
        else:
            value_attrs_list = value_attrs if value_attrs else []

        if isinstance(design_vars, pd.DataFrame):
            design_vars_list = design_vars.to_dict('records')
        else:
            design_vars_list = design_vars if design_vars else []

        if 0 <= index < len(value_attrs_list):
            attr = value_attrs_list[index]

            # 转换为设计变量（假设连续型，范围需要用户后续调整）
            new_var = {
                'name': attr['name'],
                'type': 'continuous',
                'range': '0-100',  # 默认范围，用户可后续修改
                'unit': attr.get('unit', '')
            }

            # 从价值属性列表移除
            updated_attrs = [a for i, a in enumerate(value_attrs_list) if i != index]
            # 添加到设计变量列表
            updated_vars = design_vars_list + [new_var]

            # 修复：同时保存到StateManager，确保数据一致性
            state = get_state_manager()
            state.save('phase1', 'value_attributes', updated_attrs)
            state.save('phase1', 'design_variables', updated_vars)

            return updated_attrs, updated_vars

    return no_update, no_update

# =============================================================================
# DVM矩阵交互编辑回调 (带调试探针版)
# =============================================================================

# 渲染DVM矩阵编辑器
@callback(
    Output('dvm-matrix-editor', 'children'),
    [Input('phase1-design-vars-store', 'data'),
     Input('phase1-value-attrs-store', 'data'),
     Input('phase1-dvm-matrix-store', 'data')]
)
def render_dvm_matrix_editor(design_vars, value_attrs, dvm_matrix):
    """
    渲染可编辑的DVM矩阵
    """
    import pandas as pd
    import numpy as np
    
    if not design_vars or not value_attrs:
        return dbc.Alert([
            html.Span("⚠️", className="me-2"),
            "请先添加设计变量和价值属性后再编辑DVM矩阵"
        ], color="warning")

    # 1. 获取当前的目标行/列名
    current_rows = [var.get('name', f'Var_{i}') for i, var in enumerate(design_vars)]
    current_cols = [attr.get('name', f'Attr_{i}') for i, attr in enumerate(value_attrs)]

    # 2. 准备矩阵数据容器
    df_display = pd.DataFrame(0, index=current_rows, columns=current_cols)

    # 3. 尝试回填已保存的数据 (Store -> UI)
    if dvm_matrix and dvm_matrix.get('matrix'):
        try:
            df_saved = pd.DataFrame(
                dvm_matrix['matrix'], 
                index=dvm_matrix['design_vars'], 
                columns=dvm_matrix['value_attrs']
            )
            df_display.update(df_saved)
        except Exception:
            pass

    # 4. 构建表格 UI
    matrix_values = df_display.fillna(0).astype(int).values.tolist()

    header_row = html.Tr([
        html.Th("设计变量 \\ 价值属性", className="text-center bg-light", style={'width': '200px'}),
        *[html.Th(attr_name, className="text-center") for attr_name in current_cols]
    ])

    data_rows = []
    for i, var_name in enumerate(current_rows):
        cells = [html.Td(html.Strong(var_name), className="bg-light")]

        for j, col_name in enumerate(current_cols):
            if i < len(matrix_values) and j < len(matrix_values[0]):
                val = matrix_values[i][j]
            else:
                val = 0

            cells.append(
                html.Td(
                    dbc.Select(
                        id={'type': 'dvm-cell', 'row': i, 'col': j},
                        options=[
                            {'label': '0 (无影响)', 'value': '0'},
                            {'label': '1 (弱影响)', 'value': '1'},
                            {'label': '3 (中等影响)', 'value': '3'},
                            {'label': '9 (强影响)', 'value': '9'}
                        ],
                        value=str(val),
                        size="sm",
                        className="text-center"
                    ),
                    className="p-1",
                    style={'minWidth': '100px'}
                )
            )

        data_rows.append(html.Tr(cells))

    return dbc.Table(
        [html.Thead(header_row), html.Tbody(data_rows)],
        bordered=True, hover=True, striped=True, size='sm', className="mb-0"
    )


# DVM矩阵编辑时实时保存
@callback(
    Output('phase1-dvm-matrix-store', 'data', allow_duplicate=True),
    [Input({'type': 'dvm-cell', 'row': ALL, 'col': ALL}, 'value')],
    [State('phase1-design-vars-store', 'data'),
     State('phase1-value-attrs-store', 'data')],
    prevent_initial_call=True
)
def update_dvm_matrix_on_edit(all_cell_values, design_vars, value_attrs):
    """
    当用户编辑DVM单元格时：
    1. 检查触发源：只有明确是用户点击(triggered_id有效)时才保存。
    2. 基于全量 UI 状态重建 DataFrame。
    3. 保存到数据库。
    """
    from dash import ctx
    import pandas as pd
    import numpy as np

    # === [核心防御] 过滤非用户意图的触发 ===
    # 如果是由页面刷新、组件重绘导致的批量触发，triggered_id 通常不符合预期
    # 我们只响应明确的单点修改（用户点击下拉菜单）
    if not ctx.triggered_id or not isinstance(ctx.triggered_id, dict):
        return no_update
    
    if ctx.triggered_id.get('type') != 'dvm-cell':
        return no_update
    # ====================================

    # 1. 基础校验
    if not design_vars or not value_attrs:
        return no_update

    # 2. 获取当前的行列定义
    rows = [var.get('name') for var in design_vars]
    cols = [attr.get('name') for attr in value_attrs]
    n_rows = len(rows)
    n_cols = len(cols)

    if n_rows == 0 or n_cols == 0:
        return no_update

    # 3. 解析全量 UI 数据 (Source of Truth)
    matrix = np.zeros((n_rows, n_cols), dtype=int)
    try:
        # ctx.inputs_list[0] 包含所有 dvm-cell 的当前值
        all_inputs = ctx.inputs_list[0]
        
        for item in all_inputs:
            # 确保 ID 结构完整
            if 'id' not in item or 'row' not in item['id'] or 'col' not in item['id']:
                continue
                
            row_idx = item['id']['row']
            col_idx = item['id']['col']
            val_raw = item.get('value', '0')
            
            # 安全转换为整数
            try:
                val = int(val_raw) if val_raw is not None else 0
            except (ValueError, TypeError):
                val = 0
            
            # 填入矩阵
            if 0 <= row_idx < n_rows and 0 <= col_idx < n_cols:
                matrix[row_idx, col_idx] = val

    except Exception as e:
        print(f"❌ DVM Matrix Reconstruct Error: {e}")
        return no_update

    # 4. 执行保存
    # 既然确认是用户操作，那么 UI 上的数据就是最新的真理
    try:
        df_current = pd.DataFrame(matrix, index=rows, columns=cols)
        
        state = get_state_manager()
        state.save('phase1', 'dvm_matrix', df_current)
        # print(f"✅ DVM User Edit Saved: {n_rows}x{n_cols}")
        
    except Exception as e:
        print(f"❌ DVM Save Failed: {e}")

    # 5. 更新前端 Store
    return {
        'design_vars': rows,
        'value_attrs': cols,
        'matrix': matrix.tolist()
    }


# ========== 设计变量相关回调 ==========

# 控制设计变量模态框的开关
@callback(
    Output('modal-design-var', 'is_open'),
    [Input('btn-open-design-var-modal', 'n_clicks'),
     Input('btn-cancel-design-var', 'n_clicks'),
     Input('btn-confirm-design-var', 'n_clicks')],
    [State('modal-design-var', 'is_open')],
    prevent_initial_call=True
)
def toggle_design_var_modal(n_open, n_cancel, n_confirm, is_open):
    """控制设计变量模态框的显示/隐藏"""
    return not is_open

# 添加或编辑设计变量到Store
@callback(
    [Output('phase1-design-vars-store', 'data'),
     Output('input-design-var-name', 'value'),
     Output('select-design-var-type', 'value'),
     Output('input-design-var-range', 'value'),
     Output('input-design-var-unit', 'value'),
     Output('editing-design-var-index', 'data', allow_duplicate=True),
     Output('phase1-refresh-trigger', 'data', allow_duplicate=True)],
    [Input('btn-confirm-design-var', 'n_clicks')],
    [State('phase1-design-vars-store', 'data'),
     State('input-design-var-name', 'value'),
     State('select-design-var-type', 'value'),
     State('input-design-var-range', 'value'),
     State('input-design-var-unit', 'value'),
     State('editing-design-var-index', 'data'),
     State('phase1-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def add_or_edit_design_var(n_clicks, current_data, name, var_type, var_range, unit, editing_index, current_trigger):
    """添加或编辑设计变量（修复：同步到StateManager + 解析range为min/max + 处理方括号）"""
    if n_clicks and name and var_range:
        # 🔧 修复：移除方括号、中括号等包裹符号
        cleaned_range = var_range.strip()
        if cleaned_range.startswith('[') and cleaned_range.endswith(']'):
            cleaned_range = cleaned_range[1:-1].strip()
        elif cleaned_range.startswith('(') and cleaned_range.endswith(')'):
            cleaned_range = cleaned_range[1:-1].strip()

        # 基础变量字典（保存原始输入和清理后的值）
        new_var = {
            'name': name,
            'type': var_type,
            'range': cleaned_range,  # 保存清理后的range
            'unit': unit or ''
        }

        # 对于连续型和离散型变量，解析range字符串为min/max（确保Phase 4能正确显示）
        if var_type in ['continuous', 'discrete']:
            if '-' in cleaned_range and ',' not in cleaned_range:
                # 范围格式：min-max（如 "0-100"）
                try:
                    parts = cleaned_range.split('-')
                    if len(parts) == 2:
                        new_var['min'] = float(parts[0].strip())
                        new_var['max'] = float(parts[1].strip())
                except (ValueError, IndexError):
                    # 如果解析失败，保持原样，只有range字段
                    pass
            elif ',' in cleaned_range or '，' in cleaned_range:
                # 离散值格式：逗号分隔（如 "1,5,10" 或 "[1,5,10]"）
                try:
                    # 统一处理中文和英文逗号
                    normalized_range = cleaned_range.replace('，', ',')
                    values = [float(v.strip()) for v in normalized_range.split(',') if v.strip()]
                    new_var['values'] = values
                    new_var['min'] = min(values)
                    new_var['max'] = max(values)
                    print(f"✅ Phase 1保存 - 离散变量: name={name}, 原始输入={var_range}, 解析values={values}")
                except (ValueError, IndexError) as e:
                    # 如果解析失败，保持原样
                    print(f"❌ Phase 1保存 - 离散变量解析失败: name={name}, range={var_range}, error={e}")
                    pass

        # 对于分类变量，解析values
        elif var_type == 'categorical':
            # 统一处理中文和英文逗号
            normalized_range = cleaned_range.replace('，', ',')
            if ',' in normalized_range:
                new_var['values'] = [v.strip() for v in normalized_range.split(',') if v.strip()]
            else:
                new_var['values'] = [normalized_range.strip()]

            # 调试：打印分类变量解析结果
            print(f"✅ Phase 1保存 - 分类变量: name={name}, 原始输入={var_range}, 解析values={new_var['values']}, 完整数据={new_var}")

        # 判断是编辑模式还是新增模式
        if editing_index is not None and 0 <= editing_index < len(current_data):
            # 编辑模式：更新现有数据
            current_data[editing_index] = new_var
            print(f"✅ Phase 1编辑设计变量: {name}, 索引={editing_index}")
        else:
            # 新增模式：追加新数据
            current_data.append(new_var)
            print(f"✅ Phase 1新增设计变量: {name}")

        # 修复：同步保存到StateManager，确保Phase 4能读取到
        state = get_state_manager()
        state.save('phase1', 'design_variables', current_data)
        print(f"📝 Phase 1已保存设计变量到StateManager: {len(current_data)}个")

        # 清空输入框并重置编辑索引，递增刷新触发器
        return current_data, "", "continuous", "", "", None, (current_trigger or 0) + 1

    return no_update, no_update, no_update, no_update, no_update, no_update, no_update

# 从Store渲染设计变量列表（修复：监听refresh-trigger实现自动刷新）
@callback(
    Output('design-vars-list', 'children'),
    [Input('phase1-design-vars-store', 'data'),
     Input('phase1-refresh-trigger', 'data')]
)
def render_design_vars_list(design_vars, refresh_trigger):
    """从Store渲染设计变量列表（支持标准JSON格式: name, unit, min, max, default + 自动刷新）"""
    if not design_vars:
        return dbc.Alert([
            html.Span("ℹ️", className="me-2"),
            "尚未添加设计变量"
        ], color="light")

    # 构建表格
    table_rows = []
    for i, var in enumerate(design_vars):
        # 自动推导type：如果有min/max则为连续型
        var_type = var.get('type', 'continuous' if 'min' in var or 'max' in var else 'unknown')

        type_map = {
            'continuous': ('连续', 'primary'),
            'discrete': ('离散', 'info'),
            'categorical': ('分类', 'warning'),
            'unknown': ('未知', 'secondary')
        }
        type_label, type_color = type_map.get(var_type, ('未知', 'secondary'))
        type_badge = dbc.Badge(type_label, color=type_color)

        # 自动生成range字符串：根据变量类型智能显示（P0-完整修复：防御性重新解析）
        if var_type == 'categorical':
            # 分类变量：优先显示values完整列表，否则尝试从range解析
            values = var.get('values', [])
            if values:
                # 显示所有分类值（不截断）
                range_display = ", ".join(map(str, values))
            elif 'range' in var and var['range']:
                # 防御性修复：如果values丢失但range存在，尝试重新解析
                range_str = var['range']
                if ',' in range_str or '，' in range_str:
                    # 尝试从逗号分隔的range重新解析values
                    normalized_range = range_str.replace('，', ',')
                    parsed_values = [v.strip() for v in normalized_range.split(',') if v.strip()]
                    range_display = ", ".join(parsed_values)
                else:
                    range_display = range_str
            else:
                range_display = "N/A"
        elif var_type == 'discrete':
            # 离散型：优先显示values完整列表，其次尝试从range解析
            values = var.get('values', [])
            if values:
                # 显示所有离散值（不截断，确保用户能看到完整列表）
                range_display = ", ".join(map(str, values))
            elif 'range' in var and var['range']:
                # 防御性修复：如果values丢失但range存在，尝试重新解析
                range_str = var['range']
                if ',' in range_str or '，' in range_str:
                    # 尝试从逗号分隔的range重新解析values
                    normalized_range = range_str.replace('，', ',')
                    try:
                        parsed_values = [float(v.strip()) for v in normalized_range.split(',') if v.strip()]
                        range_display = ", ".join(map(str, parsed_values))
                    except ValueError:
                        range_display = range_str
                else:
                    range_display = range_str
            elif 'min' in var and 'max' in var:
                range_display = f"[{var['min']}, {var['max']}]"
            else:
                range_display = "N/A"
        elif var_type == 'continuous':
            # 连续型：优先显示range字段，否则从min/max构造
            if 'range' in var and var['range']:
                range_display = var['range']
            elif 'min' in var and 'max' in var:
                # 连续型：从min/max构造范围
                range_display = f"[{var['min']}, {var['max']}]"
            else:
                range_display = "N/A"
        else:
            # 其他类型：直接显示range或N/A
            range_display = var.get('range', 'N/A')

        table_rows.append(
            html.Tr([
                html.Td(html.Strong(var.get('name', '未命名'))),
                html.Td(type_badge),
                html.Td(range_display),
                html.Td(var.get('unit', 'N/A')),
                html.Td(dbc.ButtonGroup([
                    dbc.Button(
                        "修改",
                        id={'type': 'btn-edit-design-var', 'index': i},
                        color="info",
                        size="sm",
                        outline=True
                    ),
                    dbc.Button(
                        "转属性",
                        id={'type': 'btn-convert-var-to-attr', 'index': i},
                        color="warning",
                        size="sm",
                        outline=True
                    ),
                    dbc.Button(
                        "删除",
                        id={'type': 'btn-delete-design-var', 'index': i},
                        color="danger",
                        size="sm",
                        outline=True
                    )
                ], size="sm"))
            ])
        )

    return dbc.Table([
        html.Thead([
            html.Tr([
                html.Th("变量名称"),
                html.Th("类型"),
                html.Th("范围/选项"),
                html.Th("单位"),
                html.Th("操作")
            ])
        ]),
        html.Tbody(table_rows)
    ], bordered=True, striped=True, hover=True, size='sm')

# Pattern-matching回调：删除设计变量
@callback(
    [Output('phase1-design-vars-store', 'data', allow_duplicate=True),
     Output('phase1-refresh-trigger', 'data', allow_duplicate=True)],
    [Input({'type': 'btn-delete-design-var', 'index': ALL}, 'n_clicks')],
    [State('phase1-design-vars-store', 'data'),
     State('phase1-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def delete_design_var(n_clicks_list, current_data, current_trigger):
    """删除设计变量（修复：同步到StateManager + 自动刷新）"""
    from dash import ctx

    if not any(n_clicks_list):
        return no_update, no_update

    # 获取点击的按钮索引
    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-delete-design-var':
        index = triggered['index']
        current_data.pop(index)

        # 修复：同步保存到StateManager，确保Phase 4能读取到
        state = get_state_manager()
        state.save('phase1', 'design_variables', current_data)

        # 递增刷新触发器
        return current_data, (current_trigger or 0) + 1

    return no_update, no_update

# P0-3修复 + P0-问题1修复：Pattern-matching回调 - 修改设计变量（从StateManager读取数据）
@callback(
    [Output('modal-design-var', 'is_open', allow_duplicate=True),
     Output('input-design-var-name', 'value', allow_duplicate=True),
     Output('select-design-var-type', 'value', allow_duplicate=True),
     Output('input-design-var-range', 'value', allow_duplicate=True),
     Output('input-design-var-unit', 'value', allow_duplicate=True),
     Output('editing-design-var-index', 'data', allow_duplicate=True)],
    [Input({'type': 'btn-edit-design-var', 'index': ALL}, 'n_clicks')],
    [State('phase1-design-vars-store', 'data')],
    prevent_initial_call=True
)
def edit_design_var(n_clicks_list, design_vars_from_store):
    """修改设计变量 - 打开模态框并预填充数据（P0-问题1修复：从StateManager读取实时数据）"""
    from dash import ctx

    if not any(n_clicks_list):
        return no_update, no_update, no_update, no_update, no_update, no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-edit-design-var':
        index = triggered['index']

        # P0-问题1修复：从StateManager读取最新数据，而不是依赖Store（可能过时）
        state = get_state_manager()
        design_vars = state.load('phase1', 'design_variables')

        # 如果StateManager没有数据，回退到Store
        # DataFrame修复：显式检查空数据
        if design_vars is None or (isinstance(design_vars, pd.DataFrame) and design_vars.empty):
            design_vars = design_vars_from_store

        # DataFrame修复：显式检查数据有效性
        if design_vars is not None and (not isinstance(design_vars, pd.DataFrame) or not design_vars.empty) and 0 <= index < len(design_vars):
            # DataFrame修复：统一索引访问方式
            if isinstance(design_vars, pd.DataFrame):
                var = design_vars.iloc[index].to_dict()  # 使用 .iloc[index] 访问 DataFrame 行
            else:
                var = design_vars[index]  # list 直接索引

            # 修复：如果range字段为空，从values字段重构range字符串（确保分类/离散变量能正确编辑）
            var_range = var.get('range', '')
            if not var_range and var.get('values'):
                # 从values重构range字符串
                var_type = var.get('type', 'continuous')
                if var_type == 'categorical':
                    # 分类变量：逗号分隔字符串
                    var_range = ', '.join(map(str, var['values']))
                elif var_type == 'discrete':
                    # 离散变量：逗号分隔数值
                    var_range = ', '.join(map(str, var['values']))

            # 打开模态框，预填充数据，记录编辑索引
            return (
                True,  # 打开模态框
                var['name'],
                var['type'],
                var_range,  # 使用重构的range字符串
                var.get('unit', ''),
                index  # 记录编辑索引
            )

    return no_update, no_update, no_update, no_update, no_update, no_update

# P0-3修复：Pattern-matching回调 - 设计变量转价值属性（修复：自动刷新）
@callback(
    [Output('phase1-design-vars-store', 'data', allow_duplicate=True),
     Output('phase1-value-attrs-store', 'data', allow_duplicate=True),
     Output('phase1-refresh-trigger', 'data', allow_duplicate=True)],
    [Input({'type': 'btn-convert-var-to-attr', 'index': ALL}, 'n_clicks')],
    [State('phase1-design-vars-store', 'data'),
     State('phase1-value-attrs-store', 'data'),
     State('phase1-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def convert_var_to_attr(n_clicks_list, design_vars, value_attrs, current_trigger):
    """设计变量转价值属性（DataFrame修复版 + StateManager同步 + 自动刷新）"""
    from dash import ctx

    if not any(n_clicks_list):
        return no_update, no_update, no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-convert-var-to-attr':
        index = triggered['index']

        # DataFrame修复：先转换为统一的list格式
        if isinstance(design_vars, pd.DataFrame):
            design_vars_list = design_vars.to_dict('records')
        else:
            design_vars_list = design_vars if design_vars else []

        if isinstance(value_attrs, pd.DataFrame):
            value_attrs_list = value_attrs.to_dict('records')
        else:
            value_attrs_list = value_attrs if value_attrs else []

        if 0 <= index < len(design_vars_list):
            var = design_vars_list[index]

            # 转换为价值属性（假设最小化优化方向）
            new_attr = {
                'name': var['name'],
                'unit': var.get('unit', ''),
                'direction': 'minimize',  # 默认最小化，用户可后续修改
                'target': None  # 无默认目标值
            }

            # 从设计变量列表移除
            updated_vars = [v for i, v in enumerate(design_vars_list) if i != index]
            # 添加到价值属性列表
            updated_attrs = value_attrs_list + [new_attr]

            # 修复：同时保存到StateManager，确保数据一致性
            state = get_state_manager()
            state.save('phase1', 'design_variables', updated_vars)
            state.save('phase1', 'value_attributes', updated_attrs)

            # 递增刷新触发器
            return updated_vars, updated_attrs, (current_trigger or 0) + 1

    return no_update, no_update, no_update

# ========== 关键目标管理回调 ==========

# 修改：添加目标时实时保存
@callback(
    [Output('phase1-objectives-store', 'data'),
     Output('input-objective', 'value')],
    [Input('btn-add-objective', 'n_clicks')],
    [State('input-objective', 'value'),
     State('phase1-objectives-store', 'data'),
     # 新增：读取当前标题和描述，以便一起保存
     State('input-mission-title', 'value'),
     State('input-mission-desc', 'value')],
    prevent_initial_call=True
)
def add_objective_to_store(n_clicks, objective_text, current_objectives, title, desc):
    """添加关键目标到Store并实时保存到数据库"""
    if n_clicks and objective_text and objective_text.strip():
        if current_objectives is None:
            current_objectives = []

        # 更新列表
        current_objectives.append(objective_text.strip())

        # === 实时保存逻辑 ===
        state = get_state_manager()
        mission_data = {
            'title': title or '',
            'description': desc or '',
            'key_objectives': current_objectives
        }
        state.save('phase1', 'mission', mission_data)
        print(f"✅ 关键目标已实时保存: {len(current_objectives)}个")
        # ===================

        return current_objectives, ""

    return no_update, no_update

# 根据Store数据渲染目标列表
@callback(
    Output('objectives-list', 'children'),
    [Input('phase1-objectives-store', 'data')]
)
def render_objectives_list(objectives):
    """根据Store数据渲染目标列表"""
    if not objectives or len(objectives) == 0:
        return dbc.Alert("尚未添加目标", color="light", className="mb-0")

    # 生成列表项，每项都有pattern-matching删除按钮
    list_items = []
    for i, obj_text in enumerate(objectives):
        list_items.append(
            dbc.ListGroupItem([
                html.Span("✓", className="text-success me-2"),
                obj_text,
                dbc.Button(
                    "×",
                    id={'type': 'btn-delete-objective', 'index': i},
                    size="sm",
                    color="danger",
                    outline=True,
                    className="float-end"
                )
            ])
        )

    return dbc.ListGroup(list_items)

# 修改：删除目标时实时保存
@callback(
    Output('phase1-objectives-store', 'data', allow_duplicate=True),
    Input({'type': 'btn-delete-objective', 'index': ALL}, 'n_clicks'),
    [State('phase1-objectives-store', 'data'),
     # 新增：读取当前标题和描述
     State('input-mission-title', 'value'),
     State('input-mission-desc', 'value')],
    prevent_initial_call=True
)
def delete_objective(n_clicks_list, current_objectives, title, desc):
    """删除指定的目标并实时保存"""
    from dash import ctx

    if not any(n_clicks_list):
        return no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-delete-objective':
        obj_index = triggered['index']

        if current_objectives and 0 <= obj_index < len(current_objectives):
            # 更新列表
            updated_objectives = [obj for i, obj in enumerate(current_objectives) if i != obj_index]
            
            # === 实时保存逻辑 ===
            state = get_state_manager()
            mission_data = {
                'title': title or '',
                'description': desc or '',
                'key_objectives': updated_objectives
            }
            state.save('phase1', 'mission', mission_data)
            print(f"✅ 关键目标已删除并保存，剩余: {len(updated_objectives)}个")
            # ===================

            return updated_objectives

    return no_update


# 识别关键变量回调
@callback(
    Output('key-vars-result', 'children'),
    [Input('btn-identify-key-vars', 'n_clicks')],
    [State('input-threshold', 'value'),
     State('phase1-dvm-matrix-store', 'data'),  # 新增: 读取DVM矩阵
     State('phase1-design-vars-store', 'data')],  # 新增: 读取设计变量
    prevent_initial_call=True
)
def identify_key_variables(n_clicks, threshold, dvm_matrix, design_vars):
    """识别关键设计变量 - 基于实际DVM矩阵"""
    if not n_clicks:
        return dash.no_update

    # 检查 DVM 矩阵是否已生成
    if not dvm_matrix or not dvm_matrix.get('matrix'):
        return dbc.Alert([
            html.Span("⚠️", className="me-2"),
            "请先生成 DVM 矩阵（在上方点击'生成DVM矩阵'按钮）"
        ], color="warning")

    # 从实际数据中提取
    matrix = dvm_matrix['matrix']  # 2D array: [[9,3,...], [3,9,...], ...]
    var_names = dvm_matrix['design_vars']  # ['frequency', 'antenna_diameter', ...]

    # 计算每个变量的平均影响强度（归一化到 0-1）
    influences = []
    for i, var_name in enumerate(var_names):
        row_values = matrix[i]  # 该变量对所有价值属性的影响
        avg_influence = sum(row_values) / (len(row_values) * 9)  # 归一化（DVM评分最大值为9）
        influences.append(avg_influence)

    # 根据阈值过滤关键变量
    key_vars = [
        {"name": var_name, "influence": inf}
        for var_name, inf in zip(var_names, influences)
        if inf >= threshold
    ]

    # 显示结果
    if key_vars:
        return dbc.Alert([
            html.H5([
                html.Span("⭐", className="me-2"),
                f"识别到 {len(key_vars)} 个关键变量"
            ], className="alert-heading"),
            html.Hr(),
            dbc.ListGroup([
                dbc.ListGroupItem([
                    html.Strong(var["name"]),
                    dbc.Badge(f"{var['influence']:.2%}", color="success", className="float-end")
                ])
                for var in key_vars
            ], flush=True),
            html.P(f"阈值: {threshold:.0%}", className="mt-2 mb-0 text-muted")
        ], color="success")
    else:
        return dbc.Alert([
            html.Span("⚠️", className="me-2"),
            f"在阈值 {threshold:.0%} 下未发现关键变量。建议降低阈值。"
        ], color="warning")

# 生成DVM热图回调
@callback(
    Output('dvm-heatmap', 'figure'),
    [Input('btn-generate-dvm', 'n_clicks'),
     Input('phase1-dvm-matrix-store', 'data')],  # 监听Store变化
    [State('phase1-design-vars-store', 'data'),
     State('phase1-value-attrs-store', 'data')],
    prevent_initial_call=True
)
def generate_dvm_heatmap(n_clicks, dvm_matrix, design_vars, value_attrs):
    """生成DVM热图（P2-1增强版：自动更新）"""
    from dash import ctx

    # 检查是否有数据
    if not design_vars or not value_attrs:
        fig = go.Figure()
        fig.add_annotation(
            text="请先添加设计变量和价值属性！",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font_size=16, font_color="red"
        )
        fig.update_layout(title="DVM矩阵", height=500)
        return fig

    # 提取变量名称
    design_var_names = [var['name'] for var in design_vars]
    value_attr_names = [attr['name'] for attr in value_attrs]

    # 获取矩阵数据
    if dvm_matrix and dvm_matrix.get('matrix'):
        import numpy as np
        matrix = np.array(dvm_matrix['matrix'])
    else:
        # 如果矩阵为空，使用全0矩阵
        import numpy as np
        matrix = np.zeros((len(design_vars), len(value_attrs)), dtype=int)

    # 创建热图
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=value_attr_names,
        y=design_var_names,
        colorscale='RdYlGn',
        text=matrix,
        texttemplate='%{text}',
        textfont={"size": 14},
        colorbar=dict(title="影响强度"),
        hovertemplate='设计变量: %{y}<br>价值属性: %{x}<br>影响强度: %{z}<extra></extra>'
    ))

    fig.update_layout(
        title=f"设计-价值映射矩阵 (DVM Matrix)<br><sub>{len(design_vars)}个变量 × {len(value_attrs)}个属性</sub>",
        xaxis_title="价值属性 (Y_val)",
        yaxis_title="设计变量 (X)",
        height=max(500, 50 * len(design_vars) + 100)  # 根据变量数量动态调整高度
    )

    return fig


# 保存Phase 1数据到StateManager
@callback(
    Output('phase1-save-status', 'children'),
    [Input('btn-save-phase1', 'n_clicks')],
    [State('input-mission-title', 'value'),
     State('input-mission-desc', 'value'),
     State('phase1-objectives-store', 'data'),
     State('phase1-value-attrs-store', 'data'),
     State('phase1-design-vars-store', 'data'),
     State('phase1-dvm-matrix-store', 'data'),
     State('input-threshold', 'value')], # 新增: 获取阈值状态
    prevent_initial_call=True
)
def save_phase1_data(n_clicks, mission_title, mission_desc, objectives, value_attrs, design_vars, dvm_matrix, threshold):
    """保存Phase 1数据到StateManager（P2-3.4增强版 + Threshold UI状态）"""
    if n_clicks:
        state = get_state_manager()

        # 1. 保存任务定义 (核心数据)
        mission_data = {
            'title': mission_title or '未命名任务',
            'description': mission_desc or '',
            'key_objectives': objectives if objectives else [],
            'value_proposition': mission_desc or ''
        }
        state.save('phase1', 'mission', mission_data)

        # 2. 保存列表数据 (核心数据)
        if value_attrs: state.save('phase1', 'value_attributes', value_attrs)
        if design_vars: state.save('phase1', 'design_variables', design_vars)

        # 3. 保存DVM矩阵 (核心数据)
        if dvm_matrix and dvm_matrix.get('matrix'):
            import pandas as pd
            matrix_data = dvm_matrix['matrix']
            design_var_names = dvm_matrix['design_vars']
            value_attr_names = dvm_matrix['value_attrs']
            dvm_df = pd.DataFrame(matrix_data, index=design_var_names, columns=value_attr_names)
            state.save('phase1', 'dvm_matrix', dvm_df)
            
        # 4. [新增] 保存 UI 状态 (Threshold, Title, Desc)
        # 将输入框的状态也作为 UI State 保存，以便刷新页面时回显
        ui_state = {
            'mission_title': mission_title,
            'mission_desc': mission_desc,
            'threshold': threshold
        }
        state.save('phase1', 'ui_state', ui_state)

        n_value_attrs = len(value_attrs) if value_attrs else 0
        n_design_vars = len(design_vars) if design_vars else 0

        return dbc.Alert([
            "✓",
            html.H5("Phase 1数据已保存 (含UI配置)", className="alert-heading"),
            html.Hr(),
            html.P([
                html.Strong("任务名称: "), mission_title or "未命名", html.Br(),
                html.Strong("价值属性: "), f"{n_value_attrs} 个", html.Br(),
                html.Strong("设计变量: "), f"{n_design_vars} 个", html.Br(),
                html.Strong("DVM矩阵: "), "已保存" if dvm_matrix.get('matrix') else "未生成", html.Br(),
                html.Strong("分析阈值: "), str(threshold)
            ])
        ], color="success")

    return ""


# 主动加载回调 (页面刷新 或 点击加载按钮)
@callback(
    [Output('input-mission-title', 'value'),
     Output('input-mission-desc', 'value'),
     Output('phase1-value-attrs-store', 'data', allow_duplicate=True),
     Output('phase1-design-vars-store', 'data', allow_duplicate=True),
     Output('phase1-dvm-matrix-store', 'data', allow_duplicate=True),
     Output('phase1-objectives-store', 'data', allow_duplicate=True),
     Output('input-threshold', 'value'), 
     Output('phase1-save-status', 'children', allow_duplicate=True),
     Output('phase1-ui-state', 'data', allow_duplicate=True)], 
    [Input('btn-load-phase1', 'n_clicks'),
     Input('url', 'pathname')], 
    prevent_initial_call='initial_duplicate'
)
def load_phase1_data(n_clicks, pathname):
    from dash import ctx
    triggered_id = ctx.triggered_id
    
    # 仅在 Phase 1 页面加载或点击按钮时触发
    if triggered_id == 'url' and pathname != '/phase1' and pathname != '/':
        return [no_update] * 9
        
    # 读取全量数据
    # _fetch_full_phase1_data 返回顺序: 
    # title, desc, val_attrs, des_vars, dvm_matrix, objectives, thresh, ui_state
    data = _fetch_full_phase1_data()
    
    # 解包数据以便重新排序
    (title, desc, val_attrs, des_vars, dvm_matrix, objectives, thresh, ui_state) = data
    
    # 生成提示信息
    msg = no_update
    if triggered_id == 'btn-load-phase1':
        msg = dbc.Alert(["✓", "数据加载成功"], color="success")
        
    # [关键修复] 调整返回顺序以匹配 Output 定义
    # Output 8: phase1-save-status (children) -> 需要 msg
    # Output 9: phase1-ui-state (data) -> 需要 ui_state
    return title, desc, val_attrs, des_vars, dvm_matrix, objectives, thresh, msg, ui_state


   

# P2-2功能：设计变量相关性分析（散点矩阵）
@callback(
    Output('variable-correlation-splom', 'figure'),
    Input('btn-generate-variable-correlation', 'n_clicks'),
    [State('phase1-design-vars-store', 'data')],
    prevent_initial_call=True
)
def generate_variable_correlation(n_clicks, design_vars):
    """生成设计变量相关性散点矩阵（P2-2核心功能）"""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
    import pandas as pd

    if not n_clicks:
        return go.Figure()

    try:
        if not design_vars or len(design_vars) == 0:
            fig = go.Figure()
            fig.add_annotation(text="请先在1.3节添加设计变量！", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font_size=16, font_color="red")
            fig.update_layout(title="设计变量相关性分析", height=600)
            return fig

        continuous_vars = [var for var in design_vars if var['type'] == 'continuous']

        if len(continuous_vars) < 2:
            fig = go.Figure()
            fig.add_annotation(text=f"至少需要2个连续型变量才能生成散点矩阵！\n当前只有 {len(continuous_vars)} 个连续变量。", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font_size=14, font_color="orange")
            fig.update_layout(title="设计变量相关性分析", height=600)
            return fig

        state = get_state_manager()
        alternatives = state.load('phase4', 'alternatives')

        if alternatives is not None and len(alternatives) > 0:
            df_data = alternatives[[var['name'] for var in continuous_vars]].copy()
            data_source = "真实采样数据 (Phase 4)"
            n_samples = len(df_data)
        else:
            n_samples = 100
            data_dict = {}
            for var in continuous_vars:
                range_str = var['range']
                if '-' in range_str:
                    min_val, max_val = map(float, range_str.split('-'))
                else:
                    min_val, max_val = 0, 100
                mean = (min_val + max_val) / 2
                std = (max_val - min_val) / 6
                samples = np.random.normal(mean, std, n_samples)
                samples = np.clip(samples, min_val, max_val)
                data_dict[var['name']] = samples

            df_data = pd.DataFrame(data_dict)
            data_source = "模拟预览数据 (请在Phase 4生成真实采样)"

        n_vars = len(continuous_vars)
        var_names = [var['name'] for var in continuous_vars]

        fig = make_subplots(rows=n_vars, cols=n_vars, shared_xaxes=False, shared_yaxes=False, horizontal_spacing=0.02, vertical_spacing=0.02)

        for i in range(n_vars):
            for j in range(n_vars):
                if i == j:
                    fig.add_trace(go.Histogram(x=df_data[var_names[i]], name=var_names[i], marker_color='rgba(55, 128, 191, 0.7)', showlegend=False, nbinsx=20), row=i+1, col=j+1)
                elif i > j:
                    fig.add_trace(go.Scatter(x=df_data[var_names[j]], y=df_data[var_names[i]], mode='markers', marker_size=4, marker_color=df_data[var_names[i]].values.tolist(), marker_colorscale='Viridis', marker_opacity=0.6, marker_line_width=0, name='{} vs {}'.format(var_names[i], var_names[j]), showlegend=False, hovertemplate='x: %{x:.2f}<br>y: %{y:.2f}<extra></extra>'), row=i+1, col=j+1)

        for i in range(n_vars):
            fig.update_yaxes(title_text=var_names[i], row=i+1, col=1)
            fig.update_xaxes(title_text=var_names[i], row=n_vars, col=i+1)

        corr_matrix = df_data.corr()
        for i in range(n_vars):
            for j in range(n_vars):
                if i < j:
                    corr_value = corr_matrix.iloc[i, j]
                    color = 'green' if corr_value > 0.5 else 'red' if corr_value < -0.5 else 'gray'
                    fig.add_annotation(text='r = {:.3f}'.format(corr_value), xref='x{} domain'.format(j+1), yref='y{} domain'.format(i+1), x=0.5, y=0.5, showarrow=False, font_size=12, font_color=color, font_family='monospace', row=i+1, col=j+1)

        fig.update_layout(title_text='设计变量相关性散点矩阵<br><sub>{}个连续变量 | {}个样本 | 数据来源: {}</sub>'.format(n_vars, n_samples, data_source), title_x=0.5, title_xanchor='center', height=max(800, 150 * n_vars), showlegend=False, hovermode='closest')
        return fig

    except Exception as e:
        import traceback
        print(f"生成变量相关性散点矩阵失败: {e}")
        print(traceback.format_exc())
        fig = go.Figure()
        fig.add_annotation(text='生成失败: {}'.format(str(e)), xref='paper', yref='paper', x=0.5, y=0.5, showarrow=False, font_size=14, font_color='red')
        fig.update_layout(title="设计变量相关性分析 - 生成失败", height=600)
        return fig

@callback(
    [Output('phase1-save-status', 'children', allow_duplicate=True),
     Output('phase1-ui-state', 'data', allow_duplicate=True)], # 同步前端 Store
    [Input('input-mission-title', 'value'),
     Input('input-mission-desc', 'value'),
     Input('input-threshold', 'value')],
    prevent_initial_call=True
)
def auto_save_phase1_ui(title, desc, threshold):
    """
    统一的 UI 状态自动保存 (防空值 + 双写)
    涵盖：任务标题、描述、分析阈值
    """
    from dash import ctx
    if not ctx.triggered: return no_update, no_update
    
    state = get_state_manager()
    
    # 1. 保存 UI 状态 (Drafts & Configs)
    current_ui = state.load('phase1', 'ui_state') or {}
    
    # 仅更新非 None 值
    updates = {}
    if title is not None: updates['mission_title'] = title
    if desc is not None: updates['mission_desc'] = desc
    if threshold is not None: updates['threshold'] = threshold
    
    if not updates:
        return no_update, no_update
        
    current_ui.update(updates)
    state.save('phase1', 'ui_state', current_ui)

    # 2. 同时更新 Mission 核心数据 (因为标题和描述属于核心业务数据)
    # 注意：这里我们做一个轻量级更新，不覆盖 key_objectives
    current_mission = state.load('phase1', 'mission') or {}
    new_mission = {
        'title': title or '',
        'description': desc or '',
        'key_objectives': current_mission.get('key_objectives', []),
        'value_proposition': desc or ''
    }
    state.save('phase1', 'mission', new_mission)
    
    return no_update, current_ui