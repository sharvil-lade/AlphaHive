import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="flex-1 min-h-[50vh] flex items-center justify-center" role="status" aria-label="Loading">
      <Loader2 className="w-5 h-5 animate-spin text-mutedText" />
    </div>
  );
}
