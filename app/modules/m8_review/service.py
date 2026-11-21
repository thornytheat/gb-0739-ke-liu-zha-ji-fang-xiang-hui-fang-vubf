from collections import defaultdict
from copy import deepcopy

from app.problems import MESSAGES, Problem
from app.modules.m6_balance.service import reconcile

# 同一票号在同一时段最多成立一段有效行程、只认一次换乘。
REVIEW_DOWNGRADE_CODE = 'REVIEW_DOWNGRADED'
MESSAGES.setdefault(REVIEW_DOWNGRADE_CODE, '同票复核：仅保留一段换乘，本段按独立进出交班')


def transfer_groups(transfers):
    """按票号汇总本批被认成换乘（含复核后降级）的进站段；复核只面向同票多段换乘。"""
    groups = defaultdict(list)
    for row in transfers:
        if row['is_transfer'] or row.get('review_status') == REVIEW_DOWNGRADE_CODE:
            groups[row['ticket']].append(row)
    return {ticket: legs for ticket, legs in groups.items() if len(legs) > 1}


def review_summary(snapshot):
    data = snapshot.get('review')
    if not data:
        return None
    return {'revision_id': data['revision_id'], 'note_id': data['note_id'], 'ticket': data['ticket'],
            'kept_anchor': data['kept_anchor'], 'reason': data['reason'], 'period': data['period'],
            'status': data['status'], 'confirmed_at': data['confirmed_at'], 'base_run_id': data['base_run_id']}


def apply_review(base, ticket, kept_anchor):
    """对一份已发布快照应用同票复核，返回新的换乘判定与班报勾稽。

    保留票号在该批的第一段换乘（以 kept_anchor 指定的出站锚点为准），
    其余同票换乘段改为独立进出：物理进出不扣，只调整人次口径的换乘指标。
    """
    transfers = deepcopy(base['transfers'])
    ticket_legs = [row for row in transfers if row['is_transfer'] and row['ticket'] == ticket]
    kept = next((row for row in ticket_legs if row['anchor'] == kept_anchor), None)
    if kept is None or len(ticket_legs) < 2:
        raise Problem('REVIEW_ANCHOR')
    downgraded = []
    for row in ticket_legs:
        if row['anchor'] == kept_anchor:
            row['review_status'] = 'kept'
            continue
        # 物理锚点信息保留用于取证，业务口径上不再计换乘。
        row['original_anchor'] = row['anchor']
        row['original_from_station'] = row['from_station']
        row['original_anchor_ms'] = row['anchor_ms']
        row['original_anchor_line'] = row['anchor_line']
        row['original_gap_ms'] = row['gap_ms']
        row['original_link_line'] = row['link_line']
        row['review_status'] = REVIEW_DOWNGRADE_CODE
        row['review_reason'] = MESSAGES[REVIEW_DOWNGRADE_CODE]
        row['is_transfer'] = False
        row['anchor'] = None
        row['from_station'] = None
        row['anchor_ms'] = None
        row['anchor_line'] = None
        row['gap_ms'] = None
        row['link_line'] = None
        row['code'] = REVIEW_DOWNGRADE_CODE
        row['reason'] = MESSAGES[REVIEW_DOWNGRADE_CODE]
        row['unique_entry'] = 1
        downgraded.append(row['encounter'])
    balance = reconcile(base['aligned'], base['duplicates'], base.get('unavailable', []),
                        deepcopy(base['direction']), transfers, base['balance']['sources'])
    if not balance['balanced']:
        raise Problem('BALANCE_FAILED', 409, balance['checks'])
    return transfers, balance, downgraded


def shift_diff(base_balance, adjusted_balance):
    """逐站逐班对比重算前后的人数与换乘净数。"""
    before = {(row['shift'], row['station']): row for row in base_balance['shifts']}
    after = {(row['shift'], row['station']): row for row in adjusted_balance['shifts']}
    fields = ('entry', 'exit', 'transfer_in', 'transfer_out', 'transfer_net',
              'unique_entries', 'physical_net', 'nontransfer_net')
    rows = []
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        changed = False
        facts = {}
        for field in fields:
            delta = (new[field] if new else 0) - (old[field] if old else 0)
            if delta:
                changed = True
            facts[field] = {'before': old[field] if old else 0, 'after': new[field] if new else 0,
                            'delta': delta}
        rows.append({'shift': key[0], 'station': key[1], 'changed': changed, **facts})
    return rows


def leg_descriptions(snapshot):
    """供页面按票号说明每段行程的复核结论。"""
    result = []
    for ticket, legs in sorted(transfer_groups(snapshot['transfers']).items()):
        ordered = sorted(legs, key=lambda row: row['at_ms'])

        def anchor_time(row):
            return row['anchor_ms'] if row['anchor_ms'] is not None else row.get('original_anchor_ms')

        result.append({
            'ticket': ticket,
            'period_start_ms': min(anchor_time(row) for row in ordered),
            'period_end_ms': max(row['at_ms'] for row in ordered),
            'legs': [{
                'encounter': row['encounter'], 'station': row['station'],
                'from_station': row['from_station'] or row.get('original_from_station'),
                'anchor': row['anchor'] or row.get('original_anchor'),
                'anchor_ms': anchor_time(row), 'at_ms': row['at_ms'],
                'gap_ms': row['gap_ms'] if row['gap_ms'] is not None else row.get('original_gap_ms'),
                'entry_line': row['entry_line'],
                'anchor_line': row['anchor_line'] if row['anchor_line'] is not None else row.get('original_anchor_line'),
                'review_status': row.get('review_status', ''),
            } for row in ordered],
        })
    return result
