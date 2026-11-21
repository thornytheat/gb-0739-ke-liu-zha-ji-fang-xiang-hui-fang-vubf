# 客流闸机方向回放

站点客运报表员上传闸机双束触发、设备偏移表、票凭证与站间换乘通道，校正时间后回放进出与折返，生成能追到脉冲来源行的班报。首页用深靛色进出双轨展示最近 36 组证据，点击条带查看束序，点击换乘标记回查出站锚点。

## 启动与试用

```bash
docker compose up --build
```

打开 `http://localhost:18428`，点「运行回放」，核对 9 次进站、2 次出站、1 次换乘与 8 次去重进站。切换左侧模块或点击瀑布中的换乘锚点，定位 `E-TR-OUT-B`。发布后「重跑」复用同源批次，「下载班报凭证」下载 ZIP。也可打开 `/?run=sample` 预览样例，或从「导入 CSV」提交四份文件。列名、阈值及班次定义见[数据字典](docs/DATA-DICTIONARY.md)。

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 18428
python -m pytest -q
```

容器内可用 `docker compose exec -T app pytest -q`。SQLite 默认写入 `data/replay.sqlite3`，环境变量 `GATE_DB_PATH` 可指定文件路径。Compose 将数据保存在命名卷 `replay-data`，确认所有批次可丢弃后可用 `docker compose down -v` 重建卷。

## 业务入口

| 模块 | 证据 | API |
|---|---|---|
| 闸机采信 | 触发原值、行号、去重和隔离 | `GET /api/intake/{run_id}` |
| 时钟偏移 | 校时前后、命中版本、重叠区间 | `GET /api/clock/{run_id}` |
| 双束配对 | 尾随配对、候选截止、孤脉冲 | `GET /api/pairing/{run_id}` |
| 方向与折返 | A→B、B→A、折返和等时歧义 | `GET /api/direction/{run_id}` |
| 换乘去重 | 有向通道、时距、凭证与出站锚点 | `GET /api/transfer/{run_id}` |
| 客流勾稽 | 同站同班的脉冲解释、进出量和换乘净数 | `GET /api/balance/{run_id}` |
| 班报复算 | 输入清单、隔离与取证 ZIP | `GET /api/report/{run_id}` |

模块查询可用 `sample` 预览，提供 `view`、`q`、`station`、`offset`、`limit`。发布样例用 `POST /api/runs/sample`，上传用 `POST /api/runs`，重跑用 `POST /api/runs/{run_id}/rerun`，导出用 `GET /api/report/{run_id}/export`。接口定义在 `/docs`。

同计算版本、阈值与原始文件字节复用同一批次，输入变化形成新批次。每份文件限 512 KiB 及 12,000 个逻辑行。本服务回放单批离线报表。脉冲及换乘所需的前后记录必须在同次输入中，自定义报告班次与实时硬件接入不在本次范围。
