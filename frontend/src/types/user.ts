export type Role = "operator" | "admin" | "super_admin";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
}

export interface UserResponse extends CurrentUser {
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: CurrentUser;
}
