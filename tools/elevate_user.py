import sys

from baselayer.app.config import load_config
from baselayer.app.models import init_db
from skyportal.model_util import make_super_user
from baselayer.app.models import User, Role
from sqlalchemy.orm import joinedload


try:
    username = sys.argv[1]
except IndexError:
    username = None

cfg = load_config()
init_db(**cfg['database'])


def list_users():
    users = (
        User.query.options(joinedload(User.roles))
        .filter(~User.roles.any(Role.id == 'Super admin'))
        .all()
    )

    if len(users) == 0:
        print('\nNo users left to elevate!')
        return False
    else:
        print('\nList of non-admin users: \n')
        for user in users:
            print(f'{user.id}. {user.username}')
        return True


def elevate_user(username=None):
    if username is not None:
        make_super_user(username)
        print(f'\nUser {username} elevated!')
    else:
        if list_users():
            username = input("\nEnter username to elevate (or hit ctrl-c to exit): ")
            make_super_user(username)
            print(f'\nUser {username} elevated!')
        else:
            print('\nExiting...')
            sys.exit()


def main():
    if username is not None:
        elevate_user(username)
    else:
        while True:
            try:
                elevate_user()
            except KeyboardInterrupt:
                print('\nExiting...')
                break


main()
