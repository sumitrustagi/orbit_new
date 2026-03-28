"""User management forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Optional, EqualTo


class UserCreateForm(FlaskForm):
    username   = StringField("Username", validators=[DataRequired(), Length(min=2, max=80)])
    email      = StringField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    first_name = StringField("First Name", validators=[Optional(), Length(max=80)])
    last_name  = StringField("Last Name", validators=[Optional(), Length(max=80)])
    password   = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    role       = SelectField("Role", choices=[
        ("end_user", "End User"),
        ("gui_admin", "GUI Admin"),
        ("platform_admin", "Platform Admin"),
    ])
    is_active  = BooleanField("Active", default=True)
    notes      = TextAreaField("Notes", validators=[Optional()])
    submit     = SubmitField("Create User")


class UserEditForm(FlaskForm):
    email      = StringField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    first_name = StringField("First Name", validators=[Optional(), Length(max=80)])
    last_name  = StringField("Last Name", validators=[Optional(), Length(max=80)])
    role       = SelectField("Role", choices=[
        ("end_user", "End User"),
        ("gui_admin", "GUI Admin"),
        ("platform_admin", "Platform Admin"),
    ])
    is_active  = BooleanField("Active")
    notes      = TextAreaField("Notes", validators=[Optional()])
    submit     = SubmitField("Save Changes")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password     = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("new_password")])
    submit           = SubmitField("Change Password")
