import React, {createContext, useContext, useReducer, useState} from 'react';

export const GlobalContext = createContext();

export const GlobalContextProvider = ({reducer, initialState, children}) => {

    return <GlobalContext.Provider
        value={useReducer(reducer, initialState)}>
        {children}
    </GlobalContext.Provider>
}

export const useGlobalReducer = () => useContext(GlobalContext)
