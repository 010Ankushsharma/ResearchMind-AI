import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background bg-gradient-radial-glow px-4">
      <div className="flex flex-col items-center gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-primary-accent shadow-glow" />
          <h1 className="text-xl font-semibold text-foreground">Welcome back</h1>
          <p className="text-sm text-foreground-muted">
            Sign in to access your AI research team
          </p>
        </div>
        <SignIn
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
          path="/sign-in"
          signUpUrl="/sign-up"
          fallbackRedirectUrl="/"
        />
      </div>
    </div>
  );
}
