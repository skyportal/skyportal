import NotificationsIcon from "@mui/icons-material/NotificationsOutlined";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import NotificationCard from "../notifications/NotificationCard";
import PreferenceOption from "../notifications/PreferenceOption";
import type { ChannelKey } from "../notifications/channels";
import DiscussionAvatar from "./DiscussionAvatar";
import { discussionTitle } from "./names";
import { Body, Header } from "./pane";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useGetDiscussionsQuery,
  useUpdateDiscussionMembershipMutation,
} from "../../ducks/discussions";

const CHANNELS: ChannelKey[] = ["email", "slack", "sms", "whatsapp"];

interface DiscussionNotificationsProps {
  onOpen: (id: number) => void;
  onBack?: (() => void) | undefined;
}

const DiscussionNotifications = ({
  onOpen,
  onBack,
}: DiscussionNotificationsProps) => {
  const myId = useGetProfileQuery().data?.id;
  const { data: discussions } = useGetDiscussionsQuery();
  const [updateMembership] = useUpdateDiscussionMembershipMutation();
  const muted = (discussions ?? []).filter((discussion) => discussion.muted);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Header
        icon={<NotificationsIcon />}
        title="Notifications"
        subtitle="How you hear about new messages"
        onBack={onBack}
      />
      <Body wide>
        <NotificationCard
          type="direct_messages"
          title="Direct messages"
          text="When someone writes to you privately."
          channels={CHANNELS}
        />
        <NotificationCard
          type="group_discussions"
          title="Group conversations"
          text="New messages in the conversations and groups you are part of."
          channels={CHANNELS}
        >
          <Box
            sx={{
              width: "fit-content",
              maxWidth: "100%",
              "& .MuiTypography-caption": { contain: "inline-size" },
            }}
          >
            <PreferenceOption
              type="group_discussions"
              field="mentions_only"
              title="Only when someone mentions me"
              text="Skip the other messages of your group conversations."
            />
          </Box>
        </NotificationCard>
        <Box
          sx={{
            border: 1,
            borderColor: "divider",
            borderRadius: 2,
            padding: "0.375rem",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              padding: "0.5rem 0.5rem 0.5rem 0.125rem",
            }}
          >
            <Box
              sx={{
                width: 32,
                display: "flex",
                justifyContent: "center",
              }}
            >
              <Box
                sx={{
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: "text.secondary",
                  backgroundColor: "action.selected",
                }}
              >
                {muted.length}
              </Box>
            </Box>
            <Box sx={{ minWidth: 0 }}>
              <Typography
                variant="body2"
                sx={{ fontWeight: 600, lineHeight: 1.3 }}
              >
                Muted conversations
              </Typography>
              <Typography
                variant="caption"
                color="textSecondary"
                component="div"
                sx={{ lineHeight: 1.3 }}
              >
                Mute a conversation from its header to stop hearing about it.
              </Typography>
            </Box>
          </Box>
          {muted.length > 0 && (
            <Box
              sx={{
                margin: "0.375rem 0.5rem 0.375rem 2.75rem",
                paddingTop: 0.75,
                borderTop: 1,
                borderColor: "divider",
              }}
            >
              {muted.map((discussion) => (
                <Box
                  key={discussion.id}
                  onClick={() => onOpen(discussion.id)}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.25,
                    padding: "0.375rem 0.5rem",
                    borderRadius: 1.5,
                    cursor: "pointer",
                    "&:hover": { backgroundColor: "action.hover" },
                  }}
                >
                  <DiscussionAvatar
                    discussion={discussion}
                    myId={myId}
                    size={28}
                  />
                  <Typography
                    variant="body2"
                    noWrap
                    sx={{ flexGrow: 1, minWidth: 0, fontWeight: 500 }}
                  >
                    {discussionTitle(discussion, myId)}
                  </Typography>
                  <Box
                    role="button"
                    tabIndex={0}
                    onClick={(event) => {
                      event.stopPropagation();
                      updateMembership({ id: discussion.id, muted: false });
                    }}
                    sx={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 0.5,
                      padding: "0.25rem 0.75rem",
                      borderRadius: 999,
                      border: 1,
                      borderColor: "divider",
                      fontSize: "0.8125rem",
                      fontWeight: 500,
                      color: "text.secondary",
                      backgroundColor: "background.paper",
                      transition: "all 120ms",
                      "&:hover": {
                        borderColor: "primary.main",
                        color: "primary.main",
                      },
                      "& svg": { fontSize: "1rem" },
                    }}
                  >
                    <NotificationsIcon />
                    Unmute
                  </Box>
                </Box>
              ))}
            </Box>
          )}
        </Box>
      </Body>
    </Box>
  );
};

export default DiscussionNotifications;
