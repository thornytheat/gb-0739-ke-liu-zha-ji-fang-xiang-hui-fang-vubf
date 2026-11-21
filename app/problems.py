class Problem(Exception):
    def __init__(self, code, status=422, detail=None):
        self.code, self.status, self.detail = code, status, detail
        super().__init__(code)


class BadRow(Exception):
    pass


MESSAGES = {
    'FILE_SET': '请提交四份规定名称的 CSV', 'EMPTY_FILE': '文件没有内容', 'ONLY_BLANK': '文件只有空行',
    'BAD_HEADER': '文件表头不符合契约', 'BAD_ENCODING': '文件编码无法识别', 'BAD_CSV': 'CSV 有未闭合字段',
    'FILE_LIMIT': '文件超过字节或逻辑行上限', 'BAD_COLUMNS': '列数与表头不符',
    'BAD_KEY': '业务编号格式无效', 'MISSING_VALUE': '必填字段缺失', 'BAD_TIME': '时间格式或时区无效',
    'BAD_INTEGER': '数值须为规定范围的整数', 'BAD_WINDOW': '开始时间须早于结束时间',
    'BAD_BEAM': '光束须为 A 或 B', 'BAD_TRANSFER_FLAG': '换乘资格须为 yes 或 no',
    'BAD_LINK': '站间通道或时长范围无效', 'NO_PULSES': '没有可采信的触发', 'NO_CLOCKED': '没有可校时的触发',
    'PULSE_DUPLICATE': '保留同编号的首条等价触发', 'PULSE_CONFLICT': '同编号触发存在矛盾',
    'CLOCK_DUPLICATE': '校时表重复定义', 'CLOCK_CONFLICT': '同一校时时窗有矛盾的偏移',
    'CLOCK_GAP': '无生效偏移', 'CLOCK_OVERLAP': '同一设备时间命中多个偏移',
    'PASS_DUPLICATE': '票凭证重复导出', 'PASS_CONFLICT': '同票有矛盾的换乘凭证',
    'LINK_DUPLICATE': '站间通道重复导出', 'LINK_CONFLICT': '同一通道有矛盾的换乘时长',
    'ORPHAN_TIMEOUT': '有效时间内只有单束触发', 'ORPHAN_TIE_BOUNDARY': '等时歧义截断候选窗口',
    'ORPHAN_END': '文件结束前缺少另一束', 'SIMULTANEOUS': '两束等时，先后不明',
    'ANONYMOUS_RETURN': '无票三束往返，方向未判定', 'RETURNED': '同票短间隔返回起始束',
    'PASS_UNKNOWN': '缺少有效票凭证', 'PASS_NOT_TRANSFERABLE': '票凭证不允许换乘',
    'PASS_EXPIRED': '进站时刻在票有效期外', 'NO_TICKET': '缺票号，保留独立进站',
    'NO_ELIGIBLE_EXIT': '没有可用的有向出站锚点', 'TRANSFER': '已关联跨站出站锚点',
    'RUN_NOT_FOUND': '未找到回放批次', 'UNKNOWN_VIEW': '证据视图不存在', 'BALANCE_FAILED': '客流勾稽失败',
}
