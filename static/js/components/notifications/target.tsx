import { ReactNode, createContext, useContext, useMemo } from "react";

import {
  Profile,
  useGetProfileQuery,
  useGetUserProfileQuery,
  useUpdateBasicUserInfoMutation,
  useUpdateOtherUserPreferencesMutation,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";

// Whose settings the notification components read and write. Null is the
// logged-in user, which is every use outside the admin dialog.
const TargetUserContext = createContext<{
  userId: number;
  groupIds: number[];
} | null>(null);

export const NotificationTarget = ({
  userId,
  groups,
  children,
}: {
  userId: number;
  groups: any[];
  children: ReactNode;
}) => {
  useGetUserProfileQuery(userId, { refetchOnMountOrArgChange: true });
  const target = useMemo(
    () => ({ userId, groupIds: groups.map((group: any) => group.id) }),
    [userId, groups],
  );
  return (
    <TargetUserContext.Provider value={target}>
      {children}
    </TargetUserContext.Provider>
  );
};

export interface Target {
  profile: Profile | undefined;
  // Both return the mutation's promise, so callers can await `.unwrap()`.
  updateUserPreferences: (preferences: any) => any;
  updateBasicUserInfo: (formData: any) => any;
  isSelf: boolean;
  groupIds: number[] | null;
}

export const useNotificationTarget = (): Target => {
  const target = useContext(TargetUserContext);
  const userId = target?.userId ?? null;
  const isSelf = userId === null;
  const own = useGetProfileQuery(undefined, { skip: !isSelf });
  const other = useGetUserProfileQuery(userId ?? 0, { skip: isSelf });
  const [updateOwnPreferences] = useUpdateUserPreferencesMutation();
  const [updateOtherPreferences] = useUpdateOtherUserPreferencesMutation();
  const [updateBasicInfo] = useUpdateBasicUserInfoMutation();

  const profile = isSelf ? own.data : other.data;

  return {
    profile,
    updateUserPreferences: (preferences: any) =>
      isSelf
        ? updateOwnPreferences(preferences)
        : updateOtherPreferences({ user_id: userId, preferences }),
    updateBasicUserInfo: (formData: any) =>
      isSelf
        ? updateBasicInfo({ formData })
        : updateBasicInfo({ formData, user_id: userId }),
    isSelf,
    groupIds: profile?.permissions?.includes("System admin")
      ? null
      : (target?.groupIds ?? null),
  };
};
