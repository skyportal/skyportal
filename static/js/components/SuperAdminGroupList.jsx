import React from 'react';
import PropTypes from 'prop-types';
import { useSelector } from 'react-redux';

import GroupList from './GroupList';


const SuperAdminGroupList = ({ title }) => {
  const groups = useSelector((state) => state.groups.all);
  return <GroupList groups={groups} title={title} />;
};
SuperAdminGroupList.propTypes = {
  title: PropTypes.string
};
SuperAdminGroupList.defaultProps = {
  title: "All groups"
};

export default SuperAdminGroupList;
