import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import Dropdown, { DropdownTrigger, DropdownContent } from 'react-simple-dropdown';

import styles from "./ProfileDropdown.css";
import Responsive from "./Responsive";


class ProfileDropdown extends Component {
  constructor(props) {
    super(props);
    this._collapse = this._collapse.bind(this);
  }

  _collapse() {
    this.dropdown.hide();
  }

  render() {
    return (
      <Responsive
        desktopStyle={styles.profileDesktop}
        mobileStyle={styles.profileMobile}
      >

        <Dropdown ref={(el) => { this.dropdown = el; }}>

          <DropdownTrigger>
            { this.props.profile.username } &nbsp;▾
          </DropdownTrigger>

          <DropdownContent>

            <Link to="/profile">
              <div className={styles.entry} onClick={this._collapse}>
                Profile
              </div>
            </Link>

            <div className={styles.rule} />

            <Link to="/groups">
              <div className={styles.entry} onClick={this._collapse}>
                Groups
              </div>
            </Link>

            <div className={styles.rule} />

            <a href="https://github.com/skyportal/skyportal/issues/new">
              <div className={styles.entry} onClick={this._collapse}>
                File an issue
              </div>
            </a>

            <a href="https://github.com/skyportal/skyportal">
              <div className={styles.entry} onClick={this._collapse}>
                Help
              </div>
            </a>

            <div className={styles.rule} />

            <a href="/logout">
              <div className={styles.entry} onClick={this._collapse}>
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
