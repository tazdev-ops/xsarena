from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Task:
    name: str
    kind: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]


@dataclass
class Edge:
    src: str
    dst: str


@dataclass
class Graph:
    tasks: Dict[str, Task]
    edges: List[Edge]

    def topological(self) -> List[str]:
        """Return a topological sort of the graph nodes"""
        # Build adjacency lists
        adj = {task_name: [] for task_name in self.tasks.keys()}
        in_degree = {task_name: 0 for task_name in self.tasks.keys()}

        for edge in self.edges:
            adj[edge.src].append(edge.dst)
            in_degree[edge.dst] += 1

        # Find all nodes with no incoming edges
        queue = []
        for task_name, degree in in_degree.items():
            if degree == 0:
                queue.append(task_name)

        result = []
        while queue:
            node = queue.pop(0)
            result.append(node)

            # Remove node and decrease in-degree of its neighbors
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check if there was a cycle
        if len(result) != len(self.tasks):
            raise ValueError("Graph has a cycle, cannot perform topological sort")

        return result
