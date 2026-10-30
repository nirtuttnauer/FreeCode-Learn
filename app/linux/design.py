"""The same educational DAG capacity model as DesignWorkspace.swift."""
import math
import uuid


def component(kind, name=None, x=0.5, y=0.5):
    return dict(id=str(uuid.uuid4()), name=name or kind, kind=kind, x=x, y=y,
                replicas=1, capacityPerReplica={'Client': 0, 'Service': 250, 'Cache': 5000, 'Database': 1000, 'Queue': 200}[kind],
                latencyMilliseconds={'Cache': 1, 'Database': 20}.get(kind, 10), available=True)


def workspace():
    nodes = [component('Client', x=0), component('Service', 'API service'), component('Database', x=1)]
    edges = [dict(id=str(uuid.uuid4()), **{'from': a['id'], 'to': b['id']}, label=label)
             for a, b, label in [(nodes[0], nodes[1], 'request'), (nodes[1], nodes[2], 'read / write')]]
    return dict(diagram=dict(components=nodes, connections=edges),
                scenario=dict(requestsPerSecond=200, readPercent=80, cacheHitPercent=80, durationSeconds=60),
                requirements='', capacityReasoning='', dataModel='', requestFlow='', failureModes='', tradeoffs=[], experiments=[])


def simulate(diagram, scenario):
    def invalid(message):
        return dict(valid=False, completedPerSecond=0, uncachedPathMilliseconds=None, stages=[], observations=[message])
    def bounded(value, low, high):
        return type(value) in (int, float) and math.isfinite(value) and low <= value <= high
    try:
        rate, reads, hits, duration = [scenario[k] for k in ['requestsPerSecond', 'readPercent', 'cacheHitPercent', 'durationSeconds']]
        if not all([bounded(rate, 0, 1e9), bounded(reads, 0, 100), bounded(hits, 0, 100), bounded(duration, 1, 86400)]):
            return invalid('Use finite nonnegative traffic, percentages from 0 to 100, and 1–86,400 seconds.')
        nodes, edges = diagram['components'], diagram['connections']
        if not 1 <= len(nodes) <= 12 or len(edges) > 36:
            return invalid('Use up to 12 components and 36 forward connections.')
        by_id = {n['id']: n for n in nodes}
        if len(by_id) != len(nodes) or len({e['id'] for e in edges}) != len(edges):
            return invalid('Component and connection IDs must be unique.')
        clients = [n for n in nodes if n['kind'] == 'Client']
        if len(clients) != 1:
            return invalid('Use exactly one client as the request source.')
        client = clients[0]['id']
        outgoing, counts = {i: [] for i in by_id}, {i: 0 for i in by_id}
        pairs = set()
        for edge in edges:
            a, b = edge['from'], edge['to']
            if a not in by_id or b not in by_id or a == b or b == client or (a, b) in pairs:
                return invalid('Use distinct forward connections between existing components.')
            pairs.add((a, b)); outgoing[a].append(b); counts[b] += 1
        order = [i for i in counts if counts[i] == 0]
        for i in order:
            for child in outgoing[i]:
                counts[child] -= 1
                if counts[child] == 0:
                    order.append(child)
        if len(order) != len(nodes):
            return invalid('Request flow cannot contain cycles. Responses are implicit.')
        for node in nodes:
            if node['kind'] not in ['Client', 'Service', 'Cache', 'Database', 'Queue']:
                return invalid('Unknown component kind.')
            if node['kind'] != 'Client' and not all([type(node['replicas']) is int, bounded(node['replicas'], 1, 32), bounded(node['capacityPerReplica'], 1, 1e7), bounded(node['latencyMilliseconds'], 0, 60000)]):
                return invalid('Use 1–32 replicas, capacity 1–10,000,000, and latency 0–60,000 ms.')
        reached = {client}
        for i in order:
            if i in reached:
                reached.update(outgoing[i])
        if len(reached) < 2:
            return invalid('Connect the client to a processing component.')
        demand, own, latency = {client: rate}, {}, {}
        stages, observations, finite = [], [], True
        bypass = reads / 100 * hits / 100
        for i in order:
            if i not in reached:
                continue
            node = by_id[i]; incoming = demand.get(i, 0); available = node['available']
            capacity = incoming if i == client else node['replicas'] * node['capacityPerReplica'] if available else 0
            completed = min(incoming, capacity) if available else 0
            own[i] = completed / incoming if incoming else 1
            utilization = incoming / capacity if i != client and capacity else None
            backlog = max(0, incoming - capacity) * duration if node['kind'] == 'Queue' else 0
            if i == client or incoming == 0:
                delay = 0
            elif not available or (utilization or 0) >= 1 or node['kind'] == 'Queue':
                delay = None
            else:
                delay = node['latencyMilliseconds'] / (1 - (utilization or 0))
            if i != client:
                stages.append(dict(id=i, name=node['name'], kind=node['kind'], incoming=incoming, capacity=capacity,
                                   utilization=utilization, completed=completed, backlog=backlog, available=available, latencyMilliseconds=delay))
                if not available:
                    observations.append(node['name'] + ' is unavailable; incoming work cannot be processed.')
                elif (utilization or 0) >= 1:
                    observations.append(node['name'] + ' has no capacity headroom. Add replicas, reduce load, or change the path.')
                if node['kind'] == 'Queue':
                    observations.append(f"{node['name']} adds {int(backlog):,} pending jobs. Queue waiting time is not modeled.")
            if delay is None:
                finite = False
            total = latency.get(i, 0) + (delay or 0); latency[i] = total
            for child in outgoing[i]:
                demand[child] = demand.get(child, 0) + completed * (1 - bypass if node['kind'] == 'Cache' else 1)
                latency[child] = max(latency.get(child, 0), total)
        success = {}
        for i in reversed(order):
            if i not in reached:
                continue
            downstream = min([success.get(c, 1) for c in outgoing[i]], default=1)
            fraction = bypass + (1 - bypass) * downstream if by_id[i]['kind'] == 'Cache' and outgoing[i] else downstream
            success[i] = own.get(i, 1) * fraction
        if len(reached) != len(nodes):
            observations.append('Disconnected components are excluded.')
        if not observations:
            observations.append('The model has capacity headroom. This does not establish a production SLA.')
        return dict(valid=True, completedPerSecond=rate * success[client], uncachedPathMilliseconds=max(latency.values(), default=0) if finite else None, stages=stages, observations=observations)
    except (KeyError, TypeError, ValueError, OverflowError):
        return invalid('The draft is incomplete. Check the component settings and request flow.')
