import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import Dropdown, { DropdownTrigger, DropdownContent } from 'react-simple-dropdown';

import styles from "./ProfileDropdown.css";
import Responsive from "./Responsive";


class ProfileDropdown extends Component {
  constructor(props) {
    super(props);
    this.collapse = this.collapse.bind(this);
  }

  collapse() {
    this.dropdown.hide();
  }

  render() {
    const dropdown = (el) => { this.dropdown = el; };
    return (
      <Responsive
        desktopStyle={styles.profileDesktop}
        mobileStyle={styles.profileMobile}
      >

        <Dropdown ref={dropdown}>

          <DropdownTrigger>
            { this.props.profile.username } &nbsp;▾
          </DropdownTrigger>

          <DropdownContent>

            <Link to="/profile">
              <div className={styles.entry} onClick={this.collapse}>
                Profile
              </div>
            </Link>

            <div className={styles.rule} />

            <div className={styles.entry} onClick={this.collapse}>
              Groups
            </div>

            <div className={styles.rule} />

            <a href="https://github.com/skyportal/skyportal/issues/new">
              <div className={styles.entry} onClick={this.collapse}>
                File an issue
              </div>
            </a>

            <a href="https://github.com/skyportal/skyportal">
              <div className={styles.entry} onClick={this.collapse}>
                Help
              </div>
            </a>

            <div className={styles.rule} />

            <a href="/logout">
              <div className={styles.entry} onClick={this.collapse}>
                Sign out
              </div>
            </a>

          </DropdownContent>

        </Dropdown>

      </Responsive>
    );
  }
}

ProfileDropdown.propTypes = {
  profile: PropTypes.object.isRequired
};

export default ProfileDropdown;
