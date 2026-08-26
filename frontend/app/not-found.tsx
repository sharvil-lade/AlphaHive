import Link from "next/link";
import { Button } from "../components/ui/primitives";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-[13px] font-mono text-mutedText">404</p>
      <h1 className="text-xl font-semibold tracking-tight">This page doesn&apos;t exist</h1>
      <p className="text-sm text-mutedText max-w-sm">
        The link may be broken, or the conversation may have been deleted.
      </p>
      <div className="flex gap-2">
        <Link href="/chat">
          <Button>Go to chat</Button>
        </Link>
        <Link href="/">
          <Button variant="outline">Home</Button>
        </Link>
      </div>
    </div>
  );
}
