import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Users, Clock, CheckCircle, Video, Plus, RefreshCw, Trophy, History } from "lucide-react";
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
import SessionBookingHistoryDialog from "@/components/dashboard/SessionBookingHistoryDialog";
import MatchmakerRequestHistoryDialog from "@/components/dashboard/MatchmakerRequestHistoryDialog";
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
import { fetchGamificationWallet } from "@/api/creditServiceApi";
import {
  createDashboardGoal,
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
import { rolesFromAccessToken } from "@/lib/jwtPayload";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

const Index = () => {
  const { user, token } = useMentorShellAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
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

  const shellRoles = useMemo(() => {
    if (user?.roles?.length) return user.roles;
    const fromJwt = rolesFromAccessToken(token);
    return fromJwt.length ? fromJwt : undefined;
  }, [user?.roles, token]);

  const { defaultRole, showRoleToggle } = useMemo(() => {
    if (profile) {
      return getRoleUiModeFromProfiles(
        profile.mentor_profile,
        profile.mentee_profile,
        shellRoles,
      );
    }
    return getRoleUiModeWhileProfileLoading(shellRoles);
  }, [profile, shellRoles]);

  const [role, setRole] = useState<"mentor" | "mentee">(defaultRole);

  useEffect(() => {
    setRole(defaultRole);
  }, [defaultRole]);

  const {
    data: upcomingListRes,
    isError: upcomingSessionsError,
    error: upcomingSessionsErr,
  } = useQuery({
    queryKey: ["user-service", "dashboard", "upcoming-sessions", token, role],
    queryFn: () => fetchDashboardUpcomingSessions(token!, role, 5),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const upcomingSessionsLoadError =
    upcomingSessionsError && upcomingSessionsErr
      ? upcomingSessionsErr instanceof Error
        ? upcomingSessionsErr.message
        : String(upcomingSessionsErr)
      : null;

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

  const profileData = role === "mentor" ? profile.mentor_profile : profile.mentee_profile;
  const greetingName = profileData?.first_name || user?.email?.split("@")[0] || "there";
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [bookingHistoryOpen, setBookingHistoryOpen] = useState(false);
  const [matchmakerHistoryOpen, setMatchmakerHistoryOpen] = useState(false);
  const [manageAvailabilityOpen, setManageAvailabilityOpen] = useState(false);
  const [bookingOpen, setBookingOpen] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<MatchProfile | null>(null);
  const [goalDialogOpen, setGoalDialogOpen] = useState(false);
  const [questDraft, setQuestDraft] = useState("");

  const createGoalMutation = useMutation({
    mutationFn: (title: string) => createDashboardGoal(token!, title),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["user-service", "dashboard", "goals"] });
      toast({
        title: "Quest added",
        description: "Your goal is saved on the mentoring service.",
      });
      setGoalDialogOpen(false);
      setQuestDraft("");
    },
    onError: (e: Error) => {
      toast({
        title: "Could not add quest",
        description: e.message.slice(0, 240),
        variant: "destructive",
      });
    },
  });

  const {
    data: aiRecs,
    refetch: refetchAi,
    isFetching: aiFetching,
    isError: aiRecsError,
  } = useAiRecommendations();

  const mentee = profile.mentee_profile;
  const usMentee = profile.mentee_profile;
  const profileCreditFallback =
    usMentee != null ? usMentee.cached_credit_score : (mentee?.cached_credit_score ?? 0);

  const { data: walletRes } = useQuery({
    queryKey: ["gamification", "wallet", "me", token],
    queryFn: () => fetchGamificationWallet(token!),
    enabled: Boolean(token),
    staleTime: 15_000,
    refetchInterval: 10_000,
  });
  /** Gamification wallet first; fall back to mentoring profile cache (synced from gamification on /profiles/me). */
  const credits = walletRes?.current_balance ?? profileCreditFallback;


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
          ? "No active connections"
          : s.active_partners === 1
            ? "1 active connection"
            : `${s.active_partners} active connections`,
    };
  }, [token, role, statsLoading, statsRes]);

  const [searchQ, setSearchQ] = useState("");
  const debouncedSearchQ = useDebouncedValue(searchQ, 250);
  /** API role: mentee dashboard searches mentors; mentor dashboard searches mentees. */
  const searchApiRole = role === "mentee" ? "mentor" : "mentee";
  const { data: searchResults = [], isFetching: searchFetching, isError: searchApiError } =
    useMentoringSearch(debouncedSearchQ, searchApiRole, 20);

  const searchMatches = useMemo(() => {
    const q = debouncedSearchQ.trim();
    if (!q) return [];

    const displayName = (r: SearchResultItem) => {
      const fromParts = [r.first_name, r.last_name]
        .filter((x): x is string => x != null && String(x).trim().length > 0)
        .map((x) => String(x).trim())
        .join(" ");
      if (fromParts) return fromParts;
      if (r.full_name && String(r.full_name).trim()) return String(r.full_name).trim();
      return r.user_id;
    };

    const mapApi = (r: SearchResultItem): MatchProfile => {
      const isMentor = r.role === "mentor";
      const tier = (r.tier ?? "PEER") as "PEER" | "PROFESSIONAL" | "EXPERT";
      const sessionCostCredits = isMentor
        ? typeof r.session_credit_cost === "number" && r.session_credit_cost > 0
          ? r.session_credit_cost
          : tier === "EXPERT"
            ? 250
            : tier === "PROFESSIONAL"
              ? 100
              : 50
        : 0;
      const skills = r.expertise ?? [];
      return {
        id: r.user_id,
        mentorUserId: isMentor ? r.user_id : undefined,
        mentorProfileId: isMentor ? r.user_id : undefined,
        name: displayName(r),
        avatar: "",
        role: isMentor ? "mentor" : "mentee",
        skills,
        bio: isMentor
          ? skills.length
            ? `Mentor skilled in ${skills.slice(0, 3).join(", ")}.`
            : "Mentor profile"
          : skills.length
            ? `Learning goals: ${skills.slice(0, 3).join(", ")}.`
            : "Mentee profile",
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
          label="Active Connections"
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
            <>
              <Button
                size="sm"
                variant="outline"
                className="text-xs shrink-0"
                onClick={() => setBookingHistoryOpen(true)}
                disabled={!token}
              >
                <History className="h-3.5 w-3.5 mr-1" />
                History
              </Button>
              <Button
                size="sm"
                className="text-xs gradient-primary border-0 shadow-sm shadow-primary/20 hover:shadow-md hover:shadow-primary/25 transition-shadow shrink-0"
                onClick={() => {
                  if (role === "mentor") setManageAvailabilityOpen(true);
                  else setScheduleOpen(true);
                }}
                disabled={guardianLocksMentorRequests}
              >
                <Plus className="h-3.5 w-3.5 mr-1" />{" "}
                {role === "mentee" ? "Request" : "Update availability"}
              </Button>
            </>
          }
        >
          <SessionList
            sessions={upcomingSessions}
            type="upcoming"
            viewerRole={role}
            emptyTitle="No upcoming sessions"
            emptySubtitle="Request or schedule a session to see it here"
            loadError={upcomingSessionsLoadError}
          />
        </SectionCard>
        <ScheduleSessionDialog
          open={scheduleOpen}
          onOpenChange={setScheduleOpen}
          role={role}
          token={token}
          cachedCreditScore={role === "mentee" ? credits : undefined}
        />
        <SessionBookingHistoryDialog
          open={bookingHistoryOpen}
          onOpenChange={setBookingHistoryOpen}
          token={token}
        />
        <MatchmakerRequestHistoryDialog
          open={matchmakerHistoryOpen}
          onOpenChange={setMatchmakerHistoryOpen}
          token={token}
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
            <div className="flex flex-wrap items-center justify-end gap-2">
              <Button
                size="sm"
                variant="outline"
                className="text-xs"
                onClick={() => setMatchmakerHistoryOpen(true)}
                disabled={!token || !isMentoringApiConfigured()}
                title={
                  !isMentoringApiConfigured()
                    ? "Set VITE_MENTORING_API_BASE_URL to load request history"
                    : !token
                      ? "Sign in to view history"
                      : undefined
                }
              >
                <History className="h-3 w-3 mr-1" /> History
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="text-xs"
                onClick={() => void handleRefreshAiMatches()}
                disabled={aiFetching}
              >
                <RefreshCw className={`h-3 w-3 mr-1 ${aiFetching ? "animate-spin" : ""}`} /> Refresh
              </Button>
            </div>
          }
        >
          <div className="space-y-5">
            <div className="flex flex-col items-center gap-2">
              <div className="w-full max-w-2xl">
                <Input
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  placeholder={
                    role === "mentee"
                      ? "Search mentors by name, expertise, bio, or user id…"
                      : "Search mentees by name, learning goals, education, or user id…"
                  }
                  className="h-9"
                  aria-label={role === "mentee" ? "Search mentors" : "Search mentees"}
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
                      {role === "mentee" && match.role === "mentor" && token ? (
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
            <>
              <Dialog open={goalDialogOpen} onOpenChange={setGoalDialogOpen}>
                <DialogContent className="sm:max-w-md">
                  <DialogHeader>
                    <DialogTitle>Add a quest</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-3 py-1">
                    <Label htmlFor="quest-title" className="text-xs text-muted-foreground">
                      What do you want to achieve?
                    </Label>
                    <Input
                      id="quest-title"
                      value={questDraft}
                      onChange={(ev) => setQuestDraft(ev.target.value)}
                      placeholder="e.g. Finish FastAPI chapter 5"
                      maxLength={2000}
                      disabled={createGoalMutation.isPending}
                      onKeyDown={(ev) => {
                        if (ev.key === "Enter" && questDraft.trim() && token && !createGoalMutation.isPending) {
                          ev.preventDefault();
                          createGoalMutation.mutate(questDraft);
                        }
                      }}
                    />
                  </div>
                  <DialogFooter className="gap-2 sm:gap-0">
                    <Button
                      variant="outline"
                      type="button"
                      disabled={createGoalMutation.isPending}
                      onClick={() => setGoalDialogOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="button"
                      disabled={!questDraft.trim() || !token || createGoalMutation.isPending}
                      onClick={() => createGoalMutation.mutate(questDraft)}
                    >
                      {createGoalMutation.isPending ? "Saving…" : "Save quest"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
              <Button
                size="sm"
                variant="outline"
                className="text-xs"
                disabled={!token}
                title={!token ? "Sign in to add goals" : undefined}
                onClick={() => {
                  setGoalDialogOpen(true);
                  setQuestDraft("");
                }}
              >
                <Trophy className="h-3.5 w-3.5 mr-1" /> Add Quest
              </Button>
            </>
          }
        >
          <GoalList
            goals={dashboardGoals}
            emptyTitle="No active goals"
            emptySubtitle="Add a quest above or sync goals from mentoring"
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
