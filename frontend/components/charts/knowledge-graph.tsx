"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3-force";

interface GraphNode {
  id: string;
  label: string;
  weight: number;
  x?: number;
  y?: number;
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

// d3-force mutates link objects in place, replacing string source/target
// with direct node-object references once the simulation resolves them —
// SimulationLinkDatum models that dual string-or-node shape.
type SimEdge = d3.SimulationLinkDatum<GraphNode> & { weight: number };

interface KnowledgeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width?: number;
  height?: number;
}

/**
 * Interactive force-directed knowledge graph — visualizes how topics/
 * concepts discovered across all research sessions relate to one another
 * (nodes sized by frequency, edges weighted by co-occurrence).
 *
 * Uses `d3-force` purely for physics simulation (no DOM manipulation via
 * d3-selection) and renders the result as plain SVG via React state, which
 * plays nicely with React's render cycle and avoids fighting React for
 * control of the DOM.
 */
export function KnowledgeGraph({ nodes, edges, width = 600, height = 400 }: KnowledgeGraphProps) {
  const [simulatedNodes, setSimulatedNodes] = useState<GraphNode[]>([]);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, undefined> | null>(null);

  useEffect(() => {
    if (nodes.length === 0) {
      setSimulatedNodes([]);
      return;
    }

    // d3-force mutates node objects in place with x/y — clone to avoid
    // mutating the props passed in from the parent component.
    const simNodes: GraphNode[] = nodes.map((n) => ({ ...n }));
    const simEdges: SimEdge[] = edges.map((e) => ({ ...e }));

    const simulation = d3
      .forceSimulation<GraphNode>(simNodes)
      .force(
        "link",
        d3
          .forceLink<GraphNode, SimEdge>(simEdges)
          .id((d) => d.id)
          .distance((d) => 90 - Math.min(d.weight * 5, 50))
          .strength(0.4)
      )
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collide",
        d3.forceCollide<GraphNode>((d) => 12 + Math.sqrt(d.weight) * 4)
      )
      .on("tick", () => setSimulatedNodes([...simNodes]));

    simulationRef.current = simulation;

    // Stop the simulation after it settles to avoid burning CPU indefinitely.
    const stopTimer = setTimeout(() => simulation.stop(), 3000);

    return () => {
      simulation.stop();
      clearTimeout(stopTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, width, height]);

  const nodeById = new Map(simulatedNodes.map((n) => [n.id, n]));
  const maxWeight = Math.max(1, ...nodes.map((n) => n.weight));

  function radiusFor(weight: number) {
    return 6 + (weight / maxWeight) * 16;
  }

  if (nodes.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-sm text-foreground-muted"
        style={{ width, height }}
      >
        Not enough topic data yet — run more research to populate the knowledge graph.
      </div>
    );
  }

  return (
    <svg width={width} height={height} className="overflow-visible">
      {/* Edges */}
      <g>
        {edges.map((edge, i) => {
          const source = nodeById.get(edge.source);
          const target = nodeById.get(edge.target);
          if (!source?.x || !target?.x) return null;

          const isHighlighted = hoveredNode === edge.source || hoveredNode === edge.target;

          return (
            <line
              key={i}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke={isHighlighted ? "#8B5CF6" : "#1F2937"}
              strokeWidth={Math.min(edge.weight, 4)}
              strokeOpacity={isHighlighted ? 0.8 : 0.4}
            />
          );
        })}
      </g>

      {/* Nodes */}
      <g>
        {simulatedNodes.map((node) => {
          if (node.x === undefined || node.y === undefined) return null;
          const isHovered = hoveredNode === node.id;

          return (
            <g
              key={node.id}
              transform={`translate(${node.x}, ${node.y})`}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              className="cursor-pointer"
            >
              <circle
                r={radiusFor(node.weight)}
                fill={isHovered ? "#8B5CF6" : "#3B82F6"}
                fillOpacity={isHovered ? 0.9 : 0.7}
                stroke="#0B1120"
                strokeWidth={2}
              />
              <text
                textAnchor="middle"
                dy={radiusFor(node.weight) + 12}
                fontSize={10}
                fill={isHovered ? "#E5E7EB" : "#9CA3AF"}
                className="pointer-events-none select-none"
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
