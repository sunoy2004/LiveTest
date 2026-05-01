/**
 * Read a JSON array from a list-style mentoring response.
 * Treats 404/204 and empty bodies as [] so the UI can show empty states instead of errors.
 */
export async function parseJsonListResponse<T>(res: Response): Promise<T[]> {
  if (res.status === 404 || res.status === 204) return [];
  const text = await res.text();
  if (!res.ok) {
    throw new Error(text.trim() || `Request failed (${res.status})`);
  }
  if (!text.trim()) return [];
  try {
    const data = JSON.parse(text) as unknown;
    return Array.isArray(data) ? (data as T[]) : [];
  } catch {
    return [];
  }
}
