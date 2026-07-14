import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background bg-gradient-radial-glow px-4">
      <div className="flex flex-col items-center gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-primary-accent shadow-glow" />
          <h1 className="text-xl font-semibold text-foreground">Create your account</h1>
          <p className="text-sm text-foreground-muted">
            Start your own AI research team in seconds
          </p>
        </div>
        <SignUp
          appearance={{
            variables: {
              colorPrimary: "#3B82F6",
              colorBackground: "#111827",
              colorInputBackground: "#0B1120",
              colorText: "#E5E7EB",
              borderRadius: "0.75rem",
            },
            elements: {
              card: "shadow-card border border-border",
              headerTitle: "hidden",
              headerSubtitle: "hidden",
            },
          }}
          path="/sign-up"
          signInUrl="/sign-in"
          fallbackRedirectUrl="/"
        />
      </div>
    </div>
  );
}
