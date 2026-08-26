import type { Metadata } from "next";
import { AuthForm } from "../../components/auth/AuthForm";

export const metadata: Metadata = {
  title: "Create an account",
  description: "Create a free Alpha Hive account to keep your stock research and portfolio.",
};

export default function SignupPage() {
  return <AuthForm mode="signup" />;
}
