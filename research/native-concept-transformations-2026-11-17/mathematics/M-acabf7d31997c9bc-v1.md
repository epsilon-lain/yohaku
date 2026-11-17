# 状态与范围
这是新原生可执行源码/冻结方法及真实失败边界，不是已运行枚举。解析证明为M-2425cab292392fd9@1。
source files/theory/round3-root-quotient.py.tex@a88addefcacdabc95fc3dbf319f8199e25bdaeb31599f3639034ea8be6d43bf4，生成SHA da2a3674295c59db460b4f5f1ac87addbb26f4ed1576464a11bc138606ef827e；freeze source round3-root-quotient-freeze.json.tex@dc4507a4ee4d5ae7ec2f82d38a279663f425b43e6705a4986cfb3cef099ff5ce，生成SHA8e69c202fa177d8e6e0eee7f36c1bddc9c66655d4ccb86106aa55404eb7ded0d。action round3-root-quotient，timeout120秒。
首次请求round3-root-quotient-audit-v1返回source_conflict，未启动。重新plan确认root两源未变、共享manifest新增理论源后，source_set=c0e58442b566c2d83a6f87654c82a22f031543810b9f370caeec9ea95557079b；新请求round3-root-quotient-audit-replanned-v2返回GateStopped，未有task_id/数值产物。resources实际回读本阶段phase=open，但shared_stop reason=Supplement observer requires inspection，evidence=No task with this identity; no process targeted，at1794886834.33122，new_dispatch_allowed=false。此新阶段门禁与旧阶段stop分别留证；没有clear/bypass/外部替代计算。不能把准备或预测计数当实测。

## 完整冻结代码
"""Native root round3: existential quotient audit, unlabelled primitive graphs.
Proof dependency M-2425cab292392fd9@1. No AC/official-core or speed claim.
External conceptual baselines remain external/framework-candidates-closure@1
and external/macro-expansion-interface@1; source and receipts separate.
"""
import itertools
import json
from collections import Counter, deque
from pathlib import Path

INF = 99
DEPENDENCIES = [
    {"id": "M-2425cab292392fd9", "revision": 1, "use": "local lifting, distance, route DP theorem"},
    {"id": "external/framework-candidates-closure", "revision": 1, "use": "observation fibre language; external"},
    {"id": "external/macro-expansion-interface", "revision": 1, "use": "raw legal path vs description; external"}]

def partitions(n):
    def extend(a):
        if len(a) == n:
            yield tuple(a)
        else:
            for c in range(max(a) + 2):
                yield from extend(a + [c])
    yield from extend([0])

def distances(adj, s):
    d = [INF] * len(adj)
    d[s] = 0
    q = deque([s])
    while q:
        x = q.popleft()
        for z in adj[x]:
            if d[z] == INF:
                d[z] = d[x] + 1
                q.append(z)
    return d

def quotient(adj, p):
    k = max(p) + 1
    q = [set() for _ in range(k)]
    profiles = []
    for x in range(len(p)):
        profile = {p[z] for z in adj[x]}
        profiles.append(profile)
        q[p[x]].update(profile)
    local = all(profiles[x] == q[p[x]] for x in range(len(p)))
    return [tuple(sorted(z)) for z in q], local

def walks(adj, s, cap):
    layer = [(s,)]
    yield from layer
    for _ in range(cap):
        layer = [path + (z,) for path in layer for z in adj[path[-1]]]
        yield from layer

def forward(adj, p, s, route):
    live = {s}
    for y in route[1:]:
        live = {z for x in live for z in adj[x] if p[z] == y}
    return live

def backward(adj, p, route, target):
    live = {x for x in target if p[x] == route[-1]}
    for y in reversed(route[:-1]):
        live = {x for x in range(len(p)) if p[x] == y and any(z in live for z in adj[x])}
    return live

def main():
    freeze = json.loads(Path(__file__).with_name("round3-root-quotient-freeze.json").read_text())
    counts = Counter()
    by_n = {}
    first_spurious = None
    for n in range(1, 5):
        before = counts.copy()
        possible = [(x,z) for x in range(n) for z in range(n) if x != z]
        pp = list(partitions(n))
        assert len(pp) == [0,1,2,5,15][n]
        for mask in range(1 << len(possible)):
            adj = [tuple(z for i,(x,z) in enumerate(possible)
                         if x == v and (mask >> i) & 1) for v in range(n)]
            counts["graphs"] += 1
            dd = [distances(adj,s) for s in range(n)]
            for p in pp:
                q, local = quotient(adj,p)
                k = len(q)
                dq = [distances(q,y) for y in range(k)]
                counts["graph_partition_pairs"] += 1
                counts["local_lifting_pairs"] += int(local)
                # All starts and every saturated target, including empty/all.
                for s in range(n):
                    for bmask in range(1 << k):
                        raw = min((dd[s][x] for x in range(n) if (bmask >> p[x]) & 1), default=INF)
                        abstract = min((dq[p[s]][y] for y in range(k) if (bmask >> y) & 1), default=INF)
                        assert abstract <= raw
                        counts["distance_inequalities"] += 1
                        if local:
                            assert raw == abstract
                            counts["local_distance_equalities"] += 1
                        if raw != abstract:
                            counts["strict_optimistic_distances"] += 1
                            if first_spurious is None and raw == INF and abstract < INF:
                                first_spurious = dict(n=n, edges=[list(e) for i,e in enumerate(possible) if (mask >> i)&1],
                                    representation=p, start=s, target_blocks=[y for y in range(k) if (bmask >> y)&1],
                                    concrete_distance=None, quotient_distance=abstract)
                if n <= 3:
                    # Raw word-tree enumeration is separate from the set recurrences.
                    for s in range(n):
                        direct = {}
                        for path in walks(adj,s,4):
                            route = tuple(p[x] for x in path)
                            direct.setdefault(route,set()).add(path[-1])
                            counts["raw_tree_walks"] += 1
                        for route in walks(q,p[s],4):
                            live = forward(adj,p,s,route)
                            assert live == direct.get(route,set())
                            counts["route_endpoint_checks"] += 1
                            if not live:
                                counts["unliftable_quotient_walks"] += 1
                            if local:
                                assert live
                                counts["local_walk_lifts"] += 1
                            # Every target subset, not just saturated sets.
                            for tmask in range(1 << n):
                                target = {x for x in range(n) if (tmask >> x)&1}
                                prev = backward(adj,p,route,target)
                                assert (s in prev) == bool(live & target)
                                counts["backward_target_checks"] += 1
        by_n[str(n)] = dict(counts - before)

    a = [( ), (2,), ()]
    p = (0,0,1)
    q, local = quotient(a,p)
    assert distances(q,p[0])[p[2]] == 1 and distances(a,0)[2] == INF
    assert not local and not forward(a,p,0,(0,1))
    two = [(1,),(),(3,),()]
    p2 = (0,1,1,2)
    assert not forward(two,p2,0,(0,1,2))
    # In the 4-state example no start in first fibre has this full route.
    assert backward(two,p2,(0,1,2),{3}) == set()
    orbit = [(1,),(0,)]
    oq, ol = quotient(orbit,(0,0))
    assert ol and distances(oq,0)[0] == 0 and distances(orbit,0)[1] == 1
    result = dict(format="native-round3-root-quotient-audit/1", status="passed",
        scope=freeze, dependencies=DEPENDENCIES, counts=dict(counts), counts_by_n=by_n,
        first_spurious=first_spurious,
        explicit_counterexamples=[
          dict(name="goal_saturated_but_one_step_spurious", edges=[[1,2]], p=[0,0,1],
               start=0, target=[2], quotient_route=[0,1], lift=False),
          dict(name="inconsistent_middle_representatives", edges=[[0,1],[2,3]], p=[0,1,1,2],
               start=0,target=[3],quotient_route=[0,1,2],lift=False),
          dict(name="uniform_orbit_but_goal_not_saturated", edges=[[0,1],[1,0]],p=[0,0],
               start=0,target=[1],quotient_distance=0,concrete_distance=1)],
        limitations=["finite checks support but do not replace analytic proof",
                     "same-author independent algorithms are not independent peer review",
                     "unlabelled primitive graphs; no resource history, official AC, benchmark speed or token claim"])
    Path("/output/round3-root-quotient-results.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(status=result["status"],counts=result["counts"],first_spurious=first_spurious),sort_keys=True))

if __name__ == "__main__":
    main()

