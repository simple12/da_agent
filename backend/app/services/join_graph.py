from __future__ import annotations

from collections import defaultdict, deque

from app.models.semantic import Join


class JoinGraph:
    """Undirected join graph built from semantic metadata."""

    def __init__(self, joins: list[Join]) -> None:
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        for join in joins:
            self._adjacency[join.source_table].add(join.target_table)
            self._adjacency[join.target_table].add(join.source_table)

    def is_connected(self, tables: set[str]) -> bool:
        if len(tables) <= 1:
            return True
        start = next(iter(tables))
        visited: set[str] = set()
        queue: deque[str] = deque([start])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            for neighbor in self._adjacency.get(node, set()):
                if neighbor in tables and neighbor not in visited:
                    queue.append(neighbor)
        return visited == tables
