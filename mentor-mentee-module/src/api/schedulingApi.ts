import type { BookSessionResponse, BookingSchedulingContext } from "@/types/scheduling";
import { getMentoringApiBaseUrl, MENTORING_API_PREFIX } from "@/config/mentoring";

function mentoringV1(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${getMentoringApiBaseUrl()}${MENTORING_API_PREFIX}${p}`;
}

function headers(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/json",
    "Content-Type": "application/json",
  };
}

export async function fetchSchedulingContext(
  token: string,
): Promise<BookingSchedulingContext> {
  const res = await fetch(mentoringV1("/scheduling/context"), {
    headers: headers(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `scheduling context (${res.status})`);
  }
  return res.json() as Promise<BookingSchedulingContext>;
}

export async function bookSession(
  token: string,
  body: { connection_id: string; slot_id: string; agreed_cost: number },
): Promise<BookSessionResponse> {
  const res = await fetch(mentoringV1("/scheduling/book"), {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `book failed (${res.status})`);
  }
  return res.json() as Promise<BookSessionResponse>;
}
