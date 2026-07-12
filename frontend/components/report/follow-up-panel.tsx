"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquarePlus, Send } from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import type { ReportRead } from "@/lib/types";

const SUGGESTED_FOLLOW_UPS = [
  "Expand the Key Findings section with more detail",
  "Add more recent sources to the Analysis section",
  "Make the Recommendations more actionable",
  "Compare this with my previous report on a similar topic",
];

interface FollowUpPanelProps {
  reportId: string;
}

export function FollowUpPanel({ reportId }: FollowUpPanelProps) {
  const [instruction, setInstruction] = useState("");
  const queryClient = useQueryClient();

  const { mutate: submitFollowUp, isPending } = useMutation({
    mutationFn: (text: string) =>
      api.post<ReportRead>(`/report/${reportId}/follow-up?instruction=${encodeURIComponent(text)}`),
    onSuccess: (updated) => {
      toast.success(`Follow-up applied — report bumped to v${updated.version}.`);
      queryClient.invalidateQueries({ queryKey: ["report-by-session"] });
      setInstruction("");
    },
    onError: () => toast.error("Couldn't apply that follow-up — please try again."),
  });

  function handleSubmit() {
    const trimmed = instruction.trim();
    if (trimmed.length < 3) {
      toast.error("Please describe what you'd like to change.");
      return;
    }
    submitFollowUp(trimmed);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquarePlus className="h-4 w-4 text-primary" />
          Follow-up Research
        </CardTitle>
        <CardDescription>
          Ask for a refinement — e.g. &quot;Expand section 3&quot; or &quot;Compare with previous report.&quot;
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="What would you like to change about this report?"
          className="min-h-[72px] resize-none"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
          }}
        />

        <div className="flex flex-wrap gap-2">
          {SUGGESTED_FOLLOW_UPS.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => setInstruction(suggestion)}
              className="rounded-full border border-border bg-background px-3 py-1 text-xs text-foreground-muted transition-colors hover:border-primary/40 hover:text-foreground"
            >
              {suggestion}
            </button>
          ))}
        </div>

        <div className="flex justify-end">
          <Button
            variant="gradient"
            disabled={isPending || instruction.trim().length < 3}
            onClick={handleSubmit}
          >
            <Send className="h-4 w-4" />
            {isPending ? "Applying…" : "Submit Follow-up"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
