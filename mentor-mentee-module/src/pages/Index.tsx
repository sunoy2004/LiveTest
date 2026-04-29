import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Users, Clock, CheckCircle, Video, Plus, RefreshCw, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import DashboardHeader from "@/components/dashboard/DashboardHeader";
import StatCard from "@/components/dashboard/StatCard";
import SectionCard from "@/components/dashboard/SectionCard";
import SessionList from "@/components/dashboard/SessionList";
import GoalList from "@/components/dashboard/GoalList";
import MatchCard from "@/components/dashboard/MatchCard";
import AiMatchCard from "@/components/dashboard/AiMatchCard";
import ScheduleSessionDialog from "@/components/dashboard/ScheduleSessionDialog";
import BookingDialog from "@/components/dashboard/BookingDialog";
import ManageAvailabilityDialog from "@/components/dashboard/ManageAvailabilityDialog";
import IncomingSessionRequestsPanel from "@/components/dashboard/IncomingSessionRequestsPanel";
import IncomingMatchmakerRequestsPanel from "@/components/dashboard/IncomingMatchmakerRequestsPanel";
import CreditWalletWidget from "@/components/dashboard/CreditWalletWidget";
import ConsentBanner from "@/components/dashboard/ConsentBanner";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel";
import { mentorMatches, menteeMatches, MatchProfile } from "@/data/mockData";
import { getDevProfileFallback } from "@/config/devProfile";
import { isAiApiConfigured, isMentoringApiConfigured } from "@/config/mentoring";
import {
  resolveProfile,
  useAiRecommendations,
  useMentoringProfileMe,
  useMentoringSearch,
} from "@/hooks/useMentoringQueries";
import { mapAiRecommendationToMatchProfile } from "@/lib/mapAiRecommendation";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { toast } from "@/hooks/use-toast";
import { fetchProfileFull } from "@/api/userService";
import { fetchGamificationWallet } from "@/api/creditServiceApi";
import {
  fetchDashboardGoals,
  fetchDashboardStats,
  fetchDashboardUpcomingSessions,
  fetchDashboardVault,
} from "@/api/dashboardApi";
import { useDashboardWebSocket } from "@/hooks/useDashboardWebSocket";
import { useMentorShellAuth } from "@/context/MentorShellAuthContext";
import type { SearchResultItem } from "@/types/domain";
import {
  getRoleUiModeFromProfiles,
  getRoleUiModeWhileProfileLoading,
} from "@/lib/roleMode";
import { mapGoals, mapUpcomingSessionList, mapVaultSessions } from "@/lib/mapDashboard";
import { cn } from "@/lib/utils";

const Index = () => {
  const { user, token } = useMentorShellAuth();
  const navigate = useNavigate();
  useDashboardWebSocket(token);
  
  const { data: profileRemote, isFetching: profileLoading } = useMentoringProfileMe();
  const profile = useMemo(
    () => resolveProfile(profileRemote, getDevProfileFallback()),
    [profileRemote],
  );


  useEffect(() => {
    if (!token || !profile?.is_admin) return;
    navigate("admin/mentors", { replace: true });
  }, [token, profile?.is_admin, navigate]);

  const { defaultRole, showRoleToggle } = useMemo(() => {
    if (profile) {
      return getRoleUiModeFromProfiles(
        profile.mentor_profile,
        profile.mentee_profile,
      );
    }
    return getRoleUiModeWhileProfileLoading();
  }, [profile]);

  const [role, setRole] = useState<"mentor" | "mentee">(defaultRole);

  useEffect(() => {
    setRole(defaultRole);
  }, [defaultRole]);

  const { data: upcomingListRes } = useQuery({
    queryKey: ["user-service", "dashboard", "upcoming-sessions", token, role],
    queryFn: () => fetchDashboardUpcomingSessions(token!, role, 5),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const { data: goalsRes } = useQuery({
    queryKey: ["user-service", "dashboard", "goals", token, role],
    queryFn: () => fetchDashboardGoals(token!, role),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const { data: vaultRes } = useQuery({
    queryKey: ["user-service", "dashboard", "vault", token, role],
    queryFn: () => fetchDashboardVault(token!, role),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const { data: statsRes, isFetching: statsLoading } = useQuery({
    queryKey: ["user-service", "dashboard", "stats", token, role],
    queryFn: () => fetchDashboardStats(token!, role),
    enabled: Boolean(token),
    staleTime: 30_000,
    refetchInterval: 10_000,
  });

  const upcomingSessions = useMemo(
    () => mapUpcomingSessionList(upcomingListRes ?? []),
    [upcomingListRes],
  );
  const dashboardGoals = useMemo(() => mapGoals(goalsRes ?? []), [goalsRes]);
  const pastSessions = useMemo(() => mapVaultSessions(vaultRes ?? []), [vaultRes]);

  const greetingName = user?.email?.split("@")[0] ?? "there";
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [manageAvailabilityOpen, setManageAvailabilityOpen] = useState(false);
  const [bookingOpen, setBookingOpen] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<MatchProfile | null>(null);

  const {
    data: aiRecs,
    refetch: refetchAi,
    isFetching: aiFetching,
    isError: aiRecsError,
  } = useAiRecommendations();

  const mentee = profile.mentee_profile;
  const usMentee = profile.mentee_profile;
  const fallbackCredits =
    usMentee != null ? usMentee.cached_credit_score : (mentee?.cached_credit_score ?? 100);

  const { data: walletRes } = useQuery({
    queryKey: ["gamification", "wallet", "me", token],
    queryFn: () => fetchGamificationWallet(token!),
    enabled: Boolean(token),
    staleTime: 15_000,
    refetchInterval: 10_000,
  });
  const credits = walletRes?.current_balance ?? fallbackCredits;


  /** Workflow 1 — POST /requests → 403 until guardian consent (DPDP). */
  const guardianLocksMentorRequests =
    role === "mentee" &&
    Boolean(usMentee ? usMentee.is_minor : mentee?.is_minor) &&
    (usMentee?.guardian_consent_status ?? mentee?.guardian_consent_status) === "PENDING";

  const showConsentBanner =
    Boolean(usMentee ? usMentee.is_minor : mentee?.is_minor) &&
    (usMentee?.guardian_consent_status ?? mentee?.guardian_consent_status) === "PENDING";

  const matches = useMemo(() => (role === "mentee" ? mentorMatches : menteeMatches), [role]);

  const aiMentorCarouselItems = useMemo(() => {
    if (!isAiApiConfigured() || role !== "mentee" || !aiRecs?.length) return [];
    return aiRecs.map(mapAiRecommendationToMatchProfile);
  }, [aiRecs, role]);

  const statCards = useMemo(() => {
    const demo =
      role === "mentee"
        ? {
            activePartners: 3,
            hoursTotal: 18.5,
            hoursWeek: 2.1,
            sessionsCompleted: 12,
            activeSessions: 5,
            partnersSub: "+1 this month",
          }
        : {
            activePartners: 7,
            hoursTotal: 78.5,
            hoursWeek: 2.1,
            sessionsCompleted: 34,
            activeSessions: 8,
            partnersSub: "+2 this month",
          };
    if (!token) {
      return {
        activePartners: demo.activePartners,
        hoursLabel: `${demo.hoursTotal} hrs`,
        hoursSub: `+${demo.hoursWeek} hrs this week`,
        sessionsCompleted: demo.sessionsCompleted,
        activeSessions: demo.activeSessions,
        partnersSub: demo.partnersSub,
      };
    }
    if (statsLoading && !statsRes) {
      return {
        activePartners: "…",
        hoursLabel: "…",
        hoursSub: "…",
        sessionsCompleted: "…",
        activeSessions: "…",
        partnersSub: "…",
      };
    }
    const s = statsRes ?? {
      active_partners: 0,
      hours_total: 0,
      hours_this_week: 0,
      sessions_completed: 0,
      active_sessions: 0,
    };
    return {
      activePartners: s.active_partners,
      hoursLabel: `${Number(s.hours_total).toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 1,
      })} hrs`,
      hoursSub:
        s.hours_this_week > 0
          ? `+${Number(s.hours_this_week).toLocaleString(undefined, {
              minimumFractionDigits: 0,
              maximumFractionDigits: 1,
            })} hrs this week`
          : "No completed hours this week",
      sessionsCompleted: s.sessions_completed,
      activeSessions: s.active_sessions,
      partnersSub:
        s.active_partners === 0
          ? "No active mentorships"
          : s.active_partners === 1
            ? "1 active mentorship"
            : `${s.active_partners} active mentorships`,
    };
  }, [token, role, statsLoading, statsRes]);

  const [searchQ, setSearchQ] = useState("");
  const debouncedSearchQ = useDebouncedValue(searchQ, 250);
  const { data: searchResults = [], isFetching: searchFetching, isError: searchApiError } =
    useMentoringSearch(debouncedSearchQ, "mentor", 8);

  const searchMatches = useMemo(() => {
    const q = debouncedSearchQ.trim();
    if (!q) return [];

    const mapApi = (r: SearchResultItem): MatchProfile => {
      const tier = (r.tier ?? "PEER") as "PEER" | "PROFESSIONAL" | "EXPERT";
      const sessionCostCredits =
        typeof r.session_credit_cost === "number" && r.session_credit_cost > 0
          ? r.session_credit_cost
          : tier === "EXPERT"
            ? 250
            : tier === "PROFESSIONAL"
              ? 100
              : 50;
      return {
        id: r.user_id,
        mentorUserId: r.user_id,
        mentorProfileId: r.mentor_profile_id ?? undefined,
        name: r.full_name ?? r.user_id,
        avatar: "",
        role: "mentor",
        skills: r.expertise ?? [],
        bio: r.expertise?.length
          ? `Mentor skilled in ${r.expertise.slice(0, 3).join(", ")}.`
          : "Mentor profile",
        aiMatchScore: 90,
        tier,
        sessionCostCredits,
        isAvailable: true,
      };

    };

    const pool = role === "mentee" ? mentorMatches : menteeMatches;
    const qLower = q.toLowerCase();
    const filterLocal = () =>
      pool.filter((m) => {
        const hay = `${m.name} ${m.id} ${m.skills.join(" ")} ${m.bio}`.toLowerCase();
        return hay.includes(qLower);
      });

    if (isMentoringApiConfigured() && !searchApiError) {
      return searchResults.map(mapApi);
    }
    return filterLocal();
  }, [debouncedSearchQ, searchResults, role, searchApiError]);

  const showSearchMatches = debouncedSearchQ.trim().length > 0;
  const showAiMentorCarousel =
    role === "mentee" &&
    isAiApiConfigured() &&
    !showSearchMatches &&
    Boolean(user?.id);
  const carouselMatches = showSearchMatches
    ? searchMatches
    : showAiMentorCarousel
      ? aiMentorCarouselItems
      : matches;

  const handleRequestSession = (match: MatchProfile) => {
    if (guardianLocksMentorRequests) {
      toast({
        title: "Guardian consent required",
        description:
          "Messaging a mentor is locked until guardian approval completes (HTTP 403 from Mentoring API).",
        variant: "destructive",
      });
      return;
    }
    setSelectedMatch(match);
    setBookingOpen(true);
  };

  const handleRefreshAiMatches = () => {
    if (isAiApiConfigured()) {
      void refetchAi();
      toast({ title: "Refreshing", description: "AI recommendations re-fetched (GET /recommendations)." });
    } else {
      toast({
        title: "AI API not configured",
        description: "Set VITE_AI_API_BASE_URL to load live Graph / matching recommendations.",
      });
    }
  };

  return (
    <div
      className={cn(
        "w-full min-h-0 space-y-6 p-4 sm:p-6 md:p-8",
        "pb-16 sm:pb-20 md:pb-24",
      )}
    >
      <DashboardHeader
        role={role}
        onRoleChange={setRole}
        showRoleToggle={showRoleToggle}
        greetingName={greetingName}
      />

      {showConsentBanner && <ConsentBanner type="consent" />}

      <CreditWalletWidget
        balance={credits}
        lifetimeEarned={walletRes?.lifetime_earned}
        token={token}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Users}
          label={role === "mentee" ? "Active Mentors" : "Active Mentees"}
          value={statCards.activePartners}
          subtitle={statCards.partnersSub}
          index={0}
        />
        <StatCard
          icon={Clock}
          label={role === "mentee" ? "Hours Received" : "Hours Mentored"}
          value={statCards.hoursLabel}
          subtitle={statCards.hoursSub}
          index={1}
        />
        <StatCard
          icon={CheckCircle}
          label="Sessions Completed"
          value={statCards.sessionsCompleted}
          index={2}
        />
        <StatCard
          icon={Video}
          label="Active Sessions"
          value={statCards.activeSessions}
          index={3}
        />
      </div>

      {token && role === "mentor" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
          <SectionCard
            title="Session requests"
            subtitle="Mentees request slots; credits are charged only when you accept"
          >
            <IncomingSessionRequestsPanel token={token} enabled />
          </SectionCard>

          <SectionCard
             title="Matchmaker requests"
             subtitle="Mentorship connection requests from users discovering you"
          >
            <IncomingMatchmakerRequestsPanel token={token} enabled />
          </SectionCard>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Widget A — Architecture §3.3 GET /api/v1/dashboard/upcoming-session */}
        <SectionCard
          title="Upcoming Session"
          subtitle="Dashboard widget A — next Meet link & timing"
          action={
            <Button
              size="sm"
              className="text-xs gradient-primary border-0 shadow-sm shadow-primary/20 hover:shadow-md hover:shadow-primary/25 transition-shadow"
              onClick={() => {
                if (role === "mentor") setManageAvailabilityOpen(true);
                else setScheduleOpen(true);
              }}
              disabled={guardianLocksMentorRequests}
            >
              <Plus className="h-3.5 w-3.5 mr-1" />{" "}
              {role === "mentee" ? "Request" : "Update availability"}
            </Button>
          }
        >
          <SessionList
            sessions={upcomingSessions}
            type="upcoming"
            viewerRole={role}
            emptyTitle="No upcoming sessions"
            emptySubtitle="Request or schedule a session to see it here"
          />
        </SectionCard>
        <ScheduleSessionDialog
          open={scheduleOpen}
          onOpenChange={setScheduleOpen}
          role={role}
          token={token}
          cachedCreditScore={role === "mentee" ? credits : undefined}
        />
        <ManageAvailabilityDialog
          open={manageAvailabilityOpen}
          onOpenChange={setManageAvailabilityOpen}
          token={token}
        />

        {/* Matchmaker carousel — Workflow 2: AI API GET /recommendations (not Mentoring API) */}
        <SectionCard
          title="Matchmaker"
          subtitle={
            [
              isAiApiConfigured()
                ? "AI discovery — semantic recommendations (View / Connect / Not interested)"
                : "AI discovery — set VITE_AI_API_BASE_URL for GET /recommendations",
              !isMentoringApiConfigured()
                ? "Search filters the local demo mentor list (set VITE_MENTORING_API_BASE_URL for GET /api/v1/search)."
                : null,
            ]
              .filter(Boolean)
              .join(" ")
          }
          action={
            <Button
              size="sm"
              variant="outline"
              className="text-xs"
              onClick={() => void handleRefreshAiMatches()}
              disabled={aiFetching}
            >
              <RefreshCw className={`h-3 w-3 mr-1 ${aiFetching ? "animate-spin" : ""}`} /> Refresh
            </Button>
          }
        >
          <div className="space-y-5">
            <div className="flex flex-col items-center gap-2">
              <div className="w-full max-w-2xl">
                <Input
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  placeholder="Search mentors by name, skill, or user_id…"
                  className="h-9"
                />

              </div>
              <div className="text-[11px] text-muted-foreground text-center">
                {debouncedSearchQ.trim()
                  ? searchFetching && isMentoringApiConfigured()
                    ? "Searching…"
                    : `${searchMatches.length} found`
                  : ""}
              </div>
            </div>
          </div>

          <div className="relative px-2 sm:px-10">
            <Carousel
              opts={{ align: "start", loop: false }}
              className="w-full"
            >
              <CarouselContent className="-ml-2 md:-ml-4">
                {showAiMentorCarousel && aiFetching && carouselMatches.length === 0 ? (
                  <CarouselItem className="pl-2 md:pl-4 basis-full">
                    <p className="text-sm text-muted-foreground text-center py-8">Loading recommendations…</p>
                  </CarouselItem>
                ) : carouselMatches.length === 0 &&
                  showAiMentorCarousel &&
                  !aiFetching &&
                  !aiRecsError ? (
                  <CarouselItem className="pl-2 md:pl-4 basis-full">
                    <p className="text-sm text-muted-foreground text-center py-8 px-4">
                      No AI recommendations yet. Ensure you have a mentee profile, mentors in the
                      system, then run{" "}
                      <code className="text-xs bg-muted px-1 rounded">POST …/internal/matchmaking/reindex</code>{" "}
                      on the AI service if needed.
                    </p>
                  </CarouselItem>
                ) : showAiMentorCarousel && aiRecsError ? (
                  <CarouselItem className="pl-2 md:pl-4 basis-full">
                    <p className="text-sm text-destructive text-center py-8 px-4">
                      Could not load AI recommendations. Check JWT, mentee role, and AI service URL.
                    </p>
                  </CarouselItem>
                ) : (
                  carouselMatches.map((match) => (
                    <CarouselItem
                      key={match.id}
                      className="pl-2 md:pl-4 basis-full min-[520px]:basis-1/2"
                    >
                      {showAiMentorCarousel ? (
                        <AiMatchCard
                          match={match}
                          token={token}
                          requestLocked={guardianLocksMentorRequests}
                        />
                      ) : (
                        <MatchCard
                          match={match}
                          onRequest={handleRequestSession}
                          requestLocked={guardianLocksMentorRequests}
                        />
                      )}
                    </CarouselItem>
                  ))
                )}
              </CarouselContent>
              <CarouselPrevious className="hidden sm:flex -left-1 border-border h-9 w-9" />
              <CarouselNext className="hidden sm:flex -right-1 border-border h-9 w-9" />
            </Carousel>
          </div>
        </SectionCard>

        {/* Widget C — Architecture §3.3 GET /api/v1/dashboard/goals */}
        <SectionCard
          title="Goals"
          subtitle="Dashboard widget C — connection quests & XP"
          action={
            <Button size="sm" variant="outline" className="text-xs">
              <Trophy className="h-3.5 w-3.5 mr-1" /> Add Quest
            </Button>
          }
        >
          <GoalList
            goals={dashboardGoals}
            emptyTitle="No active goals"
            emptySubtitle="Goals from your mentorship will show here"
          />
        </SectionCard>

        {/* Widget D — Architecture §3.3 GET /api/v1/dashboard/vault */}
        <SectionCard
          title="Session Vault"
          subtitle="Dashboard widget D — notes, ratings, JSONB history"
        >
          <SessionList
            sessions={pastSessions}
            type="history"
            viewerRole={role}
            emptyTitle="No past sessions"
            emptySubtitle="Completed sessions and notes appear in your vault"
          />
        </SectionCard>
      </div>

      <BookingDialog
        open={bookingOpen}
        onOpenChange={setBookingOpen}
        match={selectedMatch}
        cachedCreditScore={credits}
        bookingContext={null}
        token={token}
      />

      {profileLoading && (
        <p className="text-[11px] text-muted-foreground text-center">
          Syncing profile (GET /api/v1/profiles/me)…
        </p>
      )}
    </div>
  );
};

export default Index;
