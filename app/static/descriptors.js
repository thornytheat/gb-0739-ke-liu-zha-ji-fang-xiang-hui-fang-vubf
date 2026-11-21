const pulse = ['pulse', '脉冲编号'];
const encounter = ['encounter', '证据编号'];
const station = ['station', '站点'];
const gate = ['gate', '闸机'];
const ticket = ['ticket', '票号'];
const line = ['line', '源行', 'line'];
const original = ['raw', '原值', 'detail'];
const stage = ['stage', '阶段'];
const code = ['code', '原因码'];
const start = ['start_ms', '起点', 'ms'];
const end = ['end_ms', '终点', 'ms'];
const corrected = ['corrected_ms', '校正时刻', 'ms'];
const source = ['source', '文件'];
const offset = ['offset_ms', '偏移 ms', 'number'];
const beam = ['beam', '光束'];
const pulseEvidence = ['pulses', '触发证据', 'pulses'];
const isolated = ['隔离行', [source, line, stage, ['key', '关联编号'], code, ['reason', '原因'], original]];
const pairs = [encounter, station, gate, ticket, ['pattern', '束序'], start, end, code, pulseEvidence];
const directions = [encounter, station, gate, ticket, ['label', '方向'], ['pattern', '束序'], ['duration_ms', '间隔 ms', 'number'], end, code, pulseEvidence];
const transfers = [encounter, station, ticket, ['anchor', '出站锚点'], ['from_station', '出站点'], ['gap_ms', '间隔 ms', 'number'],
  ['anchor_ms', '出站时刻', 'ms'], ['at_ms', '进站时刻', 'ms'], ['entry_line', '进站源行', 'number'],
  ['anchor_line', '出站源行', 'number'], ['link_line', '通道行', 'number'], ['pass_line', '票凭证行', 'number'], code];

export const sections = {
  intake: {
    main: ['采信触发', [pulse, station, gate, beam, ticket, ['device_ms', '设备时刻', 'ms'], line, original]],
    repeat: ['重复触发', [pulse, station, gate, beam, ticket, line, ['retained_line', '保留行', 'number'], original]],
    isolated,
  },
  clock: {
    main: ['校时结果', [pulse, station, gate, ['device_ms', '设备时刻', 'ms'], offset, corrected,
      ['offset_line', '版本源行', 'number'], line]],
    versions: ['偏移表', [station, gate, start, end, offset, line, original]],
    overlaps: ['重叠区间', [station, gate, start, end, code]],
    isolated,
  },
  pairing: {main: ['有序配对', pairs], orphans: ['孤脉冲', pairs]},
  direction: {main: ['方向记录', directions], exceptions: ['折返与未判定', directions]},
  transfer: {
    main: ['进站判定', transfers], anchors: ['换乘锚点', transfers],
    passes: ['票凭证', [ticket, start, end, ['transfer', '换乘资格', 'bool'], line, original]],
    links: ['有向通道', [['from_station', '起站'], ['to_station', '终站'], ['min_ms', '最短 ms', 'number'],
      ['max_ms', '最长 ms', 'number'], line, original]],
    isolated,
  },
  balance: {
    main: ['站点班次', [['shift', '班次'], station, ['trackable', '可回放触发', 'number'], ['evidence_pulses', '配对证据', 'number'],
      ['orphan_pulses', '孤脉冲', 'number'], ['repeats', '重复', 'number'], ['entry', '进站', 'number'], ['exit', '出站', 'number'],
      ['transfer_in', '换乘进', 'number'], ['transfer_out', '换乘出', 'number'], ['transfer_net', '换乘净数', 'number'],
      ['unique_entries', '去重进站', 'number'], ['physical_net', '进出净数', 'number'], ['pulse_difference', '脉冲差异', 'number']]],
    sources: ['源行勾稽', [source, ['logical_rows', '源逻辑行', 'number'], ['headers', '表头', 'number'],
      ['blanks', '空行', 'number'], ['accepted', '采信', 'number'], ['isolated', '隔离', 'number'], ['difference', '差异', 'number']]],
  },
  report: {main: ['输入清单', [source, ['sha256', 'SHA-256'], ['bytes', '字节', 'number']]], isolated},
};
