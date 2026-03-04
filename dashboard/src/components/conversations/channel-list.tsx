"use client";

import Link from "next/link";
import { Trash2 } from "lucide-react";
import type { ChannelItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface ChannelListProps {
  channels: ChannelItem[];
  onDelete: (channelId: string) => void;
}

function formatDate(dateStr: string) {
  if (!dateStr) return "—";
  const date = new Date(dateStr);
  return date.toLocaleString();
}

export function ChannelList({ channels, onDelete }: ChannelListProps) {
  if (channels.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No conversations yet. Messages will appear here when users interact with the bot.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Channel ID</TableHead>
          <TableHead className="text-right">Messages</TableHead>
          <TableHead>Last Activity</TableHead>
          <TableHead className="w-12" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {channels.map((ch) => (
          <TableRow key={ch.channel_id}>
            <TableCell>
              <Link
                href={`/dashboard/conversations/${ch.channel_id}`}
                className="font-mono text-sm text-primary hover:underline"
              >
                #{ch.channel_id}
              </Link>
            </TableCell>
            <TableCell className="text-right">{ch.message_count}</TableCell>
            <TableCell className="text-sm text-muted-foreground">
              {formatDate(ch.last_active)}
            </TableCell>
            <TableCell>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete(ch.channel_id)}
                className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
