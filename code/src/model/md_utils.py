import math
import numpy as np
from functools import cmp_to_key


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
    def get_next_face_arc(nodes_angle, i, j):
        if j not in nodes_angle:
            return None, None

        angles = nodes_angle[j]

        if len(angles) == 0:
            return None, None
        if angles[0] == i:
            return j, angles[len(angles) - 1]
        for k in range(len(angles) - 1):
            if angles[k + 1] == i:
                return j, angles[k]
        return None, None

    @staticmethod
    def get_face(nodes_angle, i, j):
        face = [i]
        while j != face[0]:
            face.append(j)
            i, j = Utils.get_next_face_arc(nodes_angle, i, j)
            if i is None or j is None:
                break
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
    def valid_face(face, arcs):
        ac = [(face[i], face[i + 1]) for i in range(len(face) - 1)]
        ac.append((face[len(face) - 1], face[0]))

        valid = dict()
        for arc in ac:
            valid[arc] = False
            for j in arcs[arc[0]]:
                if j.target == arc[1]:
                    valid[arc] = True
                    break
        for arc in ac:
            if not valid[arc]:
                return False
        return True

    @staticmethod
    def compute_faces(nodes, arcs):
        n = len(nodes)
        feasible_faces, faces = [], []
        blocks_vert, clockwise_sorting = dict(), dict()

        for i in range(n):
            clock_list = []
            src = nodes[i]
            for arc in arcs[i]:
                tgt = nodes[arc.target]
                clock_list.append(
                    (
                        arc.target,
                        Utils.clockwise_angle((src.lon, src.lat), (tgt.lon, tgt.lat)),
                    )
                )
                clockwise_sorting[i] = [
                    x[0] for x in sorted(clock_list, key=lambda x: x[1])
                ]

        for v in nodes:
            i = v.index
            for arc in arcs[i]:
                j = arc.target
                face = Utils.get_face(clockwise_sorting, i, j)
                if len(face) <= 2:
                    continue

                face = Utils.normalize_face(face)
                if not Utils.valid_face(face, arcs):
                    continue

                face_set = set(face)
                if face_set not in feasible_faces:
                    faces.append(face)
                feasible_faces.append(face_set)

        block_index = 0
        for face in faces:
            blocks_vert[block_index] = face
            block_index += 1
        return dict(sorted(blocks_vert.items(), key=lambda item: len(item[1])))

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
    def onSegment(p, q, r):
        (px, py) = p
        (qx, qy) = q
        (rx, ry) = r
        return (
            qx <= max(px, rx)
            and qx >= min(px, rx)
            and qy <= max(py, ry)
            and qy >= min(py, ry)
        )

    # 0 --> p, q and r are colinear
    # 1 --> Clockwise
    # 2 --> Counterclockwise
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
    def doIntersect(p1, q1, p2, q2) -> bool:
        o1 = GraphUtils.orientation(p1, q1, p2)
        o2 = GraphUtils.orientation(p1, q1, q2)
        o3 = GraphUtils.orientation(p2, q2, p1)
        o4 = GraphUtils.orientation(p2, q2, q1)
        # General case
        if o1 != o2 and o3 != o4:
            return True
        return (
            (o1 == 0 and GraphUtils.onSegment(p1, p2, q1))
            or (o2 == 0 and GraphUtils.onSegment(p1, q2, q1))
            or (o3 == 0 and GraphUtils.onSegment(p2, p1, q2))
            or (o4 == 0 and GraphUtils.onSegment(p2, q1, q2))
        )

    @staticmethod
    def pointInPolygon(p, polygon) -> bool:
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
            if GraphUtils.doIntersect(polygon[i], polygon[nex], p, extreme):
                # If the point 'p' is colinear with line segment 'i-nex',
                # then check if it lies on segment. If it lies, return true,
                # otherwise false
                if GraphUtils.orientation(polygon[i], p, polygon[nex]) == 0:
                    return GraphUtils.onSegment(polygon[i], p, polygon[nex])
                count += 1
            i = nex
            if i == 0:
                break
        # Return True if count is odd, false otherwise
        return count % 2 == 1  # Same as (count%2 ==
