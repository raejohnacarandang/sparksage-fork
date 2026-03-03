"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Code2, MessageSquare, Clock, Cpu } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

interface Conversation {
  channel_id: string;
  message_count: number;
  last_active: string;
}

export default function ReviewPage() {
  const { data: session } = useSession();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  const token = (session as { accessToken?: string })?.accessToken;

  useEffect(() => {
    if (!token) return;
    api
      .getConversations(token)
      .then((data) => setConversations(Array.isArray(data) ? data : (data as any)?.channels || (data as any)?.conversations || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Code2 className="h-7 w-7 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Code Reviews</h1>
          <p className="text-muted-foreground text-sm">
            Channels where{" "}
            <code className="bg-muted px-1 rounded">/review</code> has been used
          </p>
        </div>
      </div>

      {/* How to use */}
      <Card className="border-dashed">
        <CardContent className="pt-4">
          <p className="text-sm text-muted-foreground">
            <strong>How to use:</strong> In Discord, type{" "}
            <code className="bg-muted px-1 rounded">
              /review code:&lt;your code&gt; language:python
            </code>{" "}
            to get an AI code review with bug detection, style tips, performance
            notes, and security checks.
          </p>
        </CardContent>
      </Card>

      {/* Conversation list */}
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading conversations...</p>
      ) : conversations.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            <Code2 className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>No conversations yet.</p>
            <p className="text-sm mt-1">
              Use{" "}
              <code className="bg-muted px-1 rounded">/review</code> in Discord
              to get started.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {conversations.map((conv) => (
           <Card
              key={conv.channel_id}
              className="hover:bg-muted/30 transition-colors cursor-pointer"
            >
              <Link href={`/dashboard/conversations?channel=${conv.channel_id}`}>
              <CardHeader className="pb-2 pt-4 px-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-muted-foreground" />
                    Channel{" "}
                    <code className="bg-muted px-1 rounded text-xs">
                      {conv.channel_id}
                    </code>
                  </CardTitle>
                  <Badge variant="secondary" className="text-xs">
                    Code Review
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Cpu className="h-3 w-3" />
                    {conv.message_count} messages
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Last active: {new Date(conv.last_active).toLocaleString()}
                  </span>
                </div>
              </CardContent>
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}