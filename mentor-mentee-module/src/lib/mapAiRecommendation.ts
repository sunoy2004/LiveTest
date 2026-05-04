import type { MatchProfile } from "@/data/mockData";
import type { AiRecommendationItem, MentorTierId } from "@/types/domain";

function normalizeTier(raw: string | null | undefined): MentorTierId {
  const u = String(raw ?? "PEER").toUpperCase();
  if (u === "PROFESSIONAL" || u === "EXPERT" || u === "PEER") return u;
  return "PEER";
}

/** Map AI GET /recommendations item → MatchCard / AiMatchCard model */
export function mapAiRecommendationToMatchProfile(a: AiRecommendationItem): MatchProfile {
  const tier = normalizeTier(a.tier_id ?? undefined);
  const credits =
    typeof a.session_credit_cost === "number" && a.session_credit_cost > 0
      ? a.session_credit_cost
      : tier === "EXPERT"
        ? 250
        : tier === "PROFESSIONAL"
          ? 100
          : 50;
  const skills = Array.isArray(a.expertise_areas) && a.expertise_areas.length ? a.expertise_areas : [];
  const expertiseLine = skills
    .slice(0, 5)
    .map((s) => String(s).trim())
    .filter(Boolean)
    .join(", ");
  const rawName = (a.display_name ?? "").trim();
  const hasName = Boolean(rawName);
  const idShort = String(a.mentor_id).replace(/-/g, "").slice(0, 8) || "mentor";
  /** Avoid using a bare expertise list as the card title when mentoring has no separate display name yet. */
  const nameLooksLikeExpertiseOnly =
    hasName &&
    expertiseLine.length > 0 &&
    rawName.replace(/\s+/g, " ").toLowerCase() === expertiseLine.toLowerCase();
  const name = hasName && !nameLooksLikeExpertiseOnly ? rawName : `Mentor ${idShort}`;

  const hasDisplayNameForBio = hasName && !nameLooksLikeExpertiseOnly;
  const bio = skills.length
    ? `Similarity match: ${skills.slice(0, 5).join(", ")}.`
    : hasDisplayNameForBio
      ? "Ranked by embedding similarity to your goals and their profile."
      : "Mentoring profile name will appear when the mentoring API can resolve this mentor (configure VITE_MENTORING_API_BASE_URL).";
  const scorePct = Math.round(Math.max(0, Math.min(1, a.score ?? 0)) * 100);
  return {
    id: a.mentor_id,
    mentorUserId: a.mentor_id,
    mentorProfileId: a.mentor_profile_id ?? undefined,
    name,
    avatar: "",
    role: "mentor",
    skills,
    bio,
    aiMatchScore: scorePct,
    tier,
    sessionCostCredits: credits,
    isAvailable: true,
  };
}
