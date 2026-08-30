import type { Task, TrustLadderMap, ClassInfo, ProcessAudioResponse, TaskSummary } from '../types';

// Shared-secret header for the mutating endpoints (submit/approve/reject/delete).
// Opt-in: unset VITE_API_SECRET (the default) and these calls are unchanged.
// This is a demo-grade gate baked into the client bundle, not per-user auth —
// see verify_api_secret in main.py.
const API_SECRET = import.meta.env.VITE_API_SECRET as string | undefined;
const authHeaders: HeadersInit | undefined = API_SECRET ? { 'X-Api-Secret': API_SECRET } : undefined;

export async function fetchTasks(): Promise<Task[]> {
  const res = await fetch('/api/tasks');
  if (!res.ok) throw new Error(`Failed to fetch tasks: ${res.statusText}`);
  return res.json();
}

export async function fetchTrustLadder(): Promise<TrustLadderMap> {
  const res = await fetch('/api/trust_ladder');
  if (!res.ok) throw new Error(`Failed to fetch trust ladder: ${res.statusText}`);
  return res.json();
}

export async function fetchClasses(): Promise<ClassInfo[]> {
  const res = await fetch('/api/classes');
  if (!res.ok) throw new Error(`Failed to fetch classes: ${res.statusText}`);
  return res.json();
}

export async function processAudio(
  audioBlob: Blob | null,
  filename: string,
  imageFile?: File | null,
  text?: string
): Promise<ProcessAudioResponse> {
  const formData = new FormData();
  if (audioBlob) {
    formData.append('file', audioBlob, filename);
  }
  if (text) {
    formData.append('text', text);
  }
  if (imageFile) {
    formData.append('image', imageFile, imageFile.name);
  }

  const res = await fetch('/tasks', {
    method: 'POST',
    body: formData,
    headers: authHeaders,
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Upload failed (${res.status}): ${errText}`);
  }

  return res.json();
}

export async function speakSummary(summary: TaskSummary): Promise<Blob | null> {
  try {
    const res = await fetch('/api/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(summary),
    });

    if (res.status === 204 || !res.ok) return null;
    return res.blob();
  } catch {
    return null;
  }
}

export async function approveTask(taskId: string): Promise<{ status: string; execution?: any }> {
  const res = await fetch(`/api/tasks/${taskId}/approve`, { method: 'POST', headers: authHeaders });
  if (!res.ok) throw new Error(`Approve failed (${res.status})`);
  return res.json();
}

export async function rejectTask(taskId: string): Promise<{ status: string }> {
  const res = await fetch(`/api/tasks/${taskId}/reject`, { method: 'POST', headers: authHeaders });
  if (!res.ok) throw new Error(`Reject failed (${res.status})`);
  return res.json();
}

export async function deleteTask(taskId: string): Promise<void> {
  const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE', headers: authHeaders });
  if (!res.ok) throw new Error(`Delete failed (${res.status})`);
}
