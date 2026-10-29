import { ReactNode, createContext, useContext } from "react";

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
const TargetUserContext = createContext<number | null>(null);

export const NotificationTarget = ({
  userId,
  children,
}: {
  userId: number;
  children: ReactNode;
}) => (
  <TargetUserContext.Provider value={userId}>
    {children}
  </TargetUserContext.Provider>
);

export interface Target {
  profile: Profile | undefined;
  // Both return the mutation's promise, so callers can await `.unwrap()`.
  updateUserPreferences: (preferences: any) => any;
  updateBasicUserInfo: (formData: any) => any;
  isSelf: boolean;
}

export const useNotificationTarget = (): Target => {
  const userId = useContext(TargetUserContext);
  const isSelf = userId === null;
  const own = useGetProfileQuery(undefined, { skip: !isSelf });
  const other = useGetUserProfileQuery(userId ?? 0, { skip: isSelf });
  const [updateOwnPreferences] = useUpdateUserPreferencesMutation();
  const [updateOtherPreferences] = useUpdateOtherUserPreferencesMutation();
  const [updateBasicInfo] = useUpdateBasicUserInfoMutation();

  return {
    profile: isSelf ? own.data : other.data,
    updateUserPreferences: (preferences: any) =>
      isSelf
        ? updateOwnPreferences(preferences)
        : updateOtherPreferences({ user_id: userId, preferences }),
    updateBasicUserInfo: (formData: any) =>
      isSelf
        ? updateBasicInfo({ formData })
        : updateBasicInfo({ formData, user_id: userId }),
    isSelf,
  };
};
