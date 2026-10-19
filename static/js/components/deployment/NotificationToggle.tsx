import { ReactNode } from "react";

import NotificationCard from "../notifications/NotificationCard";

const NotificationToggle = ({
  type,
  label,
  children,
}: {
  type: "deployments" | "feedback";
  label: string;
  children: ReactNode;
}) => (
  <NotificationCard
    type={type}
    title={label}
    text={children}
    {...(type === "feedback"
      ? { channels: ["email" as const, "slack" as const] }
      : {})}
  />
);

export default NotificationToggle;
