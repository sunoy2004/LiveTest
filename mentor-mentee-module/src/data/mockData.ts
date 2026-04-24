export interface User {
  id: string;
  name: string;
  avatar: string;
  role: "mentor" | "mentee";
  skills: string[];
  bio: string;
}

export interface Session {
  id: string;
  partnerName: string;
  partnerAvatar: string;
  date: string;
  time: string;
  topic: string;
  status:
    | "upcoming"
    | "completed"
    | "missed"
    | "pending_payment"
    | "in_progress"
    | "pending_approval"
    | "rejected";
  feedback?: string;
  rating?: number;
  mentorRating?: number;
  menteeRating?: number;
  notes?: string;
  costCredits?: number;
  startsInMinutes?: number;
  /** When set, Join opens this URL (dashboard upcoming session). */
  meetingUrl?: string;
  /** ISO start time from API for detail overlay. */
  startTimeIso?: string;
}

export interface Goal {
  id: string;
  title: string;
  progress: number;
  xpReward: number;
  category: string;
}

import type { MentorTierId } from "@/types/domain";

export interface MatchProfile {
  id: string;
  name: string;
  avatar: string;
  role: "mentor" | "mentee";
  skills: string[];
  bio: string;
  aiMatchScore: number;
  /** Architecture §2 — mentor_tiers.tier_id */
  tier: MentorTierId;
  sessionCostCredits: number;
  isAvailable: boolean;
  /** When set (AI flow), POST /recommendations/feedback uses this user id as target */
  mentorUserId?: string;
  /** When set (AI flow), POST /api/v1/requests body mentor_id */
  mentorProfileId?: string;
}

export interface CreditTransaction {
  id: string;
  type: "earned" | "spent" | "bonus";
  amount: number;
  description: string;
  date: string;
}

export interface CreditWallet {
  balance: number;
  lastTransaction: CreditTransaction;
  monthlyEarned: number;
  monthlySpent: number;
}

export const creditWallet: CreditWallet = {
  balance: 42,
  lastTransaction: {
    id: "t1",
    type: "spent",
    amount: -5,
    description: "Session with David Kim",
    date: "2 hours ago",
  },
  monthlyEarned: 60,
  monthlySpent: 18,
};

export const upcomingSessions: Session[] = [
  { id: "1", partnerName: "David Lee", partnerAvatar: "", date: "Today", time: "10:00 AM", topic: "Career Growth", status: "upcoming", costCredits: 5, startsInMinutes: 45 },
  { id: "2", partnerName: "Liam Chen", partnerAvatar: "", date: "Tomorrow", time: "2:00 PM", topic: "Code Review", status: "pending_payment", costCredits: 8 },
  { id: "3", partnerName: "Emily Davies", partnerAvatar: "", date: "Thursday", time: "11:00 AM", topic: "Portfolio Review", status: "upcoming", costCredits: 3, startsInMinutes: 1440 },
];

export const pastSessions: Session[] = [
  { id: "4", partnerName: "Chloe Evans", partnerAvatar: "", date: "Oct 19", time: "1:00 PM", topic: "Career Roadmap", status: "completed", feedback: "Great session! Very insightful discussion about career paths.", rating: 5, notes: "Discussed 3-year roadmap, identified key skill gaps", costCredits: 5 },
  { id: "5", partnerName: "Ben Carter", partnerAvatar: "", date: "Oct 15", time: "2:00 PM", topic: "Portfolio Review", status: "completed", rating: 4, notes: "Reviewed portfolio structure, suggested improvements", costCredits: 3 },
  { id: "6", partnerName: "Aisha Khan", partnerAvatar: "", date: "Oct 12", time: "12:00 PM", topic: "Resume Feedback", status: "missed", costCredits: 5 },
];

export const goals: Goal[] = [
  { id: "1", title: "Complete AWS Certification", progress: 87, xpReward: 500, category: "Cloud" },
  { id: "2", title: "Build Portfolio Site", progress: 40, xpReward: 300, category: "Projects" },
  { id: "3", title: "Learn Advanced Figma", progress: 62, xpReward: 250, category: "Design" },
];

/** Default carousel + local matchmaker search (when Mentoring API search is unavailable). */
export const mentorMatches: MatchProfile[] = [
  { id: "1", name: "David Kim", avatar: "", role: "mentor", skills: ["UX", "Figma", "Leadership"], bio: "Senior Designer with 8+ years experience in product design and design systems.", aiMatchScore: 94, tier: "EXPERT", sessionCostCredits: 250, isAvailable: true },
  { id: "2", name: "Maria Garcia", avatar: "", role: "mentor", skills: ["Agile", "Teamwork", "Strategy"], bio: "Project Manager passionate about mentoring the next generation of leaders.", aiMatchScore: 87, tier: "PROFESSIONAL", sessionCostCredits: 100, isAvailable: true },
  {
    id: "seed-mentor-demo",
    name: "Mentor 1 (demo)",
    avatar: "",
    role: "mentor",
    skills: ["Topic area 1", "Mentoring", "Python"],
    bio: "Matches seed naming for local search tests (no Mentoring API required).",
    aiMatchScore: 88,
    tier: "PROFESSIONAL",
    sessionCostCredits: 100,
    isAvailable: true,
  },
];

export const menteeMatches: MatchProfile[] = [
  { id: "3", name: "Alex Rivera", avatar: "", role: "mentee", skills: ["React", "TypeScript", "CSS"], bio: "Junior developer eager to learn modern frontend development practices.", aiMatchScore: 91, tier: "PEER", sessionCostCredits: 50, isAvailable: true },
  { id: "4", name: "Priya Sharma", avatar: "", role: "mentee", skills: ["Python", "Data Science", "ML"], bio: "Aspiring data scientist looking for guidance in ML engineering.", aiMatchScore: 82, tier: "PEER", sessionCostCredits: 50, isAvailable: false },
];

export const menteeStats = {
  totalMentors: 3,
  hoursReceived: 18.5,
  sessionsCompleted: 12,
  activeSessions: 5,
};

export const mentorStats = {
  totalMentees: 7,
  hoursMentored: 78.5,
  sessionsCompleted: 34,
  activeSessions: 8,
};
