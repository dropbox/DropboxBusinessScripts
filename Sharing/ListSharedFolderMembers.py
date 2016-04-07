# List shared folders + shared members as CSV format.
#
# Required permission:
#  * Dropbox Business, Team member file access
#
# Required library:
#  * Dropbox SDK Python https://github.com/dropbox/dropbox-sdk-python
#  * Tested on [Dropbox SDK Python v6.1](https://github.com/dropbox/dropbox-sdk-python/releases/tag/v6.1)


import sys
import argparse
from dropbox import Dropbox
from dropbox import DropboxTeam
from dropbox.sharing import GroupMembershipInfo
from dropbox.sharing import InviteeMembershipInfo
from dropbox.sharing import SharedFolderMetadata
from dropbox.sharing import SharedFolderMembers
from dropbox.sharing import UserMembershipInfo
from dropbox.team import TeamMemberInfo
from dropbox.team import MembersGetInfoItem
from dropbox.users import BasicAccount

reload(sys)
sys.setdefaultencoding('UTF8')


class Entity(object):
    """Base class for Entity"""

    def __init__(self, identity):
        self.__identity = identity

    def identity(self):
        return self.__identity

    def __hash__(self):
        return hash(self.__identity)

    def __eq__(self, other):
        return self.identity() == other.identity()


class Context(object):
    """Base class of Context"""


class EmptyContext(Context):
    """No context for query"""


class AsMemberContext(Context):
    """Query as member"""

    def __init__(self, dropbox_team, member):
        """
        :type dropbox_team: DropboxTeam
        :type member: Member
        """
        self.team = dropbox_team  # type: DropboxTeam
        self.member = member  # type: Member
        self.as_user = dropbox_team.as_user(self.member.identity())  # type: Dropbox

    def as_user(self):
        """
        :rtype: Dropbox
        """
        return self.as_user


class EntityNotFoundException(Exception):
    """Entity not found exception"""

    def __init__(self, identity):
        self.identity = identity


class Loader(object):
    """Base class for Loader (Bulk loading entities)"""

    def all_entities(self):
        """
        :rtype: list[Entity]
        """
        raise NotImplementedError


class CachedLoader(Loader):
    """Loader with cache"""

    def __init__(self, loader):
        """
        :type loader: Loader
        """
        self.loader = loader  # type: Loader
        self.cache = None  # type: list[Entity]

    def all_entities(self):
        if self.cache:
            return self.cache

        self.cache = self.loader.all_entities()
        return self.cache


class Resolver(object):
    """Base class for Repository"""

    def resolve(self, identity, context):
        """Resolve entity by identity
        :type identity: Identity
        :type context: Context
        :rtype: Entity
        """
        pass


class CachedResolver(Resolver):
    """Resolver with cache"""

    def __init__(self, resolver):
        """
        :type resolver: Resolver
        """
        self.__resolver = resolver
        self.__cache = {}

    def resolve(self, identity, context):
        if identity in self.__cache:
            e = self.__cache[identity]
            if e is None:
                raise EntityNotFoundException(identity)
            else:
                return e

        try:
            e = self.__resolver.resolve(identity, context)
            self.__cache[identity] = e
            return e
        except EntityNotFoundException as ex:
            self.__cache[identity] = None
            raise ex


class Member(Entity):
    def __init__(self, member_info):
        """
        :type member_info: TeamMemberInfo
        """
        super(Member, self).__init__(member_info.profile.team_member_id)
        self.member_info = member_info  # type: TeamMemberInfo

    def member_info(self):
        """
        :rtype: TeamMemberInfo
        """
        return self.member_info

    def email(self):
        """
        :rtype: str
        """
        return self.member_info.profile.email

    def status(self):
        """
        :rtype: str
        """
        if self.member_info.profile.status.is_active():
            return 'active'
        elif self.member_info.profile.status.is_invited():
            return 'invited'
        elif self.member_info.profile.status.is_suspended():
            return 'suspended'
        elif self.email().endswith('#'):
            return 'deleted'
        else:
            return 'unknown'


class MemberResolver(Resolver):
    def __init__(self, dropbox_team):
        """
        :type dropbox_team: DropboxTeam
        """
        self.team = dropbox_team  # type: DropboxTeam

    def resolve(self, identity, context):
        """
        :type identity: MemberId
        :rtype: Member
        """
        from dropbox.team import UserSelectorArg

        q = UserSelectorArg.email(identity)
        m = self.team.team_members_get_info([q])  # type: list[MembersGetInfoItem]
        if len(m) < 1:
            raise EntityNotFoundException(identity)
        elif m[0].is_member_info():
            return Member(m[0].get_member_info())
        else:
            raise EntityNotFoundException(identity)


class MemberLoader(Loader):
    def __init__(self, team):
        """
        :type team: DropboxTeam
        """
        self.team = team  # type: DropboxTeam

    def __load_team_members(self):
        """
        :rtype: list[TeamMemberInfo]
        """
        chunk = self.team.team_members_list()
        if chunk.has_more:
            more = self.__load_more_team_members(chunk.cursor)
            return chunk.members + more
        else:
            return chunk.members

    def __load_more_team_members(self, cursor):
        """
        :rtype: list[TeamMemberInfo]
        """
        chunk = self.team.team_members_list_continue(cursor)
        if chunk.has_more:
            more = self.__load_more_team_members(chunk.cursor)
            return chunk.members + more
        else:
            return chunk.members

    def all_entities(self):
        return [Member(m) for m in self.__load_team_members()]


class MemberResolverLoader(Resolver, Loader):
    def __init__(self, member_loader):
        """
        :type member_loader: Loader
        """
        self.member_loader = member_loader  # type: Loader

    def resolve(self, identity, context):
        members = self.member_loader.all_entities()  # type: list[Member]
        account_id_to_member = {m.identity(): m for m in members}

        if identity in account_id_to_member:
            return account_id_to_member[identity]
        else:
            raise EntityNotFoundException(identity)

    def resolve_by_email(self, email):
        """
        :type email: str
        :rtype: Member
        """
        members = self.member_loader.all_entities()  # type: list[Member]
        email_to_member = {m.email(): m for m in members}

        if email in email_to_member:
            return email_to_member[email]
        else:
            raise EntityNotFoundException(email)

    def all_entities(self):
        return self.member_loader.all_entities()


class SharedFolder(Entity):
    def __init__(self, shared_folder, context):
        """
        :type shared_folder: SharedFolderMetadata
        :type context: AsMemberContext
        """
        super(SharedFolder, self).__init__(shared_folder.shared_folder_id)
        self.shared_folder = shared_folder  # type: SharedFolderMetadata
        self.context = context  # type: AsMemberContext

    def members(self):
        """
        :rtype: SharedFolderMembers
        """
        return self.__load_shared_folder_members(self.shared_folder.shared_folder_id)

    def __load_shared_folder_members(self, shared_folder_id):
        chunk = self.context.as_user.sharing_list_folder_members(shared_folder_id)
        if chunk.cursor:
            more = self.__load_more_shared_folder_members(chunk.cursor)
            return self.__merge_shared_folder_members(chunk, more)
        else:
            return chunk

    def __load_more_shared_folder_members(self, cursor):
        chunk = self.context.as_user.sharing_list_folder_members_continue(cursor)
        if chunk.cursor:
            more = self.__load_more_shared_folder_members(chunk.cursor)
            return self.__merge_shared_folder_members(chunk, more)
        else:
            return chunk

    def __merge_shared_folder_members(self, a, b):
        def f(x):
            return [] if x is None else x

        def g(x, y):
            return f(x) + f(y)

        return SharedFolderMembers(
            users=g(a.users, b.users),
            groups=g(a.groups, b.groups),
            invitees=g(a.invitees, b.invitees),
            cursor=None
        )


class SharedFolderLoader(Loader):
    def __init__(self, context):
        """
        :type context: AsMemberContext
        """
        self.context = context  # type: AsMemberContext

    def __load_shared_folders(self):
        """
        :rtype: list[SharedFolderMetadata]
        """
        chunk = self.context.as_user.sharing_list_folders()
        if chunk.cursor:
            more = self.__load_more_shared_folders(chunk.cursor)
            return chunk.entries + more
        else:
            return chunk.entries

    def __load_more_shared_folders(self, cursor):
        """
        :type cursor: str
        :rtype: list[SharedFolderMetadata]
        """
        chunk = self.context.as_user.sharing_list_folders_continue(cursor)
        if chunk.cursor:
            more = self.__load_more_shared_folders(chunk.cursor)
            return chunk.entries + more
        else:
            return chunk.entries

    def all_entities(self):
        """
        :rtype: list[SharedFolder]
        """
        return [SharedFolder(sf, self.context) for sf in self.__load_shared_folders()]


class Account(Entity):
    def __init__(self, account):
        """
        :type account: BasicAccount
        """
        super(Account, self).__init__(account.account_id)
        self.account = account  # type: BasicAccount

    def status(self):
        if self.account.email.endswith('#'):
            return 'deleted'
        else:
            return ''


class AccountResolver(Resolver):
    def resolve(self, identity, context):
        """
        :type identity: str
        :type context: AsMemberContext
        :rtype: Account
        """
        a = context.as_user.users_get_account(identity)  # type: BasicAccount
        return Account(a)


class AuditRecord(object):
    def __init__(self,
                 shared_folder_id=None,
                 shared_folder_name=None,
                 access_level=None,
                 account_id=None,
                 account_status=None,
                 account_email=None,
                 is_same_team=None,
                 group_id=None,
                 group_name=None,
                 group_member_count=None,
                 group_type=None):
        def f(x):
            return u'' if x is None else x

        def e(x):
            return x.replace('"', '\\"') if isinstance(x, basestring) else ''

        self.shared_folder_id = shared_folder_id
        self.shared_folder_name = shared_folder_name
        self.access_level = access_level
        self.account_id = account_id
        self.account_status = account_status
        self.account_email = account_email
        self.is_same_team = is_same_team
        self.group_id = group_id
        self.group_name = group_name
        self.group_member_count = group_member_count
        self.group_type = group_type

        self.record = [
            (u"Shared folder ID", f(shared_folder_id)),
            (u"Shared folder name", f(e(shared_folder_name))),
            (u"Access level", self.__access_level(access_level)),
            (u"Account ID", f(account_id)),
            (u"Account email", f(account_email)),
            (u"Status", f(account_status)),
            (u"Same team", str(f(is_same_team))),
            (u"Group ID", f(group_id)),
            (u"Group name", f(e(group_name))),
            (u"Group member count", str(f(group_member_count))),
            (u"Group type", self.__group_type(group_type))
        ]
        self.output_record = {r[0]: r[1] for r in self.record}
        self.output_format = u','.join([(u'"{%s:s}"' % r[0]) for r in self.record])

    def header(self):
        return u','.join([u'"%s"' % r[0] for r in self.record])

    def format(self):
        return self.output_format.format(**self.output_record)

    def __access_level(self, access_level):
        """
        :type access_level: AccessLevel
        """
        if access_level is None:
            return u''
        elif access_level.is_editor():
            return u'editor'
        elif access_level.is_other():
            return u'other'
        elif access_level.is_owner():
            return u'owner'
        elif access_level.is_viewer():
            return u'viewer'
        else:
            return u''

    def __group_type(self, group_type):
        """
        :type group_type: GroupType
        """
        if group_type is None:
            return u''
        if group_type.is_team():
            return u'team'
        elif group_type.is_user_managed():
            return u'user_managed'
        elif group_type.is_other():
            return u'other'
        else:
            return u''


class Auditor(object):
    def __init__(self, team_token, outfile, external_user_only=False):
        self.outfile = outfile
        self.external_user_only = external_user_only  # type: bool
        self.dropbox_team = DropboxTeam(team_token)
        self.member_loader = CachedLoader(MemberLoader(self.dropbox_team))
        self.member_resolver_by_account_id = MemberResolverLoader(self.member_loader)
        self.member_resolver_by_email = CachedResolver(MemberResolver(self.dropbox_team))
        self.account_resolver = CachedResolver(AccountResolver())

    def report(self):
        self.__write_header()
        for sf in self.__shared_folders():
            self.__report_shared_folder(sf)

    def __report_shared_folder(self, shared_folder):
        """
        :type shared_folder: SharedFolder
        """
        members = shared_folder.members()
        for u in members.users:  # type: UserMembershipInfo
            self.__report_user(shared_folder, u)
        for i in members.invitees:  # type: InviteeMembershipInfo
            self.__report_invitee(shared_folder, i)
        for g in members.groups:  # type: GroupMembershipInfo
            self.__report_group(shared_folder, g)

    def __report_user(self, shared_folder, user):
        """
        :type shared_folder: SharedFolder
        :type user: UserMembershipInfo
        """
        if user.user.team_member_id:
            self.__report_member(shared_folder, user)
        else:
            self.__report_account(shared_folder, user)

    def __report_member(self, shared_folder, user):
        """
        :type shared_folder: SharedFolder
        :type user: UserMembershipInfo
        """
        member = self.member_resolver_by_account_id.resolve(user.user.team_member_id, EmptyContext())  # type: Member
        record = AuditRecord(shared_folder_id=shared_folder.identity(),
                             shared_folder_name=shared_folder.shared_folder.name,
                             access_level=user.access_type,
                             account_id=user.user.account_id,
                             account_email=member.email(),
                             account_status=member.status(),
                             is_same_team=user.user.same_team)
        self.__report_record(record)

    def __report_account(self, shared_folder, user):
        """
        :type shared_folder: SharedFolder
        :type user: UserMembershipInfo
        """
        account = self.account_resolver.resolve(user.user.account_id, shared_folder.context)  # type: Account
        record = AuditRecord(shared_folder_id=shared_folder.identity(),
                             shared_folder_name=shared_folder.shared_folder.name,
                             access_level=user.access_type,
                             account_id=user.user.account_id,
                             account_email=account.account.email,
                             account_status=account.status(),
                             is_same_team=user.user.same_team)
        self.__report_record(record)

    def __report_group(self, shared_folder, group):
        """
        :type shared_folder: SharedFolder
        :type group: GroupMembershipInfo
        """
        record = AuditRecord(shared_folder_id=shared_folder.identity(),
                             shared_folder_name=shared_folder.shared_folder.name,
                             access_level=group.access_type,
                             group_id=group.group.group_id,
                             group_name=group.group.group_name,
                             group_member_count=group.group.member_count,
                             group_type=group.group.group_type,
                             is_same_team=True)
        self.__report_record(record)

    def __write_header(self):
        self.outfile.write(AuditRecord().header())
        self.outfile.write('\n')

    def __write_record(self, record):
        """
        :type record: AuditRecord
        """
        self.outfile.write(record.format())
        self.outfile.write('\n')

    def __report_record(self, record):
        """
        :type record: AuditRecord
        """
        if self.external_user_only:
            if not record.is_same_team and record.account_status != 'deleted':
                self.__write_record(record)
        else:
            self.__write_record(record)

    def __find_member_by_email(self, email):
        """
        :type email: str
        :rtype: Member
        """
        try:
            member = self.member_resolver_by_account_id.resolve_by_email(email)
            return member
        except EntityNotFoundException:
            try:
                member = self.member_resolver_by_email.resolve(email, EmptyContext())
                return member
            except EntityNotFoundException as ex:
                raise ex

    def __report_invitee(self, shared_folder, invitee):
        """
        :type shared_folder: SharedFolder
        :type invitee: InviteeMembershipInfo
        """
        email = invitee.invitee.get_email()
        try:
            member = self.__find_member_by_email(email)
            record = AuditRecord(shared_folder_id=shared_folder.identity(),
                                 shared_folder_name=shared_folder.shared_folder.name,
                                 access_level=invitee.access_type,
                                 account_id=member.identity(),
                                 account_email=email,
                                 account_status=u'invited to folder',
                                 is_same_team=True)
            self.__report_record(record)

        except EntityNotFoundException:
            record = AuditRecord(shared_folder_id=shared_folder.identity(),
                                 shared_folder_name=shared_folder.shared_folder.name,
                                 access_level=invitee.access_type,
                                 account_email=email,
                                 account_status=u'invited to folder',
                                 is_same_team=False)
            self.__report_record(record)

    def __members(self):
        """
        :rtype: list[Member]
        """
        return self.member_loader.all_entities()

    def __shared_folders_for_member(self, member):
        """
        :type member: Member
        :rtype: list[SharedFolder]
        """
        return SharedFolderLoader(AsMemberContext(self.dropbox_team, member)).all_entities()

    def __shared_folders(self):
        members = self.__members()

        shared_folders_nested = [self.__shared_folders_for_member(m) for m in members]
        shared_folders_flatten = [sf for sublist in shared_folders_nested for sf in sublist]
        return set(shared_folders_flatten)  # remove duplicated


class AuditorCli(object):
    def test_token(self, token):
        team = DropboxTeam(token)
        try:
            team.team_get_info()
            return True
        except Exception:
            print "Please check your OAuth2 token"
            return False

    def get_token(self):
        while True:
            team_token = raw_input('Enter your Dropbox Business API App token (Team Member File Access permission): ')
            if self.test_token(team_token):
                return team_token

    def execute(self):
        parser = argparse.ArgumentParser(description=u'List all shared folders + shared members as CSV format.')
        parser.add_argument('-o', '--outfile', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
                            help=u'Output file')
        parser.add_argument('-e', '--external-only', action='store_true', help=u'List external user only')
        args = parser.parse_args()

        auditor = Auditor(self.get_token(), outfile=args.outfile, external_user_only=args.external_only)
        auditor.report()
        args.outfile.close()


AuditorCli().execute()
