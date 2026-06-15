import AuthLayout from "@/components/AuthLayout";
import AuthGoogleProvider from "@/components/AuthGoogleProvider";

export default function AuthGroupLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGoogleProvider>
      <AuthLayout>{children}</AuthLayout>
    </AuthGoogleProvider>
  );
}
