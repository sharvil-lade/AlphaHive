import type { Metadata } from "next";
import { ChatView } from "../../components/chat/ChatView";

export const metadata: Metadata = {
  title: "Chat",
  description: "Ask the hive about any Indian or global stock.",
};

export default function ChatHomePage() {
  return <ChatView />;
}
