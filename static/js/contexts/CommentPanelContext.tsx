import {
  ReactNode,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { MAIN_CHANNEL } from "../components/comment/channels";

export type CommentTarget =
  | { type: "source"; id: string }
  | { type: "gcn_event"; id: number; dateobs: string };

/** The two halves of the chat panel: a resource's comments, and the assistant. */
export type ChatSpace = "comments" | "assistant";

const INLINE_KEY = "sourceChatInline";

interface CommentPanelState {
  target: CommentTarget | null;
  setTarget: (target: CommentTarget | null) => void;
  inline: boolean;
  toggleInline: () => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  space: ChatSpace;
  setSpace: (space: ChatSpace) => void;
  channel: string;
  setChannel: (channel: string) => void;
  openChannel: (channel: string) => void;
  assistantChannel: string | null;
  setAssistantChannel: (channel: string | null) => void;
}

const CommentPanelContext = createContext<CommentPanelState | null>(null);

export const CommentPanelProvider = ({ children }: { children: ReactNode }) => {
  const [target, setTarget] = useState<CommentTarget | null>(null);
  const [inline, setInline] = useState(
    () => window.localStorage.getItem(INLINE_KEY) !== "false",
  );
  const [open, setOpen] = useState(false);
  const [space, setSpace] = useState<ChatSpace>("comments");
  const [channel, setChannel] = useState<string>(MAIN_CHANNEL);
  const [assistantChannel, setAssistantChannel] = useState<string | null>(null);

  const value = useMemo<CommentPanelState>(
    () => ({
      target,
      setTarget,
      inline,
      toggleInline: () => {
        window.localStorage.setItem(INLINE_KEY, String(!inline));
        setInline(!inline);
        setSpace("comments");
        setOpen(inline);
      },
      open,
      setOpen,
      space,
      setSpace,
      channel,
      setChannel,
      openChannel: (name: string) => {
        setSpace("comments");
        setChannel(name);
        setOpen(!inline);
      },
      assistantChannel,
      setAssistantChannel,
    }),
    [target, inline, open, space, channel, assistantChannel],
  );

  return (
    <CommentPanelContext.Provider value={value}>
      {children}
    </CommentPanelContext.Provider>
  );
};

export const useCommentPanel = (): CommentPanelState => {
  const state = useContext(CommentPanelContext);
  if (state === null) {
    throw new Error(
      "useCommentPanel must be used inside a CommentPanelProvider",
    );
  }
  return state;
};

/**
 * Tell the globally mounted panel what the page is about, so its comments and
 * the assistant both follow the user around. Pass null on pages with nothing to
 * comment on, or when the viewer may not comment.
 */
export const useCommentTarget = (target: CommentTarget | null) => {
  const { setTarget } = useCommentPanel();
  const type = target?.type ?? null;
  const id = target?.id ?? null;
  const dateobs = target && target.type === "gcn_event" ? target.dateobs : null;

  useEffect(() => {
    if (type === null || id === null) {
      setTarget(null);
      return undefined;
    }
    setTarget(
      type === "gcn_event"
        ? { type, id: id as number, dateobs: dateobs as string }
        : { type, id: id as string },
    );
    return () => setTarget(null);
  }, [setTarget, type, id, dateobs]);
};
