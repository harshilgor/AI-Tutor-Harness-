import { request } from './api';
import type { ChatAttachment } from '@/components/chat-composer';

export type MaterialAnswer = { blocks: { heading: string; body: string }[]; sources: { spanId: string; title: string; pageIndex: number; text: string }[]; message: string };
export async function materialRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  return request<T>(`/v1${path}`, init);
}
export const materialCommand = (body: unknown, signal?: AbortSignal): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal });

export async function prepareAttachment(item: ChatAttachment, signal: AbortSignal, onUploaded: (item: ChatAttachment) => void): Promise<ChatAttachment> {
  let current = item;
  if (!current.versionId) {
    const mediaType = /\.pdf$/i.test(item.name) ? 'application/pdf' : /\.md$/i.test(item.name) ? 'text/markdown' : /\.png$/i.test(item.name) ? 'image/png' : /\.jpe?g$/i.test(item.name) ? 'image/jpeg' : /\.webp$/i.test(item.name) ? 'image/webp' : /\.gif$/i.test(item.name) ? 'image/gif' : 'text/plain';
    const upload = await materialRequest<{ materialId: string; versionId: string; uploadPath: string }>('/materials', materialCommand({ title: item.name, mediaType, byteCount: item.file.size, role: 'reference' }, signal));
    await materialRequest(upload.uploadPath.replace(/^\/v1/, ''), { method: 'PUT', headers: { 'Content-Type': mediaType }, body: item.file, signal });
    current = { ...item, materialId: upload.materialId, versionId: upload.versionId };
    onUploaded(current);
  }
  for (let attempt = 0; attempt < 60; attempt++) {
    signal.throwIfAborted();
    const result = await materialRequest<{ status: string }>(`/materials/${current.materialId}`, { signal });
    if (['ready', 'partially_ready'].includes(result.status)) return current;
    if (['failed', 'needs_attention', 'deleted'].includes(result.status)) throw new Error(`${item.name} couldn't be read. Try a text-based PDF or paste the relevant passage.`);
    await new Promise(resolve => window.setTimeout(resolve, 1500));
  }
  throw new Error(`${item.name} is still processing. Send your message again in a moment.`);
}
