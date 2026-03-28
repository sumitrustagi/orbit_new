"""Flask CLI commands for administration."""
import click
from flask.cli import AppGroup

from app.extensions import db
from app.models.user import User, UserRole

admin_cli = AppGroup("admin", help="Administrative commands.")


@admin_cli.command("create-admin")
@click.option("--username", required=True, help="Admin username")
@click.option("--email", required=True, help="Admin email")
@click.option("--password", required=True, help="Admin password")
def create_admin(username, email, password):
    """Create a platform admin user."""
    existing = User.query.filter_by(username=username).first()
    if existing:
        click.echo(f"User '{username}' already exists.")
        return

    admin = User(
        username=username,
        email=email,
        role=UserRole.PLATFORM_ADMIN,
        is_active=True,
        auth_method="local",
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Platform admin '{username}' created successfully.")


@admin_cli.command("list-users")
def list_users():
    """List all users."""
    users = User.query.filter(User.deleted_at.is_(None)).all()
    if not users:
        click.echo("No users found.")
        return
    click.echo(f"{'Username':<20} {'Email':<30} {'Role':<18} {'Active':<8} {'Last Login'}")
    click.echo("-" * 100)
    for u in users:
        last = u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "never"
        click.echo(f"{u.username:<20} {u.email:<30} {u.role.value:<18} {str(u.is_active):<8} {last}")


@admin_cli.command("reset-password")
@click.option("--username", required=True, help="Username")
@click.option("--password", required=True, help="New password")
def reset_password(username, password):
    """Reset a user's password."""
    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f"User '{username}' not found.")
        return
    user.set_password(password)
    db.session.commit()
    click.echo(f"Password reset for '{username}'.")


@admin_cli.command("seed-demo")
def seed_demo():
    """Seed demo data for testing."""
    from app.models.cucm import Phone, DevicePool, Partition, CallingSearchSpace, RoutePattern, Gateway, Trunk
    from app.models.unity import UnityMailbox, UnityUser
    from app.models.imp import IMPUser
    from app.models.expressway import Expressway, Zone

    # Phones
    phone_models = ["Cisco 8845", "Cisco 8861", "Cisco 7841", "Cisco 7861", "Cisco 8851"]
    for i in range(1, 11):
        name = f"SEP00112233{i:04d}"
        if not Phone.query.filter_by(name=name).first():
            phone = Phone(
                name=name, description=f"Demo Phone {i}",
                model=phone_models[i % len(phone_models)],
                protocol="SIP", status="Registered" if i % 3 != 0 else "Unregistered",
                device_pool="Default", directory_number=f"1{i:03d}",
                ip_address=f"10.1.1.{100 + i}",
                mac_address=f"00:11:22:33:{i:02d}:00",
            )
            db.session.add(phone)

    # Device Pools
    for name in ["Default", "HQ_DP", "Branch_DP", "Remote_DP", "Lab_DP"]:
        if not DevicePool.query.filter_by(name=name).first():
            db.session.add(DevicePool(name=name, description=f"{name} device pool", region="Default"))

    # Partitions
    for name in ["Internal_PT", "National_PT", "International_PT", "Emergency_PT", "Restricted_PT"]:
        if not Partition.query.filter_by(name=name).first():
            db.session.add(Partition(name=name, description=f"{name} partition"))

    # CSS
    for name in ["Internal_CSS", "National_CSS", "International_CSS", "Restricted_CSS"]:
        if not CallingSearchSpace.query.filter_by(name=name).first():
            db.session.add(CallingSearchSpace(name=name, description=f"{name}"))

    # Route Patterns
    for pattern in ["9.1XXXXXXXXXX", "9.011!", "9.911", "9.9011!", "\\+1[2-9]XXXXXXXXX"]:
        if not RoutePattern.query.filter_by(pattern=pattern).first():
            db.session.add(RoutePattern(pattern=pattern, description=f"Route {pattern}", partition="Internal_PT"))

    # Gateways
    for name in ["GW-HQ-01", "GW-Branch-01", "GW-Remote-01"]:
        if not Gateway.query.filter_by(name=name).first():
            db.session.add(Gateway(name=name, description=f"{name}", gateway_type="SIP", status="Active"))

    # Trunks
    for name in ["SIP-Trunk-ITSP", "SIP-Trunk-CUBe", "SIP-Trunk-Unity"]:
        if not Trunk.query.filter_by(name=name).first():
            db.session.add(Trunk(name=name, description=f"{name}", trunk_type="SIP", status="Active"))

    # Unity Mailboxes
    for i in range(1, 6):
        alias = f"user{i}"
        if not UnityMailbox.query.filter_by(alias=alias).first():
            db.session.add(UnityMailbox(
                alias=alias, display_name=f"Demo User {i}",
                extension=f"2{i:03d}", mailbox_type="User",
                is_vm_enabled=True, cos_name="Default",
            ))

    # Unity Users
    for i in range(1, 6):
        alias = f"unity_user{i}"
        if not UnityUser.query.filter_by(alias=alias).first():
            db.session.add(UnityUser(
                alias=alias, display_name=f"Unity User {i}",
                first_name=f"User", last_name=f"{i}",
                extension=f"2{i:03d}", is_vm_enrolled=True,
            ))

    # IMP Users
    for i in range(1, 6):
        uid = f"imp_user{i}"
        if not IMPUser.query.filter_by(user_id=uid).first():
            db.session.add(IMPUser(
                user_id=uid, display_name=f"IM&P User {i}",
                jabber_id=f"user{i}@domain.com",
                presence_status=["Available", "Away", "DND", "Offline"][i % 4],
                im_enabled=True,
            ))

    # Expressways
    for name, ntype in [("Expressway-C", "Core"), ("Expressway-E", "Edge")]:
        if not Expressway.query.filter_by(name=name).first():
            node = Expressway(
                name=name, host=f"{name.lower()}.domain.com",
                node_type=ntype, software_version="X14.2.1",
                status="Active", active_calls=5, max_calls=500,
                active_registrations=150, max_registrations=2500,
                mra_enabled=True, b2b_enabled=ntype == "Edge",
            )
            db.session.add(node)
            db.session.flush()
            # Zones for each
            for zname, ztype in [("DefaultZone", "Default"), ("TraversalZone", "Traversal Client"), ("CUCMZone", "CUCM")]:
                if not Zone.query.filter_by(name=f"{name}_{zname}").first():
                    db.session.add(Zone(
                        name=f"{name}_{zname}", zone_type=ztype,
                        status="Active", expressway_id=node.id,
                    ))

    db.session.commit()
    click.echo("Demo data seeded successfully.")
    click.echo("  - 10 phones, 5 device pools, 5 partitions, 4 CSS")
    click.echo("  - 5 route patterns, 3 gateways, 3 trunks")
    click.echo("  - 5 Unity mailboxes, 5 Unity users")
    click.echo("  - 5 IM&P users")
    click.echo("  - 2 Expressway nodes, 6 zones")
