import math
import numpy as np
from copy import copy
from functools import cmp_to_key
from domain.node import Node
from domain.arc import Arc
from typing import List, Set, Dict
import functools
from time import sleep


class Utils:

    """
    This funciton compute the clockwise angle between two points.

    :param origin: the origin point
    :param point: the destination point
    :returns: return the angle value
    :raises keyError: raises point exception
    """

    @staticmethod
    def clockwise_angle(origin, point, refvec=[0, 1]):
        try:
            vector = [point[0] - origin[0], point[1] - origin[1]]
            lenvector = math.hypot(vector[0], vector[1])

            if lenvector == 0:
                return -math.pi

            normalized = [vector[0] / lenvector, vector[1] / lenvector]

            dotprod = (
                normalized[0] * refvec[0] + normalized[1] * refvec[1]  # x1*x2 + y1*y2
            )

            diffprod = (
                refvec[1] * normalized[0] - refvec[0] * normalized[1]  # x1*y2 - y1*x2
            )

            angle = math.atan2(diffprod, dotprod)

            if angle < 0:
                return 2 * math.pi + angle
            return angle

        except Exception as ex:
            print(ex)
            raise RuntimeError("Clockwise function error")

    """
    This function identifies the next arc of a plannar face.

    :param nodesAngle: TODO
    :param i: TODO
    :param j: TODO
    :returns: the next node from the actual face
    :raises keyError: None
    """

    @staticmethod
    def calculate_slope(cord_i: Set, cord_j: Set):
        (xi, yi), (xj, yj) = cord_i, cord_j
        return math.atan2(xj - xi, yj - yi)

    @staticmethod
    def get_next_face_arc(nodes_angle: List, i: int, j: int):
        angles = nodes_angle[j]

        if len(angles) == 0:
            return None, None
        if angles[0][0] == i:
            return j, angles[-1][0]
        for k in range(len(angles) - 1):
            if angles[k + 1][0] == i:
                return j, angles[k][0]
        return None, None

    @staticmethod
    def get_face(nodes_angle, i, j):
        face = [i]
        while j != face[0]:
            face.append(j)
            i, j = Utils.get_next_face_arc(nodes_angle, i, j)
            if i is None or j is None:
                return []
        return face

    @staticmethod
    def normalize_face(face):
        new_face = []
        min_index = np.argmin(face)
        k, n = min_index, len(face)

        while True:
            new_face.append(face[k])
            k = (k + 1) % (n)
            if k == min_index:
                break
        return new_face

    @staticmethod
    def valid_face(face, arcs, nodes):
        ac = (
            [(face[i - 1], face[i]) for i in range(1, len(face))]
            + [(face[-1], face[0])]
            + [(face[i], face[i - 1]) for i in range(1, len(face))]
            + [(face[0], face[-1])]
        )

        coordinates = [(node.lon, node.lat) for node in nodes]

        min_x, max_x, min_y, max_y = math.inf, -math.inf, math.inf, -math.inf

        for i in face:
            vi = nodes[i]
            x, y = vi.lon, vi.lat
            if x < min_x:
                min_x = x
            elif x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            elif y > max_y:
                max_y = y
        empty_poly = True

        for i in range(len(nodes)):
            for arc in arcs[i]:
                if (i, arc.target) in ac:
                    continue
                vi, vj = nodes[i], nodes[arc.target]
                xi, yi, xj, yj = vi.lon, vi.lat, vj.lon, vj.lat
                if (
                    xi < min_x
                    or xi > max_x
                    or xj < min_x
                    or xj > max_x
                    or yi < min_y
                    or yj < min_y
                    or yi > max_y
                    or yj > max_y
                ):
                    continue
                middle = ((vi.lon + vj.lon) / 2.0, (vi.lat + vj.lat) / 2.0)
                empty_poly = not Utils.point_in_polygon(middle, coordinates)
                if empty_poly:
                    break
        return empty_poly

    @staticmethod
    def compute_faces(nodes, arcs):
        n = len(nodes)
        feasible_faces, invalid_faces, faces = [], [], []
        blocks_vert, clockwise_sorting = dict(), dict()

        for i in range(n):
            clockwise_sorting[i] = sorted(
                [
                    (
                        arc.target,
                        Utils.calculate_slope(
                            (nodes[i].lon, nodes[i].lat),
                            (nodes[arc.target].lon, nodes[arc.target].lat),
                        ),
                    )
                    for arc in arcs[i]
                ],
                key=lambda x: x[1],
            )

        for node in nodes:
            i = node.index
            for arc in arcs[i]:
                j = arc.target

                face = Utils.get_face(clockwise_sorting, i, j)

                if len(face) <= 2:
                    continue

                face = Utils.normalize_face(face)

                face_set = set(face)
                if face_set in [set(f) for f in feasible_faces] or face_set in [
                    set(f) for f in invalid_faces
                ]:
                    continue

                if not Utils.is_clockwise(nodes, face):
                    face = Utils.normalize_face(face[::-1])

                    face_set = set(face)
                    if face_set in [set(f) for f in feasible_faces] or face_set in [
                        set(f) for f in invalid_faces
                    ]:
                        continue

                if Utils.valid_face(face, arcs, nodes):
                    feasible_faces.append(face)

        return sorted(feasible_faces, key=lambda x: len(x), reverse=True)

    @staticmethod
    def get_cycle(n: int, face: List, arcs: List[Arc], used_arcs: Dict):
        start_arc = (face[0], face[-1])

        cycle = []
        if start_arc in used_arcs and not used_arcs[start_arc]:
            cycle = Utils.dfs(n, arcs, start_arc, face, used_arcs)

        if len(cycle) == 0:
            rev_arc = (face[-1], face[0])
            if rev_arc in used_arcs and not used_arcs[rev_arc]:
                cycle = Utils.dfs(n, arcs, rev_arc, face, used_arcs)

        return cycle

    @staticmethod
    def dfs(n: int, arcs: List[Arc], start_arc: set, face: List, used_arcs: Dict):
        visited = [False for i in range(n)]
        pred = [None for i in range(n)]

        u, v = start_arc[0], start_arc[1]
        pred[v] = u
        visited[u] = visited[v] = True

        stack = [(u, v)]
        found_cycle = False

        while len(stack) > 0 and not found_cycle:
            p, s = stack[-1]
            stack.pop()

            if not visited[s]:
                visited[s], pred[s] = True, p

            for arc in arcs[s]:
                t = arc.target
                if not visited[t] and t in face and not used_arcs[(s, t)]:
                    stack.append((s, t))
                elif t == u and all(visited[l] for l in face):
                    pred[u] = s
                    found_cycle = True
                    break

        if found_cycle:
            arcs, i, last_vert = [], 0, u
            while i < len(face):
                arc = (pred[last_vert], last_vert)
                arcs.append(arc)
                last_vert = pred[last_vert]
                i += 1

            return arcs[::-1]
        else:
            return []

    @staticmethod
    def cross(a, b):
        return a[0] * b[1] - a[1] * b[0]

    @staticmethod
    def colinear(p, q, r):
        return abs(Utils.cross(Utils.to_vec(p, q), Utils.to_vec(p, r))) < 1e-9

    @staticmethod
    def dist(p1, p2):
        return math.hypot(p1.lon - p2.lon, p1.lat - p2.lat)

    @staticmethod
    def ccw(p, q, r):
        return Utils.cross(Utils.to_vec(p, q), Utils.to_vec(p, r)) > 0

    @staticmethod
    def to_vec(a, b):
        return [b.lon - a.lon, b.lat - a.lat]

    # Ordering function
    def angle_cmp(a, b):
        global pivot
        if Utils.colinear(pivot, a, b):
            if Utils.dist(pivot, a) < Utils.dist(pivot, b):
                return -1
            elif Utils.dist(pivot, a) > Utils.dist(pivot, b):
                return 1
            else:
                return 0

        d1x, d1y = a.lon - pivot.lon, a.lat - pivot.lat
        d2x, d2y = b.lon - pivot.lon, b.lat - pivot.lat
        if (math.atan2(d1y, d1x) - math.atan2(d2y, d2x)) < 0:
            return -1
        elif (math.atan2(d1y, d1x) - math.atan2(d2y, d2x)) > 0:
            return 1
        else:
            return 0

    @staticmethod
    def get_convex_hull(b_key, nodes, blocks_vert):
        block = blocks_vert[b_key]
        vertices, p0 = [nodes[block[0]]], 0
        global pivot

        # Select pivot
        for i in range(1, len(block)):
            vertex = nodes[block[i]]
            vertices.append(vertex)
            pivot = nodes[block[p0]]

            if (vertex.lat < pivot.lat) or (
                vertex.lat == pivot.lat and vertex.lon > pivot.lon
            ):
                p0 = i

        swap = vertices[0]
        vertices[0] = vertices[p0]
        vertices[p0] = swap

        pivot = vertices[0]
        s_block = [pivot] + sorted(vertices[1:], key=cmp_to_key(Utils.angle_cmp))

        # ccw test
        S = [s_block[-1], s_block[0], s_block[1]]

        i = 2
        while i < len(s_block):
            j = len(S) - 1
            if j < 1:
                break
            if Utils.ccw(S[j - 1], S[j], s_block[i]):
                S.append(s_block[i])
                i += 1
            else:
                S = S[:-1]
        return S

    @staticmethod
    def get_directed_block(u, v, k, S, n, arcs, arc_used):
        visited = [False for i in range(n)]
        pred = [None for i in range(n)]

        pred[u], pred[v], pred[k] = u, u, v
        visited[u] = visited[v] = visited[k] = True

        stack = [(v, k)]

        while len(stack):
            p, s = stack[-1]
            stack.pop()

            if not visited[s]:
                visited[s], pred[s] = True, p

            for arc in arcs[s]:
                t = arc.target
                if not visited[t] and t in S:
                    stack.append((s, t))
                elif t == u and all(visited[l] for l in S):
                    pred[u] = s
                    break

        arcs, i, last_vert = [], 0, u
        while i < len(S):
            arc = (pred[last_vert], last_vert)
            if arc[0] == arc[1] or arc not in arc_used or arc_used[arc]:
                return []
            arcs.append(arc)
            last_vert = pred[last_vert]
            i += 1
        return arcs[::-1]

    @staticmethod
    def on_segment(p, q, r):
        (px, py) = p
        (qx, qy) = q
        (rx, ry) = r
        return (
            qx <= max(px, rx)
            and qx >= min(px, rx)
            and qy <= max(py, ry)
            and qy >= min(py, ry)
        )

    @staticmethod
    def orientation(p, q, r) -> int:
        (px, py) = p
        (qx, qy) = q
        (rx, ry) = r
        val = (qy - py) * (rx - qx) - (qx - px) * (ry - qy)
        # colinear
        if val == 0:
            return 0
        # clock or counterclock wise
        return 1 if val > 0 else 2

    @staticmethod
    def is_clockwise(nodes: List[Node], face: List[int]) -> bool:
        n = len(face)
        res = np.sum(
            [
                nodes[face[i - 1]].lon * nodes[face[i]].lat
                - nodes[face[i]].lon * nodes[face[i - 1]].lat
                for i in range(1, n)
            ]
            + [
                nodes[face[-1]].lon * nodes[face[0]].lat
                - nodes[face[0]].lon * nodes[face[-1]].lat
            ]
        )
        return (res / 2.0) < 0.0

    @staticmethod
    def do_intersect(p1, q1, p2, q2) -> bool:
        o1 = Utils.orientation(p1, q1, p2)
        o2 = Utils.orientation(p1, q1, q2)
        o3 = Utils.orientation(p2, q2, p1)
        o4 = Utils.orientation(p2, q2, q1)

        # General case
        if o1 != o2 and o3 != o4:
            return True
        return (
            (o1 == 0 and Utils.on_segment(p1, p2, q1))
            or (o2 == 0 and Utils.on_segment(p1, q2, q1))
            or (o3 == 0 and Utils.on_segment(p2, p1, q2))
            or (o4 == 0 and Utils.on_segment(p2, q1, q2))
        )

    @staticmethod
    def point_in_polygon(p, polygon) -> bool:
        n = len(polygon)
        # There must be at least 3 vertices in polygon[]
        if n < 3:
            return False
        # Create a point for line segment from p to infinite
        (px, py) = p

        extreme = (max([x for (x, y) in polygon]), py)
        # Count intersections of the above line with sides of polygon
        count = 0
        i = 0
        while True:
            nex = (i + 1) % n
            # Check if the line   segment from 'p' to 'extreme' intersects
            # with the line segment from 'polygon[i]' to 'polygon[nex]'
            if Utils.do_intersect(polygon[i], polygon[nex], p, extreme):
                # If the point 'p' is colinear with line segment 'i-nex',
                # then check if it lies on segment. If it lies, return true,
                # otherwise false
                if Utils.orientation(polygon[i], p, polygon[nex]) == 0:
                    return Utils.on_segment(polygon[i], p, polygon[nex])
                count += 1
            i = nex
            if i == 0:
                break
        # Return True if count is odd, false otherwise
        return count % 2 == 1  # Same as (count%2 ==
