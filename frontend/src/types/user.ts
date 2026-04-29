export type Role = "operator" | "admin" | "super_admin";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
}

export interface UserResponse extends CurrentUser {
  is_active: boolean;
  phone?: string | null;
  current_location?: string | null;
  working_hours?: string | null;
  duty?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: CurrentUser;
}
