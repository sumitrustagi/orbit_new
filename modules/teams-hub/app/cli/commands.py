"""
Flask CLI commands for administrative operations.

Usage:
    flask admin create-admin --username admin --email admin@example.com --password Secret123!
    flask admin list-users
    flask admin reset-password --username admin --password NewPass123!
    flask admin seed-demo
"""
import click
from flask import current_app
from flask.cli import AppGroup

from app.extensions import db
from app.models.user import User, UserRole
from app.models.app_config import AppConfig

admin_cli = AppGroup("admin", help="Administrative commands.")


@admin_cli.command("create-admin")
@click.option("--username", required=True, help="Admin username")
@click.option("--email",    required=True, help="Admin email")
@click.option("--password", required=True, help="Admin password (min 8 chars)")
def create_admin(username: str, email: str, password: str):
    """Create a platform-admin user."""
    if len(password) < 8:
        click.echo("Error: Password must be at least 8 characters.", err=True)
        raise SystemExit(1)

    if User.query.filter_by(username=username).first():
        click.echo(f"Error: User '{username}' already exists.", err=True)
        raise SystemExit(1)

    user = User(
        username=username,
        email=email,
        first_name="Admin",
        last_name="User",
        role=UserRole.PLATFORM_ADMIN,
        is_active=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Created platform-admin: {username} ({email})")


@admin_cli.command("list-users")
def list_users():
    """List all users."""
    users = User.query.order_by(User.id.asc()).all()
    if not users:
        click.echo("No users found.")
        return
    click.echo(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Role':<16} {'Active'}")
    click.echo("-" * 80)
    for u in users:
        click.echo(
            f"{u.id:<5} {u.username:<20} {u.email:<30} "
            f"{u.role.value:<16} {'Yes' if u.is_active else 'No'}"
        )


@admin_cli.command("reset-password")
@click.option("--username", required=True, help="Username")
@click.option("--password", required=True, help="New password (min 8 chars)")
def reset_password(username: str, password: str):
    """Reset a user's password."""
    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f"Error: User '{username}' not found.", err=True)
        raise SystemExit(1)
    if len(password) < 8:
        click.echo("Error: Password must be at least 8 characters.", err=True)
        raise SystemExit(1)

    user.set_password(password)
    user.must_change_password = True
    db.session.commit()
    click.echo(f"Password reset for '{username}'. User will be prompted to change on next login.")


@admin_cli.command("seed-demo")
def seed_demo():
    """Seed the database with demo data for testing."""
    from app.models.team import Team, Channel
    from app.models.meeting import Meeting
    from app.models.call_queue import CallQueue, AutoAttendant

    # Create demo admin if none exists
    if User.query.count() == 0:
        admin = User(
            username="admin",
            email="admin@teamshub.local",
            first_name="Admin",
            last_name="User",
            role=UserRole.PLATFORM_ADMIN,
            is_active=True,
        )
        admin.set_password("Admin123!")
        db.session.add(admin)

    # Create demo teams
    demo_teams = [
        ("Engineering", "Engineering team", "private"),
        ("Marketing", "Marketing team", "public"),
        ("Sales", "Sales team", "private"),
        ("HR", "Human Resources", "private"),
        ("Support", "Customer Support", "public"),
    ]
    for name, desc, vis in demo_teams:
        if not Team.query.filter_by(display_name=name).first():
            team = Team(
                ms_team_id=f"demo-team-{name.lower()}",
                display_name=name,
                description=desc,
                visibility=vis,
                member_count=10,
                owner_count=2,
            )
            db.session.add(team)

    # Create demo channels
    eng_team = Team.query.filter_by(display_name="Engineering").first()
    if eng_team:
        channels = ["General", "Backend", "Frontend", "DevOps", "Code Review"]
        for ch_name in channels:
            if not Channel.query.filter_by(display_name=ch_name, team_id=eng_team.id).first():
                channel = Channel(
                    ms_channel_id=f"demo-ch-{ch_name.lower()}",
                    team_id=eng_team.id,
                    display_name=ch_name,
                    is_general=(ch_name == "General"),
                )
                db.session.add(channel)

    # Create demo call queues
    if CallQueue.query.count() == 0:
        for name in ["Main Support", "Sales Inquiries", "Technical Support"]:
            cq = CallQueue(
                ms_queue_id=f"demo-cq-{name.lower().replace(' ', '-')}",
                display_name=name,
                routing_method="round_robin",
                agent_count=5,
            )
            db.session.add(cq)

    # Create demo auto attendants
    if AutoAttendant.query.count() == 0:
        for name in ["Main Line", "After Hours"]:
            aa = AutoAttendant(
                ms_attendant_id=f"demo-aa-{name.lower().replace(' ', '-')}",
                display_name=name,
                greeting_text=f"Welcome to {name}.",
            )
            db.session.add(aa)

    db.session.commit()

    AppConfig.set("APP_NAME", "Teams Hub", description="Application display name")
    AppConfig.set("PRIMARY_COLOR", "#1E40AF", description="Primary brand color")
    AppConfig.set("ACCENT_COLOR", "#3B82F6", description="Accent brand color")

    click.echo("Demo data seeded successfully.")
    click.echo("  Admin user: admin / Admin123!")
    click.echo("  5 teams, 5 channels, 3 call queues, 2 auto attendants")
