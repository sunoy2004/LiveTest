/** GET /profile/full from User Service */
export type UserServiceMentorProfile = {
  id: string;
  user_id: string;
  tier_id: string;
  is_accepting_requests: boolean;
  expertise_areas: string[] | null;
  total_hours_mentored: number;
};

export type UserServiceMenteeProfile = {
  id: string;
  user_id: string;
  learning_goals: string[] | null;
  education_level: string | null;
  is_minor: boolean;
  guardian_consent_status: string;
  cached_credit_score: number;
};

export type FullProfileResponse = {
  user_id: string;
  email: string;
  is_admin: boolean;
  mentor_profile: UserServiceMentorProfile | null;
  mentee_profile: UserServiceMenteeProfile | null;
};
