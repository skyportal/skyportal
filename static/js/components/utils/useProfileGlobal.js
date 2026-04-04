import { useState, useEffect } from 'react';
import { mockProfiles } from './mockProfiles';

let currentProfile = localStorage.getItem('anomaly_hunter_profile') || 'sn_hunter';
const listeners = new Set();

export const setGlobalProfile = (profileKey) => {
  currentProfile = profileKey;
  localStorage.setItem('anomaly_hunter_profile', profileKey);
  listeners.forEach(listener => listener(profileKey));
};

export const useProfileGlobal = () => {
  const [profile, setProfile] = useState(currentProfile);

  useEffect(() => {
    const listener = (newProfile) => {
      setProfile(newProfile);
    };
    listeners.add(listener);
    return () => listeners.delete(listener);
  }, []);

  const getProfileData = () => mockProfiles.find(p => p.key === profile) || mockProfiles[0];

  return {
    profileKey: profile,
    profileData: getProfileData(),
    setProfile: setGlobalProfile,
    allProfiles: mockProfiles
  };
};
