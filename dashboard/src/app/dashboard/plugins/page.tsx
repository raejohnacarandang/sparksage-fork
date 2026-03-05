"use client";

import { useEffect, useState, useRef } from "react";
import { useSession } from "next-auth/react";
import { Puzzle, CheckCircle, XCircle, Info, Upload, X, Plus, Trash2, Package } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface Plugin {
  name: string;
  version: string;
  author: string;
  description: string;
  cog: string;
  enabled: boolean;
  source?: string;
  installed_at?: string;
}

export default function PluginsPage() {
  const { data: session } = useSession();
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<Partial<Plugin> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const token = (session as { accessToken?: string })?.accessToken;
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchPlugins = () => {
    if (!token) return;
    fetch(`${API_URL}/api/plugins`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setPlugins(Array.isArray(data) ? data : []))
      .catch(() => setPlugins([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPlugins();
  }, [token]);

  const handleFileSelect = async (file: File) => {
    if (!file.name.endsWith(".zip")) {
      toast.error("Please upload a .zip file");
      return;
    }
    setUploadFile(file);

    // Try to preview manifest from ZIP using JSZip-like parsing
    // We'll just show the filename for now and let the server parse it
    setPreview({ name: file.name.replace(".zip", ""), description: "Upload to see plugin details" });
  };

  const handleUpload = async () => {
    if (!uploadFile || !token) return;
    setUploading(true);

    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      const res = await fetch(`${API_URL}/api/plugins/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        toast.success(data.message || "Plugin installed!");
        setShowModal(false);
        setUploadFile(null);
        setPreview(null);
        fetchPlugins();
      } else {
        toast.error(data.detail || "Upload failed");
      }
    } catch {
      toast.error("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleToggle = async (plugin: Plugin) => {
    if (!token) return;
    setActionLoading(plugin.name);

    const action = plugin.enabled ? "disable" : "enable";
    try {
      const res = await fetch(`${API_URL}/api/plugins/${plugin.name}/${action}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        toast.success(data.message || `Plugin ${action}d`);
      } else {
        toast.error(data.detail || `Failed to ${action} plugin`);
      }
      fetchPlugins();
    } catch {
      toast.error("Action failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (plugin: Plugin) => {
    if (!token) return;
    if (!confirm(`Delete plugin "${plugin.name}"? This cannot be undone.`)) return;

    try {
      const res = await fetch(`${API_URL}/api/plugins/${plugin.name}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        toast.success(data.message || "Plugin deleted");
        fetchPlugins();
      } else {
        toast.error(data.detail || "Delete failed");
      }
    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6 p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Puzzle className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
          <div>
            <h1 className="text-xl sm:text-2xl font-bold">Plugins</h1>
            <p className="text-xs sm:text-sm text-muted-foreground">
              Manage community extension plugins
            </p>
          </div>
        </div>
        <Button onClick={() => setShowModal(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Add Plugin
        </Button>
      </div>

      {/* How to add plugins info */}
      <Card className="border-dashed">
        <CardContent className="pt-4 flex items-start gap-2">
          <Info className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            Upload a <code className="bg-muted px-1 rounded">.zip</code> file containing a{" "}
            <code className="bg-muted px-1 rounded">manifest.json</code> and cog <code className="bg-muted px-1 rounded">.py</code> file.
            Plugins can be enabled/disabled without restarting the bot.
          </p>
        </CardContent>
      </Card>

      {/* Plugin list */}
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading plugins...</p>
      ) : plugins.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            <Puzzle className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>No plugins installed.</p>
            <p className="text-xs mt-1">Click <strong>Add Plugin</strong> to upload your first plugin.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {plugins.map((plugin) => (
            <Card key={plugin.name} className="hover:bg-muted/30 transition-colors">
              <CardHeader className="pb-2 pt-4 px-4">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CardTitle className="text-sm font-medium">{plugin.name}</CardTitle>
                    <Badge variant="outline" className="text-xs">v{plugin.version}</Badge>
                    <Badge variant={plugin.enabled ? "default" : "secondary"} className="text-xs">
                      {plugin.enabled ? "✅ Enabled" : "❌ Disabled"}
                    </Badge>
                    {plugin.source === "database" && (
                      <Badge variant="outline" className="text-xs text-blue-500 border-blue-500/30">
                        <Package className="h-3 w-3 mr-1" /> DB
                      </Badge>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant={plugin.enabled ? "destructive" : "default"}
                      disabled={actionLoading === plugin.name}
                      onClick={() => handleToggle(plugin)}
                      className="text-xs h-7"
                    >
                      {actionLoading === plugin.name ? "..." : plugin.enabled ? "Disable" : "Enable"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={actionLoading === plugin.name}
                      onClick={() => handleDelete(plugin)}
                      className="text-xs h-7 text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <p className="text-sm text-muted-foreground">{plugin.description}</p>
                <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                  <span>by <strong>{plugin.author}</strong></span>
                  <span>cog: <code className="bg-muted px-1 rounded">{plugin.cog}</code></span>
                  {plugin.installed_at && (
                    <span>installed: {new Date(plugin.installed_at).toLocaleDateString()}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-background border rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Upload className="h-5 w-5" /> Add Plugin
              </h2>
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setShowModal(false); setUploadFile(null); setPreview(null); }}>
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Drop zone */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${uploadFile ? "border-primary bg-primary/5" : "border-muted-foreground/30 hover:border-primary/50"}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const file = e.dataTransfer.files[0];
                if (file) handleFileSelect(file);
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileSelect(f); }}
              />
              {uploadFile ? (
                <div>
                  <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
                  <p className="text-sm font-medium">{uploadFile.name}</p>
                  <p className="text-xs text-muted-foreground mt-1">{(uploadFile.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div>
                  <Upload className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm font-medium">Drop your plugin ZIP here</p>
                  <p className="text-xs text-muted-foreground mt-1">or click to browse</p>
                </div>
              )}
            </div>

            {/* Manifest format hint */}
            <div className="mt-4 p-3 bg-muted rounded-lg">
              <p className="text-xs text-muted-foreground font-medium mb-1">Required manifest.json format:</p>
              <pre className="text-xs text-muted-foreground">{`{
  "name": "my-plugin",
  "version": "1.0.0",
  "author": "you",
  "description": "What it does",
  "cog": "my_plugin.py"
}`}</pre>
            </div>

            <div className="flex gap-2 mt-4">
              <Button variant="outline" className="flex-1" onClick={() => { setShowModal(false); setUploadFile(null); setPreview(null); }}>
                Cancel
              </Button>
              <Button
                className="flex-1"
                disabled={!uploadFile || uploading}
                onClick={handleUpload}
              >
                {uploading ? "Installing..." : "Install Plugin"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}