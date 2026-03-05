"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { HelpCircle, Plus, Trash2, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface FAQ {
  id: number;
  guild_id: string;
  question: string;
  answer: string;
  match_keywords: string;
  times_used: number;
  created_by: string | null;
  created_at: string;
}

export default function FAQPage() {
  const { data: session } = useSession();
  const [faqs, setFaqs] = useState<FAQ[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [keywords, setKeywords] = useState("");
  const [guildId, setGuildId] = useState("");
  const [adding, setAdding] = useState(false);

  const token = (session as { accessToken?: string })?.accessToken;
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchFaqs = () => {
    if (!token) return;
    fetch(`${API_URL}/api/faqs`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setFaqs(Array.isArray(data) ? data : []))
      .catch(() => setFaqs([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchFaqs();
  }, [token]);

  const handleAdd = async () => {
    if (!token || !question || !answer || !keywords) return;
    setAdding(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/faqs`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guild_id: guildId || "default",
          question,
          answer,
          match_keywords: keywords,
          created_by: "dashboard",
        }),
      });
      if (res.ok) {
        setMessage({ text: "FAQ added successfully!", ok: true });
        setQuestion("");
        setAnswer("");
        setKeywords("");
        fetchFaqs();
      } else {
        setMessage({ text: "Failed to add FAQ", ok: false });
      }
    } catch {
      setMessage({ text: "Error adding FAQ", ok: false });
    } finally {
      setAdding(false);
    }
  };

  const confirmDeleteFaq = async () => {
    if (!token || confirmDelete === null) return;
    try {
      const res = await fetch(`${API_URL}/api/faqs/${confirmDelete}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMessage({ text: `FAQ #${confirmDelete} deleted`, ok: true });
        fetchFaqs();
      } else {
        setMessage({ text: "Failed to delete FAQ", ok: false });
      }
    } catch {
      setMessage({ text: "Error deleting FAQ", ok: false });
    } finally {
      setConfirmDelete(null);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center gap-3">
        <HelpCircle className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">FAQ Management</h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Manage auto-response FAQ entries for your Discord server
          </p>
        </div>
      </div>

      {message && (
        <Card className={message.ok ? "border-green-400 bg-green-50 dark:bg-green-950/20" : "border-red-400 bg-red-50 dark:bg-red-950/20"}>
          <CardContent className="pt-4 flex items-center gap-2">
            {message.ok
              ? <CheckCircle className="h-4 w-4 text-green-500" />
              : <XCircle className="h-4 w-4 text-red-500" />}
            <p className="text-sm">{message.text}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm sm:text-base flex items-center gap-2">
            <Plus className="h-4 w-4" /> Add New FAQ
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder="Question (e.g. How do I get started?)"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <textarea
            className="w-full p-2 border rounded-md text-sm bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            rows={3}
            placeholder="Answer"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
          <Input
            placeholder="Keywords (comma-separated, e.g. start,begin,how)"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
          />
          <Input
            placeholder="Guild ID (optional - leave blank for default)"
            value={guildId}
            onChange={(e) => setGuildId(e.target.value)}
          />
          <Button
            onClick={handleAdd}
            disabled={adding || !question || !answer || !keywords}
            size="sm"
          >
            {adding ? "Adding..." : "Add FAQ"}
          </Button>
        </CardContent>
      </Card>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading FAQs...</p>
      ) : faqs.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            <HelpCircle className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>No FAQs yet.</p>
            <p className="text-xs mt-1">
              Add one above or use <code className="bg-muted px-1 rounded">/faq add</code> in Discord.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {faqs.map((faq) => (
            <Card key={faq.id} className="hover:bg-muted/30 transition-colors">
              <CardHeader className="pb-2 pt-4 px-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className="text-xs">#{faq.id}</Badge>
                    <CardTitle className="text-sm font-medium">{faq.question}</CardTitle>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 w-7 p-0 text-destructive hover:text-destructive flex-shrink-0"
                    onClick={() => setConfirmDelete(faq.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4 space-y-2">
                <p className="text-sm text-muted-foreground">{faq.answer}</p>
                <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <span>Keywords: <code className="bg-muted px-1 rounded">{faq.match_keywords}</code></span>
                  <span>Used: <strong>{faq.times_used}x</strong></span>
                  {faq.guild_id && <span>Guild: <code className="bg-muted px-1 rounded">{faq.guild_id}</code></span>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={confirmDelete !== null} onOpenChange={() => setConfirmDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete FAQ #{confirmDelete}?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This FAQ will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-white hover:bg-destructive/90"
              onClick={confirmDeleteFaq}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}