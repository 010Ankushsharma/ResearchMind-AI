"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Download, Loader2, ShieldAlert, Sparkles, TrendingUp } from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FollowUpPanel } from "@/components/report/follow-up-panel";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api-client";
import type { CitationStyle, PDFExportResponse, ReportRead } from "@/lib/types";

const REPORT_SECTIONS: { key: keyof ReportRead; label: string }[] = [
  { key: "abstract", label: "Abstract" },
  { key: "introduction", label: "Introduction" },
  { key: "key_findings", label: "Key Findings" },
  { key: "analysis", label: "Analysis" },
  { key: "recommendations", label: "Recommendations" },
  { key: "conclusion", label: "Conclusion" },
];

export default function ReportPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");
  const [citationStyle, setCitationStyle] = useState<CitationStyle>("apa");

  const { data: report, isLoading } = useQuery({
    queryKey: ["report-by-session", sessionId],
    queryFn: () => api.get<ReportRead>(`/report/by-session/${sessionId}`),
    enabled: !!sessionId,
  });

  const { mutate: exportPdf, isPending: isExporting } = useMutation({
    mutationFn: () =>
      api.post<PDFExportResponse>("/export/pdf", {
        report_id: report!.id,
        citation_style: citationStyle,
        include_charts: true,
        include_cover_page: true,
        include_table_of_contents: true,
      }),
    onSuccess: (data) => {
      window.open(data.pdf_url, "_blank");
    },
    onError: () => toast.error("Couldn't export the PDF — please try again."),
  });

  if (!sessionId) {
    return <p className="text-sm text-foreground-muted">No report selected.</p>;
  }

  if (isLoading || !report) {
    return (
      <div className="flex h-64 items-center justify-center text-foreground-muted">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading report…
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Badge variant="primary" className="mb-2 gap-1.5">
            <Sparkles className="h-3 w-3" /> v{report.version}
          </Badge>
          <h1 className="text-2xl font-semibold text-foreground">{report.title}</h1>
        </div>
        <Button variant="gradient" onClick={() => exportPdf()} disabled={isExporting}>
          {isExporting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Export PDF
        </Button>
      </div>

      <Tabs defaultValue="report">
        <TabsList>
          <TabsTrigger value="report">Full Report</TabsTrigger>
          <TabsTrigger value="summary">Summaries</TabsTrigger>
          <TabsTrigger value="executive">Executive Brief</TabsTrigger>
          <TabsTrigger value="citations">Citations</TabsTrigger>
          <TabsTrigger value="follow-up">Follow-up</TabsTrigger>
        </TabsList>

        {/* Full Report */}
        <TabsContent value="report" className="flex flex-col gap-4">
          {REPORT_SECTIONS.map(({ key, label }) => {
            const content = report[key] as string | null;
            if (!content) return null;
            return (
              <Card key={key}>
                <CardHeader>
                  <CardTitle>{label}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-3 text-sm leading-relaxed text-foreground/90">
                  {content.split("\n\n").map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </CardContent>
              </Card>
            );
          })}
        </TabsContent>

        {/* Summaries */}
        <TabsContent value="summary" className="flex flex-col gap-4">
          <SummaryCard title="Short Summary" content={report.short_summary} />
          <SummaryCard title="Medium Summary" content={report.medium_summary} />
          <SummaryCard title="Detailed Summary" content={report.detailed_summary} />
        </TabsContent>

        {/* Executive Brief */}
        <TabsContent value="executive" className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Executive Summary</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-relaxed text-foreground/90">
              {report.executive_summary || "Not available."}
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <ExecListCard
              title="Key Takeaways"
              icon={<Sparkles className="h-4 w-4 text-primary" />}
              items={report.key_takeaways}
            />
            <ExecListCard
              title="Risks"
              icon={<ShieldAlert className="h-4 w-4 text-danger" />}
              items={report.risks}
            />
            <ExecListCard
              title="Opportunities"
              icon={<TrendingUp className="h-4 w-4 text-success" />}
              items={report.opportunities}
            />
          </div>
        </TabsContent>

        {/* Citations */}
        <TabsContent value="citations" className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <span className="text-sm text-foreground-muted">Citation style</span>
            <Select value={citationStyle} onValueChange={(v) => setCitationStyle(v as CitationStyle)}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="apa">APA</SelectItem>
                <SelectItem value="mla">MLA</SelectItem>
                <SelectItem value="ieee">IEEE</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Card>
            <CardContent className="flex flex-col gap-3 p-5 text-sm">
              <p className="text-foreground-muted">
                Citations are included in the exported PDF in your selected style.
                Switch styles above and export again to regenerate the PDF accordingly.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Follow-up */}
        <TabsContent value="follow-up">
          <FollowUpPanel reportId={report.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function SummaryCard({ title, content }: { title: string; content: string | null }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm leading-relaxed text-foreground/90">
        {content || "Not available."}
      </CardContent>
    </Card>
  );
}

function ExecListCard({
  title,
  icon,
  items,
}: {
  title: string;
  icon: React.ReactNode;
  items: string[] | null;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items && items.length > 0 ? (
          <ul className="flex flex-col gap-2 text-sm text-foreground/90">
            {items.map((item, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-foreground-muted">•</span>
                {item}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-foreground-muted">None identified.</p>
        )}
      </CardContent>
    </Card>
  );
}
