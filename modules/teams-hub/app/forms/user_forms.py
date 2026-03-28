"""User management forms."""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SelectField,
    BooleanField, TextAreaField, SubmitField,
)
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo


class CreateUserForm(FlaskForm):
    username   = StringField("Username", validators=[DataRequired(), Length(min=2, max=64)])
    email      = StringField("Email",    validators=[DataRequired(), Email(), Length(max=255)])
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=64)])
    last_name  = StringField("Last Name",  validators=[DataRequired(), Length(max=64)])
    password   = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm    = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    role       = SelectField("Role", choices=[
        ("gui_admin",      "GUI Admin"),
        ("platform_admin", "Platform Admin"),
        ("end_user",       "End User"),
    ], default="gui_admin")
    is_active  = BooleanField("Active", default=True)
    notes      = TextAreaField("Notes", validators=[Optional(), Length(max=2000)])
    submit     = SubmitField("Create User")


class EditUserForm(FlaskForm):
    email      = StringField("Email",    validators=[DataRequired(), Email(), Length(max=255)])
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=64)])
    last_name  = StringField("Last Name",  validators=[DataRequired(), Length(max=64)])
    role       = SelectField("Role", choices=[
        ("gui_admin",      "GUI Admin"),
        ("platform_admin", "Platform Admin"),
        ("end_user",       "End User"),
    ])
    is_active  = BooleanField("Active")
    notes      = TextAreaField("Notes", validators=[Optional(), Length(max=2000)])
    submit     = SubmitField("Save Changes")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password     = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm          = PasswordField(
        "Confirm",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")],
    )
    submit = SubmitField("Change Password")
