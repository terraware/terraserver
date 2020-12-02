from main.app import db
from main.resources.resource_util import find_resource
from main.users.auth import create_user
from main.users.models import User, OrganizationUser


def create_admin_user(email_address, password):
    """Create a new system administrator user."""
    assert '.' in email_address and '@' in email_address
    user_id = create_user(email_address, '', password, 'System Admin', User.SYSTEM_ADMIN)
    org_user = OrganizationUser()  # add to system organization
    org_user.organization_id = find_resource('/system').id
    org_user.user_id = user_id
    org_user.is_admin = True
    db.session.add(org_user)
    db.session.commit()
