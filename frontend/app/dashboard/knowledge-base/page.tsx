"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Library, Search, Tag } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn, truncate } from "@/lib/utils";
import { api } from "@/lib/api-client";
import type { HistorySearchResult } from "@/lib/types";

interface KnowledgeDocumentItem {
  id: string;
  research_session_id: string;
  source_id: string | null;
  chunk_text: string;
  chunk_index: number;
  token_count: number | null;
  metadata_tags: Record<string, unknown> | null;
  created_at: string;
}

export default function KnowledgeBasePage() {
  const [searchInput, setSearchInput] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [activeTopic, setActiveTopic] = useState<string | null>(null);

  const { data: topics } = useQuery({
    queryKey: ["knowledge-topics"],
    queryFn: () => api.get<string[]>("/knowledge/topics"),
  });

  const { data: searchResults, isFetching: isSearching } = useQuery({
    queryKey: ["knowledge-search", activeQuery],
    queryFn: () => api.get<HistorySearchResult[]>("/knowledge/search", { q: activeQuery, top_k: 15 }),
    enabled: activeQuery.length > 1,
  });

  const { data: documents, isLoading: isLoadingDocs } = useQuery({
    queryKey: ["knowledge-documents"],
    queryFn: () => api.get<KnowledgeDocumentItem[]>("/knowledge/documents", { limit: 50 }),
    enabled: activeQuery.length === 0,
  });

  function handleSearch() {
    setActiveQuery(searchInput.trim());
  }

  const filteredDocuments = activeTopic
    ? documents?.filter((doc) => {
        const tags = doc.metadata_tags?.topics as string[] | undefined;
        return tags?.includes(activeTopic);
      })
    : documents;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <Library className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-semibold text-foreground">Knowledge Base</h1>
      </div>

      {/* Search bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={`Search everything you've researched, e.g. "battery density improvements"`}
            className="pl-9"
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <Button onClick={handleSearch} disabled={searchInput.trim().length < 2}>
          Search
        </Button>
        {activeQuery && (
          <Button variant="ghost" onClick={() => { setActiveQuery(""); setSearchInput(""); }}>
            Clear
          </Button>
        )}
      </div>

      {/* Topic filters */}
      {topics && topics.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <Tag className="h-3.5 w-3.5 text-foreground-muted" />
          {topics.map((topic) => (
            <button
              key={topic}
              onClick={() => setActiveTopic(activeTopic === topic ? null : topic)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs transition-colors",
                activeTopic === topic
                  ? "border-primary/40 bg-primary/15 text-primary"
                  : "border-border text-foreground-muted hover:text-foreground"
              )}
            >
              {topic}
            </button>
          ))}
        </div>
      )}

      {/* Results */}
      {activeQuery ? (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-foreground-muted">
            {isSearching ? "Searching…" : `${searchResults?.length ?? 0} results for "${activeQuery}"`}
          </p>
          {searchResults?.map((result) => (
            <Card key={result.chroma_vector_id}>
              <CardContent className="flex flex-col gap-2 p-4">
                <div className="flex items-center justify-between">
                  {result.relevance_score !== null && (
                    <Badge variant="primary">
                      {Math.round((result.relevance_score ?? 0) * 100)}% match
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-foreground/90">{truncate(result.text, 400)}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {isLoadingDocs ? (
            Array.from({ length: 4 }).map((_, i) => <Card key={i} className="h-24 animate-pulse" />)
          ) : filteredDocuments && filteredDocuments.length > 0 ? (
            filteredDocuments.map((doc) => (
              <Card key={doc.id}>
                <CardContent className="flex flex-col gap-2 p-4">
                  <p className="text-sm text-foreground/90">{truncate(doc.chunk_text, 280)}</p>
                  <span className="text-xs text-foreground-muted">
                    Chunk #{doc.chunk_index} · {doc.token_count ?? "?"} tokens
                  </span>
                </CardContent>
              </Card>
            ))
          ) : (
            <p className="text-sm text-foreground-muted">
              No documents indexed yet — run some research to populate your knowledge base.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
