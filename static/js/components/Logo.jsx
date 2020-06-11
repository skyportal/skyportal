import React from 'react';
import { useSelector } from 'react-redux';
import styled, { keyframes } from 'styled-components';


const rotate = keyframes`
  0% {
    transform: rotate(60deg);
  }
  50% {
    transform: rotate(-10deg);
  }
  100% {
    transform: rotate(0deg);
  }
`;

const StyledLogo = styled.img`
  vertical-align: middle;
  height: 50px;
  margin-top: -0.5em;
  animation-name: ${props => props.rotate ? rotate : null};
  animation-duration: ${props => props.rotate ? '4s' : null};
`;

const Logo = () => {
  const rotateLogo = useSelector(state => state.logo.rotateLogo);
  return (
    <StyledLogo
      alt="SkyPortal logo"
      rotate={rotateLogo}
      src="/static/images/skyportal_logo_dark.png"
    />
  );
};

export default Logo;
