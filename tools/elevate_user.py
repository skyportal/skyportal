import argparse
from baselayer.app.env import load_env
from baselayer.app.models import init_db
from skyportal.model_util import add_user, setup_permissions, role_acls
from baselayer.app.models import User
from baselayer.app.models import DBSession
import sqlalchemy as sa

env, cfg = load_env()
init_db(**cfg['database'])

parser = argparse.ArgumentParser(
    description='Elevate user to super admin', add_help=False
)
parser.add_argument('--username', help='User to set role for')
parser.add_argument('--list', action='store_true', help='List all users')
parser.add_argument('--role', help='Role to elevate user to')

args = parser.parse_args(namespace=env)

BOLD = '\033[1m'
END = '\033[0m'
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'


def get_users(role=None):
    return [user[0] for user in DBSession().execute(sa.select(User))]


def roles_user_has(user):
    return [role.id for role in user.roles]


def roles_user_does_not_have(user):
    return [role for role in role_acls if role not in roles_user_has(user)]


def list_users():
    users = get_users()
    if len(users) == 0:
        print('\nNo users in database')
    else:
        # print each user's username and roles
        print(f'\n{BOLD}List of users and current roles:{END}')
        for i, user in enumerate(users):
            list_of_new_roles = (
                BOLD
                + GREEN
                + f'{END}, {BOLD}{GREEN}'.join(roles_user_does_not_have(user))
                + END
            )
            if len(user.roles) == 0:
                print(
                    f'\n{BOLD}{YELLOW}{user.username}{END} (no roles) can be elevated to {list_of_new_roles}'
                )
            else:
                list_of_roles = (
                    BOLD + RED + f'{END}, {BOLD}{RED}'.join(roles_user_has(user)) + END
                )
                print(
                    f'\n{BOLD}{i+1}. {YELLOW}{user.username}{END} has the following roles: {list_of_roles} and can be elevated to: {list_of_new_roles}'
                )
        print('\n')


def elevate_user(username=None, role=None):
    if not role:
        print(
            f'{BOLD}{RED}\nNo role given!{END} User will be elevated to {BOLD}{GREEN}Super admin{END}{BOLD} by default{END}.'
        )
        role = 'Super admin'
    if role not in role_acls:
        print(f'{BOLD}{RED}\nRole not found!{END} Try a role from the list below:\n')
        for i, role in enumerate(role_acls):
            print(f'{BOLD}{i+1}. {GREEN}{role}{END}')
        print('\n')

    elif username is not None:
        users = get_users()
        if username in [user.username for user in users]:
            if role not in [
                role.id
                for role in [
                    user.roles[0] for user in users if user.username == username
                ]
            ]:
                setup_permissions()
                add_user(username, roles=[role], auth=True)
                print(
                    f'\n{BOLD}{YELLOW}User {username}{END} successfully elevated to role: {BOLD}{GREEN}{role}{END}!\n'
                )
            else:
                print(
                    f'\nUser {BOLD}{YELLOW}{username}{END} {BOLD}{GREEN}already has this role{END}\n'
                )

        else:
            print(f'\n{BOLD}{RED}User does not exist{END}!\n')


def main():
    if args.list:
        list_users()
    elif args.username:
        elevate_user(args.username, args.role)
    else:
        print(
            f'\n{BOLD}{RED}No arguments given{END}! Displaying {BOLD}{GREEN}Help{END}:\n'
        )
        parser.print_help()


main()
