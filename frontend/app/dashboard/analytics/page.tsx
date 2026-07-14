"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, FileText, Globe, Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KnowledgeGraph } from "@/components/charts/knowledge-graph";
import { api } from "@/lib/api-client";
import type { AnalyticsOverview, ChartDataPoint } from "@/lib/types";

interface KnowledgeGraphData {
  nodes: { id: string; label: string; weight: number }[];
  edges: { source: string; target: string; weight: number }[];
}

const CHART_COLORS = ["#3B82F6", "#8B5CF6", "#22C55E", "#F59E0B", "#EF4444", "#06B6D4", "#EC4899"];

export default function AnalyticsPage() {
  const { data: overview } = useQuery({
    queryKey: ["analytics-overview"],
    queryFn: () => api.get<AnalyticsOverview>("/analytics/overview"),
  });

  const { data: sourceDistribution } = useQuery({
    queryKey: ["analytics-source-distribution"],
    queryFn: () => api.get<ChartDataPoint[]>("/analytics/source-distribution"),
  });

  const { data: timeline } = useQuery({
    queryKey: ["analytics-timeline"],
    queryFn: () => api.get<ChartDataPoint[]>("/analytics/research-timeline", { days: 30 }),
  });

  const { data: confidenceScores } = useQuery({
    queryKey: ["analytics-confidence"],
    queryFn: () => api.get<ChartDataPoint[]>("/analytics/confidence-scores"),
  });

  const { data: topicClusters } = useQuery({
    queryKey: ["analytics-topics"],
    queryFn: () => api.get<ChartDataPoint[]>("/analytics/topic-clusters", { top_n: 10 }),
  });

  const { data: knowledgeGraph } = useQuery({
    queryKey: ["analytics-knowledge-graph"],
    queryFn: () => api.get<KnowledgeGraphData>("/analytics/knowledge-graph", { max_nodes: 30 }),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <BarChart3 className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-semibold text-foreground">Analytics</h1>
      </div>

      {/* Overview stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<Sparkles className="h-4 w-4 text-primary" />}
          label="Research Sessions"
          value={overview?.total_research_sessions ?? "—"}
        />
        <StatCard
          icon={<FileText className="h-4 w-4 text-accent" />}
          label="Reports Generated"
          value={overview?.total_reports_generated ?? "—"}
        />
        <StatCard
          icon={<Globe className="h-4 w-4 text-success" />}
          label="Sources Collected"
          value={overview?.total_sources_collected ?? "—"}
        />
        <StatCard
          icon={<BarChart3 className="h-4 w-4 text-warning" />}
          label="Avg. Trust Score"
          value={overview?.average_trustworthiness_score != null ? `${Math.round(overview.average_trustworthiness_score)}%` : "—"}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Research Timeline */}
        <Card>
          <CardHeader>
            <CardTitle>Research Timeline (30 days)</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeline ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                <XAxis dataKey="label" stroke="#6B7280" fontSize={11} />
                <YAxis stroke="#6B7280" fontSize={11} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #1F2937", borderRadius: 8 }}
                />
                <Line type="monotone" dataKey="value" stroke="#3B82F6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Source Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Source Distribution by Domain</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sourceDistribution ?? []} layout="vertical" margin={{ left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                <XAxis type="number" stroke="#6B7280" fontSize={11} allowDecimals={false} />
                <YAxis dataKey="label" type="category" stroke="#6B7280" fontSize={11} width={90} />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #1F2937", borderRadius: 8 }}
                />
                <Bar dataKey="value" fill="#3B82F6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Confidence Scores */}
        <Card>
          <CardHeader>
            <CardTitle>Confidence Score Distribution</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={confidenceScores ?? []}
                  dataKey="value"
                  nameKey="label"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={2}
                >
                  {(confidenceScores ?? []).map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #1F2937", borderRadius: 8 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Topic Clusters */}
        <Card>
          <CardHeader>
            <CardTitle>Top Topic Clusters</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topicClusters ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                <XAxis dataKey="label" stroke="#6B7280" fontSize={10} angle={-25} textAnchor="end" height={50} />
                <YAxis stroke="#6B7280" fontSize={11} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #1F2937", borderRadius: 8 }}
                />
                <Bar dataKey="value" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Knowledge Graph — full width, interactive */}
      <Card>
        <CardHeader>
          <CardTitle>Knowledge Graph</CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center overflow-x-auto">
          <KnowledgeGraph
            nodes={knowledgeGraph?.nodes ?? []}
            edges={knowledgeGraph?.edges ?? []}
            width={700}
            height={420}
          />
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-background">{icon}</div>
        <div>
          <p className="text-xs text-foreground-muted">{label}</p>
          <p className="text-lg font-semibold text-foreground">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
