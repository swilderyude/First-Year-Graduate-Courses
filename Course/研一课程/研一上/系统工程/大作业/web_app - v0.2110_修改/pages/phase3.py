"""
Phase 3: 设计空间生成
集成SamplingEngine实现真实采样
"""

from dash import html, dcc, callback, Input, Output, State, no_update, ALL, MATCH
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sampling_engine import SamplingEngine, DesignVariable
from utils.state_manager import get_state_manager
from utils.csv_handler import CSVHandler
from utils.design_space_parser import DesignSpaceParser
from utils.design_space_merger import DesignSpaceMerger
from utils.cartesian_product_engine import CartesianProductEngine, ValueSampler
# from pages.phase4 import generate_design_statistics
import base64
import io


# ===== 辅助函数 =====
def is_data_empty(data):
    """检查数据是否为空，兼容DataFrame、list、dict等类型"""
    if data is None:
        return True
    if isinstance(data, pd.DataFrame):
        return data.empty
    if isinstance(data, (list, dict)):
        return not data
    return False


def has_valid_data(data):
    """检查数据是否有效（非空），兼容DataFrame、list、dict等类型"""
    return not is_data_empty(data)


layout = dbc.Container([
    # 数据存储
    dcc.Store(id='phase3-sampling-engine-store', data=None),
    dcc.Store(id='phase3-alternatives-store', data=None),
    dcc.Store(id='phase3-csv-data', data=None),
    dcc.Store(id='phase3-column-types', data=None),
    # 编辑模式索引存储
    dcc.Store(id='editing-design-var-index-p4', data=None),
    dcc.Store(id='editing-value-attr-index-p4', data=None),
    # 刷新触发器（用于触发表格即时刷新）
    dcc.Store(id='phase3-refresh-trigger', data=0),
    # DOE实验设计配置存储
    dcc.Store(id='phase3-ui-state', data={}),
    dcc.Store(id='phase3-doe-config-store', data=None),

    html.H2([
        html.Span("📐", className="me-2"),
        "Phase 3: 设计空间生成（统一流程）"
    ], className="mb-4"),

    dbc.Alert([
        html.Span("💡", className="me-2"),
        "统一的设计空间生成流程：支持CSV/Excel导入或采样生成，自动与Phase 1数据同步"
    ], color="info", className="mb-4"),

    # ===== 3.1 文件导入与数据源 =====
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("📤", className="me-2"),
                    "3.1 设计空间数据源"
                ], className="mb-0")),
                dbc.CardBody([
                    html.Label("导入设计空间数据", className="fw-bold text-primary"),
                    dcc.Upload(
                        id="upload-design-space-file",
                        children=dbc.Button([
                            html.Span("☁️", className="me-2"),
                            "选择CSV或Excel文件"
                        ], color="primary", className="w-100"),
                        multiple=False,
                        accept=".csv,.xlsx,.xls"
                    ),
                    html.Div(id="file-upload-status", className="mt-2"),
                    html.Div(id="data-source-summary", className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ], md=12)
    ]),

    # ===== 3.2 设计变量与性能属性配置（全宽表格） =====
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("📋", className="me-2"),
                    "3.2 设计变量配置"
                ], className="mb-0")),
                dbc.CardBody([
                    html.Div(id="design-variables-table", className="table-responsive")
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("📊", className="me-2"),
                    "3.3 性能属性配置"
                ], className="mb-0")),
                dbc.CardBody([
                    html.Div(id="performance-attributes-table", className="table-responsive")
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
    ]),

    # ===== 3.4 实验设计与设计空间生成 =====
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("🌐", className="me-2"),
                    "3.4 实验设计与设计空间生成"
                ], className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        html.Strong("核心流程: "),
                        "① 选择变量 → ② 配置取值 → ③ DOE实验设计筛选 → ④ 生成筛选后的设计空间"
                    ], color="success", className="mb-3"),

                    # 步骤1: 变量选择列表
                    html.H6([html.Span("✅", className="me-2"), "步骤1: 选择要生成的变量"], className="text-primary mb-2"),
                    html.Div([
                        dbc.Checklist(
                            id="checklist-cartesian-variables",
                            options=[],
                            value=[],
                            className="mb-2",
                            switch=True
                        ),
                        html.Small(id="variable-selection-summary", children="", className="text-muted")
                    ], className="mb-3"),

                    html.Hr(),

                    # 步骤2: 采样配置区域(针对选中的变量)
                    html.H6([html.Span("⚙️", className="me-2"), "步骤2: 配置变量取值"], className="text-primary mb-2"),
                    html.Div(id="sampling-config-area", className="mb-3"),

                    html.Hr(),

                    # 步骤3: 实验设计筛选 (原步骤4移到这里)
                    html.H6([html.Span("🔍", className="me-2"), "步骤3: DOE实验设计筛选 (避免组合爆炸)"], className="text-primary mb-2"),
                    dbc.Alert([
                        html.Span("💡", className="me-2"),
                        html.Strong("DOE实验设计说明: "),
                        "使用实验设计方法（LHS/正交实验）在生成设计空间",
                        html.Strong("之前"),
                        "缩减变量的因素和水平，避免组合爆炸。"
                    ], color="info", className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("筛选方法"),
                            dbc.Select(
                                id="select-doe-method",
                                options=[
                                    {"label": "无筛选(完整笛卡尔积)", "value": "none"},
                                    {"label": "LHS筛选", "value": "lhs"},
                                    {"label": "正交实验筛选", "value": "orthogonal"}
                                ],
                                value="none",
                                className="mb-2"
                            )
                        ], md=3),
                        dbc.Col([
                            dbc.Label("正交表类型 (仅正交筛选)"),
                            dbc.Select(
                                id="select-orthogonal-table",
                                options=[
                                    {"label": "L4(2³) - 4行，3因素2水平", "value": "L4"},
                                    {"label": "L8(2⁷) - 8行，7因素2水平", "value": "L8"},
                                    {"label": "L9(3⁴) - 9行，4因素3水平", "value": "L9"},
                                    {"label": "L16(2¹⁵) - 16行，15因素2水平", "value": "L16"},
                                    {"label": "L27(3¹³) - 27行，13因素3水平", "value": "L27"}
                                ],
                                value="L8",
                                disabled=True,  # 初始禁用，选择正交筛选后启用
                                className="mb-2"
                            )
                        ], md=3),
                        dbc.Col([
                            dbc.Label("LHS样本数 (仅LHS筛选)"),
                            dbc.Input(id="input-lhs-samples", type="number", value=500, min=10, max=5000,
                                     disabled=True, className="mb-2")  # 初始禁用
                        ], md=3),
                        dbc.Col([
                            dbc.Label("应用DOE配置"),
                            dbc.Button([
                                html.Span("🧪", className="me-2"),
                                "配置DOE筛选"
                            ], id="btn-config-doe", color="warning", size="lg", className="w-100"),
                        ], md=3)
                    ]),

                    html.Div(id="doe-config-status", className="mt-2"),
                    html.Div(id="doe-preview-info", className="mt-2"),

                    # 正交表说明
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        html.Strong("📋 正交表说明："),
                        html.Ul([
                            html.Li([
                                html.Strong("L4(2³)："),
                                "适用于3个因素，每个2水平，共4次实验",
                                html.Span(" (因素数 ≤ 3)", className="text-muted")
                            ]),
                            html.Li([
                                html.Strong("L8(2⁷)："),
                                "适用于7个因素，每个2水平，共8次实验",
                                html.Span(" (因素数 ≤ 7)", className="text-muted")
                            ]),
                            html.Li([
                                html.Strong("L9(3⁴)："),
                                "适用于4个因素，每个3水平，共9次实验",
                                html.Span(" (因素数 ≤ 4)", className="text-muted")
                            ]),
                            html.Li([
                                html.Strong("L16(2¹⁵)："),
                                "适用于15个因素，每个2水平，共16次实验",
                                html.Span(" (因素数 ≤ 15)", className="text-muted")
                            ]),
                            html.Li([
                                html.Strong("L27(3¹³)："),
                                "适用于13个因素，每个3水平，共27次实验",
                                html.Span(" (因素数 ≤ 13)", className="text-muted")
                            ])
                        ], className="mb-2"),
                        html.P([
                            html.Span("⚠️", className="me-2"),
                            "选择正交表时，请确保设计变量数量不超过正交表的因素容量限制"
                        ], className="mb-0 text-warning fw-bold")
                    ], color="light", className="mt-3 collapse", id="orthogonal-help"),

                    html.Hr(),

                    # 步骤4: 生成设计空间
                    html.H6([html.Span("⚙️", className="me-2"), "步骤4: 生成设计空间"], className="text-primary mb-2"),
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        "根据步骤2的变量配置和步骤3的DOE筛选配置，生成最终的设计空间。"
                    ], color="light", className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Button([
                                html.Span("▶️", className="me-2"),
                                "生成设计空间"
                            ], id="btn-generate-design-space", color="success", size="lg", className="w-100 mb-2"),
                            html.Small("根据DOE配置生成筛选后的设计方案", className="text-muted d-block text-center")
                        ], md=12)
                    ]),

                    html.Div(id="generation-status", className="mt-2")
                ])
            ], className="shadow-sm mb-4")
        ], width=12),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("✅", className="me-2"),
                    "3.5 统计信息"
                ], className="mb-0")),
                dbc.CardBody([
                    dbc.Alert([
                        html.Span("ℹ️", className="me-2"),
                        html.Strong("功能说明: "),
                        "本模块展示采样生成的统计结果。",
                        html.Br(),
                        html.Strong("输入: "),
                        "3.4节生成的设计方案数据",
                        html.Br(),
                        html.Strong("输出: "),
                        "采样方法、生成方案数、设计变量统计（最小值/最大值/平均值）"
                    ], color="light", className="mb-3"),
                    html.Div(id="generation-stats")
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
    ]),

    # ===== 3.6 采样分布可视化 =====
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("📈", className="me-2"),
                    "3.6 采样分布可视化"
                ], className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Checklist(
                                id="checklist-enable-jitter",
                                options=[{"label": "启用Jitter防重叠", "value": "enable"}],
                                value=["enable"],
                                className="mb-2",
                                switch=True
                            )
                        ], md=4),
                        dbc.Col([
                            dbc.Label("Jitter强度"),
                            dcc.Slider(
                                id="slider-jitter-strength",
                                min=0.1,
                                max=2.0,
                                step=0.1,
                                value=0.5,
                                marks={i/10: f'{i/10}' for i in range(2, 21, 5)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], md=8)
                    ], className="mb-3"),

                    dcc.Graph(id="sampling-distribution", figure=go.Figure())
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
    ]),

    # ===== 3.7 采样质量评估 =====
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("⭐", className="me-2"),
                    "3.7 采样质量评估"
                ], className="mb-0")),
                dbc.CardBody([
                    html.Div(id="quality-assessment")
                ])
            ], className="shadow-sm mb-4")
        ], width=12),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("📈", className="me-2"),
                    "3.8 成对距离分布"
                ], className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id="pairwise-distance-dist", figure=go.Figure())
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
    ]),

    # ===== 3.9 设计方案预览 =====
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.Span("📋", className="me-2"),
                    "3.9 设计方案预览"
                ], className="mb-0")),
                dbc.CardBody([
                    html.Div(id="design-alternatives-preview", className="table-responsive")
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
                            "保存 Phase 3 数据"
                        ], id="btn-save-phase3", color="success", className="me-2"),
                        dbc.Button([
                            html.Span("📤", className="me-2"),
                            "加载 Phase 3 数据"
                        ], id="btn-load-phase3", color="info")
                    ]),
                    html.Div(id="phase3-save-status", className="mt-3")
                ])
            ], className="shadow-sm mb-4")
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button("上一步: Phase 2", href="/phase2", color="secondary", outline=True),
                dbc.Button("下一步: Phase 4", href="/phase4", color="primary")
            ], className="w-100")
        ])
    ]),

    # ===== 编辑模态框 =====
    # 设计变量编辑模态框
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("编辑设计变量")),
        dbc.ModalBody([
            dbc.Label("变量名称"),
            dbc.Input(id="input-design-var-name-p4", placeholder="例如：orbit_altitude", className="mb-3"),

            dbc.Label("变量类型"),
            dbc.Select(
                id="select-design-var-type-p4",
                options=[
                    {"label": "连续 (Continuous)", "value": "continuous"},
                    {"label": "离散 (Discrete)", "value": "discrete"},
                    {"label": "分类 (Categorical)", "value": "categorical"}
                ],
                value="continuous",
                className="mb-3"
            ),

            dbc.Label("范围/选项"),
            dbc.Input(id="input-design-var-range-p4", placeholder="连续：400-800；分类：L,S,C,X", className="mb-3"),

            dbc.Label("单位 (可选)"),
            dbc.Input(id="input-design-var-unit-p4", placeholder="例如：km", className="mb-3")
        ]),
        dbc.ModalFooter([
            dbc.Button("取消", id="btn-cancel-design-var-p4", color="secondary", className="me-2"),
            dbc.Button("确认保存", id="btn-confirm-design-var-p4", color="primary")
        ])
    ], id="modal-design-var-p4", size="lg", is_open=False),

    # 性能属性编辑模态框
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("编辑性能属性")),
        dbc.ModalBody([
            dbc.Label("属性名称"),
            dbc.Input(id="input-value-attr-name-p4", placeholder="例如：resolution", className="mb-3"),

            dbc.Label("单位"),
            dbc.Input(id="input-value-attr-unit-p4", placeholder="例如：m", className="mb-3"),

            dbc.Label("优化方向"),
            dbc.Select(
                id="select-value-attr-direction-p4",
                options=[
                    {"label": "最小化 (越小越好)", "value": "minimize"},
                    {"label": "最大化 (越大越好)", "value": "maximize"}
                ],
                value="minimize",
                className="mb-3"
            ),

            dbc.Label("目标值 (可选)"),
            dbc.Input(id="input-value-attr-target-p4", type="number", placeholder="例如：1.0", className="mb-3")
        ]),
        dbc.ModalFooter([
            dbc.Button("取消", id="btn-cancel-value-attr-p4", color="secondary", className="me-2"),
            dbc.Button("确认保存", id="btn-confirm-value-attr-p4", color="primary")
        ])
    ], id="modal-value-attr-p4", size="lg", is_open=False)
], fluid=True)

# 回调函数

# ========== 统一的文件导入和数据融合回调 ==========

@callback(
    [Output('file-upload-status', 'children'),
     Output('phase3-csv-data', 'data'),
     Output('phase3-column-types', 'data'),
     Output('data-source-summary', 'children'),
     Output('phase1-auto-load-trigger', 'data', allow_duplicate=True),  # 触发Phase 1自动加载
     # Output('phase2-auto-load-trigger', 'data'),  # [已删除] 避免在Phase 3页面触发不存在的Phase 2组件
     Output('design-variables-table', 'children', allow_duplicate=True),  # 立即刷新表格
     Output('performance-attributes-table', 'children', allow_duplicate=True),  # 立即刷新表格
     Output('phase3-refresh-trigger', 'data', allow_duplicate=True)],  # 触发3.4步骤1自动刷新
    [Input('upload-design-space-file', 'contents')],
    [State('upload-design-space-file', 'filename'),
     State('phase3-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def handle_design_space_upload(contents, filename, current_trigger):
    """
    处理设计空间文件上传 (增强版 - 修复导航报错)
    功能：
    1. 智能识别全空列为 '性能属性'
    2. 智能识别非空列为 '设计变量' (自动清洗部分空值)
    3. 兼容 discrete/continuous/categorical 类型
    4. [修复] 移除对 Phase 2 组件的引用
    """
    if not contents:
        return [no_update] * 8 # 注意返回数量调整为8

    try:
        # 1. [核心要求] 重置所有状态
        state = get_state_manager()
        state.reset_all()
        print(f"📋 Phase 3文件上传: {filename} - 已执行全局重置")

        # 2. 解析文件内容
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        if filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return dbc.Alert("❌ 格式不支持，仅支持CSV/Excel", color="danger"), *([no_update] * 7)

        # 3. 数据预处理：处理ID列
        id_col_found = False
        possible_ids = ['id', 'ID', 'Id', '设计ID', 'design_id', 'index']
        for col in df.columns:
            if col in possible_ids:
                df.rename(columns={col: 'design_id'}, inplace=True)
                id_col_found = True
                break
        
        if not id_col_found:
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'design_id'}, inplace=True)

        # 4. [核心逻辑] 分流处理：设计变量 vs 性能属性
        new_design_vars = []
        new_attributes = []
        var_names = []
        attr_names = []

        cols_to_process = [c for c in df.columns if c != 'design_id']
        
        for col in cols_to_process:
            is_all_nan = df[col].isna().all()
            
            if is_all_nan:
                attr_obj = {
                    "name": col,
                    "unit": "",
                    "description": f"Imported empty column from {filename}",
                    "min": 0,
                    "max": 100,
                    "goal": "maximize"
                }
                new_attributes.append(attr_obj)
                attr_names.append(col)
            else:
                valid_data = df[col].dropna()
                is_numeric = False
                try:
                    numeric_series = pd.to_numeric(valid_data, errors='coerce')
                    if numeric_series.notna().all() and len(numeric_series) > 0:
                        is_numeric = True
                except:
                    is_numeric = False

                if is_numeric:
                    col_min = float(numeric_series.min())
                    col_max = float(numeric_series.max())
                    unique_count = numeric_series.nunique()
                    if unique_count < 10:
                        var_type = 'discrete'
                        unique_vals = sorted(numeric_series.unique().tolist())
                        range_str = ",".join(map(str, unique_vals))
                        values_list = unique_vals
                    else:
                        var_type = 'continuous'
                        range_str = f"{col_min} - {col_max}"
                        values_list = []
                else:
                    var_type = 'categorical'
                    col_min = 0
                    col_max = 0
                    unique_vals = valid_data.astype(str).unique().tolist()
                    range_str = ",".join(unique_vals[:5]) + ("..." if len(unique_vals) > 5 else "")
                    values_list = unique_vals

                var_obj = {
                    "name": col,
                    "type": var_type,
                    "min": col_min,
                    "max": col_max,
                    "range": range_str,
                    "unit": "",
                    "values": values_list,
                    "description": f"Imported from {filename}"
                }
                new_design_vars.append(var_obj)
                var_names.append(col)

        # 5. [持久化] 写入数据库
        state.save('phase1', 'design_variables', new_design_vars)
        state.save('phase1', 'value_attributes', new_attributes)
        records = df.to_dict('records')
        state.save('phase3', 'alternatives', records)

        print(f"✅ 导入完成: 变量={len(new_design_vars)}, 属性={len(new_attributes)}")

        # 6. 准备前端输出
        success_msg = dbc.Alert([
            "✓",
            f"✅ 导入成功！识别 {len(new_design_vars)} 个设计变量，{len(new_attributes)} 个性能属性。"
        ], color="success")

        summary = dbc.Alert([
            html.Div([
                html.Strong("🔹 设计变量 (有数据): "), 
                html.Span(", ".join(var_names) if var_names else "无", className="text-muted small")
            ]),
            html.Div([
                html.Strong("🔸 性能属性 (全空值): "), 
                html.Span(", ".join(attr_names) if attr_names else "无", className="text-muted small")
            ], className="mt-1")
        ], color="info", className="mt-2")

        refresh_signal = str(pd.Timestamp.now())
        csv_data_out = records
        column_types_out = {
            'design_vars': var_names,
            'attributes': attr_names
        }

        try:
            design_vars_table = display_design_variables_table('/phase3', 0)
            perf_attrs_table = display_performance_attributes_table('/phase3', 0)
        except Exception:
            design_vars_table = no_update
            perf_attrs_table = no_update

        return (
            success_msg,
            csv_data_out,
            column_types_out,
            summary,
            refresh_signal,
            # refresh_signal, # [已删除] Phase 2 信号
            design_vars_table,
            perf_attrs_table,
            (current_trigger or 0) + 1
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"❌ 处理失败: {str(e)}", color="danger"), *([no_update] * 7)
    


@callback(
    Output('design-variables-table', 'children'),
    [Input('url', 'pathname'),
     Input('phase3-refresh-trigger', 'data')],
    prevent_initial_call=False
)
def display_design_variables_table(pathname, refresh_trigger):
    """显示设计变量表格 - 使用Phase 1完全相同的渲染逻辑"""
    if pathname != '/phase3':
        return no_update

    try:
        state = get_state_manager()
        design_vars = state.load('phase1', 'design_variables')

        if is_data_empty(design_vars):
            return dbc.Alert([
                html.Span("ℹ️", className="me-2"),
                "暂无设计变量数据（请先在Phase 1中定义或在3.1导入CSV文件）"
            ], color="light", className="text-center py-4")

        # 转换DataFrame为dict列表（与Phase 1一致）
        if isinstance(design_vars, pd.DataFrame):
            design_vars = design_vars.to_dict('records')
        elif not isinstance(design_vars, list):
            design_vars = []

        # ===== 使用Phase 1完全相同的表格构建逻辑 =====
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

            # ===== Phase 1的智能range显示逻辑 =====
            if var_type == 'categorical':
                # 分类变量：优先显示values完整列表，否则尝试从range解析
                values = var.get('values', [])
                if values:
                    # 显示所有分类值（不截断）
                    range_display = ", ".join(map(str, values))
                elif 'range' in var and var['range']:
                    # 如果values丢失但range存在，尝试重新解析
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
                    # 如果values丢失但range存在，尝试重新解析
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
                            id={'type': 'btn-edit-design-var-p4', 'index': i},
                            color="info",
                            size="sm",
                            outline=True
                        ),
                        dbc.Button(
                            "转属性",
                            id={'type': 'btn-convert-var-to-attr-p4', 'index': i},
                            color="warning",
                            size="sm",
                            outline=True
                        ),
                        dbc.Button(
                            "删除",
                            id={'type': 'btn-delete-design-var-p4', 'index': i},
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

    except Exception as e:
        return dbc.Alert(f"显示表格失败: {str(e)}", color="danger")


@callback(
    Output('performance-attributes-table', 'children'),
    [Input('url', 'pathname'),
     Input('phase3-refresh-trigger', 'data')],
    prevent_initial_call=False
)
def display_performance_attributes_table(pathname, refresh_trigger):
    """显示性能属性表格 - 使用Phase 1完全相同的渲染逻辑"""
    if pathname != '/phase3':
        return no_update

    try:
        state = get_state_manager()
        value_attrs = state.load('phase1', 'value_attributes')

        if is_data_empty(value_attrs):
            return dbc.Alert([
                html.Span("ℹ️", className="me-2"),
                "暂无性能属性数据（请先在Phase 1中定义）"
            ], color="light", className="text-center py-4")

        # 转换DataFrame为dict列表（与Phase 1一致）
        if isinstance(value_attrs, pd.DataFrame):
            value_attrs = value_attrs.to_dict('records')
        elif not isinstance(value_attrs, list):
            value_attrs = []

        # ===== 使用Phase 1完全相同的表格构建逻辑 =====
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
                            id={'type': 'btn-edit-value-attr-p4', 'index': i},
                            color="info",
                            size="sm",
                            outline=True
                        ),
                        dbc.Button(
                            "转变量",
                            id={'type': 'btn-convert-attr-to-var-p4', 'index': i},
                            color="warning",
                            size="sm",
                            outline=True
                        ),
                        dbc.Button(
                            "删除",
                            id={'type': 'btn-delete-value-attr-p4', 'index': i},
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

    except Exception as e:
        return dbc.Alert(f"显示表格失败: {str(e)}", color="danger")


@callback(
    Output('design-alternatives-preview', 'children'),
    [Input('phase3-csv-data', 'data')],
    prevent_initial_call=True
)
def display_alternatives_preview(csv_data):
    """显示设计方案完整列表"""
    if not csv_data:
        return html.Div("暂无设计方案数据", className="text-muted text-center py-4")

    try:
        df = pd.DataFrame(csv_data)

        # 显示全部行（用户要求：3.9必须显示完整设计方案列表）
        full_df = df  # 移除head(10)限制

        # 构建表格
        table_header = html.Thead(
            html.Tr([html.Th(col) for col in full_df.columns])
        )

        table_rows = []
        for idx, row in full_df.iterrows():
            table_rows.append(html.Tr([
                html.Td(str(val)[:50]) for val in row.values  # 限制字符长度防止过宽
            ]))

        table_body = html.Tbody(table_rows)

        table = dbc.Table(
            [table_header, table_body],
            striped=True,
            bordered=True,
            hover=True,
            size="sm",
            className="w-100"
        )

        # 添加摘要信息（显示完整数据统计）
        summary = html.Div([
            dbc.Badge(f"共 {len(df)} 个设计方案", color="primary", className="me-2"),
            dbc.Badge(f"{len(df.columns)} 列", color="info", className="me-2"),
            html.Span(f"(显示全部 {len(full_df)} 行)", className="text-success fw-bold")
        ], className="mb-3")

        # P0-问题5：添加滚动控件，防止表格过宽/过长
        return html.Div([
            summary,
            html.Div(
                table,
                style={
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'maxHeight': '600px',
                    'border': '1px solid #dee2e6',
                    'borderRadius': '4px',
                    'boxShadow': '0 0.125rem 0.25rem rgba(0,0,0,0.075)'
                }
            )
        ])

    except Exception as e:
        return dbc.Alert(f"显示预览失败: {str(e)}", color="danger")



# ========== 采样变量选择回调 ==========

@callback(
    Output('sampling-variables-checklist', 'children'),
    [Input('url', 'pathname'),
     Input('phase3-csv-data', 'data')],
    prevent_initial_call='initial_duplicate'
)
def populate_sampling_variables(pathname, csv_data):
    """自动从Phase 1加载设计变量并显示为选择列表"""
    if pathname != '/phase3':
        return no_update

    try:
        state = get_state_manager()
        phase1_vars = state.load('phase1', 'design_variables')

        if not phase1_vars:
            return dbc.Alert(
                "❌ 暂无设计变量可用（请先在Phase 1中定义设计变量）",
                color="warning",
                className="mb-0"
            )

        # 创建变量选项列表
        var_options = []
        for var in phase1_vars:
            var_name = var.get('name', 'Unknown')
            var_type = var.get('type', 'unknown')
            var_badge = dbc.Badge(
                var_type,
                color="info" if var_type == "continuous" else "success",
                className="ms-2"
            )
            var_options.append({
                "label": [html.Span(var_name), var_badge],
                "value": var_name
            })

        # 默认选中所有变量
        default_selected = [v.get('name') for v in phase1_vars]

        return dbc.Checklist(
            id="checklist-sampling-variables",
            options=var_options,
            value=default_selected,
            className="mb-2",
            switch=False
        )

    except Exception as e:
        return dbc.Alert(
            f"❌ 加载变量失败: {str(e)}",
            color="danger",
            className="mb-0"
        )


# ========== 采样生成回调 ==========

@callback(
    [Output('generation-stats', 'children'),
     Output('phase3-alternatives-store', 'data'),
     Output('sampling-distribution', 'figure'),
     # P2-6: 采样质量评估输出
     Output('quality-assessment', 'children'),
     Output('pairwise-distance-dist', 'figure')],
    [Input('btn-generate-designs', 'n_clicks')],
    [State('radio-sampling-method', 'value'),
     State('input-n-samples', 'value'),
     State('input-seed', 'value'),
     State('checklist-sampling-variables', 'value')],
    prevent_initial_call=True
)
def generate_design_space(n_clicks, method, n_samples, seed, selected_variables):
    """生成设计空间 - 集成SamplingEngine + P2-6质量评估 + 动态变量选择"""
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update

    try:
        # 1. 从Phase 1加载设计变量定义
        state = get_state_manager()
        phase1_vars = state.load('phase1', 'design_variables') or []

        if not phase1_vars:
            error_display = dbc.Alert([
                html.H5("❌ 生成失败", className="alert-heading"),
                html.P("暂无设计变量定义，请先在Phase 1中定义设计变量")
            ], color="danger")
            return error_display, None, {}, no_update, go.Figure()

        # 2. 创建采样引擎并添加选中的变量
        engine = SamplingEngine()
        selected_var_names = selected_variables or []

        for var in phase1_vars:
            var_name = var.get('name', '')
            # 只添加被选中的变量
            if var_name not in selected_var_names:
                continue

            var_type = var.get('type', 'continuous')
            var_unit = var.get('unit', '')

            if var_type == 'continuous':
                var_min = var.get('min', 0)
                var_max = var.get('max', 100)
                engine.add_variable(DesignVariable(var_name, 'continuous', (var_min, var_max), var_unit))
            elif var_type == 'categorical':
                var_values = var.get('values', [])
                engine.add_variable(DesignVariable(var_name, 'categorical', var_values))

        # 如果没有选中任何变量，返回错误
        if len(engine.design_variables) == 0:
            error_display = dbc.Alert([
                html.H5("❌ 生成失败", className="alert-heading"),
                html.P("请至少选择一个设计变量进行采样")
            ], color="danger")
            return error_display, None, {}, no_update, go.Figure()

        # 2. 生成样本
        if method == 'lhs':
            alternatives = engine.generate_lhs(n_samples=n_samples, seed=seed)
        elif method == 'monte_carlo':
            alternatives = engine.generate_monte_carlo(n_samples=n_samples, seed=seed)
        elif method == 'sobol':
            alternatives = engine.generate_sobol(n_samples=n_samples, seed=seed)
        else:
            alternatives = engine.generate_lhs(n_samples=n_samples, seed=seed)

        # 3. 验证覆盖度
        coverage = engine.validate_coverage(alternatives)

        # 4. 保存到StateManager
        state = get_state_manager()
        state.save('phase3', 'design_variables', [v.to_dict() for v in engine.design_variables.values()])
        state.save('phase3', 'alternatives', alternatives)
        state.save('phase3', 'sampling_config', {
            'method': method,
            'n_samples': n_samples,
            'seed': seed
        })

        # 5. 生成统计信息显示
        stats_rows = []
        continuous_cols = []

        for var_name, var_obj in engine.design_variables.items():
            if var_obj.var_type == 'continuous':
                continuous_cols.append(var_name)
                min_val = alternatives[var_name].min()
                max_val = alternatives[var_name].max()
                mean_val = alternatives[var_name].mean()
                unit = var_obj.unit if var_obj.unit else ''

                stats_rows.append(html.Tr([
                    html.Td(var_name, className="fw-bold"),
                    html.Td(f"{min_val:.2f} {unit}" if unit else f"{min_val:.2f}"),
                    html.Td(f"{max_val:.2f} {unit}" if unit else f"{max_val:.2f}"),
                    html.Td(f"{mean_val:.2f} {unit}" if unit else f"{mean_val:.2f}")
                ]))

        stats_display = dbc.Alert([
            html.H5(["✓", "生成成功！"], className="alert-heading"),
            html.Hr(),
            html.P([
                html.Strong("采样方法: "), method.upper(), html.Br(),
                html.Strong("生成方案数: "), f"{len(alternatives)}", html.Br(),
                html.Strong("设计变量: "), f"{len(engine.design_variables)}个", html.Br(),
                html.Strong("随机种子: "), str(seed)
            ]),
            dbc.Table([
                html.Thead(html.Tr([html.Th("变量"), html.Th("最小值"), html.Th("最大值"), html.Th("平均值")])),
                html.Tbody(stats_rows) if stats_rows else html.Tbody([html.Tr([html.Td("(无连续变量)", colSpan=4, className="text-muted text-center")])])
            ], bordered=True, hover=True, size='sm')
        ], color="success")

        # 6. 动态创建采样分布图（基于选中的变量）
        import numpy as np

        # 分离连续和分类变量
        continuous_vars = []
        categorical_vars = []

        for var_name, var_obj in engine.design_variables.items():
            if var_obj.var_type == 'continuous':
                continuous_vars.append((var_name, var_obj))
            else:
                categorical_vars.append((var_name, var_obj))

        # 计算子图网格尺寸
        total_plots = len(continuous_vars) + len(categorical_vars)
        if total_plots == 0:
            fig = go.Figure()
            fig.add_annotation(text="暂无变量可显示", showarrow=False)
        elif total_plots == 1:
            rows, cols = 1, 1
        elif total_plots == 2:
            rows, cols = 1, 2
        elif total_plots <= 4:
            rows, cols = 2, 2
        elif total_plots <= 6:
            rows, cols = 2, 3
        else:
            rows, cols = (total_plots + 2) // 3, 3

        # 创建子图
        subplot_titles = []
        specs = []
        for i, (var_name, var_obj) in enumerate(continuous_vars + categorical_vars):
            subplot_titles.append(f"{var_name}分布")
            if var_obj.var_type == 'categorical':
                specs.append({"type": "bar"})
            else:
                specs.append({"type": "scatter"})

        specs_grid = [specs[i:i+cols] if i+cols <= len(specs) else specs[i:] + [{"type": "scatter"}]*(i+cols-len(specs))
                      for i in range(0, len(specs), cols)]

        fig = make_subplots(
            rows=rows, cols=cols,
            subplot_titles=tuple(subplot_titles),
            specs=specs_grid
        )

        # 添加连续变量的直方图 + Jitter
        colors = ['rgb(55, 83, 109)', 'rgb(26, 118, 255)', 'rgb(214, 39, 40)', 'rgb(31, 119, 180)']

        for idx, (var_name, var_obj) in enumerate(continuous_vars):
            row = idx // cols + 1
            col = idx % cols + 1

            # 直方图
            fig.add_trace(
                go.Histogram(x=alternatives[var_name], name=var_name, nbinsx=30,
                            marker=dict(color=colors[idx % len(colors)], opacity=0.7)),
                row=row, col=col
            )

            # Jitter点
            jitter_y = np.random.uniform(-0.5, 0.5, len(alternatives))
            fig.add_trace(
                go.Scatter(
                    x=alternatives[var_name],
                    y=jitter_y,
                    mode='markers',
                    name='数据点',
                    marker_size=2, marker_color='rgba(100, 100, 100, 0.4)', marker_line_width=0,
                    showlegend=False,
                    hovertemplate=f'{var_name}: %{{x:.2f}}<extra></extra>'
                ),
                row=row, col=col
            )

            fig.update_xaxes(title_text=var_name, row=row, col=col)
            fig.update_yaxes(title_text="频数", row=row, col=col)

        # 添加分类变量的柱状图
        for idx, (var_name, var_obj) in enumerate(categorical_vars):
            plot_idx = len(continuous_vars) + idx
            row = plot_idx // cols + 1
            col = plot_idx % cols + 1

            cat_counts = alternatives[var_name].value_counts()
            fig.add_trace(
                go.Bar(x=cat_counts.index, y=cat_counts.values, name=var_name,
                      marker=dict(color=colors[plot_idx % len(colors)])),
                row=row, col=col
            )

            fig.update_xaxes(title_text=var_name, row=row, col=col)
            fig.update_yaxes(title_text="频数", row=row, col=col)

        fig.update_layout(
            height=300 + rows * 250,
            showlegend=False,
            title_text=f"设计空间采样分布<br><sub>{method.upper()} 采样 | {len(alternatives)}个设计点 | {len(engine.design_variables)}个变量</sub>",
            hovermode='closest'
        )

        # 7. 覆盖度验证显示 (动态生成)
        coverage_rows = []
        for var_name, cov_data in coverage.items():
            var_type = "连续" if cov_data.get('type') == 'continuous' else "分类"
            coverage_rate = cov_data.get('coverage_rate', 0)

            if var_type == "连续":
                # 连续变量：根据覆盖率显示徽章
                if coverage_rate >= 90:
                    badge = dbc.Badge("优秀", color="success")
                elif coverage_rate >= 70:
                    badge = dbc.Badge("良好", color="info")
                else:
                    badge = dbc.Badge(f"{coverage_rate:.1f}%", color="warning")
                detail = f"采样范围覆盖 {coverage_rate:.1f}% 定义域"
            else:
                # 分类变量：显示覆盖的分类值数量
                badge_color = "success" if coverage_rate >= 80 else "warning"
                badge = dbc.Badge(f"{coverage_rate:.0f}%", color=badge_color)
                n_unique = cov_data.get('n_unique', 0)
                n_total = cov_data.get('n_total', 0)
                detail = f"覆盖 {n_unique}/{n_total} 个值"

            coverage_rows.append(html.Tr([
                html.Td(var_name),
                html.Td(var_type),
                html.Td(badge),
                html.Td(detail)
            ]))

        coverage_display = dbc.Alert([
            html.H5("覆盖度验证报告", className="alert-heading"),
            html.Hr(),
            dbc.Table([
                html.Thead(html.Tr([html.Th("变量"), html.Th("类型"), html.Th("覆盖率"), html.Th("详情")])),
                html.Tbody(coverage_rows)
            ], bordered=True, hover=True)
        ], color="info")

        # ==== P2-6: 采样质量评估 ====
        # 8. 计算质量指标
        # 提取连续变量的数值矩阵用于质量评估
        if len(continuous_cols) == 0:
            # 没有连续变量，无法计算质量指标
            quality_display = dbc.Alert(
                "⚠️ 暂无连续变量，无法进行质量评估",
                color="warning"
            )
            distance_fig = go.Figure()
        else:
            X_normalized = alternatives[continuous_cols].values

            # 归一化到[0,1]范围（用于公平比较）
            from sklearn.preprocessing import MinMaxScaler
            scaler = MinMaxScaler()
            X_normalized = scaler.fit_transform(X_normalized)

            # 8.1 计算成对距离
            from scipy.spatial.distance import pdist, squareform
            pairwise_distances = pdist(X_normalized, metric='euclidean')
            min_distance = pairwise_distances.min()
            max_distance = pairwise_distances.max()
            avg_distance = pairwise_distances.mean()
            std_distance = pairwise_distances.std()

            # 8.2 空间填充度量（越大越好）
            space_filling_score = min_distance * 100  # 归一化到0-100

            # 8.3 均匀性评分（基于距离标准差，越小越均匀）
            uniformity_score = max(0, 100 * (1 - std_distance / avg_distance))

            # 8.4 整体质量评分（综合指标）
            overall_quality = (space_filling_score * 0.5 + uniformity_score * 0.5)

            # 8.5 评级
            def get_quality_rating(score):
                if score >= 80:
                    return ("优秀", "success")
                elif score >= 60:
                    return ("良好", "info")
                elif score >= 40:
                    return ("中等", "warning")
                else:
                    return ("较差", "danger")

            quality_label, quality_color = get_quality_rating(overall_quality)

            # 9. 生成质量评估显示
            quality_display = dbc.Alert([
                html.H5("采样质量报告", className="alert-heading"),
                html.Hr(),

                # 整体评分卡片
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.H2(f"{overall_quality:.1f}", className="mb-0 text-center"),
                            html.P("整体质量评分", className="text-center text-muted"),
                            dbc.Badge(quality_label, color=quality_color, className="w-100")
                        ], className="text-center p-3 border rounded")
                    ], md=4),
                    dbc.Col([
                        html.Div([
                            html.H2(f"{space_filling_score:.1f}", className="mb-0 text-center"),
                            html.P("空间填充度", className="text-center text-muted"),
                            dbc.Badge("越大越好", color="light", className="w-100")
                        ], className="text-center p-3 border rounded")
                    ], md=4),
                    dbc.Col([
                        html.Div([
                            html.H2(f"{uniformity_score:.1f}", className="mb-0 text-center"),
                            html.P("分布均匀性", className="text-center text-muted"),
                            dbc.Badge("越大越均匀", color="light", className="w-100")
                        ], className="text-center p-3 border rounded")
                    ], md=4)
                ], className="mb-3"),

                # 详细指标表格
                dbc.Table([
                    html.Thead(html.Tr([html.Th("指标"), html.Th("数值"), html.Th("说明")])),
                    html.Tbody([
                        html.Tr([
                            html.Td("最小成对距离"),
                            html.Td(f"{min_distance:.4f}"),
                            html.Td("样本点之间的最小间隔（越大越好）")
                        ]),
                        html.Tr([
                            html.Td("平均成对距离"),
                            html.Td(f"{avg_distance:.4f}"),
                            html.Td("整体分散程度")
                        ]),
                        html.Tr([
                            html.Td("最大成对距离"),
                            html.Td(f"{max_distance:.4f}"),
                            html.Td("空间的最大跨度")
                        ]),
                        html.Tr([
                            html.Td("距离标准差"),
                            html.Td(f"{std_distance:.4f}"),
                            html.Td("分布均匀性（越小越均匀）")
                        ]),
                        html.Tr([
                            html.Td("采样方法"),
                            html.Td(method.upper()),
                            html.Td("LHS通常有最优质量")
                        ])
                    ])
                ], bordered=True, hover=True, size='sm')
            ], color="light")

            # 10. 生成成对距离分布图
            distance_fig = go.Figure()

            # 直方图
            distance_fig.add_trace(go.Histogram(
                x=pairwise_distances,
                nbinsx=50,
                name='距离分布',
                marker_color='rgba(55, 128, 191, 0.7)', marker_line_color='white', marker_line_width=1,
                hovertemplate='距离: %{x:.4f}<br>频数: %{y}<extra></extra>'
            ))

            # 添加统计线
            distance_fig.add_vline(x=min_distance, line_dash="dash", line_color="red",
                                  annotation_text=f"最小: {min_distance:.4f}")
            distance_fig.add_vline(x=avg_distance, line_dash="dot", line_color="green",
                                  annotation_text=f"平均: {avg_distance:.4f}")
            distance_fig.add_vline(x=max_distance, line_dash="dash", line_color="blue",
                                  annotation_text=f"最大: {max_distance:.4f}")

            distance_fig.update_layout(
                title=dict(
                    text=f"成对距离分布直方图<br><sub>{len(pairwise_distances)}个距离对 | 质量评分: {overall_quality:.1f}</sub>",
                    x=0.5,
                    xanchor='center'
                ),
                xaxis_title="归一化欧氏距离",
                yaxis_title="频数",
                height=400,
                showlegend=False,
                hovermode='closest'
            )

        # 转换DataFrame为JSON（用于存储）
        alternatives_json = alternatives.to_dict('records')

        return stats_display, alternatives_json, fig, quality_display, distance_fig

    except Exception as e:
        error_display = dbc.Alert([
            html.H5("生成失败", className="alert-heading"),
            html.P(f"错误: {str(e)}")
        ], color="danger")

        return error_display, None, {}, no_update, no_update, go.Figure()

# ========== P1-5: Jitter防重叠功能回调 ==========

# 回调1: 根据checkbox启用/禁用slider
@callback(
    Output('slider-jitter-strength', 'disabled'),
    Input('checklist-enable-jitter', 'value')
)
def toggle_jitter_slider(enable_jitter):
    """根据checkbox启用/禁用Jitter强度滑块（P1-5功能）"""
    # 如果checkbox选中（value=['enable']），slider启用（disabled=False）
    # 否则slider禁用（disabled=True）
    return 'enable' not in (enable_jitter or [])

# 回调2: 根据Jitter参数重新绘制分布图
@callback(
    Output('sampling-distribution', 'figure', allow_duplicate=True),
    [Input('checklist-enable-jitter', 'value'),
     Input('slider-jitter-strength', 'value')],
    State('phase3-alternatives-store', 'data'),
    prevent_initial_call=True
)
def update_jitter_distribution(enable_jitter, jitter_strength, alternatives_json):
    """根据Jitter参数重新绘制采样分布图（P1-5核心功能）"""
    if not alternatives_json:
        return no_update

    try:
        import numpy as np

        # 从JSON恢复DataFrame
        alternatives = pd.DataFrame(alternatives_json)

        # 从StateManager获取采样配置和设计变量
        state = get_state_manager()
        sampling_config = state.load('phase3', 'sampling_config')
        design_vars = state.load('phase3', 'design_variables') or []
        method = sampling_config.get('method', 'LHS') if sampling_config else 'LHS'

        # 检查是否启用Jitter
        jitter_enabled = 'enable' in (enable_jitter or [])

        # 获取列名并分离连续和分类变量
        all_cols = list(alternatives.columns)
        # 排除 design_id 列如果存在
        all_cols = [col for col in all_cols if col != 'design_id']

        # 根据唯一值数量分离连续和分类变量
        continuous_cols = []
        categorical_cols = []

        for col in all_cols:
            try:
                numeric_data = pd.to_numeric(alternatives[col], errors='coerce')
                unique_count = numeric_data.nunique()
                # 唯一值超过10个认为是连续变量
                if unique_count > 10:
                    continuous_cols.append(col)
                else:
                    categorical_cols.append(col)
            except:
                categorical_cols.append(col)

        # 计算子图网格（最多显示前4个变量）
        display_cols = continuous_cols[:3] + categorical_cols[:1]  # 最多3个连续+1个分类
        if not display_cols:
            display_cols = all_cols[:4]

        # 确定子图类型
        specs_list = []
        for col in display_cols:
            if col in categorical_cols:
                specs_list.append({"type": "bar"})
            else:
                specs_list.append({"type": "scatter"})

        # 创建子图网格（固定2x2以保持稳定布局）
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=tuple([f"{col}分布" for col in display_cols] + [""]*max(0, 4-len(display_cols))),
            specs=[[specs_list[0] if len(specs_list) > 0 else {"type": "scatter"},
                    specs_list[1] if len(specs_list) > 1 else {"type": "scatter"}],
                   [specs_list[2] if len(specs_list) > 2 else {"type": "scatter"},
                    specs_list[3] if len(specs_list) > 3 else {"type": "scatter"}]]
        )

        # 颜色列表
        colors = ['rgb(55, 83, 109)', 'rgb(26, 118, 255)', 'rgb(214, 39, 40)', 'rgb(31, 119, 180)']

        # 添加每个变量的图表
        for idx, col in enumerate(display_cols):
            row = (idx // 2) + 1
            col_pos = (idx % 2) + 1

            if col in categorical_cols:
                # 分类变量：柱状图
                cat_counts = alternatives[col].value_counts()
                fig.add_trace(
                    go.Bar(x=cat_counts.index, y=cat_counts.values, name=col,
                          marker=dict(color=colors[idx % len(colors)])),
                    row=row, col=col_pos
                )
                fig.update_xaxes(title_text=col, row=row, col=col_pos)
            else:
                # 连续变量：直方图 + 可选Jitter
                fig.add_trace(
                    go.Histogram(x=alternatives[col], name=col, nbinsx=30,
                                marker=dict(color=colors[idx % len(colors)], opacity=0.7)),
                    row=row, col=col_pos
                )

                if jitter_enabled:
                    jitter_y = np.random.uniform(-jitter_strength, jitter_strength, len(alternatives))
                    fig.add_trace(
                        go.Scatter(
                            x=alternatives[col],
                            y=jitter_y,
                            mode='markers',
                            name='数据点',
                            marker_size=3, marker_color=f'rgba(100, 100, 100, 0.4)', marker_line_width=0,
                            showlegend=False,
                            hovertemplate=f'{col}: %{{x:.2f}}<extra></extra>'
                        ),
                        row=row, col=col_pos
                    )

                fig.update_xaxes(title_text=col, row=row, col=col_pos)

            fig.update_yaxes(title_text="频数", row=row, col=col_pos)

        # 标题显示Jitter状态
        jitter_status = f"Jitter强度={jitter_strength}" if jitter_enabled else "无Jitter"
        fig.update_layout(
            height=600,
            showlegend=False,
            title_text=f"设计空间采样分布 ({jitter_status})<br><sub>{method.upper()} 采样 | {len(alternatives)}个设计点 | {len(display_cols)}个变量</sub>",
            hovermode='closest'
        )

        return fig

    except Exception as e:
        print(f"P1-5 Jitter更新失败: {e}")
        import traceback
        traceback.print_exc()
        return no_update


# ========== 自动加载Phase 3数据 ==========
@callback(
    Output('phase3-alternatives-store', 'data', allow_duplicate=True),
    [Input('url', 'pathname')],
    prevent_initial_call='initial_duplicate'
)
def auto_load_phase4_data(pathname):
    """Phase 3页面切换时自动加载数据"""
    from dash import ctx

    # 只在切换到Phase 3页面时加载
    if pathname != '/phase3':
        return no_update

    state = get_state_manager()
    alternatives = state.load('phase3', 'alternatives')

    if alternatives is not None:
        # 如果是DataFrame，转换为dict
        if hasattr(alternatives, 'to_dict'):
            return alternatives.to_dict('records')
        # 如果已经是dict格式（从JSON加载）
        elif isinstance(alternatives, dict) and 'data' in alternatives:
            return alternatives['data']  # 提取data字段
        # 如果是list
        elif isinstance(alternatives, list):
            return alternatives
        else:
            return no_update
    else:
        return no_update


# ========== Phase 3.4 排列组合工作流回调==========

# 步骤1: 变量选择列表回调
@callback(
    [Output('checklist-cartesian-variables', 'options'),
     Output('checklist-cartesian-variables', 'value'),
     Output('variable-selection-summary', 'children')],
    [Input('url', 'pathname'),
     Input('phase3-refresh-trigger', 'data')], 
    prevent_initial_call='initial_duplicate'
)
def populate_variable_selection_list(pathname, refresh_trigger):
    """
    从数据库加载 Phase 1 变量。
    一致性保证：不依赖前端 Store 传递，直接查库。
    UI状态恢复：加载 UI State 中上次选中的变量。
    """
    if pathname != '/phase3':
        return no_update, no_update, no_update

    try:
        state = get_state_manager()
        
        # 1. 强制从 DB 加载最新的 Phase 1 变量
        phase1_vars = state.load('phase1', 'design_variables')
        
        # 2. 加载 Phase 3 UI 状态 (恢复上次勾选)
        ui_state = state.load('phase3', 'ui_state') or {}
        saved_selected = ui_state.get('selected_variables', None)

        if is_data_empty(phase1_vars):
            return [], [], html.Small("❌ 暂无变量 (请先在 Phase 1 定义)", className="text-warning")

        # 转换 DataFrame
        if isinstance(phase1_vars, pd.DataFrame):
            phase1_vars = phase1_vars.to_dict('records')

        # 构建选项
        var_options = []
        all_var_names = []
        for var in phase1_vars:
            name = var.get('name', 'Unknown')
            all_var_names.append(name)
            # ... (保持原有的 Badge 构建逻辑) ...
            var_badge = dbc.Badge(var.get('type',''), color="info", className="me-2")
            var_options.append({
                "label": [var_badge, html.Span(name)],
                "value": name
            })

        # 3. 决定选中项：如果有保存的记录且有效，用保存的；否则全选
        if saved_selected:
            # 过滤掉已经删除的变量
            selected = [v for v in saved_selected if v in all_var_names]
        else:
            selected = all_var_names

        summary = html.Small(f"已选中 {len(selected)}/{len(phase1_vars)} 个变量", className="text-muted")

        return var_options, selected, summary

    except Exception as e:
        return [], [], html.Small(f"加载失败: {str(e)}", className="text-danger")
    


# 步骤2: 采样配置区域动态生成回调
@callback(
    Output('sampling-config-area', 'children'),
    [Input('checklist-cartesian-variables', 'value'),
     Input('phase3-refresh-trigger', 'data')], 
    prevent_initial_call=True
)
def update_sampling_config_area(selected_variables, refresh_trigger):
    """
    步骤2: 根据选中的变量动态生成采样配置控件
    [修复逻辑]：从 ui_state 加载草稿配置，确保映射值等用户输入在刷新后能自动回填。
    """
    if not selected_variables:
        return dbc.Alert(
            "请先在上方选择要生成的变量",
            color="light",
            className="text-center"
        )

    try:
        state = get_state_manager()
        phase1_vars = state.load('phase1', 'design_variables')
        
        # [新增] 加载 UI 草稿状态，用于回填
        ui_state = state.load('phase3', 'ui_state') or {}
        draft_configs = ui_state.get('var_configs_draft', {})

        if is_data_empty(phase1_vars):
            return dbc.Alert("未找到设计变量", color="warning")

        if isinstance(phase1_vars, pd.DataFrame):
            phase1_vars = phase1_vars.to_dict('records')

        config_panels = []
        for var in phase1_vars:
            var_name = var.get('name', '')
            if var_name not in selected_variables:
                continue

            var_type = var.get('type', 'continuous')
            var_min = var.get('min', 0)
            var_max = var.get('max', 100)
            var_values = var.get('values', [])
            
            # 获取该变量的草稿配置
            draft = draft_configs.get(var_name, {})

            # -------------------------------------------------
            # 1. 连续型变量 (Continuous)
            # -------------------------------------------------
            if var_type == 'continuous':
                # 读取草稿或默认值
                def_method = draft.get('method', 'uniform')
                def_n = draft.get('n_values', 5)
                def_manual = draft.get('manual_values', "")
                
                config_panel = dbc.Card([
                    dbc.CardHeader([
                        dbc.Badge("连续", color="info", className="me-2"),
                        html.Strong(var_name),
                        html.Span(f" [{var_min}, {var_max}]", className="text-muted small ms-2")
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("取值方法"),
                                dbc.Select(
                                    id={'type': 'sampling-method', 'var': var_name},
                                    options=[
                                        {'label': '均匀间隔', 'value': 'uniform'},
                                        {'label': '随机采样', 'value': 'random'},
                                        {'label': '手动输入', 'value': 'manual'}
                                    ],
                                    value=def_method
                                )
                            ], md=4),
                            dbc.Col([
                                dbc.Label("样本数"),
                                dbc.Input(
                                    id={'type': 'n-values', 'var': var_name},
                                    type="number",
                                    value=def_n, min=2, max=20
                                )
                            ], md=4),
                            dbc.Col([
                                dbc.Label("手动输入值"),
                                dbc.Input(
                                    id={'type': 'manual-values', 'var': var_name},
                                    type="text",
                                    placeholder="例: 100,200,300",
                                    value=def_manual,
                                    disabled=(def_method != 'manual')
                                )
                            ], md=4)
                        ])
                    ])
                ], className="mb-2 shadow-sm")
                config_panels.append(config_panel)

            # -------------------------------------------------
            # 2. 离散型变量 (Discrete)
            # -------------------------------------------------
            elif var_type == 'discrete':
                if not isinstance(var_values, list):
                    var_values = [var_values] if var_values is not None else []
                
                try:
                    sorted_vals = sorted(var_values, key=float)
                except:
                    sorted_vals = var_values
                
                # 读取草稿或默认全选
                def_selected = draft.get('selected_values', sorted_vals)

                config_panel = dbc.Card([
                    dbc.CardHeader([
                        dbc.Badge("离散", color="primary", className="me-2"),
                        html.Strong(var_name),
                        html.Span(f" (数值集合: {len(sorted_vals)}个)", className="text-muted small ms-2")
                    ]),
                    dbc.CardBody([
                        dbc.Label("选择要包含的采样点:", className="small text-muted mb-2"),
                        dbc.Checklist(
                            id={'type': 'discrete-values', 'var': var_name},
                            options=[{'label': str(v), 'value': v} for v in sorted_vals],
                            value=def_selected,
                            inline=True,
                            inputClassName="me-2",
                            labelClassName="me-3"
                        )
                    ])
                ], className="mb-2 shadow-sm")
                config_panels.append(config_panel)

            # -------------------------------------------------
            # 3. 分类变量 (Categorical)
            # -------------------------------------------------
            elif var_type == 'categorical':
                mapping_rows = []
                if not isinstance(var_values, list):
                    var_values = [str(var_values)] if var_values else []
                
                # 获取该变量的详细映射草稿 (包含每个选项的 selected 和 map_val)
                # auto_save_phase3_ui 中我们将保存 'mappings' 字段
                saved_mappings = draft.get('mappings', {})

                # 标题行
                mapping_rows.append(dbc.Row([
                    dbc.Col(html.Label("选择选项"), width=6, className="fw-bold small"),
                    dbc.Col(html.Label("映射数值 (用于计算)"), width=6, className="fw-bold small"),
                ], className="mb-2 border-bottom pb-1"))

                for val in var_values:
                    val_str = str(val)
                    
                    # 获取该选项的保存状态
                    opt_state = saved_mappings.get(val_str, {})
                    # 默认选中，默认映射值为空
                    is_selected = opt_state.get('selected', True)
                    saved_map_val = opt_state.get('map_val', None)

                    mapping_rows.append(dbc.Row([
                        dbc.Col([
                            dbc.Checkbox(
                                id={'type': 'cat-select-val', 'var': var_name, 'opt': val_str},
                                label=val_str,
                                value=is_selected
                            )
                        ], width=6, className="d-flex align-items-center"),
                        dbc.Col([
                            dbc.Input(
                                id={'type': 'cat-map-val', 'var': var_name, 'opt': val_str},
                                type="number",
                                placeholder=f"对应数值",
                                size="sm",
                                value=saved_map_val  # [关键] 回填保存的映射值
                            )
                        ], width=6)
                    ], className="mb-1"))
                
                config_panel = dbc.Card([
                    dbc.CardHeader([
                        dbc.Badge("分类", color="success", className="me-2"),
                        html.Strong(var_name),
                        html.Span(" (需定义数值映射)", className="text-danger small ms-2 fw-bold")
                    ]),
                    dbc.CardBody([
                        html.Div(mapping_rows, style={"maxHeight": "200px", "overflowY": "auto"})
                    ])
                ], className="mb-2 shadow-sm")
                config_panels.append(config_panel)

        if not config_panels:
            return dbc.Alert("未找到有效的变量配置 (请检查变量类型)", color="warning")

        return html.Div(config_panels)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"配置生成失败: {str(e)}", color="danger")



# ========== DOE-first工作流回调 ==========
@callback(
    [Output('phase3-doe-config-store', 'data', allow_duplicate=True),
     Output('doe-config-status', 'children', allow_duplicate=True),
     Output('doe-preview-info', 'children', allow_duplicate=True)],
    [Input('btn-config-doe', 'n_clicks')],
    [State('select-doe-method', 'value'),
     State('select-orthogonal-table', 'value'),
     State('input-lhs-samples', 'value'),
     State('checklist-cartesian-variables', 'value'),
     # 连续变量输入
     State({'type': 'sampling-method', 'var': ALL}, 'value'),
     State({'type': 'n-values', 'var': ALL}, 'value'),
     State({'type': 'manual-values', 'var': ALL}, 'value'),
     # 离散变量输入
     State({'type': 'discrete-values', 'var': ALL}, 'value'),
     # 分类变量输入
     State({'type': 'cat-select-val', 'var': ALL, 'opt': ALL}, 'value'),
     State({'type': 'cat-select-val', 'var': ALL, 'opt': ALL}, 'id'), # 获取ID以知道是哪个变量的哪个选项
     State({'type': 'cat-map-val', 'var': ALL, 'opt': ALL}, 'value')],
    prevent_initial_call=True
)
def configure_doe_filtering(n_clicks, doe_method, orthogonal_table, lhs_samples,
                           selected_variables, 
                           # 连续变量状态
                           sm_vals, n_vals, manual_vals,
                           # 离散变量状态
                           discrete_vals,
                           # 分类变量状态
                           cat_sel_vals, cat_sel_ids, cat_map_vals):
    """
    配置DOE筛选参数并预览估算的设计数量
    [修复]：使用 ctx.states_list 或通过 ID 映射来精确匹配变量配置，解决顺序错位问题。
    """
    from dash import ctx

    if not n_clicks or not selected_variables:
        return no_update, no_update, no_update

    try:
        state = get_state_manager()
        phase1_vars = state.load('phase1', 'design_variables')

        if is_data_empty(phase1_vars):
            error_status = dbc.Alert("未找到设计变量定义", color="danger")
            return no_update, error_status, no_update

        # DataFrame转换为字典列表
        if isinstance(phase1_vars, pd.DataFrame):
            phase1_vars = phase1_vars.to_dict('records')

        # --- 1. 构建配置映射表 (Map: var_name -> config) ---
        # Dash 的 ALL Pattern 匹配返回的是列表，我们需要将其转化为以 var_name 为键的字典
        # 我们利用 ctx.states_list 来获取带有 ID 的完整信息，或者利用辅助的 ID State
        
        # 辅助函数：解析 State 列表到字典
        # 结构: {'var_name': value}
        def map_state_to_dict(state_values, state_ids):
            mapping = {}
            for val, id_spec in zip(state_values, state_ids):
                var_name = id_spec['id']['var']
                mapping[var_name] = val
            return mapping

        # 获取各 State 的 ID 结构 (Dash 自动提供的 hidden property)
        # 注意：在回调参数中，我们只有 values。我们需要通过 ctx.states_list 来获取 ID。
        # ctx.states_list 是一个列表，顺序对应于 @callback 中 State 的定义顺序。
        # 索引对应关系：
        # 0: select-doe-method, 1: select-orthogonal-table, 2: input-lhs-samples, 3: checklist-cartesian-variables
        # 4: sampling-method (ALL), 5: n-values (ALL), 6: manual-values (ALL)
        # 7: discrete-values (ALL)
        # 8: cat-select-val (ALL), 9: cat-select-val (ID - this is explicit state), 10: cat-map-val (ALL)
        
        # 连续变量配置映射
        cont_sm_map = {}
        cont_n_map = {}
        cont_manual_map = {}
        
        # 离散变量配置映射
        discrete_val_map = {}

        # 分类变量配置映射 (需要特殊处理，因为有多个选项)
        # {var_name: {opt_name: {'selected': bool, 'map_val': val}}}
        cat_config_map = {}

        # 解析连续变量 State
        # ctx.states_list[4] 对应 sampling-method
        for item in ctx.states_list[4]:
            if item['id']['type'] == 'sampling-method':
                cont_sm_map[item['id']['var']] = item['value']
        
        for item in ctx.states_list[5]:
            if item['id']['type'] == 'n-values':
                cont_n_map[item['id']['var']] = item['value']

        for item in ctx.states_list[6]:
            if item['id']['type'] == 'manual-values':
                cont_manual_map[item['id']['var']] = item['value']

        # 解析离散变量 State
        for item in ctx.states_list[7]:
            if item['id']['type'] == 'discrete-values':
                discrete_val_map[item['id']['var']] = item['value']

        # 解析分类变量 State (直接使用传入的显式 ID 参数更方便，因为分类变量有三个 State 列表)
        # cat_sel_ids 已经包含了 ID 信息
        if cat_sel_ids:
            for sel_val, id_spec, map_val in zip(cat_sel_vals, cat_sel_ids, cat_map_vals):
                var_name = id_spec['var']
                opt_name = id_spec['opt']
                
                if var_name not in cat_config_map:
                    cat_config_map[var_name] = []
                
                # 仅当选中时才加入配置
                if sel_val:
                    # 优先使用映射值，否则用原值
                    final_val = opt_name
                    if map_val is not None and str(map_val).strip() != "":
                        try:
                            final_val = float(map_val)
                        except ValueError:
                            final_val = map_val
                    
                    cat_config_map[var_name].append(final_val)

        # --- 2. 计算组合数并构建最终配置 ---
        full_combinations = 1
        var_configs = []

        for var in phase1_vars:
            var_name = var.get('name', '')
            if var_name not in selected_variables:
                continue

            var_type = var.get('type', 'continuous')
            
            # --- 连续变量 ---
            if var_type == 'continuous':
                method = cont_sm_map.get(var_name, 'uniform')
                n_vals = cont_n_map.get(var_name, 5)
                manual_val = cont_manual_map.get(var_name, "")
                
                # 计算组合数贡献
                count = n_vals
                if method == 'manual' and manual_val:
                    try:
                        count = len([x for x in manual_val.replace('，', ',').split(',') if x.strip()])
                        count = max(1, count)
                    except:
                        pass
                
                full_combinations *= count
                
                var_configs.append({
                    'name': var_name, 
                    'type': var_type, 
                    'n_values': n_vals,
                    'method': method,
                    'manual_values': manual_val
                })

            # --- 离散变量 ---
            elif var_type == 'discrete':
                # 获取用户勾选的值
                selected_vals = discrete_val_map.get(var_name, [])
                # 如果用户未勾选任何值，默认使用全部定义值（防呆）
                if not selected_vals:
                    selected_vals = var.get('values', [])
                
                count = len(selected_vals)
                full_combinations *= count
                
                var_configs.append({
                    'name': var_name,
                    'type': var_type,
                    'n_values': count,
                    'selected_values': selected_vals
                })

            # --- 分类变量 ---
            elif var_type == 'categorical':
                # 获取用户勾选且映射后的值
                mapped_vals = cat_config_map.get(var_name, [])
                # 如果未配置，默认使用全部原始值
                if not mapped_vals:
                    mapped_vals = var.get('values', [])
                
                count = len(mapped_vals)
                full_combinations *= count
                
                var_configs.append({
                    'name': var_name, 
                    'type': var_type, 
                    'n_values': count,
                    'selected_values': mapped_vals
                })

        # --- 3. 估算筛选后数量 ---
        if doe_method == 'none':
            doe_samples = full_combinations
            method_name = "无筛选（完整笛卡尔积）"
            reduction_rate = 0.0
        elif doe_method == 'lhs':
            doe_samples = int(lhs_samples) if lhs_samples else 500
            method_name = "LHS筛选"
            reduction_rate = (1 - doe_samples / full_combinations) * 100 if full_combinations > 0 else 0
        elif doe_method == 'orthogonal':
            orthogonal_samples_map = {'L4': 4, 'L8': 8, 'L9': 9, 'L16': 16, 'L27': 27}
            doe_samples = orthogonal_samples_map.get(orthogonal_table, 8)
            method_name = f"正交实验 ({orthogonal_table})"
            reduction_rate = (1 - doe_samples / full_combinations) * 100 if full_combinations > 0 else 0
        else:
            doe_samples = full_combinations
            method_name = "未知方法"
            reduction_rate = 0.0

        # 保存DOE配置
        doe_config = {
            'method': doe_method,
            'orthogonal_table': orthogonal_table,
            'lhs_samples': lhs_samples,
            'estimated_samples': doe_samples,
            'full_combinations': full_combinations,
            'var_configs': var_configs
        }

        state.save('phase3', 'doe_config', doe_config)

        # 生成状态消息
        status_msg = dbc.Alert([
            "✓",
            html.Strong("✅ DOE配置成功！"),
            html.Hr(),
            html.P([
                html.Strong("筛选方法: "), method_name, html.Br(),
                html.Strong("原始组合: "), f"{full_combinations:,} 个设计", html.Br(),
                html.Strong("筛选后: "), f"{doe_samples:,} 个设计", html.Br(),
                html.Strong("缩减率: "), f"{reduction_rate:.1f}%"
            ])
        ], color="success")

        # 生成预览警告
        if doe_samples > 10000:
            color = "danger"
            icon = "⚠️"
            warning = "⚠️ 筛选后仍然过大，建议进一步缩减！"
        elif doe_samples > 3000:
            color = "warning"
            icon = "fa-exclamation-circle"
            warning = "提示: 筛选后数量较大"
        else:
            color = "success"
            icon = "fa-check-circle"
            warning = "筛选后数量合理，可以生成"

        preview_info = html.Div([
            html.I(className=f"fas {icon} fa-2x text-{color} mb-2"),
            html.H4(f"{doe_samples:,} 个设计", className=f"text-{color}"),
            html.P(warning, className=f"text-{color} fw-bold")
        ], className="text-center")

        return doe_config, status_msg, preview_info

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_status = dbc.Alert(f"DOE配置失败: {str(e)}", color="danger")
        return no_update, error_status, no_update
    


# 生成筛选后的设计空间回调
@callback(
    [Output('phase3-csv-data', 'data', allow_duplicate=True),
     Output('phase3-column-types', 'data', allow_duplicate=True),
     Output('generation-status', 'children'),
     Output('generation-stats', 'children', allow_duplicate=True)],
    [Input('btn-generate-design-space', 'n_clicks')],
    [State('phase3-doe-config-store', 'data'),
     State('checklist-cartesian-variables', 'value'),
     # 连续变量输入
     State({'type': 'sampling-method', 'var': ALL}, 'value'),
     State({'type': 'n-values', 'var': ALL}, 'value'),
     State({'type': 'manual-values', 'var': ALL}, 'value'),
     # 离散变量输入
     State({'type': 'discrete-values', 'var': ALL}, 'value'),
     # 分类变量输入
     State({'type': 'cat-select-val', 'var': ALL, 'opt': ALL}, 'value'),
     State({'type': 'cat-select-val', 'var': ALL, 'opt': ALL}, 'id'),
     State({'type': 'cat-map-val', 'var': ALL, 'opt': ALL}, 'value'),
     # [新增] 读取 UI State 作为兜底
     State('phase3-ui-state', 'data')],
    prevent_initial_call=True
)
def generate_filtered_design_space(n_clicks, doe_config, selected_variables, 
                                   sm_vals, n_vals, manual_vals,
                                   discrete_vals_list,
                                   cat_select_values, cat_select_ids, cat_map_values,
                                   ui_state):
    """
    根据DOE配置生成设计空间
    [修复]：使用 ctx.states_list 映射配置，并支持从 ui_state 兜底读取配置，确保步骤2的输入有效。
    """
    from dash import ctx
    
    if not n_clicks or not selected_variables:
        return no_update, no_update, no_update, no_update

    try:
        import numpy as np
        state = get_state_manager()
        phase1_vars = state.load('phase1', 'design_variables')

        if is_data_empty(phase1_vars):
            return no_update, no_update, dbc.Alert("未找到设计变量定义", color="danger"), no_update

        if isinstance(phase1_vars, pd.DataFrame):
            phase1_vars = phase1_vars.to_dict('records')

        # 初始化引擎
        engine = CartesianProductEngine()

        # --- 1. 构建配置映射表 (Map: var_name -> config) ---
        cont_sm_map = {}
        cont_n_map = {}
        cont_manual_map = {}
        discrete_val_map = {}
        cat_config_map = {}

        # 尝试从当前 UI Context 读取
        # 索引对应：0:doe, 1:checklist, 2:sm, 3:n, 4:manual, 5:discrete, 6:cat_sel, 7:cat_id, 8:cat_map
        if len(ctx.states_list) > 2:
            for item in ctx.states_list[2]:
                if item['id']['type'] == 'sampling-method': cont_sm_map[item['id']['var']] = item['value']
            for item in ctx.states_list[3]:
                if item['id']['type'] == 'n-values': cont_n_map[item['id']['var']] = item['value']
            for item in ctx.states_list[4]:
                if item['id']['type'] == 'manual-values': cont_manual_map[item['id']['var']] = item['value']
            for item in ctx.states_list[5]:
                if item['id']['type'] == 'discrete-values': discrete_val_map[item['id']['var']] = item['value']

        if cat_select_ids:
            for val, id_spec, map_val in zip(cat_select_values, cat_select_ids, cat_map_values):
                var_name = id_spec['var']
                opt_name = id_spec['opt']
                if var_name not in cat_config_map:
                    cat_config_map[var_name] = []
                if val:
                    final_value = opt_name
                    if map_val is not None and str(map_val).strip() != "":
                        try:
                            final_value = float(map_val)
                        except ValueError:
                            final_value = map_val
                    cat_config_map[var_name].append(final_value)

        # [兜底逻辑] 如果 Context 读取为空（可能由于 DOM 刷新导致），尝试从 ui_state 读取
        draft_configs = ui_state.get('var_configs_draft', {}) if ui_state else {}

        # --- 2. 配置变量参数并传递给 Engine ---
        for var in phase1_vars:
            var_name = var.get('name', '')
            if var_name not in selected_variables:
                continue

            var_type = var.get('type', 'continuous')
            var_min = var.get('min', 0)
            var_max = var.get('max', 100)
            
            # 尝试从 draft 获取兜底配置
            draft = draft_configs.get(var_name, {})

            # --- 连续变量 ---
            if var_type == 'continuous':
                method = cont_sm_map.get(var_name) or draft.get('method', 'uniform')
                n_vals = cont_n_map.get(var_name) or draft.get('n_values', 5)
                manual_val = cont_manual_map.get(var_name) or draft.get('manual_values', "")

                values = []
                if method == 'uniform':
                    values = ValueSampler.uniform_sampling(var_min, var_max, n_vals)
                elif method == 'random':
                    values = ValueSampler.random_sampling(var_min, var_max, n_vals, seed=42)
                elif method == 'manual' and manual_val:
                    values = ValueSampler.manual_input(manual_val)
                else:
                    values = ValueSampler.uniform_sampling(var_min, var_max, n_vals)
                
                engine.configure_variable(var_name, values, var_type)

            # --- 离散变量 ---
            elif var_type == 'discrete':
                selected_vals = discrete_val_map.get(var_name) or draft.get('selected_values', [])
                if not selected_vals:
                    selected_vals = var.get('values', [])
                engine.configure_variable(var_name, selected_vals, var_type)

            # --- 分类变量 ---
            elif var_type == 'categorical':
                mapped_vals = cat_config_map.get(var_name) or draft.get('selected_values', [])
                if not mapped_vals:
                    mapped_vals = var.get('values', [])
                engine.configure_variable(var_name, mapped_vals, var_type)

        # --- 3. 调用 Engine 生成数据 ---
        doe_method = doe_config.get('method', 'none') if doe_config else 'none'
        
        # 即使选择 'none' (无筛选)，也必须基于 engine.configure_variable 设置的值来生成笛卡尔积
        # 之前的问题是 engine 配置失效，导致生成了空的或错误的笛卡尔积
        
        final_df = pd.DataFrame()
        method_name = ""

        if doe_method == 'none':
            final_df = engine.generate_full_combinations()
            method_name = "无筛选（完整笛卡尔积）"
            
        elif doe_method == 'lhs':
            n_samples = int(doe_config.get('lhs_samples', 500)) if doe_config else 500
            final_df = engine.apply_lhs_filtering(n_samples=n_samples, seed=42)
            method_name = f"LHS筛选 ({n_samples}个样本)"
            
        elif doe_method == 'orthogonal':
            orthogonal_table = doe_config.get('orthogonal_table', 'L8') if doe_config else 'L8'
            final_df = engine.apply_orthogonal_filtering(orthogonal_table=orthogonal_table)
            method_name = f"正交实验 ({orthogonal_table})"
            
        else:
            final_df = engine.generate_full_combinations()
            method_name = "默认生成"

        # --- 4. 结果校验与保存 ---
        if final_df.empty:
            error_msg = dbc.Alert("生成失败: 无有效数据，请检查变量配置", color="danger")
            return no_update, no_update, error_msg, no_update

        if 'design_id' not in final_df.columns:
            final_df.reset_index(drop=True, inplace=True)
            final_df['design_id'] = range(len(final_df))
        else:
            final_df['design_id'] = range(len(final_df))

        alternatives_records = final_df.to_dict('records')
        state.save('phase3', 'alternatives', alternatives_records)
        state.save('phase3', 'cartesian_engine', engine.get_summary())
        
        print(f"✅ Phase 3 ({method_name}): 生成 {len(final_df)} 个方案")

        csv_data = alternatives_records
        column_types = {
            'design_vars': [col for col in final_df.columns if col != 'design_id'],
            'attributes': []
        }

        success_msg = dbc.Alert([
            "✓",
            html.Strong(f"✅ {method_name} 生成成功！"),
            html.Hr(),
            html.P([
                f"生成了 {len(final_df)} 个设计方案",
                html.Br(),
                html.Small("分类变量已自动转换为对应的数值，可直接用于计算。", className="text-success")
            ])
        ], color="success")

        stats_display = html.Div([
            dbc.Badge(f"设计方案数: {len(final_df)}", color="primary", className="me-2"),
            dbc.Badge(f"变量数: {len(column_types['design_vars'])}", color="info")
        ])

        return csv_data, column_types, success_msg, stats_display

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = dbc.Alert(f"生成失败: {str(e)}", color="danger")
        return no_update, no_update, error_msg, no_update

    
    

#  根据DOE方法启用/禁用输入框
@callback(
    [Output('select-orthogonal-table', 'disabled'),
     Output('input-lhs-samples', 'disabled')],
    Input('select-doe-method', 'value'),
    prevent_initial_call=False
)
def toggle_doe_inputs(method):
    """根据DOE方法启用/禁用相应的输入控件"""
    if method == 'orthogonal':
        return False, True  # 启用正交表，禁用LHS
    elif method == 'lhs':
        return True, False  # 禁用正交表，启用LHS
    else:  # none
        return True, True  # 禁用所有




# ========== 辅助回调: 启用/禁用手动输入框 ==========
@callback(
    Output({'type': 'manual-values', 'var': MATCH}, 'disabled'),
    Input({'type': 'sampling-method', 'var': MATCH}, 'value'),
    prevent_initial_call=True
)
def toggle_manual_input(method):
    """根据采样方法启用/禁用手动输入框"""
    return method != 'manual'

from dash import html, callback, Input, Output, State, no_update, ALL
import dash_bootstrap_components as dbc
from utils.state_manager import get_state_manager
from dash import ctx

# ========== 3.2 设计变量按钮回调 ==========

@callback(
    [Output('design-variables-table', 'children', allow_duplicate=True),
     Output('phase3-refresh-trigger', 'data', allow_duplicate=True)],
    [Input({'type': 'btn-delete-design-var-p4', 'index': ALL}, 'n_clicks')],
    [State('phase3-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def delete_design_variable_p4(n_clicks_list, current_trigger):
    """删除设计变量 - Phase 3版本，操作Phase 1数据"""
    if not any(n_clicks_list):
        return no_update, no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-delete-design-var-p4':
        index = triggered['index']

        # 从StateManager加载Phase 1数据
        state = get_state_manager()
        design_vars = state.load('phase1', 'design_variables')

        # 使用has_valid_data检查DataFrame
        if has_valid_data(design_vars) and 0 <= index < len(design_vars):
            # DataFrame统一处理list和DataFrame
            if isinstance(design_vars, pd.DataFrame):
                design_vars_list = design_vars.to_dict('records')
                # 删除指定变量
                deleted_var = design_vars_list.pop(index)
                design_vars = design_vars_list
            else:
                # 删除指定变量
                deleted_var = design_vars.pop(index)

            # 保存回StateManager
            state.save('phase1', 'design_variables', design_vars)

            # 触发刷新（通过修改触发器的值）
            return no_update, (current_trigger or 0) + 1

    return no_update, no_update


@callback(
    [Output('design-variables-table', 'children', allow_duplicate=True),
     Output('performance-attributes-table', 'children', allow_duplicate=True),
     Output('phase3-refresh-trigger', 'data', allow_duplicate=True)],
    [Input({'type': 'btn-convert-var-to-attr-p4', 'index': ALL}, 'n_clicks')],
    [State('phase3-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def convert_var_to_attr_p4(n_clicks_list, current_trigger):
    """设计变量转性能属性 - Phase 3版本"""
    if not any(n_clicks_list):
        return no_update, no_update, no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-convert-var-to-attr-p4':
        index = triggered['index']

        # 从StateManager加载数据
        state = get_state_manager()
        design_vars = state.load('phase1', 'design_variables')
        value_attrs = state.load('phase1', 'value_attributes')

        # 统一处理DataFrame和list
        if isinstance(design_vars, pd.DataFrame):
            design_vars_list = design_vars.to_dict('records')
        else:
            design_vars_list = design_vars if design_vars else []

        if isinstance(value_attrs, pd.DataFrame):
            value_attrs_list = value_attrs.to_dict('records')
        else:
            value_attrs_list = value_attrs if value_attrs else []

        # 使用has_valid_data检查
        if has_valid_data(design_vars_list) and 0 <= index < len(design_vars_list):
            var = design_vars_list[index]

            # 转换为性能属性（假设优化方向为最小化）
            new_attr = {
                'name': var['name'],
                'unit': var.get('unit', ''),
                'direction': 'minimize',  # 默认最小化，用户可后续调整
                'target': None  # 目标值未设置
            }

            # 从设计变量列表移除
            design_vars_list.pop(index)
            # 添加到性能属性列表
            value_attrs_list.append(new_attr)

            # 保存回StateManager
            state.save('phase1', 'design_variables', design_vars_list)
            state.save('phase1', 'value_attributes', value_attrs_list)

            # 触发刷新
            return no_update, no_update, (current_trigger or 0) + 1

    return no_update, no_update, no_update


# ========== 3.3 性能属性按钮回调 ==========

@callback(
    [Output('performance-attributes-table', 'children', allow_duplicate=True),
     Output('phase3-refresh-trigger', 'data', allow_duplicate=True)],
    [Input({'type': 'btn-delete-value-attr-p4', 'index': ALL}, 'n_clicks')],
    [State('phase3-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def delete_value_attribute_p4(n_clicks_list, current_trigger):
    """删除性能属性 - Phase 3版本，操作Phase 1数据"""
    if not any(n_clicks_list):
        return no_update, no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-delete-value-attr-p4':
        index = triggered['index']

        # 从StateManager加载Phase 1数据
        state = get_state_manager()
        value_attrs = state.load('phase1', 'value_attributes')

        # 使用has_valid_data检查DataFrame
        if has_valid_data(value_attrs) and 0 <= index < len(value_attrs):
            # DataFrame统一处理list和DataFrame
            if isinstance(value_attrs, pd.DataFrame):
                value_attrs_list = value_attrs.to_dict('records')
                # 删除指定属性
                deleted_attr = value_attrs_list.pop(index)
                value_attrs = value_attrs_list
            else:
                # 删除指定属性
                deleted_attr = value_attrs.pop(index)

            # 保存回StateManager
            state.save('phase1', 'value_attributes', value_attrs)

            # 触发刷新
            return no_update, (current_trigger or 0) + 1

    return no_update, no_update


@callback(
    [Output('performance-attributes-table', 'children', allow_duplicate=True),
     Output('design-variables-table', 'children', allow_duplicate=True),
     Output('phase3-refresh-trigger', 'data', allow_duplicate=True)],
    [Input({'type': 'btn-convert-attr-to-var-p4', 'index': ALL}, 'n_clicks')],
    [State('phase3-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def convert_attr_to_var_p4(n_clicks_list, current_trigger):
    """性能属性转设计变量 - Phase 3版本"""
    if not any(n_clicks_list):
        return no_update, no_update, no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-convert-attr-to-var-p4':
        index = triggered['index']

        # 从StateManager加载数据
        state = get_state_manager()
        value_attrs = state.load('phase1', 'value_attributes')
        design_vars = state.load('phase1', 'design_variables')

        # 统一处理DataFrame和list
        if isinstance(value_attrs, pd.DataFrame):
            value_attrs_list = value_attrs.to_dict('records')
        else:
            value_attrs_list = value_attrs if value_attrs else []

        if isinstance(design_vars, pd.DataFrame):
            design_vars_list = design_vars.to_dict('records')
        else:
            design_vars_list = design_vars if design_vars else []

        # 使用has_valid_data检查
        if has_valid_data(value_attrs_list) and 0 <= index < len(value_attrs_list):
            attr = value_attrs_list[index]

            # 转换为设计变量（假设连续型，范围需要用户后续调整）
            new_var = {
                'name': attr['name'],
                'type': 'continuous',
                'range': '0-100',  # 默认范围，用户可后续修改
                'min': 0,  # 默认最小值
                'max': 100,  # 默认最大值
                'unit': attr.get('unit', '')
            }

            # 从性能属性列表移除
            value_attrs_list.pop(index)
            # 添加到设计变量列表
            design_vars_list.append(new_var)

            # 保存回StateManager
            state.save('phase1', 'value_attributes', value_attrs_list)
            state.save('phase1', 'design_variables', design_vars_list)

            # 触发刷新
            return no_update, no_update, (current_trigger or 0) + 1

    return no_update, no_update, no_update


# ========== 编辑功能回调 ==========

# 设计变量编辑模态框控制
@callback(
    Output('modal-design-var-p4', 'is_open'),
    [Input('btn-cancel-design-var-p4', 'n_clicks'),
     Input('btn-confirm-design-var-p4', 'n_clicks')],
    [State('modal-design-var-p4', 'is_open')],
    prevent_initial_call=True
)
def toggle_design_var_modal_p4(n_cancel, n_confirm, is_open):
    """控制设计变量编辑模态框的显示/隐藏"""
    return not is_open


# 打开设计变量编辑模态框并预填充数据
@callback(
    [Output('modal-design-var-p4', 'is_open', allow_duplicate=True),
     Output('input-design-var-name-p4', 'value'),
     Output('select-design-var-type-p4', 'value'),
     Output('input-design-var-range-p4', 'value'),
     Output('input-design-var-unit-p4', 'value'),
     Output('editing-design-var-index-p4', 'data')],
    [Input({'type': 'btn-edit-design-var-p4', 'index': ALL}, 'n_clicks')],
    prevent_initial_call=True
)
def open_edit_design_var_modal_p4(n_clicks_list):
    """打开设计变量编辑模态框并预填充数据"""
    from dash import ctx

    if not any(n_clicks_list):
        return no_update, no_update, no_update, no_update, no_update, no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-edit-design-var-p4':
        index = triggered['index']

        # 从StateManager读取最新数据
        state = get_state_manager()
        design_vars = state.load('phase1', 'design_variables')

        # 统一处理DataFrame和list
        if isinstance(design_vars, pd.DataFrame):
            design_vars_list = design_vars.to_dict('records')
        else:
            design_vars_list = design_vars if design_vars else []

        if has_valid_data(design_vars_list) and 0 <= index < len(design_vars_list):
            var = design_vars_list[index]

            # 如果range字段为空，从values字段重构range字符串（确保分类/离散变量能正确编辑）
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
                var.get('type', 'continuous'),
                var_range,  # 使用重构的range字符串
                var.get('unit', ''),
                index  # 记录编辑索引
            )

    return no_update, no_update, no_update, no_update, no_update, no_update


# 确认编辑设计变量
@callback(
    [Output('editing-design-var-index-p4', 'data', allow_duplicate=True),
     Output('input-design-var-name-p4', 'value', allow_duplicate=True),
     Output('select-design-var-type-p4', 'value', allow_duplicate=True),
     Output('input-design-var-range-p4', 'value', allow_duplicate=True),
     Output('input-design-var-unit-p4', 'value', allow_duplicate=True),
     Output('phase3-refresh-trigger', 'data', allow_duplicate=True)],
    [Input('btn-confirm-design-var-p4', 'n_clicks')],
    [State('input-design-var-name-p4', 'value'),
     State('select-design-var-type-p4', 'value'),
     State('input-design-var-range-p4', 'value'),
     State('input-design-var-unit-p4', 'value'),
     State('editing-design-var-index-p4', 'data'),
     State('phase3-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def confirm_edit_design_var_p4(n_clicks, name, var_type, var_range, unit, editing_index, current_trigger):
    """确认编辑设计变量（通过refresh-trigger触发表格刷新）"""
    if n_clicks and name and var_range and editing_index is not None:
        state = get_state_manager()
        design_vars = state.load('phase1', 'design_variables')

        # 统一处理DataFrame和list
        if isinstance(design_vars, pd.DataFrame):
            design_vars_list = design_vars.to_dict('records')
        else:
            design_vars_list = design_vars if design_vars else []

        if 0 <= editing_index < len(design_vars_list):
            # 基础变量字典
            new_var = {
                'name': name,
                'type': var_type,
                'range': var_range,
                'unit': unit or ''
            }

            # 对于连续型和离散型变量，解析range字符串为min/max
            if var_type in ['continuous', 'discrete']:
                if '-' in var_range and ',' not in var_range:
                    # 范围格式：min-max（如 "0-100"）
                    try:
                        parts = var_range.split('-')
                        if len(parts) == 2:
                            new_var['min'] = float(parts[0].strip())
                            new_var['max'] = float(parts[1].strip())
                    except (ValueError, IndexError):
                        # 如果解析失败，保持原样，只有range字段
                        pass
                elif ',' in var_range or '，' in var_range:
                    # 离散值格式：逗号分隔（如 "0,50,100"）
                    try:
                        # 统一处理中文和英文逗号
                        normalized_range = var_range.replace('，', ',')
                        values = [float(v.strip()) for v in normalized_range.split(',')]
                        new_var['values'] = values
                        new_var['min'] = min(values)
                        new_var['max'] = max(values)
                    except (ValueError, IndexError):
                        # 如果解析失败，保持原样
                        pass

            # 对于分类变量，解析values
            elif var_type == 'categorical':
                # 统一处理中文和英文逗号
                normalized_range = var_range.replace('，', ',')
                if ',' in normalized_range:
                    new_var['values'] = [v.strip() for v in normalized_range.split(',')]
                else:
                    new_var['values'] = [normalized_range.strip()]

            # 更新变量数据
            design_vars_list[editing_index] = new_var

            # 保存到StateManager
            state.save('phase1', 'design_variables', design_vars_list)

            # 打印日志确认保存
            print(f"✅ Phase 3编辑保存成功: {name}, 索引={editing_index}")
            print(f"📝 保存的数据: {design_vars_list[editing_index]}")

            # 清空输入框并重置编辑索引，触发刷新
            return None, "", "continuous", "", "", (current_trigger or 0) + 1

    return no_update, no_update, no_update, no_update, no_update, no_update


# 性能属性编辑模态框控制
@callback(
    Output('modal-value-attr-p4', 'is_open'),
    [Input('btn-cancel-value-attr-p4', 'n_clicks'),
     Input('btn-confirm-value-attr-p4', 'n_clicks')],
    [State('modal-value-attr-p4', 'is_open')],
    prevent_initial_call=True
)
def toggle_value_attr_modal_p4(n_cancel, n_confirm, is_open):
    """控制性能属性编辑模态框的显示/隐藏（移除编辑按钮Input避免误触发）"""
    return not is_open


# 打开性能属性编辑模态框并预填充数据
@callback(
    [Output('modal-value-attr-p4', 'is_open', allow_duplicate=True),
     Output('input-value-attr-name-p4', 'value'),
     Output('input-value-attr-unit-p4', 'value'),
     Output('select-value-attr-direction-p4', 'value'),
     Output('input-value-attr-target-p4', 'value'),
     Output('editing-value-attr-index-p4', 'data')],
    [Input({'type': 'btn-edit-value-attr-p4', 'index': ALL}, 'n_clicks')],
    prevent_initial_call=True
)
def open_edit_value_attr_modal_p4(n_clicks_list):
    """打开性能属性编辑模态框并预填充数据"""
    from dash import ctx

    if not any(n_clicks_list):
        return no_update, no_update, no_update, no_update, no_update, no_update

    triggered = ctx.triggered_id
    if triggered and triggered['type'] == 'btn-edit-value-attr-p4':
        index = triggered['index']

        # 从StateManager读取最新数据
        state = get_state_manager()
        value_attrs = state.load('phase1', 'value_attributes')

        # 统一处理DataFrame和list
        if isinstance(value_attrs, pd.DataFrame):
            value_attrs_list = value_attrs.to_dict('records')
        else:
            value_attrs_list = value_attrs if value_attrs else []

        if has_valid_data(value_attrs_list) and 0 <= index < len(value_attrs_list):
            attr = value_attrs_list[index]

            # 打开模态框，预填充数据，记录编辑索引
            return (
                True,  # 打开模态框
                attr['name'],
                attr.get('unit', ''),
                attr.get('direction', 'minimize'),
                str(attr.get('target')) if attr.get('target') is not None else '',
                index  # 记录编辑索引
            )

    return no_update, no_update, no_update, no_update, no_update, no_update


# 确认编辑性能属性
@callback(
    [Output('editing-value-attr-index-p4', 'data', allow_duplicate=True),
     Output('input-value-attr-name-p4', 'value', allow_duplicate=True),
     Output('input-value-attr-unit-p4', 'value', allow_duplicate=True),
     Output('select-value-attr-direction-p4', 'value', allow_duplicate=True),
     Output('input-value-attr-target-p4', 'value', allow_duplicate=True),
     Output('phase3-refresh-trigger', 'data', allow_duplicate=True)],
    [Input('btn-confirm-value-attr-p4', 'n_clicks')],
    [State('input-value-attr-name-p4', 'value'),
     State('input-value-attr-unit-p4', 'value'),
     State('select-value-attr-direction-p4', 'value'),
     State('input-value-attr-target-p4', 'value'),
     State('editing-value-attr-index-p4', 'data'),
     State('phase3-refresh-trigger', 'data')],
    prevent_initial_call=True
)
def confirm_edit_value_attr_p4(n_clicks, name, unit, direction, target, editing_index, current_trigger):
    """确认编辑性能属性 (修复目标值为0无法保存的问题)"""
    if n_clicks and name and editing_index is not None:
        state = get_state_manager()
        value_attrs = state.load('phase1', 'value_attributes')

        # 统一处理DataFrame和list
        if isinstance(value_attrs, pd.DataFrame):
            value_attrs_list = value_attrs.to_dict('records')
        else:
            value_attrs_list = value_attrs if value_attrs else []

        # 允许 target 为 0
        final_target = None
        if target is not None and str(target).strip() != "":
            try:
                final_target = float(target)
            except ValueError:
                final_target = None

        if 0 <= editing_index < len(value_attrs_list):
            # 更新属性数据
            value_attrs_list[editing_index] = {
                'name': name,
                'unit': unit or '',
                'direction': direction,
                'target': final_target
            }

            # 保存到StateManager（确保数据持久化）
            state.save('phase1', 'value_attributes', value_attrs_list)

            # 打印日志确认保存
            print(f"✅ Phase 3编辑保存成功: {name}, 索引={editing_index}, target={final_target}")

            # 清空输入框并重置编辑索引，触发刷新
            return None, "", "", "minimize", "", (current_trigger or 0) + 1

    return no_update, no_update, no_update, no_update, no_update, no_update


@callback(
    Output('phase3-doe-config-store', 'data', allow_duplicate=True),
    Input('url', 'pathname'),
    prevent_initial_call='initial_duplicate'
)
def load_doe_config_on_init(pathname):
    if pathname != '/phase3':
        return no_update
    state = get_state_manager()
    return state.load('phase3', 'doe_config')

@callback(
    [Output('checklist-cartesian-variables', 'value', allow_duplicate=True),
     Output('select-doe-method', 'value'),
     Output('input-lhs-samples', 'value'),
     Output('select-orthogonal-table', 'value')],
    Input('phase3-doe-config-store', 'data'),
    [State('checklist-cartesian-variables', 'options'),
     State('checklist-cartesian-variables', 'value')], 
    prevent_initial_call=True
)
def restore_ui_from_config(doe_config, current_options, current_values):
    """
    从配置恢复 UI 状态
    [关键修复]: 增加比对逻辑，如果变量选择未发生变化，返回 no_update，
    防止触发 update_sampling_config_area 导致 Step 2 DOM 重建和数据丢失。
    """
    if not doe_config:
        return no_update, no_update, no_update, no_update
    
    # 1. 恢复变量选择
    saved_vars = [v['name'] for v in doe_config.get('var_configs', [])]
    # 过滤掉已经不存在的变量
    valid_vars = [v for v in saved_vars if any(opt['value'] == v for opt in current_options)]
    
    # [核心修复] 检查是否真的需要更新
    # 如果当前选中的变量集合与保存的一致，则不更新 checklist，防止 DOM 重置
    current_set = set(current_values) if current_values else set()
    valid_set = set(valid_vars)
    
    update_checklist = valid_vars if current_set != valid_set else no_update
    
    # 2. 恢复 DOE 设置
    method = doe_config.get('method', 'none')
    lhs = doe_config.get('lhs_samples', 500)
    orth = doe_config.get('orthogonal_table', 'L8')
    
    return update_checklist, method, lhs, orth


# ==================== 数据管理回调 ====================

@callback(
    Output('phase3-save-status', 'children'),
    Input('btn-save-phase3', 'n_clicks'),
    [State('phase3-doe-config-store', 'data'),
     State('phase3-alternatives-store', 'data'), # Store数据优先
     State('phase3-csv-data', 'data'),           # CSV导入数据备用
     State('checklist-cartesian-variables', 'value'),
     State('checklist-enable-jitter', 'value'),
     State('slider-jitter-strength', 'value')],
    prevent_initial_call=True
)
def save_phase3_data(n_clicks, doe_config, alternatives, csv_data, 
                    selected_vars, enable_jitter, jitter_strength):
    """保存 Phase 3 所有数据 (DOE配置 + 设计方案 + UI状态)"""
    if not n_clicks:
        return no_update

    try:
        state = get_state_manager()
        
        # 1. 保存 DOE 配置
        if doe_config:
            state.save('phase3', 'doe_config', doe_config)
            
        # 2. 保存设计方案 
        #明确数据优先级：Store (生成/编辑后的) > CSV Data (导入的)
        data_to_save = None
        
        def _extract_data(source):
            if not source: return None
            if isinstance(source, dict) and 'data' in source: return source['data']
            if isinstance(source, list): return source
            if isinstance(source, pd.DataFrame): return source.to_dict('records')
            return None

        # 尝试从 alternatives-store 提取 (通常由 generate_filtered_design_space 更新)
        data_to_save = _extract_data(alternatives)
        
        # 如果 store 为空，尝试从 csv-data 提取
        if not data_to_save:
            data_to_save = _extract_data(csv_data)
            
        design_count = 0
        if data_to_save:
            # 确保每条记录都有 design_id
            for idx, row in enumerate(data_to_save):
                if 'design_id' not in row:
                    row['design_id'] = idx
            
            # 存入数据库
            state.save('phase3', 'alternatives', data_to_save)
            design_count = len(data_to_save)
        else:
            return dbc.Alert("⚠️ 未检测到有效的设计方案数据，仅保存了配置。", color="warning")

        # 3. 保存 UI 状态
        ui_state = {
            'selected_variables': selected_vars, 
            'enable_jitter': enable_jitter,      
            'jitter_strength': jitter_strength   
        }
        state.save('phase3', 'ui_state', ui_state)

        return dbc.Alert([
            "✓",
            f"Phase 3 数据已手动保存！",
            html.Hr(),
            html.Small([
                f"• 设计方案: {design_count} 个 (Phase 4 将使用此数据)", html.Br(),
                f"• DOE配置: {'已保存' if doe_config else '无'}", html.Br(),
                f"• UI状态: 已同步"
            ])
        ], color="success")

    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert([
            html.Span("⚠️", className="me-2"),
            f"❌ 保存失败: {str(e)}"
        ], color="danger")
    

@callback(
    [Output('phase3-doe-config-store', 'data', allow_duplicate=True),
     Output('phase3-alternatives-store', 'data', allow_duplicate=True),
     Output('phase3-csv-data', 'data', allow_duplicate=True),
     Output('phase3-column-types', 'data', allow_duplicate=True),
     Output('generation-stats', 'children', allow_duplicate=True),
     Output('phase3-save-status', 'children', allow_duplicate=True),
     Output('checklist-cartesian-variables', 'value', allow_duplicate=True),
     Output('checklist-enable-jitter', 'value', allow_duplicate=True),
     Output('slider-jitter-strength', 'value', allow_duplicate=True),
     Output('select-doe-method', 'value', allow_duplicate=True),     
     Output('input-lhs-samples', 'value', allow_duplicate=True),     
     Output('select-orthogonal-table', 'value', allow_duplicate=True),
     # [新增 Output] 同步 UI 状态到前端 Store
     Output('phase3-ui-state', 'data', allow_duplicate=True)], 
    [Input('btn-load-phase3', 'n_clicks'),
     Input('url', 'pathname')], 
    prevent_initial_call='initial_duplicate'
)
def load_phase3_data(n_clicks, pathname):
    """加载 Phase 3 数据并恢复 UI 状态 (包含 phase3-ui-state 的同步)"""
    from dash import ctx
    
    triggered_by_button = ctx.triggered_id == 'btn-load-phase3' and n_clicks
    triggered_by_url = ctx.triggered_id == 'url' and pathname == '/phase3'

    # 注意：Output增加了1个，返回元组长度必须为 13
    if not (triggered_by_button or triggered_by_url):
        return tuple([no_update] * 13)

    try:
        state = get_state_manager()
        
        # 1. 加载核心数据
        doe_config = state.load('phase3', 'doe_config')
        alternatives = state.load('phase3', 'alternatives')
        
        # 2. 加载 UI 状态
        ui_state = state.load('phase3', 'ui_state') or {}
        
        # 3. 准备恢复的 UI 值 (Drafts & Configs)
        restored_vars = ui_state.get('selected_variables', no_update)
        restored_jitter_en = ui_state.get('enable_jitter', ['enable']) 
        restored_jitter_str = ui_state.get('jitter_strength', 0.5)
        
        # DOE 配置恢复逻辑
        restored_doe_method = ui_state.get('doe_method') or (doe_config.get('method') if doe_config else 'none')
        restored_lhs_samples = ui_state.get('lhs_samples') or (doe_config.get('lhs_samples') if doe_config else 500)
        restored_orth_table = ui_state.get('orthogonal_table') or (doe_config.get('orthogonal_table') if doe_config else 'L8')

        # 4. 数据存在性检查
        def _has_valid_data(d):
            if d is None: return False
            if isinstance(d, pd.DataFrame): return not d.empty
            if isinstance(d, list): return len(d) > 0
            if isinstance(d, dict) and 'data' in d: return len(d['data']) > 0
            return False

        has_data = _has_valid_data(alternatives)
        alternatives_list = []
        column_types = {'design_vars': [], 'attributes': []}
        stats_msg = ""
        status_msg = no_update

        if has_data:
            if isinstance(alternatives, pd.DataFrame):
                alternatives_list = alternatives.to_dict('records')
                cols = [c for c in alternatives.columns if c != 'design_id']
            elif isinstance(alternatives, list) and len(alternatives) > 0:
                alternatives_list = alternatives
                cols = list(alternatives[0].keys())
            elif isinstance(alternatives, dict) and 'data' in alternatives:
                alternatives_list = alternatives['data']
                cols = list(alternatives_list[0].keys()) if alternatives_list else []
            else:
                alternatives_list = []
                cols = []
                
            column_types = {'design_vars': cols, 'attributes': []}

            stats_msg = html.Div([
                html.Strong(f"已加载 {len(alternatives_list)} 个设计方案"),
                html.Span(" (点击上方'生成统计信息'可查看详情)", className="text-muted ms-2")
            ])

            if triggered_by_button:
                status_msg = dbc.Alert([
                    "✓",
                    f"加载成功: {len(alternatives_list)} 个设计方案 + 配置状态"
                ], color="success")
        elif triggered_by_button:
             status_msg = dbc.Alert([
                html.Span("⚠️", className="me-2"),
                "未找到保存的设计方案数据"
            ], color="warning")

        # 返回值: 增加 ui_state 作为最后一个返回值
        return (
            doe_config, 
            alternatives_list, 
            alternatives_list, 
            column_types, 
            stats_msg, 
            status_msg,
            restored_vars,          
            restored_jitter_en,     
            restored_jitter_str,
            restored_doe_method,    
            restored_lhs_samples,   
            restored_orth_table,
            ui_state  # [新增] 将 DB 中的 state 注入前端 Store
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = dbc.Alert(f"加载异常: {str(e)}", color="danger")
        return tuple([no_update] * 12) + (error_msg,)
    

@callback(
    [Output('phase3-save-status', 'children', allow_duplicate=True),
     # [新增 Output] 更新前端 Store，确保其他回调能立即读到最新状态
     Output('phase3-ui-state', 'data', allow_duplicate=True)],
    [
        # 静态组件
        Input('checklist-cartesian-variables', 'value'),
        Input('checklist-enable-jitter', 'value'),
        Input('slider-jitter-strength', 'value'),
        Input('select-doe-method', 'value'),
        Input('input-lhs-samples', 'value'),
        Input('select-orthogonal-table', 'value'),
        
        # 动态组件 (Pattern Matching)
        Input({'type': 'sampling-method', 'var': ALL}, 'value'),
        Input({'type': 'n-values', 'var': ALL}, 'value'),
        Input({'type': 'manual-values', 'var': ALL}, 'value'),
        Input({'type': 'discrete-values', 'var': ALL}, 'value'),
        Input({'type': 'cat-select-val', 'var': ALL, 'opt': ALL}, 'value'),
        Input({'type': 'cat-map-val', 'var': ALL, 'opt': ALL}, 'value')
    ],
    prevent_initial_call=True
)
def auto_save_phase3_ui(selected_vars, enable_jitter, jitter_strength, 
                        doe_method, lhs_samples, orth_table,
                        sm_vals, n_vals, manual_vals, 
                        discrete_vals, 
                        cat_sel_vals, cat_map_vals):
    """
    UI 草稿层自动保存 (双写模式: DB + Frontend Store)
    [修复]: 增加保存分类变量的原始映射状态 (mappings)，支持UI回显
    """
    from dash import ctx
    
    if not ctx.triggered:
        return no_update, no_update

    try:
        state = get_state_manager()
        
        # 1. 基础配置
        current_ui = {
            'selected_variables': selected_vars,
            'enable_jitter': enable_jitter,
            'jitter_strength': jitter_strength,
            'doe_method': doe_method,
            'lhs_samples': lhs_samples,
            'orthogonal_table': orth_table,
            'timestamp': str(pd.Timestamp.now())
        }

        # 2. 解析动态组件状态 (var_configs_draft)
        var_configs = {}

        def get_var_config(v_name):
            if v_name not in var_configs:
                var_configs[v_name] = {}
            return var_configs[v_name]

        # 映射 ctx.inputs_list 索引
        # 0-5: 静态
        # 6: sampling-method
        for item in ctx.inputs_list[6]:
            var = item['id']['var']
            get_var_config(var)['method'] = item.get('value')
        # 7: n-values
        for item in ctx.inputs_list[7]:
            var = item['id']['var']
            get_var_config(var)['n_values'] = item.get('value')
        # 8: manual-values
        for item in ctx.inputs_list[8]:
            var = item['id']['var']
            get_var_config(var)['manual_values'] = item.get('value')
        # 9: discrete-values
        for item in ctx.inputs_list[9]:
            var = item['id']['var']
            get_var_config(var)['selected_values'] = item.get('value')
            
        # 10/11: categorical
        cat_temp = {} 
        for item in ctx.inputs_list[10]: # select
            var = item['id']['var']
            opt = item['id']['opt']
            if var not in cat_temp: cat_temp[var] = {}
            if opt not in cat_temp[var]: cat_temp[var][opt] = {}
            cat_temp[var][opt]['selected'] = item.get('value', False)

        for item in ctx.inputs_list[11]: # map
            var = item['id']['var']
            opt = item['id']['opt']
            if var not in cat_temp: cat_temp[var] = {}
            if opt not in cat_temp[var]: cat_temp[var][opt] = {}
            cat_temp[var][opt]['map_val'] = item.get('value')

        for var, opts in cat_temp.items():
            selected_mapped_values = []
            for opt, status in opts.items():
                if status.get('selected'):
                    raw_map = status.get('map_val')
                    final_val = opt
                    if raw_map is not None and str(raw_map).strip() != "":
                        try:
                            final_val = float(raw_map)
                        except ValueError:
                            final_val = raw_map
                    selected_mapped_values.append(final_val)
            get_var_config(var)['selected_values'] = selected_mapped_values
            # [关键修复] 保存原始映射状态，用于 update_sampling_config_area 回显
            get_var_config(var)['mappings'] = opts

        # 3. 合并配置
        current_ui['var_configs_draft'] = var_configs
        
        # 4. 执行 DB 保存
        state.save('phase3', 'ui_state', current_ui)
        
        # 5. 返回值: (无状态消息, 更新后的Store数据)
        return no_update, current_ui

    except Exception as e:
        print(f"Auto-save error: {e}")
        return no_update, no_update