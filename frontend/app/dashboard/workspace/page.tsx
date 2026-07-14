"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, FileText, Loader2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { DocumentUploadDialog } from "@/components/upload/document-upload-dialog";
import { api } from "@/lib/api-client";
import { cn, formatScore, humanizeSnakeCase, scoreToColor } from "@/lib/utils";
import type {
  AgentStatusItem,
  AgentLogRead,
  ResearchSessionRead,
  ResearchSessionSummary,
  SourceRead,
} from "@/lib/types";

const TERMINAL_STATUSES = new Set(["completed", "failed"]);

export default function WorkspacePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");

  const { data: history } = useQuery({
    queryKey: ["research-history", "sidebar-list"],
    queryFn: () => api.get<ResearchSessionSummary[]>("/research", { limit: 15 }),
    enabled: !sessionId,
  });

  if (!sessionId) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-semibold text-foreground">Research Workspace</h1>
        <p className="text-sm text-foreground-muted">
          Select a research session from your history to view its live activity and report.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {history?.map((session) => (
            <Card
              key={session.id}
              className="cursor-pointer hover:border-primary/40"
              onClick={() => router.push(`/workspace?session=${session.id}`)}
            >
              <CardContent className="p-4">
                <Badge variant="primary">{humanizeSnakeCase(session.status)}</Badge>
                <p className="mt-2 line-clamp-2 text-sm font-medium">{session.query}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return <SessionWorkspace sessionId={sessionId} />;
}

function SessionWorkspace({ sessionId }: { sessionId: string }) {
  const { data: session } = useQuery({
    queryKey: ["research-session", sessionId],
    queryFn: () => api.get<ResearchSessionRead>(`/research/${sessionId}`),
    refetchInterval: (query) =>
      query.state.data && TERMINAL_STATUSES.has(query.state.data.status) ? false : 2000,
  });

  const isRunning = session ? !TERMINAL_STATUSES.has(session.status) : true;

  const { data: agentStatus } = useQuery({
    queryKey: ["agent-status", sessionId],
    queryFn: () => api.get<AgentStatusItem[]>("/agents/status", { research_session_id: sessionId }),
    refetchInterval: isRunning ? 2000 : false,
  });

  const { data: logs } = useQuery({
    queryKey: ["agent-logs", sessionId],
    queryFn: () => api.get<AgentLogRead[]>(`/research/${sessionId}/logs`),
    refetchInterval: isRunning ? 3000 : false,
  });

  const { data: sources } = useQuery({
    queryKey: ["research-sources", sessionId],
    queryFn: () => api.get<SourceRead[]>(`/research/${sessionId}/sources`),
    enabled: !!session && session.progress_percent > 25,
    refetchInterval: isRunning ? 4000 : false,
  });

  if (!session) {
    return (
      <div className="flex h-64 items-center justify-center text-foreground-muted">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading session…
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header / progress */}
      <Card>
        <CardContent className="flex flex-col gap-3 p-5">
          <div className="flex items-center justify-between">
            <h1 className="text-base font-semibold text-foreground">{session.query}</h1>
            <Badge variant={session.status === "completed" ? "success" : session.status === "failed" ? "danger" : "primary"}>
              {humanizeSnakeCase(session.status)}
            </Badge>
          </div>
          <Progress value={session.progress_percent} />
          <div className="flex justify-between text-xs text-foreground-muted">
            <span>{session.progress_percent}% complete</span>
            {session.error_message && <span className="text-danger">{session.error_message}</span>}
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="activity">
        <TabsList>
          <TabsTrigger value="activity">Agent Activity</TabsTrigger>
          <TabsTrigger value="sources">Sources ({sources?.length ?? 0})</TabsTrigger>
          <TabsTrigger value="report">Report</TabsTrigger>
        </TabsList>

        {/* Live Agent Activity */}
        <TabsContent value="activity" className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1.2fr]">
          <Card>
            <CardHeader>
              <CardTitle>Task Progress</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {agentStatus?.map((agent) => (
                <div key={agent.agent_name} className="flex items-center gap-3 rounded-lg px-2 py-1.5">
                  <span
                    className={cn(
                      agent.is_active
                        ? "status-dot-active"
                        : agent.current_task
                        ? "status-dot-done"
                        : "status-dot-pending"
                    )}
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">
                      {humanizeSnakeCase(agent.agent_name)}
                    </p>
                    {agent.current_task && (
                      <p className="text-xs text-foreground-muted">{agent.current_task}</p>
                    )}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Agent Logs</CardTitle>
            </CardHeader>
            <CardContent className="flex max-h-96 flex-col gap-2 overflow-y-auto font-mono text-xs">
              {logs?.length ? (
                logs.map((log) => (
                  <div key={log.id} className="flex gap-2 border-b border-border/60 pb-2">
                    <span className="text-foreground-muted">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </span>
                    <span
                      className={cn(
                        "font-semibold",
                        log.level === "error" && "text-danger",
                        log.level === "warning" && "text-warning",
                        log.level === "success" && "text-success",
                        log.level === "info" && "text-primary"
                      )}
                    >
                      [{humanizeSnakeCase(log.agent_name)}]
                    </span>
                    <span className="text-foreground-muted">{log.message}</span>
                  </div>
                ))
              ) : (
                <p className="text-foreground-muted">Waiting for agent activity…</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sources */}
        <TabsContent value="sources" className="flex flex-col gap-3">
          <div className="flex justify-end">
            <DocumentUploadDialog researchSessionId={sessionId} />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {sources?.map((source) => (
              <Card key={source.id}>
                <CardContent className="flex flex-col gap-2 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="line-clamp-1 text-sm font-medium text-foreground">
                      {source.title || source.domain || source.url}
                    </p>
                    <a href={source.url} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-3.5 w-3.5 text-foreground-muted hover:text-primary" />
                    </a>
                  </div>
                  <p className="text-xs text-foreground-muted">{source.domain}</p>
                  <div className="flex items-center gap-2">
                    <Badge variant={scoreToColor(source.trustworthiness_score)}>
                      Trust: {formatScore(source.trustworthiness_score)}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
            {!sources?.length && (
              <p className="text-sm text-foreground-muted">No sources collected yet.</p>
            )}
          </div>
        </TabsContent>

        {/* Report */}
        <TabsContent value="report">
          {session.status === "completed" ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
                <FileText className="h-8 w-8 text-primary" />
                <p className="text-sm text-foreground-muted">
                  Your report is ready.
                </p>
                <Button
                  variant="gradient"
                  onClick={() => (window.location.href = `/report?session=${sessionId}`)}
                >
                  View Full Report
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="flex items-center gap-2 p-8 text-sm text-foreground-muted">
                <Loader2 className="h-4 w-4 animate-spin" />
                Report will appear here once the research pipeline completes.
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
