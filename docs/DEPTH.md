# 深度登记 · 客流闸机方向回放

中型项目。站点客运报表员在核准班报前校正闸机时钟、核对束序及跨站换乘，并从凭证追到具体触发及规则源行。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 闸机采信 | 导入四表，检查触发原值与矛盾 | `POST /api/runs`、`GET /api/intake/{run_id}` | `app/modules/m1_intake/reader.py` `app/modules/m1_intake/service.py` | `tests/test_intake.py` |
| M2 时钟偏移 | 回查设备版本、校时及冲突区间 | `GET /api/clock/{run_id}` | `app/modules/m2_clock/index.py` `app/modules/m2_clock/service.py` | `tests/test_clock.py` |
| M3 双束配对 | 对照预期顺序、尾随与孤脉冲 | `GET /api/pairing/{run_id}` | `app/modules/m3_pairing/stream.py` `app/modules/m3_pairing/service.py` | `tests/test_pairing.py` |
| M4 方向与折返 | 从方向轨定位往返、等时及证据 | `GET /api/direction/{run_id}` | `app/modules/m4_direction/service.py` | `tests/test_direction.py` |
| M5 换乘去重 | 复核票有效期、通道和出站锚点 | `GET /api/transfer/{run_id}` | `app/modules/m5_transfer/contracts.py` `app/modules/m5_transfer/service.py` | `tests/test_transfer.py` |
| M6 客流勾稽 | 核对逐站逐班源行、触发与客流 | `GET /api/balance/{run_id}` | `app/modules/m6_balance/shifts.py` `app/modules/m6_balance/service.py` | `tests/test_balance.py` |
| M7 班报复算 | 核对输入哈希及原始依据，下载班报 | `GET /api/report/{run_id}`、`GET /api/report/{run_id}/export` | `app/modules/m7_report/bundle.py` `app/modules/m7_report/serializers.py` | `tests/test_report.py` |

## 陷阱登记

| TRAP | 样例现象 | 朴素实现会怎样 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-01 | offsets.csv 的「待校」以 GB18030 编码 | 直接 UTF-8 导入失败 | 回退并保留原始非数值 | `app/modules/m1_intake/reader.py` | `tests/test_clock.py::test_gb18030_fallback_preserves_dirty_calibration_value` |
| TRAP-02 | pulses.csv 有 BOM | 首列编号偏离列名 | UTF-8 BOM 解码 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_bom_ticket_zeroes_and_multiline_note` |
| TRAP-03 | pulses.csv 补单有带换行的附注 | 将记录拆为两条 | 逻辑记录归一，保留物理行 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_bom_ticket_zeroes_and_multiline_note` |
| TRAP-04 | pulses.csv 分段有重复表头 | 把列名当脉冲解析 | 计表头并跳过 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_extra_column_retained_and_segment_headers_are_skipped` |
| TRAP-05 | pulses.csv 给 EXTRA 留多余分隔符 | 脏列被静默吞掉 | 从源行隔离并报告列数 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_extra_column_retained_and_segment_headers_are_skipped` |
| TRAP-07 | pulses.csv 尾随行混用空串、N/A、未知 | 误当有效票凭证 | 统一匿名，禁止匿名换乘 | `app/fields.py` | `tests/test_intake.py::test_missing_ticket_sentinels_are_null_and_remain_traceable` |
| TRAP-08 | pulses.csv 票号 00017 | 丢前导零，接不上票凭证 | 票号文本贯穿全部业务 | `app/fields.py` | `tests/test_intake.py::test_bom_ticket_zeroes_and_multiline_note` |
| TRAP-11 | pulses.csv 同一触发两种时区表示 | 重传算两次 | UTC 毫秒归一后去重 | `app/fields.py` | `tests/test_intake.py::test_equal_pulse_in_utc_is_a_retransmission` |
| TRAP-13 | pulses.csv 的 TR-IN-B 先于 TR-IN-A 到文件 | 判成出站 | 先对齐版本再排序 | `app/modules/m3_pairing/service.py` | `tests/test_pairing.py::test_out_of_order_source_uses_corrected_time_and_keeps_each_source_line` |
| TRAP-14 | pulses.csv 的 CONFLICT 同号异束 | 后写覆盖产生方向 | 冲突组全隔离 | `app/evidence.py` | `tests/test_intake.py::test_same_pulse_with_two_different_beams_is_excluded` |
| TRAP-19 | pulses.csv 两束等时、匿名短往返 | 用文件顺序强行算方向 | 等时优先切段，匿名往返保留歧义 | `app/modules/m3_pairing/service.py` `app/modules/m4_direction/service.py` | `tests/test_direction.py::test_anonymous_return_and_simultaneous_frame_never_invent_direction` |
| TRAP-23 | offsets.csv 两个相邻版本在午夜切换 | 双命中或用错校时偏差 | 起点含、终点不含 | `app/modules/m2_clock/index.py` | `tests/test_clock.py::test_end_of_old_clock_interval_is_start_of_new_clock_version` |
| TRAP-25 | offsets.csv 西站两段版本交叠 | 任取第一个导致方向漂移 | 保留重叠区间及版本行，隔离命中的触发 | `app/modules/m2_clock/index.py` `app/modules/m2_clock/service.py` | `tests/test_clock.py::test_intersecting_clock_versions_quarantine_only_overlap` |

## 勾稽与回放边界

逐站逐班核对触发、配对证据、孤脉冲、重复、进出、换乘净数及去重进站。逐脉冲唯一归属也必须满足。文件按逻辑行勾稽，偏移缺失与重叠单列。原始快照和结果同一事务发布，同源并发只建立一条批次，历史重跑只复用历史批次。受输入边界约束，缺前置或后续脉冲按孤脉冲保留，缺换乘锚点保留独立进站。
