# -*- coding: utf-8 -*-
"""
生成 iOS 快捷指令源文件（XML plist）
====================================
产出一个未签名的 .shortcut 源文件，可在 macOS 上用 `shortcuts sign` 签名后导入 iPhone。

关键设计
--------
1. **WFWorkflowImportQuestions**：导入时弹窗问「推送地址」，用户不用打开编辑器改任何东西。
2. **类型筛选用 Values.Enumeration + WFStringSubstitutableState**：
   这是 iOS Shortcuts 识别「健康类型选择器」的唯一正确写法。
   用普通字符串会退化成可编辑文本筛选（导入后显示成 "Value is Step Count"）。
3. **日期筛选用 Operator 1002（is today）+ 相对天数**，覆盖「昨天之后 → 现在之前」。
4. **输出用「统计」动作**：步数类求和、体重/HRV/血氧取平均值。

用法：python make_shortcut.py
产出：推送健康数据.plist
"""
import uuid, plistlib, os, sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '推送健康数据.plist')

# ── 动作标识符 ──────────────────────────────────────────────
FIND_HEALTH = 'is.workflow.actions.filter.health.quantity'
GET_DETAIL = 'is.workflow.actions.properties.health.quantity'
GET_URL = 'is.workflow.actions.getcontentsOfURL'
DICT = 'is.workflow.actions.dictionary'
TEXT = 'is.workflow.actions.text'
MATH = 'is.workflow.actions.math'
SET_VAR = 'is.workflow.actions.setvariable'
COMMENT = 'is.workflow.actions.comment'

# ── 健康类型 → iOS 选择器显示名 ──────────────────────────────
# 注意：必须是 Shortcuts 选择器里的显示名，不是 HealthKit 标识符。
HEALTH_TYPES = [
    # (显示名, 输出变量名, 聚合方式, 单位提示)
    ('Steps',                    'Steps',      'sum',  'count'),
    ('Body Mass',                'BodyMass',   'last', 'kg'),
    ('Heart Rate Variability',   'HRV',        'last', 'ms'),
    ('Oxygen Saturation',        'SpO2',       'last', 'fraction'),
    ('VO2 Max',                  'VO2Max',     'last', 'mL/kg/min'),
    ('Active Energy',            'ActiveEnergy','sum', 'kcal'),
    ('Basal Energy',             'BasalEnergy','sum', 'kcal'),
    ('Exercise Minutes',         'ExerciseMin','sum', 'min'),
    ('Apple Stand Time',         'StandMin',   'sum', 'min'),
    ('Daylight Exposure',        'DaylightMin','sum', 'min'),
    ('Flights Climbed',          'Flights',    'sum', 'count'),
]

# 目标 JSON 键名（与服务端 SHORTCUT_METRIC_MAP 对应）
KEY_MAP = {
    'Steps': 'steps', 'BodyMass': 'body_mass', 'HRV': 'hrv_sdnn',
    'SpO2': 'spo2', 'VO2Max': 'vo2max', 'ActiveEnergy': 'active_kcal',
    'BasalEnergy': 'basal_kcal', 'ExerciseMin': 'exercise_min',
    'StandMin': 'stand_min', 'DaylightMin': 'daylight_min', 'Flights': 'floors',
}

# 睡眠类型（类别样本，单独处理）
SLEEP_TYPE = 'Sleep'


def uid():
    return str(uuid.uuid4()).upper()


def token_attachment(output_uuid, output_name, prefix='￼'):
    """构造引用上一个动作输出的附件（WFTextTokenAttachment）。"""
    return {
        'Value': {
            'string': f'{prefix}{output_uuid}',
            'attachmentsByRange': {
                '{0, 1}': {
                    'Type': 'ActionOutput',
                    'OutputName': output_name,
                    'OutputUUID': output_uuid,
                    'Aggrandizements': [],
                }
            },
        },
        'WFSerializationType': 'WFTextTokenAttachment',
    }


def dict_value_attachment(output_uuid, output_name):
    """把字典作为值引用（WFTextTokenAttachment + DictionaryValue）。"""
    return {
        'Value': {
            'Value': {
                'Type': 'ActionOutput',
                'OutputName': output_name,
                'OutputUUID': output_uuid,
                'Aggrandizements': [],
            },
            'OutputUUID': output_uuid,
            'OutputName': output_name,
            'Aggrandizements': [],
        },
        'WFSerializationType': 'WFTextTokenAttachment',
    }


def find_health_samples(display_name, output_uuid, output_name, type_only=False):
    """构造「查找健康样本」动作。

    type_only=True 时不加日期筛选（用于睡眠这类需要跨夜查询的）。
    """
    params = {
        'UUID': output_uuid,
        'CustomOutputName': output_name,
        'WFContentItemFilter': {
            'Value': {
                'WFActionParameterFilterPrefix': 1,
                'WFContentPredicateBoundedDate': {
                    'Value': {
                        'Bounded': True,
                        'Operator': 4,
                        'Removable': False,
                        'Values': {
                            'Enumeration': {
                                'Value': display_name,
                                'WFSerializationType': 'WFStringSubstitutableState',
                            },
                        },
                    },
                },
            },
        },
    }
    if not type_only:
        # 开始日期：昨天之后（相对天数）
        params['WFContentItemFilter']['Value']['WFContentPredicateBoundedDate']['Value']['Values']['Enumeration'] = {
            'Value': display_name,
            'WFSerializationType': 'WFStringSubstitutableState',
        }
        # 结束日期：现在之前
        params['WFEndDateFilter'] = {
            'Value': {
                'Bounded': True,
                'Operator': 1002,
                'Removable': False,
                'Values': {'Number': 0, 'Unit': 16},
            },
        }
        params['WFStartDateFilter'] = {
            'Value': {
                'Bounded': True,
                'Operator': 1002,
                'Removable': False,
                'Values': {'Number': 1, 'Unit': 16},
            },
        }
    return {
        'WFWorkflowActionIdentifier': FIND_HEALTH,
        'WFWorkflowActionParameters': params,
    }


def get_detail(prop, output_uuid, output_name, source_uuid, source_name):
    """「取健康样本详情」——取出某个属性。"""
    return {
        'WFWorkflowActionIdentifier': GET_DETAIL,
        'WFWorkflowActionParameters': {
            'UUID': output_uuid,
            'CustomOutputName': output_name,
            'WFContentItemPropertyName': prop,
            'WFInput': token_attachment(source_uuid, source_name),
        },
    }


def math_op(operation, operand_uuid, operand_name, output_uuid, output_name):
    """数学运算（求和/平均）。"""
    return {
        'WFWorkflowActionIdentifier': MATH,
        'WFWorkflowActionParameters': {
            'UUID': output_uuid,
            'CustomOutputName': output_name,
            'WFInput': token_attachment(operand_uuid, operand_name),
            'WFMathOperation': operation,
        },
    }


def build():
    actions = []
    # 每个指标的取值变量名 → (action uuid, 变量名)
    value_refs = {}

    # ── 1) 逐个指标：查找健康样本 → 取详情(值) → 统计
    for disp, out_name, agg, unit in HEALTH_TYPES:
        find_uuid = uid()
        actions.append(find_health_samples(disp, find_uuid, f'{out_name}Samples'))

        val_uuid = uid()
        actions.append(get_detail('Value', val_uuid, f'{out_name}Value',
                                  find_uuid, f'{out_name}Samples'))

        stat_uuid = uid()
        stat_name = f'{out_name}Stat'
        actions.append(math_op('StatisticsAverage' if agg == 'last' else 'StatisticsSum',
                               val_uuid, f'{out_name}Value', stat_uuid, stat_name))
        value_refs[out_name] = (stat_uuid, stat_name, KEY_MAP[out_name])

    # ── 2) 睡眠：查找睡眠样本（不加日期筛选，交由起止时间决定归属）
    sleep_find_uuid = uid()
    actions.append(find_health_samples(SLEEP_TYPE, sleep_find_uuid, 'SleepSamples', type_only=True))
    sleep_start_uuid = uid()
    actions.append(get_detail('Start Date', sleep_start_uuid, 'SleepStart',
                              sleep_find_uuid, 'SleepSamples'))
    sleep_end_uuid = uid()
    actions.append(get_detail('End Date', sleep_end_uuid, 'SleepEnd',
                              sleep_find_uuid, 'SleepSamples'))
    sleep_val_uuid = uid()
    actions.append(get_detail('Value', sleep_val_uuid, 'SleepStage',
                              sleep_find_uuid, 'SleepSamples'))

    # ── 3) 组装 metrics 字典
    dict_uuid = uid()
    dict_params = {
        'UUID': dict_uuid,
        'CustomOutputName': 'Metrics',
        'WFDictionaryType': 'Dictionary',
    }
    for out_name, (s_uuid, s_name, key) in value_refs.items():
        dict_params[key] = token_attachment(s_uuid, s_name)
    actions.append({
        'WFWorkflowActionIdentifier': DICT,
        'WFWorkflowActionParameters': dict_params,
    })

    # ── 4) 组装 sleep 数组（分段 → 字典）
    #    为简化：每段一个字典，放进数组
    sleep_dict_uuid = uid()
    actions.append({
        'WFWorkflowActionIdentifier': DICT,
        'WFWorkflowActionParameters': {
            'UUID': sleep_dict_uuid,
            'CustomOutputName': 'SleepItem',
            'WFDictionaryType': 'Dictionary',
            'type': 'sleep',
            'start': token_attachment(sleep_start_uuid, 'SleepStart'),
            'end': token_attachment(sleep_end_uuid, 'SleepEnd'),
            'stage': token_attachment(sleep_val_uuid, 'SleepStage'),
        },
    })

    # 重复输出为数组
    repeat_uuid = uid()
    actions.append({
        'WFWorkflowActionIdentifier': 'is.workflow.actions.repeat.each',
        'WFWorkflowActionParameters': {
            'UUID': repeat_uuid,
            'CustomOutputName': 'SleepArray',
            'WFInput': token_attachment(sleep_find_uuid, 'SleepSamples'),
            'WFGroupingIdentifier': uid(),
            'WFStopOnEnd': False,
        },
    })
    # repeat 内部再放一个字典动作（引用 repeat 的输入）
    inner_uuid = uid()
    actions.append({
        'WFWorkflowActionIdentifier': DICT,
        'WFWorkflowActionParameters': {
            'UUID': inner_uuid,
            'CustomOutputName': 'SleepItem',
            'WFDictionaryType': 'Dictionary',
            'type': 'sleep',
            'start': token_attachment(sleep_start_uuid, 'SleepStart'),
            'end': token_attachment(sleep_end_uuid, 'SleepEnd'),
            'stage': token_attachment(sleep_val_uuid, 'SleepStage'),
        },
    })
    # repeat 结束
    actions.append({
        'WFWorkflowActionIdentifier': 'is.workflow.actions.stop',
        'WFWorkflowActionParameters': {'UUID': uid(), 'WFGroupingIdentifier': actions[-2]['WFWorkflowActionParameters']['WFGroupingIdentifier']},
    })

    # ── 5) 最终 payload 字典
    payload_uuid = uid()
    url_action_index = None
    payload_dict_uuid = uid()
    actions.append({
        'WFWorkflowActionIdentifier': DICT,
        'WFWorkflowActionParameters': {
            'UUID': payload_dict_uuid,
            'CustomOutputName': 'Payload',
            'WFDictionaryType': 'Dictionary',
            'source': 'shortcut',
            'metrics': dict_value_attachment(dict_uuid, 'Metrics'),
            'sleep': token_attachment(repeat_uuid, 'SleepArray'),
        },
    })

    # ── 6) 获取 URL 内容（POST）
    geturl_uuid = uid()
    url_action_index = len(actions)
    actions.append({
        'WFWorkflowActionIdentifier': GET_URL,
        'WFWorkflowActionParameters': {
            'UUID': geturl_uuid,
            'CustomOutputName': 'Server Response',
            'WFURL': '{{PUSH_URL}}',          # 导入时由 WFWorkflowImportQuestions 填充
            'WFHTTPMethod': 'POST',
            'WFHTTPBodyType': 'Json',
            'WFRequestBody': dict_value_attachment(payload_dict_uuid, 'Payload'),
        },
    })

    # ── 7) 收尾：显示结果
    actions.append({
        'WFWorkflowActionIdentifier': 'is.workflow.actions.showresult',
        'WFWorkflowActionParameters': {
            'UUID': uid(),
            'CustomOutputName': 'Result',
            'WFInput': token_attachment(geturl_uuid, 'Server Response'),
        },
    })

    root = {
        'WFWorkflowActions': actions,
        'WFWorkflowClientVersion': '2607.0.3',
        'WFWorkflowClientRelease': '2.7',
        'WFWorkflowMinimumClientVersion': 900,
        'WFWorkflowMinimumClientVersionString': '900',
        'WFWorkflowName': '推送健康数据',
        'WFWorkflowIcon': {
            'WFWorkflowIconGlyphNumber': 59754,   # heart
            'WFWorkflowIconStartColor': 4282601983,  # 红
        },
        'WFWorkflowImportQuestions': [
            {
                'ActionIndex': url_action_index,
                'Category': 'Parameter',
                'DefaultValue': '',
                'ParameterKey': 'WFURL',
                'Text': '粘贴推送地址（含 ?sharecode= 参数）',
            },
        ],
        'WFWorkflowInputContentItemClasses': [],
        'WFWorkflowOutputContentItemClasses': [],
        'WFWorkflowTypes': [],
        'WFWorkflowHasShortcutInputVariables': False,
    }

    with open(OUT, 'wb') as f:
        plistlib.dump(root, f, fmt=plistlib.FMT_XML)
    print(f'已生成: {OUT}')
    print(f'  动作数: {len(actions)}')
    print(f'  指标数: {len(value_refs)} + 睡眠')
    return OUT


if __name__ == '__main__':
    build()
