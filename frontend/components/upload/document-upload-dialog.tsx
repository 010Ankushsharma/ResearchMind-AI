"use client";

import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { FileUp, Loader2, UploadCloud } from "lucide-react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";

interface DocumentUploadDialogProps {
  researchSessionId: string;
  trigger?: React.ReactNode;
}

interface UploadResponse {
  source_id: string;
  filename: string;
  chunks_stored: number;
  characters_extracted: number;
}

const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md"];

export function DocumentUploadDialog({ researchSessionId, trigger }: DocumentUploadDialogProps) {
  const [open, setOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { mutate: upload, isPending } = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const response = await apiClient.post<UploadResponse>(
        `/upload?research_session_id=${researchSessionId}`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`Indexed "${data.filename}" into ${data.chunks_stored} chunks.`);
      queryClient.invalidateQueries({ queryKey: ["research-sources", researchSessionId] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-documents"] });
      setOpen(false);
      setSelectedFile(null);
    },
    onError: (error: AxiosError<{ detail?: string }>) => {
      const detail = error?.response?.data?.detail;
      toast.error(detail || "Upload failed — please try a different file.");
    },
  });

  function handleFileSelect(file: File | null) {
    if (!file) return;
    const extension = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      toast.error(`Unsupported file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`);
      return;
    }
    setSelectedFile(file);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button variant="outline" size="sm">
            <FileUp className="h-4 w-4" />
            Upload Document
          </Button>
        )}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload a document</DialogTitle>
          <DialogDescription>
            Add a PDF, TXT, or Markdown file to this research session&apos;s knowledge base. It
            will be chunked, embedded, and made available to every agent — just like a web source.
          </DialogDescription>
        </DialogHeader>

        <div
          className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed border-border bg-background px-6 py-10 text-center transition-colors hover:border-primary/40"
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            handleFileSelect(e.dataTransfer.files?.[0] ?? null);
          }}
        >
          <UploadCloud className="h-6 w-6 text-foreground-muted" />
          {selectedFile ? (
            <p className="text-sm font-medium text-foreground">{selectedFile.name}</p>
          ) : (
            <>
              <p className="text-sm text-foreground-muted">
                Click to browse or drag a file here
              </p>
              <p className="text-xs text-foreground-muted">PDF, TXT, or MD — up to 15MB</p>
            </>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md"
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
          />
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="gradient"
            disabled={!selectedFile || isPending}
            onClick={() => selectedFile && upload(selectedFile)}
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Uploading…
              </>
            ) : (
              "Upload & Index"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
