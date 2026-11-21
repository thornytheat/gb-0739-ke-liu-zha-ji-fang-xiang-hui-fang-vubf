from collections import Counter
from time import perf_counter

from app.manifest import describe, run_manifest
from app.modules.m1_intake.reader import read
from app.modules.m1_intake.service import intake
from app.modules.m2_clock.service import correct, prepare
from app.modules.m3_pairing.service import pair
from app.modules.m4_direction.service import classify
from app.modules.m5_transfer.contracts import load_rules
from app.modules.m5_transfer.service import deduplicate
from app.modules.m6_balance.service import reconcile, source_balance
from app.problems import Problem
from app.settings import COLUMNS


def calculate(run_id, files):
    started = perf_counter()
    inputs = describe(files)
    issues = []
    stats = {name: {} for name in COLUMNS}

    def rows(name):
        return read(files[name], name, stats[name], issues)

    intake_rows, dup = intake(rows('pulses.csv'), issues)
    versions, conflicting, overlaps = prepare(rows('offsets.csv'), issues)
    aligned, unavailable = correct(intake_rows, versions + conflicting, issues)
    paired = pair(aligned)
    direction = classify(paired)
    passes, links = load_rules(rows('passes.csv'), rows('links.csv'), issues)
    transfers = deduplicate(direction, passes, links)
    counts = {'pulses.csv': len(aligned), 'offsets.csv': len(versions), 'passes.csv': len(passes), 'links.csv': len(links)}
    sources = source_balance(stats, issues, counts)
    balance = reconcile(aligned, dup, unavailable, direction, transfers, sources)
    if not balance['balanced']:
        raise Problem('BALANCE_FAILED', 409, balance['checks'])
    issues.sort(key=lambda item: (item['source'], item['line'], item['stage']))
    return {'manifest': run_manifest(run_id, inputs, round((perf_counter() - started) * 1000)),
            'intake': intake_rows, 'duplicates': dup, 'versions': versions, 'overlaps': overlaps,
            'aligned': aligned, 'pairs': paired, 'direction': direction, 'passes': passes, 'links': links,
            'transfers': transfers, 'balance': balance, 'isolated': issues,
            'reason_counts': dict(sorted(Counter(row['code'] for row in issues).items()))}
