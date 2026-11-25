import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";

export interface FavoriteLocalization {
  id: number;
  dateobs: string;
  localization_name: string;
}

// Skymaps the user starred, kept in their preferences, most recent first.
export const useFavoriteLocalizations = () => {
  const { data: profile } = useGetProfileQuery();
  const [updatePreferences] = useUpdateUserPreferencesMutation();
  const favorites: FavoriteLocalization[] =
    profile?.preferences?.["favoriteLocalizations"] || [];

  const isFavorite = (id: number) => favorites.some((f) => f.id === id);

  const toggleFavorite = ({ id, dateobs, localization_name }: any) =>
    updatePreferences({
      favoriteLocalizations: isFavorite(id)
        ? favorites.filter((f) => f.id !== id)
        : [{ id, dateobs, localization_name }, ...favorites],
    });

  const removeFavorite = (id: number) =>
    updatePreferences({
      favoriteLocalizations: favorites.filter((f) => f.id !== id),
    });

  return { favorites, isFavorite, toggleFavorite, removeFavorite };
};
