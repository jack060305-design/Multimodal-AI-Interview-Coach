export type AuthUser = {
  id: string;
  email: string | null;
  name: string;
  avatar_url: string | null;
  provider?: string;
};
