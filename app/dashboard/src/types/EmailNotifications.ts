export type EmailNotificationTrigger =
  | "user_created"
  | "user_updated"
  | "user_deleted"
  | "user_limited"
  | "user_expired"
  | "user_enabled"
  | "user_disabled"
  | "data_usage_reset"
  | "data_reset_by_next"
  | "subscription_revoked"
  | "reached_usage_percent"
  | "reached_days_left";

export type EmailNotificationPreference = {
  trigger: EmailNotificationTrigger;
  enabled: boolean;
};

export type EmailSMTPSettings = {
  host: string;
  port: number;
  username: string | null;
  use_tls: boolean;
  use_ssl: boolean;
  from_email: string;
  from_name: string | null;
  has_password?: boolean;
};

export type EmailNotificationConfig = {
  smtp: EmailSMTPSettings | null;
  preferences: EmailNotificationPreference[];
};

export type EmailNotificationConfigUpdate = {
  smtp: Omit<EmailSMTPSettings, "has_password"> & {
    password?: string | null;
  };
  preferences: EmailNotificationPreference[];
};
