from collections import Counter, defaultdict
import heapq


def gate_key(row):
    return row['station'], row['gate']


def normalize_by_gate(pulses, versions):
    by_pulse, by_version = defaultdict(list), defaultdict(list)
    for pulse in pulses:
        by_pulse[gate_key(pulse)].append(pulse)
    for version in versions:
        by_version[gate_key(version)].append(version)
    for gate, entries in by_pulse.items():
        history = sorted(by_version[gate], key=lambda item: (item['start_ms'], item['line']))
        active, cursor = [], 0
        for entry in sorted(entries, key=lambda item: (item['device_ms'], item['pulse'])):
            instant = entry['device_ms']
            while cursor < len(history) and history[cursor]['start_ms'] <= instant:
                version = history[cursor]
                heapq.heappush(active, (version['end_ms'], version['line'], version))
                cursor += 1
            while active and active[0][0] <= instant:
                heapq.heappop(active)
            if len(active) == 1:
                yield entry, active[0][2], []
            else:
                yield entry, None, [active_item[1] for active_item in heapq.nsmallest(20, active)]


def overlap_regions(versions):
    marks = defaultdict(Counter)
    for version in versions:
        marks[gate_key(version)][version['start_ms']] += 1
        marks[gate_key(version)][version['end_ms']] -= 1
    for (station, gate), events in sorted(marks.items()):
        count = 0
        start = None
        for instant, delta in sorted(events.items()):
            before, count = count, count + delta
            if before < 2 <= count:
                start = instant
            elif before >= 2 > count:
                yield {'station': station, 'gate': gate, 'start_ms': start, 'end_ms': instant, 'code': 'CLOCK_OVERLAP'}
