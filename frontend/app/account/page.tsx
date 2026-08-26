"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Download, Loader2, LogOut, Trash2 } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { deleteAccount, exportDataUrl, ApiError } from "../../services/api";
import { Button, Card, PageHeader } from "../../components/ui/primitives";

export default function AccountPage() {
  const { session, loading, logout } = useAuth();
  const toast = useToast();
  const router = useRouter();
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-mutedText" />
      </div>
    );
  }

  if (!session?.authenticated) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="text-sm text-mutedText max-w-sm">
          You&apos;re browsing anonymously. Your research lives in this browser only — create an
          account to reach it from anywhere.
        </p>
        <div className="flex gap-2">
          <Link href="/signup">
            <Button>Create account</Button>
          </Link>
          <Link href="/login">
            <Button variant="outline">Sign in</Button>
          </Link>
        </div>
      </div>
    );
  }

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteAccount();
      toast("Your account and all its data have been deleted.");
      router.push("/");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Couldn't delete the account.", "error");
      setDeleting(false);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader title="Account" description={session.email ?? undefined} />

      <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-2xl w-full mx-auto">
        <Card className="space-y-3">
          <h2 className="text-sm font-medium">Signed in as</h2>
          <p className="text-sm text-mutedText">{session.email}</p>
          <Button variant="outline" onClick={logout}>
            <LogOut className="w-3.5 h-3.5" /> Sign out
          </Button>
        </Card>

        <Card className="space-y-3">
          <h2 className="text-sm font-medium">Your data</h2>
          <p className="text-[13px] text-mutedText leading-relaxed">
            Download everything we store about you — portfolio holdings and full chat history — as
            a JSON file.
          </p>
          <a href={exportDataUrl()} download="alphahive-export.json">
            <Button variant="outline">
              <Download className="w-3.5 h-3.5" /> Export my data
            </Button>
          </a>
        </Card>

        <Card className="space-y-3 border-bearish/30">
          <h2 className="text-sm font-medium text-bearish">Delete account</h2>
          <p className="text-[13px] text-mutedText leading-relaxed">
            Permanently erases your account, portfolio and every conversation. This cannot be
            undone. Type <span className="font-mono text-foreground">DELETE</span> to confirm.
          </p>
          <div className="flex flex-wrap gap-2 items-center">
            <input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              aria-label="Type DELETE to confirm"
              placeholder="DELETE"
              className="bg-surface-raised border border-surface-border rounded-md px-3 py-1.5 text-sm w-32"
            />
            <Button variant="danger" disabled={confirmText !== "DELETE" || deleting} onClick={handleDelete}>
              {deleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
              Delete everything
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
