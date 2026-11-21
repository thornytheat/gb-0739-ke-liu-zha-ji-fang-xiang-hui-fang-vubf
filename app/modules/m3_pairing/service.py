from collections import defaultdict
from itertools import groupby

from app.modules.m3_pairing.stream import encounter, match_stream


def pair(pulses):
    gates = defaultdict(list)
    for pulse in pulses:
        gates[pulse['station'], pulse['gate']].append(pulse)
    evidence = []
    for gate_rows in gates.values():
        streams = defaultdict(list)
        ordered = sorted(gate_rows, key=lambda item: (item['corrected_ms'], item['pulse']))
        for instant, same_time in groupby(ordered, key=lambda item: item['corrected_ms']):
            frame = list(same_time)
            if len({row['beam'] for row in frame}) > 1:
                for stream in streams.values():
                    evidence.extend(match_stream(stream, tie_cut=instant))
                streams.clear()
                evidence.append(encounter('tie', frame, 'SIMULTANEOUS'))
            else:
                for pulse in frame:
                    streams[pulse['ticket']].append(pulse)
        for stream in streams.values():
            evidence.extend(match_stream(stream))
    return sorted(evidence, key=lambda item: (item['start_ms'], item['station'], item['gate'], item['encounter']))
