"use client";

import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Settings as SettingsIcon, Sliders, Palette, FileOutput, KeyRound, Loader2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api-client";

const MODEL_OPTIONS = [
  { value: "deepseek/deepseek-chat-v3:free", label: "DeepSeek V3 (balanced, default)" },
  { value: "deepseek/deepseek-r1:free", label: "DeepSeek R1 (best reasoning)" },
  { value: "qwen/qwen3-8b:free", label: "Qwen 3 8B (fastest)" },
  { value: "meta-llama/llama-3.3-70b-instruct:free", label: "Llama 3.3 70B" },
  { value: "google/gemma-3-12b-it:free", label: "Gemma 3 12B" },
];

interface UserSettingsRead {
  openrouter_key_configured: boolean;
  groq_key_configured: boolean;
  tavily_key_configured: boolean;
  preferred_model: string | null;
  default_max_sources: number;
  default_citation_style: "apa" | "mla" | "ieee";
}

interface UserSettingsUpdate {
  openrouter_api_key?: string;
  groq_api_key?: string;
  tavily_api_key?: string;
  preferred_model?: string;
  default_max_sources?: number;
  default_citation_style?: "apa" | "mla" | "ieee";
}

export default function SettingsPage() {
  const { user } = useUser();
  const queryClient = useQueryClient();

  const { data: settings, isLoading } = useQuery({
    queryKey: ["user-settings"],
    queryFn: () => api.get<UserSettingsRead>("/settings"),
  });

  // Local form state for the three (write-only) key inputs — these never
  // get pre-filled with real values from the server (the API only ever
  // returns *_key_configured booleans, never the keys themselves), so an
  // empty field here always means "leave the existing key untouched"
  // unless the person types something new.
  const [openrouterKey, setOpenrouterKey] = useState("");
  const [groqKey, setGroqKey] = useState("");
  const [tavilyKey, setTavilyKey] = useState("");
  const [selectedModel, setSelectedModel] = useState(MODEL_OPTIONS[0].value);
  const [defaultMaxSources, setDefaultMaxSources] = useState(10);
  const [defaultCitationStyle, setDefaultCitationStyle] = useState<"apa" | "mla" | "ieee">("apa");

  useEffect(() => {
    if (!settings) return;
    setSelectedModel(settings.preferred_model || MODEL_OPTIONS[0].value);
    setDefaultMaxSources(settings.default_max_sources);
    setDefaultCitationStyle(settings.default_citation_style as "apa" | "mla" | "ieee");
  }, [settings]);

  const { mutate: updateSettings, isPending } = useMutation({
    mutationFn: (payload: UserSettingsUpdate) => api.put<UserSettingsRead>("/settings", payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["user-settings"], updated);
      toast.success("Settings saved.");
    },
    onError: () => toast.error("Couldn't save settings — please try again."),
  });

  function handleSaveApiKeys() {
    const payload: UserSettingsUpdate = {};
    // Only send fields the person actually typed something into — leaving
    // a field blank means "don't touch the existing stored key" per the
    // semantics implemented in api/settings.py's apply_settings_update().
    if (openrouterKey) payload.openrouter_api_key = openrouterKey;
    if (groqKey) payload.groq_api_key = groqKey;
    if (tavilyKey) payload.tavily_api_key = tavilyKey;

    if (Object.keys(payload).length === 0) {
      toast.info("Enter a key value first, or use the clear button to remove an existing one.");
      return;
    }
    updateSettings(payload, {
      onSuccess: () => {
        setOpenrouterKey("");
        setGroqKey("");
        setTavilyKey("");
      },
    });
  }

  function handleClearKey(field: "openrouter_api_key" | "groq_api_key" | "tavily_api_key") {
    // Empty string is the explicit "clear this key" sentinel the backend understands.
    updateSettings({ [field]: "" } as UserSettingsUpdate);
  }

  function handleSaveExportDefaults() {
    updateSettings({
      preferred_model: selectedModel,
      default_max_sources: defaultMaxSources,
      default_citation_style: defaultCitationStyle,
    });
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-foreground-muted">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading settings…
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <SettingsIcon className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-semibold text-foreground">Settings</h1>
      </div>

      {/* Account */}
      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Managed by Clerk — signed in as {user?.primaryEmailAddress?.emailAddress}</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center gap-3">
          <Badge variant="success">Active</Badge>
          <span className="text-sm text-foreground-muted">
            {user?.fullName || "Anonymous Researcher"}
          </span>
        </CardContent>
      </Card>

      {/* API Keys */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-primary" /> API Keys
          </CardTitle>
          <CardDescription>
            Bring your own free-tier API keys, encrypted at rest. Leave blank to use the platform&apos;s
            shared defaults (subject to shared rate limits). Keys are never shown again once saved —
            only whether one is configured.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <LabeledKeyInput
            label="OpenRouter API Key"
            value={openrouterKey}
            onChange={setOpenrouterKey}
            placeholder="sk-or-v1-..."
            configured={settings?.openrouter_key_configured}
            onClear={() => handleClearKey("openrouter_api_key")}
          />
          <LabeledKeyInput
            label="Groq API Key (fallback)"
            value={groqKey}
            onChange={setGroqKey}
            placeholder="gsk_..."
            configured={settings?.groq_key_configured}
            onClear={() => handleClearKey("groq_api_key")}
          />
          <LabeledKeyInput
            label="Tavily API Key"
            value={tavilyKey}
            onChange={setTavilyKey}
            placeholder="tvly-..."
            configured={settings?.tavily_key_configured}
            onClear={() => handleClearKey("tavily_api_key")}
          />
          <div>
            <Button onClick={handleSaveApiKeys} disabled={isPending}>
              {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Save API Keys
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Model Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sliders className="h-4 w-4 text-primary" /> Model Selection
          </CardTitle>
          <CardDescription>Choose the preferred OpenRouter free model used for report writing.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {MODEL_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setSelectedModel(option.value)}
              className={`flex items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                selectedModel === option.value
                  ? "border-primary/40 bg-primary/10 text-foreground"
                  : "border-border text-foreground-muted hover:text-foreground"
              }`}
            >
              {option.label}
              {selectedModel === option.value && <Badge variant="primary">Selected</Badge>}
            </button>
          ))}
        </CardContent>
      </Card>

      {/* Export Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileOutput className="h-4 w-4 text-primary" /> Export Defaults
          </CardTitle>
          <CardDescription>Defaults applied to new research sessions and PDF exports.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <label className="w-48 text-sm text-foreground-muted">Max sources per report</label>
            <Input
              type="number"
              min={1}
              max={20}
              value={defaultMaxSources}
              onChange={(e) => setDefaultMaxSources(Number(e.target.value))}
              className="w-24"
            />
          </div>
          <div className="flex items-center gap-3">
            <label className="w-48 text-sm text-foreground-muted">Default citation style</label>
            <div className="flex gap-2">
              {(["apa", "mla", "ieee"] as const).map((style) => (
                <Button
                  key={style}
                  size="sm"
                  variant={defaultCitationStyle === style ? "default" : "outline"}
                  onClick={() => setDefaultCitationStyle(style)}
                >
                  {style.toUpperCase()}
                </Button>
              ))}
            </div>
          </div>
          <div>
            <Button onClick={handleSaveExportDefaults} disabled={isPending}>
              {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Save Defaults
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Theme (fixed for now — premium dark mode is the platform's signature look) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-4 w-4 text-primary" /> Theme
          </CardTitle>
          <CardDescription>
            This platform ships with a premium dark theme by design. Light mode is not currently supported.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Badge variant="primary">Dark Mode (Default)</Badge>
        </CardContent>
      </Card>
    </div>
  );
}

function LabeledKeyInput({
  label,
  value,
  onChange,
  placeholder,
  configured,
  onClear,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  configured?: boolean;
  onClear: () => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <label className="w-48 text-sm text-foreground-muted">{label}</label>
      <Input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={configured ? "•••••••••••••••• (configured)" : placeholder}
        className="flex-1"
      />
      {configured && (
        <Button variant="ghost" size="sm" onClick={onClear}>
          Clear
        </Button>
      )}
    </div>
  );
}
