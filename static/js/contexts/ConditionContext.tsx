import React, { createContext } from "react";

const ConditionContext = createContext<any>(undefined);

interface ConditionProviderProps {
  children: React.ReactNode;
  customVariables: any[];
  customListVariables: any[];
  customSwitchCases: any[];
  fieldOptionsList: any[];
  isListDialogOpen: boolean;
  setListConditionDialog: (...a: any[]) => void;
}

export const ConditionProvider = ({
  children,
  customVariables,
  customListVariables,
  customSwitchCases,
  fieldOptionsList,
  isListDialogOpen,
  setListConditionDialog,
}: ConditionProviderProps) => {
  const value = {
    customVariables,
    customListVariables,
    customSwitchCases,
    fieldOptionsList,
    isListDialogOpen,
    setListConditionDialog,
  };

  return (
    <ConditionContext.Provider value={value}>
      {children}
    </ConditionContext.Provider>
  );
};

// Export the context for the hook
export { ConditionContext };
