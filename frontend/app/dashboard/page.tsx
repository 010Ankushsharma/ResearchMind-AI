"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import { cn, formatRelativeTime, humanizeSnakeCase } from "@/lib/utils";
import type { ResearchSessionCreate, ResearchSessionRead, ResearchSessionSummary } from "@/lib/types";

const SUGGESTED_PROMPTS = [
  "Latest advancements in AI Agents",
  "Impact of generative AI on software engineering jobs",
  "State of solid-state battery technology in 2026",
  "How quantum computing could affect cybersecurity",
  "Trends in renewable energy storage solutions",
];

const STATUS_BADGE_VARIANT: Record<string, "primary" | "success" | "danger" | "default"> = {
  completed: "success",
  failed: "danger",
  pending: "default",
};

export default function HomePage() {
  const [query, setQuery] = useState("");
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: recentSessions, isLoading: isLoadingHistory } = useQuery({
    queryKey: ["research-history", "recent"],
    queryFn: () => api.get<ResearchSessionSummary[]>("/research", { limit: 6 }),
  });

  const { mutate: startResearch, isPending } = useMutation({
    mutationFn: (payload: ResearchSessionCreate) =>
      api.post<ResearchSessionRead>("/research", payload),
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ["research-history"] });
      router.push(`/workspace?session=${session.id}`);
    },
    onError: () => {
      toast.error("Couldn't start research — please try again.");
    },
  });

  function handleSubmit() {
    const trimmed = query.trim();
    if (trimmed.length < 3) {
      toast.error("Please enter a more specific research topic or question.");
      return;
    }
    startResearch({ query: trimmed });
  }

  return (
    <div className="flex flex-col gap-10">
      {/* Hero / Input */}
      <section className="flex flex-col items-center gap-6 pt-10 text-center">
        <Badge variant="primary" className="gap-1.5">
          <Sparkles className="h-3 w-3" />
          AI Research Team, On Demand
        </Badge>
        <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          What would you like your{" "}
          <span className="text-gradient-brand">research team</span> to dig into?
        </h1>
        <p className="max-w-xl text-sm text-foreground-muted">
          Enter a topic or question. Ten specialized AI agents will research,
          verify, summarize, and write a fully-cited report — automatically.
        </p>

        <Card className="w-full max-w-2xl">
          <CardContent className="flex flex-col gap-3 p-4">
            <Textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder='e.g. "Latest advancements in AI Agents"'
              className="min-h-[88px] resize-none border-none bg-transparent text-base focus-visible:ring-0"
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  handleSubmit();
                }
              }}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-foreground-muted">⌘ + Enter to start</span>
              <Button
                variant="gradient"
                disabled={isPending || query.trim().length < 3}
                onClick={handleSubmit}
              >
                {isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Starting research…
                  </>
                ) : (
                  <>
                    Start Research
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Suggested prompts */}
        <div className="flex flex-wrap items-center justify-center gap-2">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => setQuery(prompt)}
              className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-foreground-muted transition-colors hover:border-primary/40 hover:text-foreground"
            >
              {prompt}
            </button>
          ))}
        </div>
      </section>

      {/* Recent Research */}
      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Recent Research</h2>
          <Button variant="ghost" size="sm" onClick={() => router.push("/workspace")}>
            View all
          </Button>
        </div>

        {isLoadingHistory ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i} className="h-28 animate-pulse" />
            ))}
          </div>
        ) : recentSessions && recentSessions.length > 0 ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {recentSessions.map((session) => (
              <Card
                key={session.id}
                className={cn(
                  "cursor-pointer transition-colors hover:border-primary/40"
                )}
                onClick={() => router.push(`/workspace?session=${session.id}`)}
              >
                <CardContent className="flex flex-col gap-2 p-4">
                  <div className="flex items-center justify-between">
                    <Badge variant={STATUS_BADGE_VARIANT[session.status] ?? "primary"}>
                      {humanizeSnakeCase(session.status)}
                    </Badge>
                    <span className="text-xs text-foreground-muted">
                      {formatRelativeTime(session.created_at)}
                    </span>
                  </div>
                  <p className="line-clamp-2 text-sm font-medium text-foreground">
                    {session.query}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
              <p className="text-sm text-foreground-muted">
                No research yet — enter a topic above to get started.
              </p>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}
