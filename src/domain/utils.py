from typing import List
from datetime import datetime, timedelta
import math
import numpy as np
import pandas as pd
from domain.graph import Graph

def on_segment(p, q, r):
    px, py = p
    qx, qy = q
    rx, ry = r
    return (min(px, rx) <= qx <= max(px, rx)) and (min(py, ry) <= qy <= max(py, ry))

def orientation(p, q, r):
    px, py = p
    qx, qy = q
    rx, ry = r
    val = (qy - py) * (rx - qx) - (qx - px) * (ry - qy)
    if val == 0:
        return 0  # colinear
    return 1 if val > 0 else 2  # clockwise or counterclockwise

def do_intersect(p1, q1, p2, q2):
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4:
        return True

    # Special Cases
    if o1 == 0 and on_segment(p1, p2, q1):
        return True
    if o2 == 0 and on_segment(p1, q2, q1):
        return True
    if o3 == 0 and on_segment(p2, p1, q2):
        return True
    if o4 == 0 and on_segment(p2, q1, q2):
        return True

    return False

def get_intersection_point(a, b, c, d):
    (xa, ya), (xb, yb), (xc, yc), (xd, yd) = a, b, c, d
    m1 = (yb - ya) / (xb - xa)
    m2 = (yc - yd) / (xc - xd)
    k1 = ya - m1 * xa
    k2 = yc - m2 * xc
    x = (k2 - k1) / (m1 - m2)
    return (x, m1 * x + k1)

def point_in_polygon(p, polygon):
    n = len(polygon)
    if n < 3:
        return False

    px, py = p
    extreme = (2e7, py)  # simulate "infinity" horizontally

    count = 0
    i = 0
    while True:
        nex = (i + 1) % n
        nexnex = (nex + 1) % n

        if orientation(polygon[i], polygon[nex], polygon[nexnex]) == 0 and \
           (polygon[i], polygon[nex]) != (polygon[nexnex], polygon[nex]):
            nex = nexnex

        if do_intersect(polygon[i], polygon[nex], p, extreme):
            if orientation(polygon[i], p, polygon[nex]) == 0:
                return on_segment(polygon[i], p, polygon[nex])
            count += 1

        if i == n - 1 and nex == 1:
            break
        i = nex
        if i == 0:
            break

    return count % 2 == 1

def clockwise_angle(origin, point, ref_vec=(0, 1)):
    try:
        vec = [point[0] - origin[0], point[1] - origin[1]]
        len_vector = math.hypot(vec[0], vec[1])
        if len_vector == 0:
            return math.pi
        normalized_vec = [v / len_vector for v in vec]
        dot_product = sum(a * b for a, b in zip(normalized_vec, ref_vec))
        diff_product = normalized_vec[0] * ref_vec[1] - normalized_vec[1] * ref_vec[0]
        angle = math.atan2(diff_product, dot_product)
        return angle + 2 * math.pi if angle < 0 else angle
    except Exception as e:
        print(f"[!!!] (clockwise_angle) Error: {e}")

def calculate_slope(coord_i, coord_j):
    try:
        xi, yi = coord_i
        xj, yj = coord_j
        return math.atan2(xj - xi, yj - yi)
    except Exception as e:
        print(f"[!!!] (slope) Error: {e}")

def get_next_face_arc(nodes_angle, i, j):
    try:
        if j not in nodes_angle or not nodes_angle[j]:
            return None, None
        angles = nodes_angle[j]
        if angles[0][0] == i:
            return j, angles[-1][0]
        for k in range(len(angles) - 1):
            if angles[k + 1][0] == i:
                return j, angles[k][0]
        return None, None
    except Exception as e:
        print(f"[!!!] (next_face_arc) Error: {e}")

def get_face(nodes_angle, i, j):
    try:
        face = [i]
        while j != face[0]:
            face.append(j)
            i, j = get_next_face_arc(nodes_angle, i, j)
            if i is None or j is None:
                return []
        return face
    except Exception as e:
        print(f"[!!!] (get_face) Error: {e}")

def normalize_face(face):
    try:
        min_index = face.index(min(face))
        return [face[(min_index + i) % len(face)] for i in range(len(face))]
    except Exception as e:
        print(f"[!!!] (Normalize) Error: {e}")

def is_valid_face(graph, face):
    try:
        face_arcs = [(face[i - 1], face[i]) for i in range(1, len(face))] + \
                    [(face[-1], face[0])] + \
                    [(face[i], face[i - 1]) for i in range(1, len(face))] + \
                    [(face[0], face[-1])]

        coords = [(graph.nodes[i].lon, graph.nodes[i].lat) for i in face]

        min_x = min(v.lon for v in map(graph.nodes.get, face))
        max_x = max(v.lon for v in map(graph.nodes.get, face))
        min_y = min(v.lat for v in map(graph.nodes.get, face))
        max_y = max(v.lat for v in map(graph.nodes.get, face))

        for i in range(graph.n):
            for arc in graph.arcs[i]:
                if (i, arc.target.index) in face_arcs:
                    continue
                xi, yi = arc.source.lon, arc.source.lat
                xj, yj = arc.target.lon, arc.target.lat
                if any(val < min_val or val > max_val for val, min_val, max_val in zip([xi, xj, yi, yj], [min_x]*2 + [min_y]*2, [max_x]*2 + [max_y]*2)):
                    continue
                mid = ((xi + xj) / 2.0, (yi + yj) / 2.0)
                if point_in_polygon(mid, coords):
                    return False
        return True
    except Exception as e:
        print(f"[!!!] (is_valid_face) Error: {e}")

def is_clockwise(graph, face):
    nodes = graph.nodes
    area = sum(
        nodes[face[i - 1]].lon * nodes[face[i]].lat -
        nodes[face[i]].lon * nodes[face[i - 1]].lat
        for i in range(1, len(face))
    ) + (
        nodes[face[-1]].lon * nodes[face[0]].lat -
        nodes[face[0]].lon * nodes[face[-1]].lat
    )
    return (area / 2.0) < 0.0

def compute_faces(graph):
    n = graph.n
    feasible_faces = []
    unfeasible_faces = []
    clockwise_sorting = {}

    for i in range(n):
        clockwise_sorting[i] = sorted(
            [(arc.target.index, calculate_slope(
                (graph.nodes[i].lon, graph.nodes[i].lat),
                (arc.target.lon, arc.target.lat)
            )) for arc in graph.arcs[i] if len(graph.arcs[arc.target.index]) > 1],
            key=lambda x: x[1]
        )

    for i in range(n):
        for arc in graph.arcs[i]:
            j = arc.target.index
            face = get_face(clockwise_sorting, i, j)
            if len(face) <= 2:
                continue
            face = normalize_face(face)
            if face in feasible_faces or face in unfeasible_faces:
                continue
            if not is_clockwise(graph, face):
                face = normalize_face(face[::-1])
                if face in feasible_faces or face in unfeasible_faces:
                    continue
            if is_valid_face(graph, face):
                feasible_faces.append(face)
            else:
                unfeasible_faces.append(face)

    return sorted(feasible_faces, key=len)

def dfs(graph, face, start_arc, used_arcs):
    try:
        n = graph.n
        visited = [False] * (n + 1)
        pred = [None] * (n + 1)
        u, v = start_arc
        pred[v] = u
        visited[u] = visited[v] = True
        stack = [(u, v)]
        found_cycle = False

        while stack and not found_cycle:
            p, s = stack.pop()
            if not visited[s]:
                visited[s] = True
                pred[s] = p
            for arc in graph.arcs[s]:
                t = arc.target.index
                if not visited[t] and t in face and not used_arcs.get((s, t), False):
                    stack.append((s, t))
                elif t == u and all(visited[i] for i in face):
                    pred[u] = s
                    found_cycle = True
                    break
                if (v, t) == start_arc:
                    found_cycle = True
                    break

        if found_cycle:
            arcs = []
            last_node = u
            for _ in range(len(face)):
                arc = (pred[last_node], last_node)
                arcs.append(arc)
                last_node = pred[last_node]
            return arcs[::-1]
        else:
            return []
    except Exception as e:
        print(f"[!!!] (dfs) Error: {e}")

def get_cycle(graph, face, used_arcs):
    try:
        start_arc = (face[0], face[-1])
        if used_arcs.get(start_arc) is False:
            cycle = dfs(graph, face, start_arc, used_arcs)
            if cycle:
                return cycle
        rev_arc = (face[-1], face[0])
        if used_arcs.get(rev_arc) is False:
            return dfs(graph, face, rev_arc, used_arcs)
        return []
    except Exception as e:
        print(f"[!!!] (get_cycles) Error: {e}")

def all_blocks_as_polygon(graph):
    b = graph.b
    coords = [[] for _ in range(b)]
    for i in range(0, b):
        block_index = i
        if block_index in graph.block_nodes:
            coords[i] = [(graph.nodes[j].lon, graph.nodes[j].lat) for j in graph.block_nodes[block_index]]
    return coords

def compute_people_per_block(graph: Graph, people_per_km2: float):
    """
    Computes estimated people per block using min and max arc lengths.

    Args:
        graph: An object with `block_arcs`, where each block_arcs[i] is a list of arcs with a `length` attribute.
        people_per_km2: Density of people per km² (float).

    Returns:
        A NumPy array of estimated people per block (rounded up).
    """
    num_blocks = graph.b
    people_per_block = np.zeros(num_blocks, dtype=np.float64)

    for i in range(num_blocks):
        lengths = [arc.length for arc in graph.block_arcs[i]]
        if lengths:
            min_len = min(lengths)
            max_len = max(lengths)
            area_est = max_len * min_len
            people_per_block[i] = math.ceil(area_est * people_per_km2)
        else:
            people_per_block[i] = 0.0

    return people_per_block

def get_infected_recovered_people_per_block(df: pd.DataFrame, graph: Graph, start_date: datetime.date, coord_blocks: List):
    """
    Maps dengue notification points to blocks and classifies as infected or recovered.

    Args:
        df (pd.DataFrame): DataFrame with 'x', 'y', 'data_notification', 'classification'.
        graph: Graph with attribute `b` = number of blocks.
        start_date (datetime.date): Start date of simulation.
        coord_blocks (list): List of polygons (each block).
        point_in_polygon (func): Function to check if point (y, x) is in polygon.

    Returns:
        Tuple of two np.arrays: infected_people_per_block, recovered_people_per_block
    """
    # Filter out classification 5 (likely "discarded" cases)
    filtered_df = df[df["classification"] != 5]

    num_blocks = graph.b
    infected = np.zeros(num_blocks, dtype=int)
    recovered = np.zeros(num_blocks, dtype=int)

    range_infected_date = start_date - timedelta(days=7)

    for _, row in filtered_df.iterrows():
        y, x = float(row["y"]), float(row["x"])
        notif_date = pd.to_datetime(row["data_notification"])
        
        for i, polygon in enumerate(coord_blocks):
            if point_in_polygon((y, x), polygon):
                if notif_date > range_infected_date:
                    infected[i] += 1
                else:
                    recovered[i] += 1
                break  # once matched to a block, stop checking

    return infected, recovered